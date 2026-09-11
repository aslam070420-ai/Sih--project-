"""REST API endpoints (JSON) consumed by the frontend via fetch().

Covers: products, cart, orders, farmer actions, quotations, AI endpoints
(forecast / pricing / route optimization), logistics updates, admin stats.
"""
import os

from flask import Blueprint, g, jsonify, request, session

import db
from ai.forecasting import forecast_crop
from ai.pricing import recommend_price
from ai.routing import optimize_from_db
from auth import login_required, role_required

bp = Blueprint("api", __name__)


# ------------------------------------------------------------------ Products
@bp.get("/products")
def list_products():
    sql = ("SELECT p.id,p.name,p.crop,p.grade,p.quantity_kg,p.price_per_kg,p.organic, "
           "u.name AS seller,u.city,u.role AS seller_role FROM products p "
           "JOIN users u ON u.id=p.seller_id WHERE p.status='active'")
    args = []
    if request.args.get("q"):
        sql += " AND (p.name LIKE ? OR p.crop LIKE ?)"
        args += [f"%{request.args['q']}%"] * 2
    if request.args.get("crop"):
        sql += " AND p.crop=?"
        args.append(request.args["crop"])
    if request.args.get("min_qty"):
        sql += " AND p.quantity_kg>=?"
        args.append(float(request.args["min_qty"]))
    rows = db.query(sql, args)
    return jsonify([dict(r) for r in rows])


@bp.get("/products/<int:pid>")
def get_product(pid):
    row = db.query("SELECT p.*, u.name AS seller FROM products p JOIN users u ON u.id=p.seller_id "
                   "WHERE p.id=?", (pid,), one=True)
    return (jsonify(dict(row)) if row else (jsonify({"error": "not found"}), 404))


# ------------------------------------------------------------------ Cart
@bp.post("/cart/add")
@login_required
def cart_add():
    data = request.get_json(silent=True) or request.form
    pid = int(data.get("product_id", 0))
    qty = float(data.get("quantity_kg", 1))
    product = db.query("SELECT * FROM products WHERE id=? AND status='active'", (pid,), one=True)
    if not product:
        return jsonify({"ok": False, "error": "Product unavailable"}), 400
    qty = max(0.5, min(qty, product["quantity_kg"]))
    existing = db.query("SELECT * FROM cart_items WHERE user_id=? AND product_id=?",
                        (g.user["id"], pid), one=True)
    if existing:
        new_qty = min(existing["quantity_kg"] + qty, product["quantity_kg"])
        db.execute("UPDATE cart_items SET quantity_kg=? WHERE id=?", (new_qty, existing["id"]))
    else:
        db.execute("INSERT INTO cart_items (user_id,product_id,quantity_kg) VALUES (?,?,?)",
                   (g.user["id"], pid, qty))
    n = db.query("SELECT COUNT(*) n FROM cart_items WHERE user_id=?", (g.user["id"],), one=True)["n"]
    return jsonify({"ok": True, "cart_items": n, "message": f"{product['name']} added to cart"})


@bp.post("/cart/update")
@login_required
def cart_update():
    data = request.get_json(silent=True) or request.form
    cid = int(data.get("cart_id", 0))
    qty = float(data.get("quantity_kg", 1))
    item = db.query("SELECT c.*, p.quantity_kg AS available FROM cart_items c "
                    "JOIN products p ON p.id=c.product_id WHERE c.id=? AND c.user_id=?",
                    (cid, g.user["id"]), one=True)
    if not item:
        return jsonify({"ok": False, "error": "Item not in cart"}), 404
    qty = max(0.5, min(qty, item["available"]))
    db.execute("UPDATE cart_items SET quantity_kg=? WHERE id=?", (qty, cid))
    return jsonify({"ok": True, "quantity_kg": qty})


@bp.post("/cart/remove")
@login_required
def cart_remove():
    data = request.get_json(silent=True) or request.form
    cid = int(data.get("cart_id", 0))
    db.execute("DELETE FROM cart_items WHERE id=? AND user_id=?", (cid, g.user["id"]))
    return jsonify({"ok": True})


@bp.get("/cart")
@login_required
def cart_get():
    rows = db.query(
        "SELECT c.id, c.quantity_kg, p.name, p.price_per_kg, p.crop, p.grade "
        "FROM cart_items c JOIN products p ON p.id=c.product_id WHERE c.user_id=?",
        (g.user["id"],))
    return jsonify([dict(r) for r in rows])


# ------------------------------------------------------------------ Orders
from order_engine import place_order


@bp.post("/orders")
@login_required
def create_order():
    data = request.get_json(silent=True) or request.form
    items = [(int(i["product_id"]), float(i["quantity_kg"]))
             for i in (data.get("items") or [])]
    oid, err = place_order(g.user["id"], items,
                           data.get("address", ""), data.get("city", ""),
                           data.get("pincode", ""), data.get("pay_method", "UPI"))
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, "order_id": oid})


@bp.get("/orders")
@login_required
def list_orders():
    rows = db.query("SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC", (g.user["id"],))
    return jsonify([dict(r) for r in rows])


@bp.post("/orders/<int:oid>/item/<int:iid>/status")
@role_required("farmer", "fpo", "admin")
def farmer_item_status(oid, iid):
    """Farmer accepts / rejects their line item."""
    data = request.get_json(silent=True) or request.form
    action = data.get("action")  # accept | reject
    item = db.query("SELECT * FROM order_items WHERE id=? AND order_id=? AND farmer_id=?",
                    (iid, oid, g.user["id"]), one=True)
    if not item:
        return jsonify({"ok": False, "error": "Order item not found"}), 404
    if action not in ("accept", "reject"):
        return jsonify({"ok": False, "error": "Invalid action"}), 400

    new_status = "accepted" if action == "accept" else "rejected"
    db.execute("UPDATE order_items SET item_status=? WHERE id=?", (new_status, iid))
    if action == "reject":
        # restore stock
        db.execute("UPDATE products SET quantity_kg=quantity_kg+? WHERE id=?",
                   (item["quantity_kg"], item["product_id"]))
        db.execute("UPDATE orders SET status='rejected' WHERE id=?", (oid,))
    else:
        # if all items accepted → confirm order & schedule delivery
        pending = db.query("SELECT COUNT(*) n FROM order_items WHERE order_id=? AND item_status='pending'",
                           (oid,), one=True)["n"]
        rejected = db.query("SELECT COUNT(*) n FROM order_items WHERE order_id=? AND item_status='rejected'",
                            (oid,), one=True)["n"]
        if pending == 0 and rejected == 0:
            db.execute("UPDATE orders SET status='confirmed', updated_at=datetime('now','localtime') "
                       "WHERE id=?", (oid,))
            db.execute("UPDATE deliveries SET status='confirmed', "
                       "driver_name=COALESCE(NULLIF(driver_name,'Unassigned'),'Ramesh Pawar'), "
                       "driver_phone=COALESCE(NULLIF(driver_phone,''),'9822011223'), "
                       "vehicle=COALESCE(NULLIF(vehicle,''),'MH15-AB-1234') WHERE order_id=?", (oid,))
    return jsonify({"ok": True, "item_status": new_status})


@bp.post("/deliveries/<int:did>/status")
@role_required("admin")
def delivery_status(did):
    """Logistics pipeline: pending → confirmed → picked_up → in_transit → delivered."""
    data = request.get_json(silent=True) or request.form
    nxt = data.get("status")
    allowed = ["pending", "confirmed", "picked_up", "in_transit", "delivered"]
    if nxt not in allowed:
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    d = db.query("SELECT * FROM deliveries WHERE id=?", (did,), one=True)
    if not d:
        return jsonify({"ok": False, "error": "Delivery not found"}), 404
    if allowed.index(nxt) != allowed.index(d["status"]) + 1 and not (d["status"] == "pending" and nxt == "confirmed"):
        return jsonify({"ok": False, "error": f"Cannot skip from {d['status']} to {nxt}"}), 400
    db.execute("UPDATE deliveries SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
               (nxt, did))
    order_status = {"confirmed": "confirmed", "picked_up": "picked_up",
                    "in_transit": "in_transit", "delivered": "delivered"}.get(nxt)
    if order_status:
        db.execute("UPDATE orders SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
                   (order_status, d["order_id"]))
        if nxt == "picked_up":
            db.execute("UPDATE payments SET status='completed' WHERE order_id=?", (d["order_id"],))
    return jsonify({"ok": True, "status": nxt})


# ------------------------------------------------------------------ AI endpoints
@bp.get("/ai/forecast")
def ai_forecast():
    crop = request.args.get("crop", "Tomato")
    horizon = request.args.get("horizon", "7")
    horizon = int(horizon) if horizon in ("7", "30") else 7
    return jsonify(forecast_crop(crop, None, horizon))


@bp.get("/ai/price")
def ai_price():
    crop = request.args.get("crop", "Tomato")
    grade = request.args.get("grade", "B")
    try:
        qty = float(request.args.get("qty", 500))
    except ValueError:
        qty = 500.0
    rec = recommend_price(crop, grade, qty, request.args.get("city"),
                          state=request.args.get("state") or None)
    return jsonify(rec)


@bp.get("/logistics/optimize")
@role_required("admin")
def logistics_optimize():
    return jsonify(optimize_from_db())

# ------------------------------------------------------------------ Official mandi market data
@bp.get("/market/price")
def market_price():
    """Latest verified AGMARKNET mandi reference, with optional refresh."""
    import market_sync
    crop = (request.args.get("crop") or "Tomato").strip()
    state = (request.args.get("state") or "").strip() or None
    refresh = request.args.get("refresh", "0") in ("1", "true", "yes")
    sync = None
    if refresh:
        sync = market_sync.sync_crop(crop, state=state, force=True, limit=200)
    reference = market_sync.get_reference_price(crop, state)
    return jsonify({
        "ok": bool(reference),
        "crop": crop,
        "state": state,
        "reference": reference,
        "sync": sync,
        "source_status": market_sync.status_summary(),
    })


@bp.get("/market/status")
def market_status():
    import market_sync
    return jsonify(market_sync.status_summary())


# ------------------------------------------------------------------ Quotations (bulk)
@bp.post("/quotes")
@role_required("buyer")
def create_quote():
    data = request.get_json(silent=True) or request.form
    crop = data.get("crop", "Onion")
    try:
        qty = float(data.get("quantity_kg", 1000))
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid quantity"}), 400
    grade = data.get("grade", "A")
    city = data.get("city", "Mumbai")
    qid = db.execute("INSERT INTO quotes (buyer_id,crop,quantity_kg,grade,city) VALUES (?,?,?,?,?)",
                     (g.user["id"], crop, qty, grade, city))
    # Auto-generate responses from matching sellers (simulated negotiation)
    sellers = db.query(
        "SELECT p.*, u.city, u.name FROM products p JOIN users u ON u.id=p.seller_id "
        "WHERE p.crop=? AND p.status='active' AND p.quantity_kg>=? ORDER BY p.grade LIMIT 5",
        (crop, min(qty, 500)))
    seen = set()
    for s in sellers:
        if s["seller_id"] in seen:
            continue
        seen.add(s["seller_id"])
        rec = recommend_price(crop, s["grade"], qty, s["city"])
        price = round(rec["suggested_price"] * (0.95 if qty >= 1000 else 0.98), 1)
        eta = 2 if s["city"] == city else (3 if (s["city"] in ("Pune", "Nashik")) else 4)
        db.execute("INSERT INTO quote_responses (quote_id,seller_id,price_per_kg,total_amount,eta_days) "
                   "VALUES (?,?,?,?,?)", (qid, s["seller_id"], price, round(price * qty, 0), eta))
    return jsonify({"ok": True, "quote_id": qid})


@bp.post("/quotes/<int:qid>/accept/<int:rid>")
@role_required("buyer")
def accept_quote(qid, rid):
    q = db.query("SELECT * FROM quotes WHERE id=? AND buyer_id=?", (qid, g.user["id"]), one=True)
    resp = db.query("SELECT * FROM quote_responses WHERE id=? AND quote_id=?", (rid, qid), one=True)
    if not q or not resp:
        return jsonify({"ok": False, "error": "Quote not found"}), 404
    product = db.query("SELECT id FROM products WHERE seller_id=? AND crop=? AND status='active' "
                       "ORDER BY id LIMIT 1", (resp["seller_id"], q["crop"]), one=True)
    if not product:
        return jsonify({"ok": False, "error": "Seller listing unavailable"}), 400
    oid, err = place_order(g.user["id"], [(product["id"], min(q["quantity_kg"], 20000))],
                           f"{g.user['city']} — bulk dock", g.user["city"], "", "Bank Transfer")
    if err:
        return jsonify({"ok": False, "error": err}), 400
    db.execute("UPDATE quote_responses SET status='accepted' WHERE id=?", (rid,))
    db.execute("UPDATE quote_responses SET status='declined' WHERE quote_id=? AND id<>?", (qid, rid))
    db.execute("UPDATE quotes SET status='converted' WHERE id=?", (qid,))
    return jsonify({"ok": True, "order_id": oid})


# ------------------------------------------------------------------ Admin
@bp.get("/admin/stats")
@role_required("admin")
def admin_stats():
    kpi = {
        "users": db.query("SELECT COUNT(*) n FROM users", one=True)["n"],
        "orders": db.query("SELECT COUNT(*) n FROM orders", one=True)["n"],
        "gmv": db.query("SELECT COALESCE(SUM(total_amount),0) v FROM orders", one=True)["v"],
        "active": db.query("SELECT COUNT(*) n FROM products WHERE status='active'", one=True)["n"],
    }
    return jsonify(kpi)


@bp.post("/admin/users/<int:uid>/toggle")
@role_required("admin")
def admin_toggle_user(uid):
    u = db.query("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not u or u["role"] == "admin":
        return jsonify({"ok": False, "error": "Cannot modify this account"}), 400
    db.execute("UPDATE users SET active=? WHERE id=?", (0 if u["active"] else 1, uid))
    return jsonify({"ok": True, "active": 0 if u["active"] else 1})


@bp.post("/admin/products/<int:pid>/status")
@role_required("admin")
def admin_product_status(pid):
    data = request.get_json(silent=True) or request.form
    status = data.get("status")
    if status not in ("active", "removed"):
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    db.execute("UPDATE products SET status=? WHERE id=?", (status, pid))
    return jsonify({"ok": True})

# ------------------------------------------------------------------ Vercel / cloud scheduled market refresh
@bp.get("/cron/market-sync")
def cron_market_sync():
    """Refresh popular official mandi prices from a Vercel Cron invocation."""
    secret = os.environ.get("CRON_SECRET") or os.environ.get("FD_CRON_SECRET")
    if secret:
        if request.headers.get("Authorization") != f"Bearer {secret}":
            return jsonify({"ok": False, "error": "unauthorized"}), 401
    elif os.environ.get("VERCEL"):
        # Fail closed in production if the owner forgot to configure a secret.
        return jsonify({"ok": False, "error": "CRON_SECRET is not configured"}), 503

    import market_sync
    try:
        max_crops = max(1, min(int(os.environ.get("FD_MARKET_SYNC_CROPS", "12")), 30))
    except ValueError:
        max_crops = 12
    result = market_sync.sync_popular_crops(max_crops=max_crops)
    result["source_status"] = market_sync.status_summary()
    return jsonify(result), (200 if result.get("ok") else 207)


# ------------------------------------------------------------------ Final release health check
@bp.get("/system/health")
def system_health():
    """Fast local diagnostics for judging/demo readiness; never blocks on external providers."""
    from datetime import datetime
    import market_sync

    try:
        products = int(db.query("SELECT COUNT(*) n FROM products WHERE status='active'", one=True)["n"])
        users = int(db.query("SELECT COUNT(*) n FROM users", one=True)["n"])
        orders = int(db.query("SELECT COUNT(*) n FROM orders", one=True)["n"])
        db_ok = True
    except Exception:
        products = users = orders = 0
        db_ok = False
    status = market_sync.status_summary()
    return jsonify({
        "ok": db_ok,
        "version": "16-vercel-final",
        "time": datetime.now().replace(microsecond=0).isoformat(),
        "database": {"ok": db_ok, "backend": db.backend_name(), "active_products": products, "users": users, "orders": orders},
        "market": {
            "cached_rows": int(status.get("cached_rows") or 0),
            "cached_crops": int(status.get("cached_crops") or 0),
            "auto_sync_interval_min": status.get("auto_sync_interval_min"),
            "providers": status.get("providers") or [],
        },
    })
