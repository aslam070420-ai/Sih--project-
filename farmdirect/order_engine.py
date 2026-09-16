"""Shared FarmDirect order engine.

Used by both web checkout/API and IVR so inventory, fees, payments and
delivery creation follow one source of truth.
"""
from __future__ import annotations

import db

def place_order(buyer_id, items, address, city, pincode, pay_method="UPI"):
    """Shared order engine. items = [(product_id, qty_kg)]. Returns (order_id, error)."""
    if not items:
        return None, "Cart is empty."
    buyer = db.query("SELECT * FROM users WHERE id=?", (buyer_id,), one=True)
    subtotal, lines, fshare_by_farmer = 0.0, [], {}
    for pid, qty in items:
        p = db.query("SELECT * FROM products WHERE id=? AND status='active'", (pid,), one=True)
        if not p:
            return None, "A product in your cart is no longer available."
        qty = min(qty, p["quantity_kg"])
        if qty <= 0:
            return None, f"Insufficient stock for {p['name']}."
        sub = round(p["price_per_kg"] * qty, 2)
        subtotal += sub
        lines.append((p, qty, sub))
        fshare_by_farmer[p["seller_id"]] = fshare_by_farmer.get(p["seller_id"], 0) + sub
    total_qty = sum(q for _, q, _ in lines)
    buyer_type = "bulk" if (buyer["role"] == "buyer" or total_qty >= 500) else "consumer"
    fee = round(subtotal * 0.06, 2)
    dfee = 25 if buyer_type == "consumer" else round(subtotal * 0.015, 2)
    total = round(subtotal + fee + dfee, 2)

    from datetime import datetime
    code = "FD-" + datetime.now().strftime("%y%m%d") + "-" + f"{buyer_id}{int(datetime.now().timestamp()) % 10000:04d}"
    lat, lng = buyer["lat"], buyer["lng"]
    oid = db.execute(
        "INSERT INTO orders (order_code,buyer_id,buyer_type,total_amount,platform_fee,delivery_fee,"
        "delivery_address,delivery_city,delivery_pincode,delivery_lat,delivery_lng,order_type,status) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pending')",
        (code, buyer_id, buyer_type, total, fee, dfee, address or buyer["city"],
         city or buyer["city"], pincode or "422005", lat, lng, buyer_type))
    for p, qty, sub in lines:
        db.execute("INSERT INTO order_items (order_id,product_id,farmer_id,crop,grade,quantity_kg,"
                   "unit_price,subtotal,item_status) VALUES (?,?,?,?,?,?,?,?,'pending')",
                   (oid, p["id"], p["seller_id"], p["crop"], p["grade"], qty,
                    p["price_per_kg"], sub))
        remaining = p["quantity_kg"] - qty
        db.execute("UPDATE products SET quantity_kg=?, status=? WHERE id=?",
                   (remaining, "active" if remaining > 0 else "sold_out", p["id"]))
    db.execute("INSERT INTO payments (order_id,buyer_id,amount,farmer_share,platform_fee,delivery_fee,"
               "method,status,txn_code) VALUES (?,?,?,?,?,?,?,?,?)",
               (oid, buyer_id, total, round(sum(fshare_by_farmer.values()), 2), fee, dfee,
                pay_method, "completed" if pay_method != "Cash on Delivery" else "pending",
                f"TXN{int(datetime.now().timestamp()) % 1000000}"))
    # Create the delivery record (pending pickup at first farmer / hub)
    first_farmer = db.query("SELECT u.lat,u.lng,u.city FROM order_items oi JOIN users u "
                            "ON u.id=oi.farmer_id WHERE oi.order_id=? LIMIT 1", (oid,), one=True)
    if first_farmer:
        dist = round(42.0, 1)
        db.execute(
            "INSERT INTO deliveries (order_id,pickup_name,pickup_lat,pickup_lng,drop_name,drop_lat,"
            "drop_lng,distance_km,eta_minutes,driver_name,driver_phone,vehicle,status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pending')",
            (oid, f"Farm pickup — {first_farmer['city']}", first_farmer["lat"], first_farmer["lng"],
             address or buyer["city"], lat, lng, dist, int(dist / 26 * 60 + 15),
             "Unassigned", "", ""))
    return oid, None

