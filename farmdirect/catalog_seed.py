"""Idempotent India-wide crop catalogue expansion for existing FarmDirect DBs.

This migration is intentionally separate from the original demo seeder so a
user upgrading V9 -> V10 does not need to delete farmdirect.db. It inserts the
national demo FPO network, one or more marketplace listings for every crop in
india_catalog.py, and synthetic sales history used by the offline AI modules.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

import db
from india_catalog import CROP_CATALOG, CROP_REGION_HINTS, LISTING_TITLES

CATALOG_SEED_KEY = "india_crop_catalog"
CATALOG_VERSION = 10
_rng = random.Random(20260911)

# key, org name, city, state, lat, lng, member count
REGIONAL_FPOS = (
    ("nashik", "Nashik Horticulture FPO", "Nashik", "Maharashtra", 19.9975, 73.7898, 386),
    ("ratnagiri", "Konkan Mango Growers FPO", "Ratnagiri", "Maharashtra", 16.9902, 73.3120, 214),
    ("nagpur", "Vidarbha Orange & Grain FPO", "Nagpur", "Maharashtra", 21.1458, 79.0882, 428),
    ("pune", "Pune Valley Farmers Collective", "Pune", "Maharashtra", 18.5204, 73.8567, 312),
    ("guntur", "Guntur Chilli & Produce FPO", "Guntur", "Andhra Pradesh", 16.3067, 80.4365, 510),
    ("hyderabad", "Telangana Fresh Producer Co.", "Hyderabad", "Telangana", 17.3850, 78.4867, 355),
    ("bengaluru", "Karnataka FreshGrow FPO", "Bengaluru", "Karnataka", 12.9716, 77.5946, 404),
    ("chikmagalur", "Malnad Coffee Growers FPO", "Chikmagalur", "Karnataka", 13.3153, 75.7754, 268),
    ("mangaluru", "Coastal Karnataka Plantation FPO", "Mangaluru", "Karnataka", 12.9141, 74.8560, 241),
    ("coimbatore", "Kongu Horticulture FPO", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558, 392),
    ("erode", "Erode Turmeric Farmers FPO", "Erode", "Tamil Nadu", 11.3410, 77.7172, 476),
    ("madurai", "Madurai Malli & Fresh Produce FPO", "Madurai", "Tamil Nadu", 9.9252, 78.1198, 338),
    ("trichy", "Cauvery Delta Banana FPO", "Tiruchirappalli", "Tamil Nadu", 10.7905, 78.7047, 361),
    ("thanjavur", "Thanjavur Delta Grains FPO", "Thanjavur", "Tamil Nadu", 10.7870, 79.1378, 525),
    ("kochi", "Kerala Spice & Plantation FPO", "Kochi", "Kerala", 9.9312, 76.2673, 447),
    ("goa", "Goa Cashew & Kokum Growers", "Panaji", "Goa", 15.4909, 73.8278, 183),
    ("karnal", "Haryana Basmati Producers Co.", "Karnal", "Haryana", 29.6857, 76.9905, 612),
    ("amritsar", "Punjab Grain & Kinnow FPO", "Amritsar", "Punjab", 31.6340, 74.8723, 588),
    ("jaipur", "Rajasthan Millet & Spice FPO", "Jaipur", "Rajasthan", 26.9124, 75.7873, 473),
    ("indore", "Malwa Pulses Producer Co.", "Indore", "Madhya Pradesh", 22.7196, 75.8577, 526),
    ("lucknow", "UP Fresh & Pulse Farmers FPO", "Lucknow", "Uttar Pradesh", 26.8467, 80.9462, 502),
    ("muzaffarpur", "Bihar Litchi & Vegetable FPO", "Muzaffarpur", "Bihar", 26.1209, 85.3647, 327),
    ("kolkata", "Bengal Jute & Horticulture FPO", "Kolkata", "West Bengal", 22.5726, 88.3639, 461),
    ("bhubaneswar", "Odisha Millet & Produce FPO", "Bhubaneswar", "Odisha", 20.2961, 85.8245, 304),
    ("raipur", "Chhattisgarh Nutri-Cereal FPO", "Raipur", "Chhattisgarh", 21.2514, 81.6296, 341),
    ("ranchi", "Jharkhand Tribal Produce FPO", "Ranchi", "Jharkhand", 23.3441, 85.3096, 289),
    ("guwahati", "Assam Tea & Horticulture FPO", "Guwahati", "Assam", 26.1445, 91.7362, 366),
    ("agartala", "Tripura Pineapple Growers FPO", "Agartala", "Tripura", 23.8315, 91.2868, 226),
    ("gangtok", "Sikkim Organic Producers FPO", "Gangtok", "Sikkim", 27.3389, 88.6065, 196),
    ("shillong", "Meghalaya Natural Produce FPO", "Shillong", "Meghalaya", 25.5788, 91.8933, 213),
    ("itanagar", "Arunachal Kiwi & Horticulture FPO", "Itanagar", "Arunachal Pradesh", 27.0844, 93.6053, 174),
    ("imphal", "Manipur Hills Producer FPO", "Imphal", "Manipur", 24.8170, 93.9368, 188),
    ("srinagar", "Kashmir Valley Growers FPO", "Srinagar", "Jammu & Kashmir", 34.0837, 74.7973, 406),
    ("shimla", "Himachal Mountain Fruit FPO", "Shimla", "Himachal Pradesh", 31.1048, 77.1734, 352),
    ("dehradun", "Uttarakhand Hill Produce FPO", "Dehradun", "Uttarakhand", 30.3165, 78.0322, 278),
    ("ahmedabad", "Gujarat Oilseed & Produce FPO", "Ahmedabad", "Gujarat", 23.0225, 72.5714, 481),
)

CATEGORY_REGION_POOLS = {
    "Vegetables": ("nashik", "pune", "bengaluru", "coimbatore", "hyderabad", "lucknow", "muzaffarpur", "indore"),
    "Fruits": ("nashik", "ratnagiri", "nagpur", "coimbatore", "muzaffarpur", "shimla", "srinagar", "agartala", "itanagar"),
    "Cereals & Grains": ("thanjavur", "karnal", "amritsar", "lucknow", "raipur", "kolkata"),
    "Millets": ("jaipur", "raipur", "bhubaneswar", "bengaluru", "coimbatore"),
    "Pulses & Legumes": ("indore", "jaipur", "lucknow", "hyderabad", "ahmedabad"),
    "Oilseeds": ("ahmedabad", "jaipur", "indore", "hyderabad", "bengaluru"),
    "Spices": ("kochi", "guntur", "erode", "jaipur", "shillong", "gangtok"),
    "Plantation & Commercial": ("guwahati", "kochi", "coimbatore", "mangaluru", "chikmagalur", "kolkata"),
    "Nuts & Dry Fruits": ("srinagar", "shimla", "goa", "mangaluru"),
    "Flowers": ("madurai", "bengaluru", "pune", "kolkata", "hyderabad"),
    "Herbs & Medicinal": ("dehradun", "jaipur", "indore", "gangtok", "ranchi"),
    "Fodder & Forage": ("karnal", "amritsar", "jaipur", "lucknow", "ahmedabad"),
}


def _slug(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum() or ch in "-_")


def _ensure_sellers(conn) -> dict[str, int]:
    import hashlib

    cur = conn.cursor()
    # Reuse an existing demo password hash. The national FPO records are data
    # providers, not separate demo-login identities, so no new auth dependency
    # is needed for this migration.
    existing_pw = cur.execute("SELECT password_hash FROM users ORDER BY id LIMIT 1").fetchone()
    pw = existing_pw[0] if existing_pw else "catalog-demo-disabled"
    result: dict[str, int] = {}
    for key, org, city, state, lat, lng, members in REGIONAL_FPOS:
        email = f"catalog.{_slug(key)}@farmdirect.in"
        row = cur.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if row:
            uid = int(row[0])
        else:
            # Keep deterministic but obviously demo-only phone numbers.
            phone = "97" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:8].translate(str.maketrans("abcdef", "123456"))
            cur.execute(
                "INSERT INTO users (name,email,phone,password_hash,role,city,state,lat,lng,active) "
                "VALUES (?,?,?,?,?,?,?,?,?,1)",
                (org, email, phone, pw, "fpo", city, state, lat, lng),
            )
            uid = cur.lastrowid
            cur.execute(
                "INSERT INTO fpos (user_id,fpo_name,member_count,district,state,description,verified) "
                "VALUES (?,?,?,?,?,?,1)",
                (uid, org, members, city, state,
                 f"Regional FarmDirect demo producer network serving {city}, {state}."),
            )
        result[key] = uid
    return result


def _seller_key_for(spec, idx: int) -> str:
    special = CROP_REGION_HINTS.get(spec.name)
    if special:
        return special
    pool = CATEGORY_REGION_POOLS[spec.category]
    return pool[idx % len(pool)]


def _quantity_for(spec, idx: int) -> float:
    if spec.name == "Saffron":
        return 8.0 + idx % 5
    if spec.category in ("Spices", "Nuts & Dry Fruits", "Herbs & Medicinal"):
        return float(120 + (idx * 37) % 780)
    if spec.category == "Flowers":
        return float(180 + (idx * 29) % 900)
    if spec.category == "Fodder & Forage":
        return float(1800 + (idx * 173) % 6000)
    if spec.category in ("Cereals & Grains", "Millets", "Pulses & Legumes", "Oilseeds"):
        return float(1800 + (idx * 211) % 6200)
    if spec.category == "Plantation & Commercial":
        return float(900 + (idx * 181) % 5200)
    return float(450 + (idx * 97) % 2600)


def _price_for(spec, idx: int, variant: int) -> float:
    factor = 1.0 + (((idx * 13 + variant * 7) % 15) - 7) / 100.0
    price = spec.base_price * factor
    if price < 10:
        return round(price, 1)
    return round(price * 2) / 2


def _insert_products(conn, seller_ids: dict[str, int]) -> int:
    cur = conn.cursor()
    inserted = 0
    today = datetime.now().date()
    for idx, spec in enumerate(CROP_CATALOG):
        curated = list(LISTING_TITLES.get(spec.name, ()))
        titles = curated[:2]
        if not titles:
            titles = [f"Farm Fresh {spec.name}", f"Premium {spec.name} — Direct Farm Lot"]
        elif len(titles) == 1:
            titles.append(f"Farm Fresh {spec.name} — Regional Lot")
        for variant, title in enumerate(titles[:2]):
            key = _seller_key_for(spec, idx + variant)
            seller_id = seller_ids[key]
            exists = cur.execute(
                "SELECT 1 FROM products WHERE seller_id=? AND crop=? AND name=? LIMIT 1",
                (seller_id, spec.name, title),
            ).fetchone()
            if exists:
                continue
            grade = ("A", "A", "B", "B", "C")[(idx + variant) % 5]
            qty = _quantity_for(spec, idx + variant * 17)
            price = _price_for(spec, idx, variant)
            organic = 1 if (idx + variant) % 7 == 0 else 0
            age = (idx * 3 + variant) % 9
            harvest = (today - timedelta(days=age)).isoformat()
            description = (
                f"{title} — verified regional farm listing. {spec.category}; Grade {grade}. "
                "Farm packed and ready for direct marketplace dispatch."
            )
            cur.execute(
                "INSERT INTO products (seller_id,crop,name,category,grade,quantity_kg,price_per_kg,"
                "harvest_date,organic,description,status) VALUES (?,?,?,?,?,?,?,?,?,?, 'active')",
                (seller_id, spec.name, title, spec.category, grade, qty, price,
                 harvest, organic, description),
            )
            inserted += 1
    return inserted


def _insert_sales_history(conn) -> int:
    cur = conn.cursor()
    today = datetime.now().date()
    rows = []
    for idx, spec in enumerate(CROP_CATALOG):
        has = cur.execute("SELECT 1 FROM sales_history WHERE crop=? LIMIT 1", (spec.name,)).fetchone()
        if has:
            continue
        # 96 days is enough for the 60/90-day forecasting/price windows while
        # remaining fast on a phone-sized SQLite database.
        phase = (idx % 23) / 23 * math.tau
        trend = ((idx % 9) - 4) * 0.0009
        for day_back in range(95, -1, -1):
            d = today - timedelta(days=day_back)
            t = 95 - day_back
            weekly = 1.0 + 0.11 * math.sin((t / 7.0) * math.tau + phase)
            seasonal = 1.0 + 0.07 * math.sin((t / 45.0) * math.tau + phase / 2)
            noise = 1.0 + _rng.uniform(-0.075, 0.075)
            daily_qty = max(1.0, (spec.base_demand / 7.0) * weekly * seasonal * noise * (1 + trend * t))
            price_wave = 1.0 + 0.09 * math.sin((t / 19.0) * math.tau + phase)
            price_noise = 1.0 + _rng.uniform(-0.045, 0.045)
            avg_price = max(0.5, spec.base_price * price_wave * price_noise)
            rows.append((spec.name, None, d.isoformat(), round(daily_qty, 1), round(avg_price, 2)))
    if rows:
        cur.executemany(
            "INSERT INTO sales_history (crop,city,date,quantity_kg,avg_price) VALUES (?,?,?,?,?)",
            rows,
        )
    return len(rows)


def ensure_india_catalog() -> dict:
    """Apply the national catalogue exactly once per catalogue version."""
    conn = db.get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS catalog_seed_state ("
            "seed_key TEXT PRIMARY KEY, version INTEGER NOT NULL, "
            "applied_at TEXT DEFAULT (datetime('now','localtime')))"
        )
        row = cur.execute(
            "SELECT version FROM catalog_seed_state WHERE seed_key=?", (CATALOG_SEED_KEY,)
        ).fetchone()
        if row and int(row[0]) >= CATALOG_VERSION:
            return {"applied": False, "version": int(row[0]), "crops": len(CROP_CATALOG)}

        # Normalize the original demo label into the expanded category system.
        cur.execute("UPDATE products SET category='Cereals & Grains' WHERE category='Grains'")
        sellers = _ensure_sellers(conn)
        products = _insert_products(conn, sellers)
        history = _insert_sales_history(conn)
        cur.execute(
            "INSERT INTO catalog_seed_state(seed_key,version,applied_at) "
            "VALUES (?,?,datetime('now','localtime')) "
            "ON CONFLICT(seed_key) DO UPDATE SET version=excluded.version, applied_at=excluded.applied_at",
            (CATALOG_SEED_KEY, CATALOG_VERSION),
        )
        conn.commit()
        return {
            "applied": True,
            "version": CATALOG_VERSION,
            "crops": len(CROP_CATALOG),
            "regional_sellers": len(sellers),
            "products_added": products,
            "sales_rows_added": history,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
