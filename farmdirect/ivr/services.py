"""IVR service layer — every action goes through the existing FarmDirect
backend (SQLite tables, ai.pricing, ai.forecasting).

These functions are the ONLY bridge between the IVR dialog and the
real database. The IVR never opens the DB directly.
"""
from __future__ import annotations
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

import db
from ai.pricing import recommend_price
from ai.forecasting import forecast_crop

# --------------------------------------------------------------------- Farmer lookup
def getFarmerByPhone(phone: str) -> Optional[dict]:
    """Match a caller phone number to a registered users row (farmer/fpo).

    Tries exact match first, then a normalized last-10-digits match —
    many Indian phone strings are stored with +91 prefix or leading 0.
    """
    if not phone:
        return None
    raw = phone.strip()
    norm = raw.lstrip("+").lstrip("0")
    if norm.startswith("91") and len(norm) == 12:
        norm10 = norm[-10:]
    else:
        norm10 = norm[-10:] if len(norm) >= 10 else norm
    rows = db.query(
        "SELECT u.*, f.id AS farmer_profile_id, f.farm_name, f.crops_grown "
        "FROM users u LEFT JOIN farmers f ON f.user_id=u.id "
        "WHERE u.role IN ('farmer','fpo') AND (u.phone=? OR u.phone LIKE ?)",
        (raw, f"%{norm10}"))
    if not rows:
        return None
    return dict(rows[0])


def getUserByPhone(phone: str) -> Optional[dict]:
    """Match any active FarmDirect user by phone number.

    The original IVR was farmer-only.  V7 keeps all farmer behaviour intact,
    but also needs a registered consumer/buyer identity for placing orders by
    voice.  The normalization mirrors :func:`getFarmerByPhone` so the same
    Indian +91 / local-number demo inputs work reliably.
    """
    if not phone:
        return None
    raw = phone.strip()
    norm = raw.lstrip("+").lstrip("0")
    norm10 = norm[-10:] if len(norm) >= 10 else norm
    row = db.query(
        "SELECT u.*, f.id AS farmer_profile_id, f.farm_name, f.crops_grown, "
        "fp.fpo_name FROM users u "
        "LEFT JOIN farmers f ON f.user_id=u.id "
        "LEFT JOIN fpos fp ON fp.user_id=u.id "
        "WHERE u.active=1 AND (u.phone=? OR u.phone LIKE ?) "
        "ORDER BY CASE WHEN u.phone=? THEN 0 ELSE 1 END, u.id LIMIT 1",
        (raw, f"%{norm10}", raw), one=True)
    return dict(row) if row else None


def getFarmerProfile(user_id: int) -> Optional[dict]:
    row = db.query(
        "SELECT u.*, f.farm_name, f.crops_grown, f.farm_size_acres, fp.fpo_name "
        "FROM users u "
        "LEFT JOIN farmers f ON f.user_id=u.id "
        "LEFT JOIN fpos fp ON fp.user_id=u.id "
        "WHERE u.id=?", (user_id,), one=True)
    return dict(row) if row else None


# --------------------------------------------------------------------- Buy via IVR
def previewIVROrder(buyer_user_id: int, crop: str, quantity_kg: float,
                    grade: str = "A") -> Dict[str, Any]:
    """Find the best live marketplace listing and calculate an IVR order quote.

    The order is intentionally limited to one crop/grade/listing per IVR flow
    so the spoken confirmation remains short and deterministic.  It still uses
    the exact marketplace stock and fee rules used by the web checkout.
    """
    buyer = db.query("SELECT * FROM users WHERE id=? AND active=1", (buyer_user_id,), one=True)
    if not buyer:
        return {"ok": False, "error": "Registered caller account not found."}
    try:
        qty = float(quantity_kg)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Invalid quantity."}
    if qty <= 0:
        return {"ok": False, "error": "Quantity must be greater than zero."}
    grade = "A" if grade in ("A+", "A") else (grade if grade in ("B", "C") else "A")

    product = db.query(
        "SELECT p.*, u.name AS seller_name, u.city AS seller_city "
        "FROM products p JOIN users u ON u.id=p.seller_id "
        "WHERE p.status='active' AND p.crop=? AND p.grade=? AND p.quantity_kg>=? "
        "ORDER BY p.price_per_kg ASC, p.harvest_date DESC, p.id ASC LIMIT 1",
        (crop, grade, qty), one=True)
    if not product:
        # Return useful stock information for the requested crop/grade.
        stock = db.query(
            "SELECT COALESCE(MAX(quantity_kg),0) max_qty, MIN(price_per_kg) min_price "
            "FROM products WHERE status='active' AND crop=? AND grade=?",
            (crop, grade), one=True)
        return {
            "ok": False,
            "error": "No single active listing has enough stock for that quantity.",
            "available_max_kg": float(stock["max_qty"] or 0) if stock else 0,
            "min_price": float(stock["min_price"]) if stock and stock["min_price"] is not None else None,
        }

    p = dict(product)
    subtotal = round(float(p["price_per_kg"]) * qty, 2)
    buyer_type = "bulk" if (buyer["role"] == "buyer" or qty >= 500) else "consumer"
    platform_fee = round(subtotal * 0.06, 2)
    delivery_fee = 25.0 if buyer_type == "consumer" else round(subtotal * 0.015, 2)
    total = round(subtotal + platform_fee + delivery_fee, 2)
    return {
        "ok": True,
        "product_id": p["id"],
        "product_name": p["name"],
        "crop": p["crop"],
        "grade": p["grade"],
        "quantity_kg": qty,
        "unit_price": float(p["price_per_kg"]),
        "seller_name": p["seller_name"],
        "seller_city": p["seller_city"],
        "subtotal": subtotal,
        "platform_fee": platform_fee,
        "delivery_fee": delivery_fee,
        "total": total,
        "buyer_type": buyer_type,
        "delivery_city": buyer["city"],
    }


def createIVROrder(buyer_user_id: int, quote: Dict[str, Any]) -> Dict[str, Any]:
    """Place a real FarmDirect order from a confirmed IVR quote.

    Reuses the web app's shared ``place_order`` engine so stock, order items,
    payments and delivery rows stay perfectly consistent with checkout.
    Cash on Delivery is used for IVR prototype safety; payment can later be
    upgraded to OTP/UPI without changing the dialog state machine.
    """
    if not quote or not quote.get("product_id"):
        return {"ok": False, "error": "Order quote is missing."}
    buyer = db.query("SELECT * FROM users WHERE id=? AND active=1", (buyer_user_id,), one=True)
    if not buyer:
        return {"ok": False, "error": "Registered caller account not found."}
    from order_engine import place_order
    oid, err = place_order(
        buyer_user_id,
        [(int(quote["product_id"]), float(quote["quantity_kg"]))],
        f"IVR order — {buyer['city']}",
        buyer["city"],
        "422005",
        "Cash on Delivery",
    )
    if err:
        return {"ok": False, "error": err}
    order = db.query(
        "SELECT id,order_code,total_amount,status,delivery_city,created_at "
        "FROM orders WHERE id=?", (oid,), one=True)
    return {"ok": True, **(dict(order) if order else {"id": oid})}


def authenticateIVRSession(session: dict, pin: Optional[str] = None) -> bool:
    """Lightweight auth: for the prototype we trust caller-id matching.

    A production deployment would call a provider OTP/PIN step here.
    Returns True if the session's farmer_id is set.
    """
    return bool(session.get("farmer_id"))


# --------------------------------------------------------------------- Market price
def getMarketPrice(crop: str, city: Optional[str] = None) -> Dict[str, Any]:
    """Return official AGMARKNET market price when available.

    The function performs a conservative cached refresh for the requested crop
    when the data.gov.in API key is configured.  If official data is missing or
    unreachable it falls back to FarmDirect's local historical estimate and
    clearly marks the result as demo/estimate data.
    """
    try:
        import market_sync
        if market_sync.is_configured():
            market_sync.sync_crop(crop, force=False, limit=120)
        official = market_sync.get_reference_price(crop)
    except Exception:
        official = None

    rec = recommend_price(crop, "A", 100, city)
    suggested = float(rec["suggested_price"])

    if official:
        return {
            "crop": crop,
            "low": round(float(official["low"]), 1),
            "high": round(float(official["high"]), 1),
            "avg": round(float(official["modal"]), 1),
            "suggested": round(suggested, 1),
            "mandi": round(float(official["modal"]), 1),
            "unit": "kg",
            "city": city,
            "updated": official["arrival_date"],
            "demo_data": False,
            "official": True,
            "source": official["source"],
            "market": official.get("market"),
            "state": official.get("state"),
            "status": official.get("status", "official"),
            "observations": official.get("observations", 1),
        }

    # Offline fallback: local synthetic sales history.
    base = float(rec["mandi_price"])
    rows = db.query(
        "SELECT MIN(avg_price) lo, MAX(avg_price) hi, AVG(avg_price) av, MAX(date) latest "
        "FROM sales_history WHERE crop=? AND avg_price>0 "
        "AND date >= date('now','-14 days')", (crop,))
    if rows and rows[0]["lo"] is not None:
        lo = round(float(rows[0]["lo"]), 1)
        hi = round(float(rows[0]["hi"]), 1)
        av = round(float(rows[0]["av"]), 1)
        latest = rows[0]["latest"]
    else:
        lo = hi = av = base
        latest = date.today().isoformat()

    return {
        "crop": crop, "low": lo, "high": hi, "avg": av,
        "suggested": round(suggested, 1), "mandi": round(base, 1),
        "unit": "kg", "city": city, "updated": latest,
        "demo_data": True, "official": False, "source": "FarmDirect estimate",
        "market": None, "state": None, "status": "estimate", "observations": 0,
    }


# --------------------------------------------------------------------- Create listing
def createProduceListing(farmer_user_id: int, crop: str, quantity_kg: float,
                        price_per_kg: float, grade: str = "A",
                        harvest_date: Optional[str] = None,
                        organic: bool = False) -> Dict[str, Any]:
    """Create a real ``products`` row. Returns the new product id."""
    if not harvest_date:
        harvest_date = date.today().isoformat()
    # Canonical marketplace/database grades are A/B/C. Keep a defensive legacy
    # A+ normalization so stale clients can never violate the schema.
    grade = "A" if grade in ("A+", "A") else (grade or "A")
    farmer = db.query("SELECT * FROM users WHERE id=?", (farmer_user_id,), one=True)
    city = farmer["city"] if farmer else "Nashik"
    name = f"{crop} — {city}"
    try:
        from india_catalog import CROP_BY_NAME
        category = CROP_BY_NAME[crop].category if crop in CROP_BY_NAME else "Vegetables"
    except Exception:
        category = "Vegetables"
    pid = db.execute(
        "INSERT INTO products (seller_id,crop,name,category,grade,quantity_kg,price_per_kg,"
        "harvest_date,organic,description,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))",
        (farmer_user_id, crop, name, category, grade, float(quantity_kg),
         float(price_per_kg), harvest_date, 1 if organic else 0,
         f"Listed via IVR voice channel by {farmer['name'] if farmer else 'farmer'}."))
    return {"product_id": pid, "crop": crop, "quantity_kg": quantity_kg,
            "price_per_kg": price_per_kg, "grade": grade, "harvest_date": harvest_date}


# --------------------------------------------------------------------- Orders
_STATUS_TA = {
    "pending": "நிலுவையில் உள்ளது",
    "confirmed": "உறுதி செய்யப்பட்டது",
    "picked_up": "பொருட்கள் எடுக்கப்பட்டது",
    "in_transit": "பயணத்தில் உள்ளது",
    "delivered": "டெலிவர் செய்யப்ப�ட்டது",
    "rejected": "நிராகரிக்கப்பட்டது",
    "cancelled": "ரத்து செய்யப்பட்டது",
}
_STATUS_EN = {k: k.replace("_", " ") for k in _STATUS_TA}


def pretty_status(s: str, lang: str = "ta") -> str:
    return (_STATUS_TA if lang == "ta" else _STATUS_EN).get(s, s)


def getFarmerOrders(farmer_user_id: int, limit: int = 5) -> List[dict]:
    """Return the farmer's most recent orders (as a seller)."""
    rows = db.query(
        "SELECT o.id, o.order_code, o.status, o.created_at, o.delivery_city, "
        "oi.crop, oi.grade, oi.quantity_kg, oi.unit_price, oi.subtotal, "
        "u.name AS buyer_name "
        "FROM order_items oi "
        "JOIN orders o ON o.id=oi.order_id "
        "JOIN users u ON u.id=o.buyer_id "
        "WHERE oi.farmer_id=? "
        "ORDER BY o.id DESC LIMIT ?", (farmer_user_id, limit))
    return [dict(r) for r in rows]


def getDeliveryStatus(farmer_user_id: int, limit: int = 3) -> List[dict]:
    """Return deliveries for orders that include this farmer's items."""
    rows = db.query(
        "SELECT d.id, d.order_id, o.order_code, d.status, d.pickup_name, d.drop_name, "
        "d.distance_km, d.eta_minutes, d.driver_name, d.driver_phone, d.vehicle, "
        "o.delivery_city, d.updated_at, o.created_at "
        "FROM deliveries d JOIN orders o ON o.id=d.order_id "
        "WHERE d.order_id IN (SELECT DISTINCT order_id FROM order_items WHERE farmer_id=?) "
        "ORDER BY d.id DESC LIMIT ?", (farmer_user_id, limit))
    return [dict(r) for r in rows]


# --------------------------------------------------------------------- Bulk orders
def getBulkOpportunities(farmer_user_id: int, limit: int = 3) -> List[dict]:
    """Find open bulk quote requests that the farmer could fulfill.

    Re-uses the existing ``quotes`` table. For each open quote we
    compute how much of it the farmer can supply based on their
    active listings of that crop.
    """
    # What crops + total available quantity does this farmer have?
    listings = db.query(
        "SELECT crop, SUM(quantity_kg) AS avail "
        "FROM products WHERE seller_id=? AND status='active' "
        "GROUP BY crop", (farmer_user_id,))
    avail_map = {r["crop"]: float(r["avail"]) for r in listings}
    if not avail_map:
        return []

    crops = list(avail_map.keys())
    placeholders = ",".join("?" * len(crops))
    quotes = db.query(
        f"SELECT q.*, u.name AS buyer_name, u.city AS buyer_city "
        f"FROM quotes q JOIN users u ON u.id=q.buyer_id "
        f"WHERE q.status='open' AND q.crop IN ({placeholders}) "
        f"ORDER BY q.id DESC LIMIT ?", (*crops, limit))
    out = []
    for q in quotes:
        avail = avail_map.get(q["crop"], 0)
        if avail <= 0:
            continue
        out.append({
            "quote_id": q["id"],
            "buyer_name": q["buyer_name"],
            "buyer_city": q["buyer_city"],
            "crop": q["crop"],
            "quantity_kg": float(q["quantity_kg"]),
            "grade": q["grade"],
            "can_supply_kg": min(avail, float(q["quantity_kg"])),
            "my_available_kg": avail,
        })
    return out


def acceptBulkOpportunity(farmer_user_id: int, quote_id: int,
                          supply_kg: Optional[float] = None) -> Dict[str, Any]:
    """Create a quote_response from this farmer for ``quote_id`` and
    mark it accepted — the simulator equivalent of the existing
    ``/api/quotes/<qid>/accept/<rid>`` flow but from the SELLER side.

    For the prototype we just register an accepted response. The buyer
    will then convert it via their normal flow.
    """
    q = db.query("SELECT * FROM quotes WHERE id=?", (quote_id,), one=True)
    if not q:
        return {"ok": False, "error": "Quote not found"}
    # find one of this farmer's listings of that crop
    product = db.query(
        "SELECT * FROM products WHERE seller_id=? AND crop=? AND status='active' "
        "ORDER BY id LIMIT 1", (farmer_user_id, q["crop"]), one=True)
    if not product:
        return {"ok": False, "error": "No matching listing"}
    qty = min(supply_kg or q["quantity_kg"], product["quantity_kg"])
    price = product["price_per_kg"]
    # add an accepted response row (the existing flow accepts on the buyer
    # side; here we record the seller-side acceptance)
    rid = db.execute(
        "INSERT INTO quote_responses (quote_id,seller_id,price_per_kg,total_amount,eta_days,status) "
        "VALUES (?,?,?,?,?,?)",
        (quote_id, farmer_user_id, price, round(price * qty, 0), 2, "accepted"))
    return {"ok": True, "quote_response_id": rid, "supply_kg": qty,
            "price_per_kg": price, "crop": q["crop"]}


# --------------------------------------------------------------------- Earnings
def getFarmerEarnings(farmer_user_id: int) -> Dict[str, Any]:
    """Today / week / month / paid / pending earnings (real data)."""
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    month_ago = (date.today() - timedelta(days=30)).isoformat()
    def _sum(sql, args):
        row = db.query(sql, args, one=True)
        return float(row["v"] or 0) if row else 0.0

    today_amt = _sum(
        "SELECT COALESCE(SUM(oi.subtotal),0) v FROM order_items oi "
        "JOIN orders o ON o.id=oi.order_id "
        "WHERE oi.farmer_id=? AND oi.item_status='accepted' "
        "AND substr(o.created_at,1,10)=?", (farmer_user_id, today))
    week_amt = _sum(
        "SELECT COALESCE(SUM(oi.subtotal),0) v FROM order_items oi "
        "JOIN orders o ON o.id=oi.order_id "
        "WHERE oi.farmer_id=? AND oi.item_status='accepted' "
        "AND substr(o.created_at,1,10)>=?", (farmer_user_id, week_ago))
    month_amt = _sum(
        "SELECT COALESCE(SUM(oi.subtotal),0) v FROM order_items oi "
        "JOIN orders o ON o.id=oi.order_id "
        "WHERE oi.farmer_id=? AND oi.item_status='accepted' "
        "AND substr(o.created_at,1,10)>=?", (farmer_user_id, month_ago))
    paid = _sum(
        "SELECT COALESCE(SUM(p.farmer_share),0) v FROM payments p "
        "WHERE p.farmer_id=? AND p.status='completed'", (farmer_user_id,))
    pending = _sum(
        "SELECT COALESCE(SUM(p.farmer_share),0) v FROM payments p "
        "WHERE p.farmer_id=? AND p.status='pending'", (farmer_user_id,))

    return {
        "today": round(today_amt, 0),
        "week": round(week_amt, 0),
        "month": round(month_amt, 0),
        "paid": round(paid, 0),
        "pending": round(pending, 0),
    }


# --------------------------------------------------------------------- Bulk order opp text
def format_bulk_text(opp: dict, lang: str) -> dict:
    """Helper used by the dialog to format a bulk opportunity."""
    from .i18n import pick_prompt
    text = pick_prompt("bulk_report", lang,
                      qty=int(opp["quantity_kg"]),
                      crop=opp["crop"],
                      avail=int(opp["can_supply_kg"]))
    return {"text": text, "opp": opp}

# --------------------------------------------------------------------- Extended farmer self-service
def getFarmerActiveListings(farmer_user_id: int, limit: int = 5) -> Dict[str, Any]:
    """Summarise the farmer's current marketplace inventory for IVR."""
    rows = db.query(
        "SELECT id,crop,grade,quantity_kg,price_per_kg,harvest_date,organic,status "
        "FROM products WHERE seller_id=? AND status='active' ORDER BY id DESC LIMIT ?",
        (farmer_user_id, limit))
    total = db.query(
        "SELECT COUNT(*) n, COALESCE(SUM(quantity_kg),0) qty FROM products "
        "WHERE seller_id=? AND status='active'", (farmer_user_id,), one=True)
    return {
        "count": int(total["n"] or 0),
        "total_quantity_kg": round(float(total["qty"] or 0), 1),
        "items": [dict(r) for r in rows],
    }


def getDemandForecast(crop: str, horizon_days: int = 7) -> Dict[str, Any]:
    """Expose the existing offline demand-forecast engine through IVR."""
    return forecast_crop(crop, None, horizon_days)


def getAIPriceRecommendation(farmer_user_id: int, crop: str,
                             grade: str = "A", quantity_kg: float = 100) -> Dict[str, Any]:
    """Expose the same farmer price recommendation used by the web page."""
    farmer = db.query("SELECT city FROM users WHERE id=?", (farmer_user_id,), one=True)
    city = farmer["city"] if farmer and farmer["city"] else None
    return recommend_price(crop, grade, quantity_kg, city)
