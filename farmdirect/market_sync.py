"""Multi-source Indian mandi price synchronisation for FarmDirect FINAL V16.

Provider order: AGMARKNET 2.0 public report backend, optional data.gov.in,
Tamil Nadu AgriMarket public government feed, optional e-NAM, then the last
verified database cache. Prices are normalized to ₹/kg while source,
market, reporting date and fetch time are preserved. FarmDirect never fabricates
an "official" observation when external providers are unavailable.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from html import unescape
from datetime import date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import db

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
API_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
SOURCE_NAME = "AGMARKNET · data.gov.in"
AGMARKNET2_SOURCE = "AGMARKNET 2.0 · Ministry of Agriculture"
AGMARKNET2_BASE = "https://api.agmarknet.gov.in/v1"
AGMARKNET2_RESOURCE = "agmarknet-2.0-public-api"
ENAM_SOURCE = "e-NAM Live Price · Government of India"
ENAM_DASHBOARD_URL = "https://enam.gov.in/web/dashboard/live_price"
ENAM_RESOURCE = "enam-live-price-dashboard"
TN_SOURCE = "Tamil Nadu AgriMarket · Government of Tamil Nadu"
TN_MARKET_URL = "https://www.agrimark.tn.gov.in/"
TN_RESOURCE = "tn-agrimarket-public-price"
DEFAULT_TTL_MINUTES = 20
DEFAULT_TIMEOUT_SECONDS = 8

# Stable commodity IDs used by the current AGMARKNET 2.0 report backend for
# common FarmDirect crops. The normal path still resolves everything from the
# live filters payload; this table is only a resilience fallback when metadata
# changes shape or is temporarily incomplete.
AGMARKNET2_COMMON_COMMODITY_IDS = {
    "Wheat": 1,
    "Rice": 3,
    "Maize": 4,
    "Chickpea": 6,
    "Mustard": 12,
    "Soybean": 13,
    "Cotton": 15,
    "Onion": 23,
    "Potato": 24,
    "Tomato": 65,
}

# AGMARKNET commodity labels are not always identical to FarmDirect canonical
# names. Candidates are tried in order; the canonical name is always included.
COMMODITY_CANDIDATES = {
    "Rice": ("Paddy(Dhan)(Common)", "Rice"),
    "Basmati Rice": ("Paddy(Dhan)(Basmati)", "Rice"),
    "Sona Masoori Rice": ("Paddy(Dhan)(Common)", "Rice"),
    "Red Rice": ("Rice",),
    "Black Rice": ("Rice",),
    "Okra": ("Bhindi(Ladies Finger)", "Bhindi", "Okra"),
    "Green Chili": ("Green Chilli", "Chilly Capsicum", "Green Chili"),
    "Dry Chili": ("Dry Chillies", "Chilly Capsicum", "Dry Chili"),
    "Brinjal": ("Brinjal",),
    "Capsicum": ("Capsicum",),
    "Sweet Lime": ("Mousambi(Sweet Lime)", "Sweet Lime"),
    "Mandarin": ("Kinnow", "Orange"),
    "Pomegranate": ("Pomegranate",),
    "Green Peas": ("Peas Wet", "Green Peas"),
    "French Bean": ("French Beans (Frasbean)", "French Bean"),
    "Cluster Bean": ("Guar", "Cluster beans"),
    "Bottle Gourd": ("Bottle gourd",),
    "Bitter Gourd": ("Bitter gourd",),
    "Ridge Gourd": ("Ridgeguard(Tori)", "Ridge Gourd"),
    "Snake Gourd": ("Snakeguard", "Snake Gourd"),
    "Ivy Gourd": ("Tinda", "Ivy Gourd"),
    "Drumstick": ("Drumstick",),
    "Coriander Leaves": ("Coriander(Leaves)", "Coriander Leaves"),
    "Fenugreek Leaves": ("Methi(Leaves)", "Fenugreek Leaves"),
    "Chickpea": ("Bengal Gram(Gram)(Whole)", "Gram Raw(Chholia)", "Chickpea"),
    "Pigeon Pea": ("Arhar (Tur/Red Gram)(Whole)", "Arhar Dal(Tur Dal)", "Pigeon Pea"),
    "Green Gram": ("Green Gram (Moong)(Whole)", "Green Gram Dal (Moong Dal)", "Green Gram"),
    "Black Gram": ("Black Gram (Urd Beans)(Whole)", "Black Gram Dal (Urd Dal)", "Black Gram"),
    "Lentil": ("Lentil (Masur)(Whole)", "Masur Dal", "Lentil"),
    "Kidney Bean": ("Rajma", "Kidney Bean"),
    "Groundnut": ("Groundnut",),
    "Mustard": ("Mustard", "Mustard Seed"),
    "Sesame": ("Sesamum(Sesame,Gingelly,Til)", "Sesame"),
    "Sunflower Seed": ("Sunflower", "Sunflower Seed"),
    "Turmeric": ("Turmeric",),
    "Black Pepper": ("Black pepper", "Black Pepper"),
    "Small Cardamom": ("Cardamoms", "Cardamom"),
    "Large Cardamom": ("Black Cardamom", "Cardamoms"),
    "Coriander Seed": ("Corriander seed", "Coriander Seed"),
    "Cumin": ("Cummin Seed(Jeera)", "Cumin"),
    "Fenugreek Seed": ("Methi Seeds", "Fenugreek Seed"),
    "Ginger": ("Ginger(Green)", "Ginger(Dry)", "Ginger"),
    "Garlic": ("Garlic",),
    "Coconut": ("Coconut",),
    "Arecanut": ("Arecanut(Betelnut/Supari)", "Arecanut"),
    "Cashew": ("Cashewnuts", "Cashew"),
    "Cotton": ("Cotton",),
    "Jute": ("Jute",),
    "Sugarcane": ("Sugarcane",),
    "Pearl Millet": ("Bajra(Pearl Millet/Cumbu)", "Bajra", "Pearl Millet"),
    "Finger Millet": ("Ragi (Finger Millet)", "Ragi", "Finger Millet"),
    "Sorghum": ("Jowar(Sorghum)", "Jowar", "Sorghum"),
    "Maize": ("Maize",),
    "Wheat": ("Wheat",),
    "Barley": ("Barley (Jau)", "Barley"),
    "Banana": ("Banana",),
    "Mango": ("Mango",),
    "Apple": ("Apple",),
    "Grapes": ("Grapes",),
    "Orange": ("Orange",),
    "Lemon": ("Lemon",),
    "Guava": ("Guava",),
    "Papaya": ("Papaya",),
    "Pineapple": ("Pine Apple", "Pineapple"),
    "Watermelon": ("Water Melon", "Watermelon"),
    "Muskmelon": ("Musk Melon", "Muskmelon"),
    "Litchi": ("Litchi",),
    "Jackfruit": ("Jack Fruit", "Jackfruit"),
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mandi_prices (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    crop             TEXT NOT NULL,
    api_commodity    TEXT NOT NULL,
    state            TEXT,
    district         TEXT,
    market           TEXT,
    variety          TEXT,
    source_grade     TEXT,
    arrival_date     TEXT NOT NULL,
    min_price_qtl    REAL,
    max_price_qtl    REAL,
    modal_price_qtl  REAL,
    min_price_kg     REAL,
    max_price_kg     REAL,
    modal_price_kg   REAL,
    source           TEXT DEFAULT 'AGMARKNET · data.gov.in',
    resource_id      TEXT,
    fetched_at       TEXT NOT NULL,
    UNIQUE(crop, api_commodity, state, district, market, variety, source_grade, arrival_date)
);
CREATE INDEX IF NOT EXISTS idx_mandi_crop_date ON mandi_prices(crop, arrival_date DESC);
CREATE INDEX IF NOT EXISTS idx_mandi_state_crop_date ON mandi_prices(state, crop, arrival_date DESC);

CREATE TABLE IF NOT EXISTS market_sync_state (
    sync_key          TEXT PRIMARY KEY,
    crop              TEXT,
    state             TEXT,
    status            TEXT,
    last_attempt_at   TEXT,
    last_success_at   TEXT,
    last_arrival_date TEXT,
    records_received  INTEGER DEFAULT 0,
    api_commodity     TEXT,
    error_message     TEXT
);

CREATE TABLE IF NOT EXISTS market_provider_state (
    provider          TEXT PRIMARY KEY,
    label             TEXT NOT NULL,
    status            TEXT,
    last_attempt_at   TEXT,
    last_success_at   TEXT,
    records_received  INTEGER DEFAULT 0,
    message           TEXT
);
"""

_BG_STARTED = False
_BG_LOCK = threading.Lock()
_QUEUE_LOCK = threading.Lock()
_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()
_PENDING_CROPS: list[tuple[str, str | None]] = []
_RECENTLY_QUEUED: dict[tuple[str, str | None], float] = {}
QUEUE_COOLDOWN_SECONDS = 90
_REFERENCE_CACHE: dict[tuple[str, str], tuple[float, dict]] = {}
_REFERENCE_CACHE_LOCK = threading.Lock()
REFERENCE_CACHE_SECONDS = 12

_ENAM_RAW_CACHE: str | None = None
_ENAM_RAW_AT = 0.0
_TN_RAW_CACHE: str | None = None
_TN_RAW_AT = 0.0


def ensure_schema() -> None:
    """Ensure market tables once per process instead of on every read.

    This function is called by price/status helpers very frequently. Running
    CREATE TABLE/INDEX statements for every product card creates avoidable I/O
    and lock contention on SQLite, particularly on Termux/shared storage.
    """
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        conn = db.get_db()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
        _SCHEMA_READY = True


def _env_file_value(key: str) -> str | None:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                k, v = raw.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def api_key() -> str | None:
    return (os.environ.get("DATA_GOV_IN_API_KEY") or
            os.environ.get("DATAGOV_API_KEY") or
            _env_file_value("DATA_GOV_IN_API_KEY") or
            _env_file_value("DATAGOV_API_KEY"))


def is_configured() -> bool:
    """Return True when at least one automatic market provider is enabled."""
    enabled = [
        os.environ.get("FD_AGMARKNET2_ENABLED", "1"),
        os.environ.get("FD_TN_MARKET_ENABLED", "1"),
        # e-NAM's public live-price page is a dynamic UI, not a stable JSON API.
        # Keep its best-effort adapter opt-in so it never delays the verified
        # AGMARKNET 2.0 feed that powers FarmDirect's live price path.
        os.environ.get("FD_ENAM_ENABLED", "0"),
    ]
    return any(str(v).strip().lower() not in {"0", "false", "no", "off"} for v in enabled) or bool(api_key())


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _sync_key(crop: str, state: str | None) -> str:
    return f"{crop}|{state or '*'}"


def _invalidate_reference_cache(crop: str) -> None:
    """Drop tiny in-process read cache entries after verified rows change."""
    with _REFERENCE_CACHE_LOCK:
        for key in [k for k in _REFERENCE_CACHE if k[0] == crop]:
            _REFERENCE_CACHE.pop(key, None)


def _parse_date(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    # AGMARKNET 2.0 has returned both date-only and ISO datetime values across
    # report endpoints. Accept the first ISO date component before trying the
    # legacy report formats.
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            pass
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _num(value) -> float | None:
    try:
        n = float(str(value).replace(",", "").strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _candidate_labels(crop: str) -> tuple[str, ...]:
    seen = set()
    values = list(COMMODITY_CANDIDATES.get(crop, ())) + [crop]
    out = []
    for value in values:
        if value and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return tuple(out)





def _provider_state(provider: str, label: str, status: str, *, ok: bool,
                    records: int = 0, message: str | None = None) -> None:
    """Persist provider health without disturbing the price cache."""
    now = _now_iso()
    db.execute(
        "INSERT INTO market_provider_state (provider,label,status,last_attempt_at,last_success_at,records_received,message) "
        "VALUES (?,?,?,?,?,?,?) ON CONFLICT(provider) DO UPDATE SET label=excluded.label,status=excluded.status,"
        "last_attempt_at=excluded.last_attempt_at,last_success_at=CASE WHEN ? THEN excluded.last_success_at ELSE market_provider_state.last_success_at END,"
        "records_received=excluded.records_received,message=excluded.message",
        (provider, label, status, now, now if ok else None, int(records or 0), message, 1 if ok else 0),
    )


def _http_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    req = Request(url, headers=headers or {"User-Agent": "FarmDirect-SIH/15"})
    timeout = int(os.environ.get("FD_MARKET_SYNC_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _cached_public_text(kind: str, url: str, headers: dict[str, str], ttl_seconds: int = 600) -> str:
    global _ENAM_RAW_CACHE, _ENAM_RAW_AT, _TN_RAW_CACHE, _TN_RAW_AT
    now = time.time()
    if kind == "enam" and _ENAM_RAW_CACHE is not None and now - _ENAM_RAW_AT < ttl_seconds:
        return _ENAM_RAW_CACHE
    if kind == "tn" and _TN_RAW_CACHE is not None and now - _TN_RAW_AT < ttl_seconds:
        return _TN_RAW_CACHE
    raw = _http_text(url, headers=headers)
    if kind == "enam":
        _ENAM_RAW_CACHE, _ENAM_RAW_AT = raw, now
    elif kind == "tn":
        _TN_RAW_CACHE, _TN_RAW_AT = raw, now
    return raw


def _strip_html(value: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(unescape(text).split())


def _store_normalized_rows(crop: str, api_commodity: str, rows: list[dict],
                           source: str, resource_id: str) -> tuple[int, str | None]:
    """Store normalized provider rows. Input prices are already ₹/kg and/or ₹/qtl."""
    if not rows:
        return 0, None
    fetched = _now_iso()
    normalized = []
    latest = None
    for r in rows:
        arrival = _parse_date(str(r.get("arrival_date") or r.get("date") or ""))
        if not arrival:
            continue
        min_kg = _num(r.get("min_price_kg"))
        max_kg = _num(r.get("max_price_kg"))
        modal_kg = _num(r.get("modal_price_kg"))
        min_q = _num(r.get("min_price_qtl"))
        max_q = _num(r.get("max_price_qtl"))
        modal_q = _num(r.get("modal_price_qtl"))
        if modal_kg is None and modal_q is not None:
            modal_kg = round(modal_q / 100.0, 2)
        if min_kg is None and min_q is not None:
            min_kg = round(min_q / 100.0, 2)
        if max_kg is None and max_q is not None:
            max_kg = round(max_q / 100.0, 2)
        if modal_q is None and modal_kg is not None:
            modal_q = round(modal_kg * 100.0, 2)
        if min_q is None and min_kg is not None:
            min_q = round(min_kg * 100.0, 2)
        if max_q is None and max_kg is not None:
            max_q = round(max_kg * 100.0, 2)
        if modal_kg is None:
            continue
        latest = max(latest or arrival, arrival)
        normalized.append((
            crop, api_commodity, str(r.get("state") or ""), str(r.get("district") or ""),
            str(r.get("market") or ""), str(r.get("variety") or ""), str(r.get("grade") or ""),
            arrival, min_q, max_q, modal_q, min_kg, max_kg, modal_kg,
            source, resource_id, fetched,
        ))
    if not normalized:
        return 0, latest
    conn = db.get_db()
    try:
        conn.executemany(
            "INSERT INTO mandi_prices (crop,api_commodity,state,district,market,variety,source_grade,arrival_date,"
            "min_price_qtl,max_price_qtl,modal_price_qtl,min_price_kg,max_price_kg,modal_price_kg,source,resource_id,fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(crop,api_commodity,state,district,market,variety,source_grade,arrival_date) DO UPDATE SET "
            "min_price_qtl=excluded.min_price_qtl,max_price_qtl=excluded.max_price_qtl,modal_price_qtl=excluded.modal_price_qtl,"
            "min_price_kg=excluded.min_price_kg,max_price_kg=excluded.max_price_kg,modal_price_kg=excluded.modal_price_kg,"
            "source=excluded.source,resource_id=excluded.resource_id,fetched_at=excluded.fetched_at",
            normalized,
        )
        conn.commit()
    finally:
        conn.close()
    _invalidate_reference_cache(crop)
    return len(normalized), latest


_ENAM_ROW_PATTERNS = (
    # Handles JSON-like payloads if e-NAM ever embeds or exposes them in the public dashboard response.
    re.compile(r'\{[^{}]{0,900}?"(?:commodity|commodity_name)"\s*:\s*"(?P<commodity>[^"]+)"[^{}]{0,900}?"(?:min_price|minPrice)"\s*:\s*"?(?P<min>[0-9.,]+)"?[^{}]{0,900}?"(?:modal_price|modalPrice|model_price)"\s*:\s*"?(?P<modal>[0-9.,]+)"?[^{}]{0,900}?"(?:max_price|maxPrice)"\s*:\s*"?(?P<max>[0-9.,]+)"?[^{}]{0,900}?\}', re.I | re.S),
)


def _sync_enam(crop: str, state: str | None = None) -> dict:
    """Best-effort e-NAM public dashboard adapter.

    e-NAM's live-price page currently renders the price grid dynamically. FINAL V15
    probes it first and accepts data only when a valid machine-readable price row
    is present. Otherwise it fails closed and immediately falls through to the
    next official provider instead of inventing an e-NAM result.
    """
    if os.environ.get("FD_ENAM_ENABLED", "0").strip().lower() in {"0", "false", "no", "off"}:
        return {"ok": False, "error": "e-NAM provider disabled"}
    url = os.environ.get("FD_ENAM_PRICE_FEED_URL", ENAM_DASHBOARD_URL)
    try:
        raw = _cached_public_text("enam", url, {
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Referer": "https://enam.gov.in/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/135 Mobile Safari/537.36 FarmDirect/15",
        })
        rows = []
        # JSON endpoint override is supported when e-NAM exposes a stable public feed.
        if raw.lstrip().startswith(("{", "[")):
            try:
                payload = json.loads(raw)
                for item in _walk_dicts(payload):
                    commodity = str(_pick(item, ("commodity", "commodity_name", "commodityName", "cmdt_name")) or "")
                    if not commodity or not any(_norm_name(x) in _norm_name(commodity) or _norm_name(commodity) in _norm_name(x) for x in _candidate_labels(crop)):
                        continue
                    modal = _num(_pick(item, ("modal_price", "modalPrice", "model_price", "modelPrice")))
                    if modal is None:
                        continue
                    minv = _num(_pick(item, ("min_price", "minPrice")))
                    maxv = _num(_pick(item, ("max_price", "maxPrice")))
                    unit = str(_pick(item, ("unit", "price_unit", "unit_name_price")) or "Rs./Quintal").lower()
                    divisor = 1.0 if ("kg" in unit and "quint" not in unit) else 100.0
                    report_date = _parse_date(str(_pick(item, ("arrival_date", "arrivalDate", "date", "report_date")) or "")) or date.today().isoformat()
                    rows.append({
                        "arrival_date": report_date,
                        "state": str(_pick(item, ("state", "state_name", "stateName")) or state or ""),
                        "district": str(_pick(item, ("district", "district_name", "districtName")) or ""),
                        "market": str(_pick(item, ("market", "market_name", "marketName", "apmc_name")) or "e-NAM mandi"),
                        "variety": str(_pick(item, ("variety", "variety_name", "varietyName")) or ""),
                        "grade": str(_pick(item, ("grade", "grade_name", "gradeName")) or ""),
                        "min_price_kg": round(minv / divisor, 2) if minv else None,
                        "max_price_kg": round(maxv / divisor, 2) if maxv else None,
                        "modal_price_kg": round(modal / divisor, 2),
                    })
            except json.JSONDecodeError:
                pass
        else:
            # Conservative embedded-JSON fallback. The normal dashboard HTML may
            # contain no rows at all; that is treated as unavailable, not success.
            for pattern in _ENAM_ROW_PATTERNS:
                for m in pattern.finditer(raw):
                    commodity = m.group("commodity")
                    if not any(_norm_name(x) in _norm_name(commodity) or _norm_name(commodity) in _norm_name(x) for x in _candidate_labels(crop)):
                        continue
                    modal = _num(m.group("modal")); minv = _num(m.group("min")); maxv = _num(m.group("max"))
                    if modal:
                        rows.append({"arrival_date": date.today().isoformat(), "state": state or "", "market": "e-NAM live dashboard", "min_price_qtl": minv, "max_price_qtl": maxv, "modal_price_qtl": modal})
        count, latest = _store_normalized_rows(crop, f"eNAM::{crop}", rows, ENAM_SOURCE, ENAM_RESOURCE)
        if count:
            _provider_state("enam", ENAM_SOURCE, "online", ok=True, records=count, message=f"{count} verified price rows")
            return {"ok": True, "provider": "enam", "records": count, "arrival_date": latest, "source": ENAM_SOURCE}
        msg = "Dashboard reachable, but no machine-readable price row was exposed for this crop"
        _provider_state("enam", ENAM_SOURCE, "reachable-no-feed", ok=False, message=msg)
        return {"ok": False, "error": msg}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        msg = str(exc)[:300]
        _provider_state("enam", ENAM_SOURCE, "offline", ok=False, message=msg)
        return {"ok": False, "error": msg}


_TN_CROP_LABELS = {
    "Rice": ("paddy", "rice"), "Basmati Rice": ("paddy",), "Sona Masoori Rice": ("paddy",),
    "Red Rice": ("paddy",), "Black Rice": ("paddy",), "Groundnut": ("groundnut", "peanut"),
    "Black Gram": ("blackgram", "black gram", "urad"), "Green Gram": ("greengram", "green gram", "moong"),
    "Maize": ("maize", "corn"), "Cotton": ("cotton",), "Turmeric": ("turmeric",),
    "Coconut": ("coconut",), "Onion": ("onion",), "Tomato": ("tomato",), "Banana": ("banana",),
}


def _sync_tn_agrimarket(crop: str, state: str | None = None) -> dict:
    if state and _norm_name(state) not in {"tamil nadu", "tamilnadu", "tn"}:
        return {"ok": False, "error": "Tamil Nadu provider only applies to Tamil Nadu"}
    if os.environ.get("FD_TN_MARKET_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return {"ok": False, "error": "Tamil Nadu market provider disabled"}
    labels = _TN_CROP_LABELS.get(crop, tuple(_norm_name(x) for x in _candidate_labels(crop)))
    try:
        raw = _cached_public_text("tn", TN_MARKET_URL, {"User-Agent": "Mozilla/5.0 FarmDirect/15", "Accept": "text/html,*/*"})
        text = _strip_html(raw)
        dm = re.search(r"Commodity\s+Price\s+(\d{1,2}-[A-Za-z]{3}-\d{4})", text, re.I)
        report_date = None
        if dm:
            try:
                report_date = datetime.strptime(dm.group(1), "%d-%b-%Y").date().isoformat()
            except ValueError:
                pass
        report_date = report_date or date.today().isoformat()
        # Current TN page publishes strings such as: Paddy-ADT 37 ( Max Price 2239, Min Price 0)
        matches = re.findall(r"([A-Za-z][A-Za-z0-9 /().&_-]{1,80}?)\s*\(\s*Max\s+Price\s+([0-9.,]+)\s*,\s*Min\s+Price\s+([0-9.,]+)\s*\)", text, re.I)
        rows=[]
        for label, max_raw, min_raw in matches:
            norm = _norm_name(label)
            if not any(_norm_name(x) in norm or norm.startswith(_norm_name(x)) for x in labels):
                continue
            maxv = _num(max_raw); minv = _num(min_raw)
            if not maxv:
                continue
            # TN regulated-market commodity prices on the homepage are normally ₹/quintal.
            # A very small number is treated as already ₹/kg to avoid a 100x error.
            divisor = 100.0 if maxv > 500 else 1.0
            valid_min = minv if minv and minv > 0 else maxv
            modal = (valid_min + maxv) / 2.0 if valid_min else maxv
            rows.append({
                "arrival_date": report_date, "state": "Tamil Nadu", "district": "",
                "market": "Tamil Nadu regulated markets", "variety": label.strip(), "grade": "",
                "min_price_kg": round(valid_min / divisor, 2), "max_price_kg": round(maxv / divisor, 2),
                "modal_price_kg": round(modal / divisor, 2),
            })
        count, latest = _store_normalized_rows(crop, f"TN::{crop}", rows, TN_SOURCE, TN_RESOURCE)
        if count:
            _provider_state("tn-agrimarket", TN_SOURCE, "online", ok=True, records=count, message=f"{count} Tamil Nadu rows")
            return {"ok": True, "provider": "tn-agrimarket", "records": count, "arrival_date": latest, "source": TN_SOURCE}
        msg = "Tamil Nadu portal reachable, but no matching public commodity row was found"
        _provider_state("tn-agrimarket", TN_SOURCE, "reachable-no-match", ok=False, message=msg)
        return {"ok": False, "error": msg}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        msg = str(exc)[:300]
        _provider_state("tn-agrimarket", TN_SOURCE, "offline", ok=False, message=msg)
        return {"ok": False, "error": msg}

def _browser_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://agmarknet.gov.in",
        "Referer": "https://agmarknet.gov.in/",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36 FarmDirect/13"
        ),
    }


def _agmarknet2_request(path: str, params: dict | None = None) -> object:
    query = f"?{urlencode(params or {})}" if params else ""
    url = f"{AGMARKNET2_BASE.rstrip('/')}/{path.lstrip('/')}{query}"
    timeout = int(os.environ.get("FD_MARKET_SYNC_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
    last_error = None
    # One short retry is useful on mobile networks while still keeping live-price
    # refresh bounded. Browser-like headers match the public AGMARKNET frontend.
    for attempt in range(2):
        try:
            req = Request(url, headers=_browser_headers())
            with urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.25)
    raise last_error or RuntimeError("AGMARKNET 2.0 request failed")


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _pick(d: dict, names: tuple[str, ...]):
    lower = {str(k).lower(): v for k, v in d.items()}
    for name in names:
        if name in d and d[name] not in (None, ""):
            return d[name]
        value = lower.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def _norm_name(value) -> str:
    return " ".join(str(value or "").replace("-", " ").replace("_", " ").lower().split())


def _best_named_item(items: list[dict], candidates: tuple[str, ...], kind: str) -> dict | None:
    if kind == "commodity":
        name_keys = ("cmdt_name", "commodity_name", "commodityName", "commodity", "name", "label")
        id_keys = ("cmdt_id", "commodity_id", "commodityId", "commodityid", "id", "value")
    else:
        name_keys = ("state_name", "stateName", "state", "name", "label")
        id_keys = ("state_id", "stateId", "stateid", "id", "value")
    valid=[]
    for item in items:
        name=_pick(item,name_keys); ident=_pick(item,id_keys)
        if name is not None and ident is not None:
            valid.append((item,_norm_name(name)))
    wanted=[_norm_name(x) for x in candidates if x]
    for target in wanted:
        for item,name in valid:
            if name == target:
                return item
    for target in wanted:
        for item,name in valid:
            if target and (target in name or name in target):
                return item
    # conservative token-overlap fallback
    best=None; score=0
    for target in wanted:
        t=set(target.split())
        for item,name in valid:
            n=set(name.split()); s=len(t & n)
            if s > score:
                score=s; best=item
    return best if score >= 1 else None


_AGMARKNET2_FILTER_CACHE: dict | None = None
_AGMARKNET2_FILTER_AT = 0.0


def _agmarknet2_filters() -> dict:
    global _AGMARKNET2_FILTER_CACHE, _AGMARKNET2_FILTER_AT
    if _AGMARKNET2_FILTER_CACHE and time.time() - _AGMARKNET2_FILTER_AT < 21600:
        return _AGMARKNET2_FILTER_CACHE
    payload = _agmarknet2_request("/daily-price-arrival/filters")
    if not isinstance(payload, dict):
        raise RuntimeError("AGMARKNET 2.0 filters returned an unexpected response")
    _AGMARKNET2_FILTER_CACHE = payload
    _AGMARKNET2_FILTER_AT = time.time()
    return payload


def _resolve_agmarknet2(crop: str, state: str | None) -> tuple[object, str, object, str] | None:
    payload = _agmarknet2_filters()
    dicts = list(_walk_dicts(payload))
    commodity = _best_named_item(dicts, _candidate_labels(crop), "commodity")
    if commodity:
        commodity_id = _pick(commodity, ("cmdt_id", "commodity_id", "commodityId", "commodityid", "id", "value"))
        commodity_name = str(_pick(commodity, ("cmdt_name", "commodity_name", "commodityName", "commodity", "name", "label")) or crop)
    else:
        # Metadata payloads have changed shape across AGMARKNET 2.0 releases.
        # Keep the live filters as source of truth, but do not let a temporary
        # metadata mismatch break the most common demo commodities.
        commodity_id = AGMARKNET2_COMMON_COMMODITY_IDS.get(crop)
        commodity_name = crop
        if commodity_id is None:
            return None

    state_candidates=(state,) if state else ()
    state_item = _best_named_item(dicts, state_candidates, "state") if state else None
    if state and not state_item:
        # The dedicated state endpoint is independently public and has a stable
        # paginated response. Use it when the filters response omits states.
        try:
            state_payload = _agmarknet2_request("/location/state", {"page": 1, "search": state})
            state_item = _best_named_item(list(_walk_dicts(state_payload)), state_candidates, "state")
        except Exception:
            state_item = None
    if state and not state_item:
        return None
    if state_item:
        state_id=_pick(state_item,("state_id","stateId","stateid","id","value"))
        state_name=str(_pick(state_item,("state_name","stateName","state","name","label")) or state)
        return commodity_id, commodity_name, state_id, state_name
    return commodity_id, commodity_name, None, ""


def _candidate_states_for_crop(crop: str, limit: int = 3) -> list[str]:
    rows = db.query(
        "SELECT u.state, COUNT(*) n FROM products p JOIN users u ON u.id=p.seller_id "
        "WHERE p.status='active' AND p.crop=? AND COALESCE(u.state,'')<>'' "
        "GROUP BY u.state ORDER BY n DESC,u.state LIMIT ?", (crop, max(1, min(limit, 5))))
    return [str(r["state"]) for r in rows if r["state"]]


def _extract_agmarknet2_rows(payload: object, state_hint: str | None = None) -> list[dict]:
    """Flatten the current AGMARKNET 2.0 report response.

    The date-wise/specific-commodity endpoint is hierarchical, typically:

        {"markets": [{"marketName": ..., "dates": [
          {"arrivalDate": ..., "data": [
            {"variety": ..., "minimumPrice": ...,
             "maximumPrice": ..., "modalPrice": ...}
          ]}
        ]}]}

    Older FarmDirect code only accepted a dictionary that contained the market,
    date and price together. That silently rejected every valid row from this
    nested response. Keep a permissive flat-record fallback too because the
    public backend has used more than one response shape.
    """
    rows: list[dict] = []
    seen: set[tuple] = set()
    price_keys = (
        "model_price", "modal_price", "modalPrice", "modelPrice",
        "modalprice", "modelprice"
    )

    def append_row(price_row: dict, *, market: str = "", district: str = "",
                   state: str = "", arrival: str = "", unit: str = "") -> None:
        modal = _pick(price_row, price_keys)
        if _num(modal) is None:
            return
        merged = dict(price_row)
        if market and _pick(merged, ("market_name", "marketName", "market", "apmc_name", "apmcName")) in (None, ""):
            merged["marketName"] = market
        if district and _pick(merged, ("district_name", "districtName", "district")) in (None, ""):
            merged["districtName"] = district
        if state and _pick(merged, ("state_name", "stateName", "state")) in (None, ""):
            merged["stateName"] = state
        if arrival and _pick(merged, ("arrival_date", "arrivalDate", "date")) in (None, ""):
            merged["arrivalDate"] = arrival
        if unit and _pick(merged, ("unit_name_price", "price_unit", "unitPrice", "unit")) in (None, ""):
            merged["unit_name_price"] = unit
        key = (
            str(_pick(merged, ("state_name", "stateName", "state")) or ""),
            str(_pick(merged, ("district_name", "districtName", "district")) or ""),
            str(_pick(merged, ("market_name", "marketName", "market", "apmc_name", "apmcName")) or ""),
            str(_pick(merged, ("arrival_date", "arrivalDate", "date")) or ""),
            str(_pick(merged, ("variety_name", "varietyName", "variety")) or ""),
            str(modal),
        )
        if key not in seen:
            seen.add(key)
            rows.append(merged)

    # Current hierarchical response. Search recursively because some deployments
    # wrap it in {data: ...} or {result: ...}.
    for container in _walk_dicts(payload):
        markets = _pick(container, ("markets", "marketData", "market_data"))
        if not isinstance(markets, list):
            continue
        for market_row in markets:
            if not isinstance(market_row, dict):
                continue
            market_name = str(_pick(market_row, ("market_name", "marketName", "market", "apmc_name", "apmcName")) or "")
            district_name = str(_pick(market_row, ("district_name", "districtName", "district")) or "")
            state_name = str(_pick(market_row, ("state_name", "stateName", "state")) or state_hint or "")
            market_unit = str(_pick(market_row, ("unit_name_price", "price_unit", "unitPrice", "unit")) or "")
            dates = _pick(market_row, ("dates", "dateData", "date_data"))
            if not isinstance(dates, list):
                # Some variants flatten the price directly at market level.
                append_row(market_row, market=market_name, district=district_name,
                           state=state_name, unit=market_unit)
                continue
            for date_row in dates:
                if not isinstance(date_row, dict):
                    continue
                arrival = str(_pick(date_row, ("arrival_date", "arrivalDate", "date", "report_date", "reportDate")) or "")
                date_unit = str(_pick(date_row, ("unit_name_price", "price_unit", "unitPrice", "unit")) or market_unit or "")
                details = _pick(date_row, ("data", "prices", "records", "varieties"))
                if isinstance(details, list):
                    for price_row in details:
                        if isinstance(price_row, dict):
                            append_row(price_row, market=market_name, district=district_name,
                                       state=state_name, arrival=arrival, unit=date_unit)
                else:
                    append_row(date_row, market=market_name, district=district_name,
                               state=state_name, arrival=arrival, unit=date_unit)

    # Generic context-propagating fallback. This also handles API wrappers that
    # rename/remove the top-level ``markets`` key while keeping the same nested
    # market -> date -> price relationship.
    def walk_with_context(value, ctx: dict[str, str]) -> None:
        if isinstance(value, dict):
            next_ctx = dict(ctx)
            mapping = {
                "market": ("market_name", "marketName", "market", "apmc_name", "apmcName"),
                "district": ("district_name", "districtName", "district"),
                "state": ("state_name", "stateName", "state"),
                "arrival": ("arrival_date", "arrivalDate", "date", "report_date", "reportDate"),
                "unit": ("unit_name_price", "price_unit", "unitPrice", "unit"),
            }
            for target, names in mapping.items():
                found = _pick(value, names)
                if found not in (None, ""):
                    next_ctx[target] = str(found)
            if _num(_pick(value, price_keys)) is not None:
                append_row(value, market=next_ctx.get("market", ""),
                           district=next_ctx.get("district", ""),
                           state=next_ctx.get("state", state_hint or ""),
                           arrival=next_ctx.get("arrival", ""),
                           unit=next_ctx.get("unit", ""))
            for child in value.values():
                walk_with_context(child, next_ctx)
        elif isinstance(value, list):
            for child in value:
                walk_with_context(child, ctx)

    walk_with_context(payload, {"state": state_hint or ""})
    return rows


def _store_agmarknet2_records(crop: str, api_commodity: str, payload: object, state_hint: str | None = None) -> tuple[int, str | None]:
    raw_rows=_extract_agmarknet2_rows(payload, state_hint=state_hint)
    normalized=[]
    latest=None
    for r in raw_rows:
        arrival=_parse_date(str(_pick(r,("arrival_date","arrivalDate","date","report_date","reportDate")) or ""))
        if not arrival:
            # Some API variants return ISO datetime strings.
            raw=str(_pick(r,("arrival_date","arrivalDate","date")) or "")[:10]
            arrival=_parse_date(raw)
        min_q=_num(_pick(r,("min_price","minPrice","minimum_price","minimumPrice","minprice")))
        max_q=_num(_pick(r,("max_price","maxPrice","maximum_price","maximumPrice","maxprice")))
        modal_q=_num(_pick(r,("model_price","modal_price","modalPrice","modelPrice","modalprice","modelprice")))
        if not arrival or not modal_q:
            continue
        unit=str(_pick(r,("unit_name_price","price_unit","unitPrice","unit")) or "Rs./Quintal").lower()
        # AGMARKNET report prices are normally per quintal. Respect kg-labelled responses if provided.
        divisor=1.0 if ("kg" in unit and "quint" not in unit) else 100.0
        latest=max(latest or arrival,arrival)
        normalized.append({
            "state": str(_pick(r,("state_name","stateName","state")) or state_hint or ""),
            "district": str(_pick(r,("district_name","districtName","district")) or ""),
            "market": str(_pick(r,("market_name","marketName","market","apmc_name","apmcName","apmc")) or ""),
            "variety": str(_pick(r,("variety_name","varietyName","variety")) or ""),
            "grade": str(_pick(r,("grade_name","gradeName","grade")) or ""),
            "arrival": arrival,
            "min_q": min_q * (100.0 if divisor == 1.0 else 1.0) if min_q else None,
            "max_q": max_q * (100.0 if divisor == 1.0 else 1.0) if max_q else None,
            "modal_q": modal_q * (100.0 if divisor == 1.0 else 1.0),
            "min_kg": round(min_q / divisor,2) if min_q else None,
            "max_kg": round(max_q / divisor,2) if max_q else None,
            "modal_kg": round(modal_q / divisor,2),
        })
    if not normalized:
        return 0, latest
    fetched=_now_iso()
    rows=[(crop,api_commodity,x["state"],x["district"],x["market"],x["variety"],x["grade"],x["arrival"],x["min_q"],x["max_q"],x["modal_q"],x["min_kg"],x["max_kg"],x["modal_kg"],AGMARKNET2_SOURCE,AGMARKNET2_RESOURCE,fetched) for x in normalized]
    conn=db.get_db()
    try:
        conn.executemany(
            "INSERT INTO mandi_prices (crop,api_commodity,state,district,market,variety,source_grade,arrival_date,min_price_qtl,max_price_qtl,modal_price_qtl,min_price_kg,max_price_kg,modal_price_kg,source,resource_id,fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(crop,api_commodity,state,district,market,variety,source_grade,arrival_date) DO UPDATE SET "
            "min_price_qtl=excluded.min_price_qtl,max_price_qtl=excluded.max_price_qtl,modal_price_qtl=excluded.modal_price_qtl,min_price_kg=excluded.min_price_kg,max_price_kg=excluded.max_price_kg,modal_price_kg=excluded.modal_price_kg,source=excluded.source,resource_id=excluded.resource_id,fetched_at=excluded.fetched_at",
            rows)
        conn.commit()
    finally:
        conn.close()
    _invalidate_reference_cache(crop)
    return len(rows),latest


def _sync_agmarknet2(crop: str, state: str | None = None) -> dict:
    states=[state] if state else _candidate_states_for_crop(crop, limit=3)
    if not states:
        # A compact nationwide fallback that keeps API load bounded.
        states=["Tamil Nadu","Maharashtra","Karnataka"]
    total=0; latest=None; used=[]; last_error="No AGMARKNET 2.0 records returned"
    for st in states:
        try:
            resolved=_resolve_agmarknet2(crop,st)
            if not resolved:
                last_error=f"Could not resolve {crop} / {st} in AGMARKNET 2.0 filters"
                continue
            commodity_id,commodity_name,state_id,state_name=resolved
            today=date.today()
            payload=None
            for delta_month in (0,1):
                y=today.year; m=today.month-delta_month
                if m <= 0:
                    m += 12; y -= 1
                params={"year":y,"month":m,"stateId":state_id,"commodityId":commodity_id,"includeExcel":"false"}
                payload=_agmarknet2_request("/prices-and-arrivals/date-wise/specific-commodity",params)
                count, d=_store_agmarknet2_records(crop,commodity_name,payload,state_name)
                if count:
                    total += count; latest=max(latest or d,d) if d else latest; used.append(state_name); break
            time.sleep(.08)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            last_error=str(exc)[:300]
    return {"ok": total>0,"records":total,"arrival_date":latest,"states":used,"source":AGMARKNET2_SOURCE,"error":None if total else last_error}


def _request_records(commodity: str, state: str | None = None,
                     limit: int = 100) -> list[dict]:
    key = api_key()
    if not key:
        raise RuntimeError("DATA_GOV_IN_API_KEY is not configured")
    params = {
        "api-key": key,
        "format": "json",
        "offset": 0,
        "limit": max(1, min(int(limit), 500)),
        "filters[commodity]": commodity,
    }
    if state:
        params["filters[state.keyword]"] = state
    req = Request(f"{API_URL}?{urlencode(params)}",
                  headers={"User-Agent": "FarmDirect-SIH/12 market-sync"})
    timeout = int(os.environ.get("FD_MARKET_SYNC_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
    with urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    records = payload.get("records") or []
    return [r for r in records if isinstance(r, dict)]


def _store_records(crop: str, api_commodity: str, records: list[dict]) -> tuple[int, str | None]:
    rows = []
    latest = None
    fetched_at = _now_iso()
    for r in records:
        arrival = _parse_date(r.get("arrival_date"))
        min_q = _num(r.get("min_price"))
        max_q = _num(r.get("max_price"))
        modal_q = _num(r.get("modal_price"))
        if not arrival or not modal_q:
            continue
        latest = max(latest or arrival, arrival)
        rows.append((
            crop, api_commodity, r.get("state") or "", r.get("district") or "",
            r.get("market") or "", r.get("variety") or "", r.get("grade") or "",
            arrival, min_q, max_q, modal_q,
            round(min_q / 100, 2) if min_q else None,
            round(max_q / 100, 2) if max_q else None,
            round(modal_q / 100, 2), SOURCE_NAME, RESOURCE_ID, fetched_at,
        ))
    if rows:
        conn = db.get_db()
        try:
            conn.executemany(
                "INSERT INTO mandi_prices (crop,api_commodity,state,district,market,variety,source_grade,"
                "arrival_date,min_price_qtl,max_price_qtl,modal_price_qtl,min_price_kg,max_price_kg,"
                "modal_price_kg,source,resource_id,fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(crop,api_commodity,state,district,market,variety,source_grade,arrival_date) "
                "DO UPDATE SET min_price_qtl=excluded.min_price_qtl,max_price_qtl=excluded.max_price_qtl,"
                "modal_price_qtl=excluded.modal_price_qtl,min_price_kg=excluded.min_price_kg,"
                "max_price_kg=excluded.max_price_kg,modal_price_kg=excluded.modal_price_kg,"
                "fetched_at=excluded.fetched_at",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
    _invalidate_reference_cache(crop)
    return len(rows), latest


def _last_state(crop: str, state: str | None) -> dict | None:
    ensure_schema()
    row = db.query("SELECT * FROM market_sync_state WHERE sync_key=?",
                   (_sync_key(crop, state),), one=True)
    return dict(row) if row else None


def _is_sync_fresh(sync: dict | None, ttl_minutes: int) -> bool:
    if not sync or not sync.get("last_success_at"):
        return False
    try:
        ts = datetime.fromisoformat(sync["last_success_at"])
        return datetime.now() - ts < timedelta(minutes=ttl_minutes)
    except (ValueError, TypeError):
        return False



def sync_crop(crop: str, state: str | None = None, force: bool = False,
              limit: int = 100) -> dict:
    """Refresh one crop from the freshest official Indian mandi source.

    FarmDirect's primary live path is the public AGMARKNET 2.0 report backend,
    which is the same backend used by the official Agmarknet web application.
    The underlying government observation cadence is daily/as-reported by APMCs,
    so "live" means the freshest currently published official mandi observation,
    not a fabricated second-by-second quote.
    """
    ensure_schema()
    key = _sync_key(crop, state)
    if os.environ.get("FD_MARKET_SYNC_TTL_MIN") is not None:
        ttl_minutes = max(1, int(os.environ.get("FD_MARKET_SYNC_TTL_MIN", DEFAULT_TTL_MINUTES)))
    elif os.environ.get("FD_MARKET_SYNC_TTL_HOURS") is not None:
        ttl_minutes = max(1, int(float(os.environ.get("FD_MARKET_SYNC_TTL_HOURS", "1")) * 60))
    else:
        ttl_minutes = DEFAULT_TTL_MINUTES
    previous = _last_state(crop, state)
    if not force and _is_sync_fresh(previous, ttl_minutes):
        cached = get_reference_price(crop, state)
        return {"ok": True, "cached": True, "status": "fresh-cache", "reference": cached, **previous}

    attempted_at = _now_iso()
    errors: list[str] = []

    # 1) AGMARKNET 2.0 — verified public report backend, keyless and nationwide.
    if os.environ.get("FD_AGMARKNET2_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}:
        try:
            direct = _sync_agmarknet2(crop, state)
            if direct.get("ok"):
                _provider_state("agmarknet2", AGMARKNET2_SOURCE, "online", ok=True,
                                records=direct.get("records", 0), message="Fresh official mandi report rows")
                _record_sync_success(key, crop, state, "success-agmarknet2", attempted_at,
                                     direct.get("arrival_date"), direct.get("records", 0), crop)
                return {"ok": True, "status": "success", "provider": "agmarknet2", "crop": crop, "state": state, **direct}
            msg = direct.get("error") or "AGMARKNET 2.0 returned no records"
            _provider_state("agmarknet2", AGMARKNET2_SOURCE, "no-data", ok=False, message=msg)
            errors.append(f"AGMARKNET 2.0: {msg}")
        except Exception as exc:
            msg = str(exc)[:220]
            _provider_state("agmarknet2", AGMARKNET2_SOURCE, "offline", ok=False, message=msg)
            errors.append(f"AGMARKNET 2.0: {msg}")

    # 2) data.gov.in official AGMARKNET daily dataset when a free user key is configured.
    if api_key():
        last_error = "No official mandi records returned"
        for commodity in _candidate_labels(crop):
            try:
                records = _request_records(commodity, state=state, limit=limit)
                count, latest = _store_records(crop, commodity, records)
                if count:
                    _provider_state("data-gov", SOURCE_NAME, "online", ok=True, records=count,
                                    message="Official OGD daily mandi feed")
                    _record_sync_success(key, crop, state, "success-datagov", attempted_at,
                                         latest, count, commodity)
                    return {"ok": True, "status": "success", "provider": "data-gov", "crop": crop, "state": state,
                            "records": count, "arrival_date": latest, "api_commodity": commodity, "source": SOURCE_NAME}
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
                last_error = str(exc)[:300]
        _provider_state("data-gov", SOURCE_NAME, "failed", ok=False, message=last_error)
        errors.append(f"data.gov.in: {last_error}")
    else:
        _provider_state("data-gov", SOURCE_NAME, "not-configured", ok=False,
                        message="Optional API key not configured; AGMARKNET 2.0 remains active")

    # 3) Tamil Nadu's public regulated-market page is a useful local fallback.
    try:
        direct = _sync_tn_agrimarket(crop, state)
        if direct.get("ok"):
            _record_sync_success(key, crop, state, "success-tn-agrimarket", attempted_at,
                                 direct.get("arrival_date"), direct.get("records", 0), crop)
            return {"ok": True, "status": "success", "provider": "tn-agrimarket", "crop": crop, "state": state, **direct}
        if direct.get("error") and "only applies" not in direct.get("error", ""):
            errors.append(f"Tamil Nadu AgriMarket: {direct.get('error')}")
    except Exception as exc:
        errors.append(f"Tamil Nadu AgriMarket: {str(exc)[:220]}")

    # 4) e-NAM adapter is opt-in because the public dashboard normally renders
    # dynamically and does not consistently expose a machine-readable price feed.
    if os.environ.get("FD_ENAM_ENABLED", "0").strip().lower() not in {"0", "false", "no", "off"}:
        try:
            direct = _sync_enam(crop, state)
            if direct.get("ok"):
                _record_sync_success(key, crop, state, "success-enam", attempted_at,
                                     direct.get("arrival_date"), direct.get("records", 0), crop)
                return {"ok": True, "status": "success", "provider": "enam", "crop": crop, "state": state, **direct}
            errors.append(f"e-NAM: {direct.get('error') or 'no verified rows'}")
        except Exception as exc:
            errors.append(f"e-NAM: {str(exc)[:220]}")

    err = " | ".join(e for e in errors if e)[:700] or "Official sources unavailable"
    db.execute(
        "INSERT INTO market_sync_state (sync_key,crop,state,status,last_attempt_at,records_received,error_message) "
        "VALUES (?,?,?,?,?,0,?) ON CONFLICT(sync_key) DO UPDATE SET status=excluded.status,"
        "last_attempt_at=excluded.last_attempt_at,records_received=0,error_message=excluded.error_message",
        (key, crop, state, "failed", attempted_at, err),
    )
    cached = get_reference_price(crop, state)
    return {"ok": bool(cached), "status": "cached-fallback" if cached else "failed", "crop": crop, "state": state,
            "cached": cached, "provider": "cache" if cached else None, "error": err}


def _record_sync_success(key: str, crop: str, state: str | None, status: str,
                         attempted_at: str, arrival_date: str | None,
                         records: int, commodity: str) -> None:
    db.execute(
        "INSERT INTO market_sync_state (sync_key,crop,state,status,last_attempt_at,last_success_at,"
        "last_arrival_date,records_received,api_commodity,error_message) VALUES (?,?,?,?,?,?,?,?,?,NULL) "
        "ON CONFLICT(sync_key) DO UPDATE SET status=excluded.status,last_attempt_at=excluded.last_attempt_at,"
        "last_success_at=excluded.last_success_at,last_arrival_date=excluded.last_arrival_date,"
        "records_received=excluded.records_received,api_commodity=excluded.api_commodity,error_message=NULL",
        (key, crop, state, status, attempted_at, _now_iso(), arrival_date, int(records or 0), commodity),
    )


def _age_days(arrival_date: str | None) -> int | None:
    if not arrival_date:
        return None
    try:
        return max((date.today() - date.fromisoformat(arrival_date)).days, 0)
    except ValueError:
        return None



def _get_reference_price_uncached(crop: str, state: str | None = None) -> dict | None:
    """Read the latest verified official price using provider precedence."""
    ensure_schema()
    args = [crop]
    state_clause = ""
    if state:
        state_clause = " AND state=?"
        args.append(state)
    latest = db.query(
        "SELECT MAX(arrival_date) d FROM mandi_prices WHERE crop=?" + state_clause,
        args, one=True)
    if (not latest or not latest["d"]) and state:
        ref = get_reference_price(crop, None)
        if ref:
            ref = dict(ref)
            ref["requested_state"] = state
            ref["state_fallback"] = True
        return ref
    if not latest or not latest["d"]:
        return None
    d = latest["d"]
    qargs = [crop, d]
    state_clause2 = ""
    if state:
        state_clause2 = " AND state=?"
        qargs.append(state)

    source_row = db.query(
        "SELECT source, COUNT(*) n FROM mandi_prices WHERE crop=? AND arrival_date=?" + state_clause2 +
        " GROUP BY source ORDER BY CASE source "
        "WHEN ? THEN 1 WHEN ? THEN 2 WHEN ? THEN 3 WHEN ? THEN 4 ELSE 9 END, n DESC LIMIT 1",
        qargs + [AGMARKNET2_SOURCE, SOURCE_NAME, TN_SOURCE, ENAM_SOURCE], one=True)
    source = source_row["source"] if source_row else None
    source_clause = " AND source=?" if source else ""
    qargs_source = qargs + ([source] if source else [])
    agg = db.query(
        "SELECT MIN(min_price_kg) low, MAX(max_price_kg) high, AVG(modal_price_kg) modal,"
        "COUNT(*) observations, MAX(fetched_at) fetched_at FROM mandi_prices "
        "WHERE crop=? AND arrival_date=?" + state_clause2 + source_clause,
        qargs_source, one=True)
    sample = db.query(
        "SELECT state,district,market,variety,source_grade,api_commodity,source,fetched_at "
        "FROM mandi_prices WHERE crop=? AND arrival_date=?" + state_clause2 + source_clause +
        " ORDER BY modal_price_kg DESC LIMIT 1",
        qargs_source, one=True)
    if not agg or agg["modal"] is None:
        return None
    age = _age_days(d)
    provider = {
        ENAM_SOURCE: "e-NAM",
        AGMARKNET2_SOURCE: "AGMARKNET 2.0",
        TN_SOURCE: "Tamil Nadu AgriMarket",
        SOURCE_NAME: "data.gov.in",
    }.get(source or "", source or "Official market source")
    return {
        "crop": crop,
        "low": round(float(agg["low"] or agg["modal"]), 2),
        "high": round(float(agg["high"] or agg["modal"]), 2),
        "modal": round(float(agg["modal"]), 2),
        "observations": int(agg["observations"] or 0),
        "arrival_date": d,
        "fetched_at": agg["fetched_at"],
        "state": sample["state"] if sample else state,
        "district": sample["district"] if sample else None,
        "market": sample["market"] if sample else None,
        "variety": sample["variety"] if sample else None,
        "source_grade": sample["source_grade"] if sample else None,
        "api_commodity": sample["api_commodity"] if sample else crop,
        "source": source or (sample["source"] if sample else SOURCE_NAME),
        "provider": provider,
        "age_days": age,
        "status": "official" if age is not None and age <= 2 else "cached",
        "is_today": age == 0,
        "reporting_label": "TODAY'S OFFICIAL MANDI" if age == 0 else "LATEST OFFICIAL MANDI",
        "unit": "kg",
        "state_fallback": False,
    }


def get_reference_price(crop: str, state: str | None = None) -> dict | None:
    """Return a verified reference with a tiny process-local read cache.

    Product grids can ask for the same crop/state many times during one paint.
    Caching successful reads for a few seconds avoids dozens of identical SQLite
    aggregate queries; successful provider writes invalidate the cache instantly.
    """
    cache_key = (str(crop), str(state or ""))
    now = time.monotonic()
    with _REFERENCE_CACHE_LOCK:
        hit = _REFERENCE_CACHE.get(cache_key)
        if hit and now - hit[0] < REFERENCE_CACHE_SECONDS:
            return dict(hit[1])
    ref = _get_reference_price_uncached(crop, state)
    if ref:
        with _REFERENCE_CACHE_LOCK:
            _REFERENCE_CACHE[cache_key] = (now, dict(ref))
        return dict(ref)
    return None


def get_recent_series(crop: str, state: str | None = None, days: int = 14) -> list[dict]:
    ensure_schema()
    args = [crop]
    state_clause = ""
    if state:
        state_clause = " AND state=?"
        args.append(state)
    rows = db.query(
        "SELECT arrival_date, ROUND(AVG(modal_price_kg),2) modal, ROUND(MIN(min_price_kg),2) low,"
        "ROUND(MAX(max_price_kg),2) high, COUNT(*) observations FROM mandi_prices "
        "WHERE crop=?" + state_clause + " GROUP BY arrival_date ORDER BY arrival_date DESC LIMIT ?",
        args + [max(2, min(int(days), 60))])
    return [dict(r) for r in reversed(rows)]


def get_market_rows(crop: str, state: str | None = None, limit: int = 20) -> list[dict]:
    ensure_schema()
    args = [crop]
    state_clause = ""
    if state:
        state_clause = " AND state=?"
        args.append(state)
    rows = db.query(
        "SELECT * FROM mandi_prices WHERE crop=?" + state_clause +
        " ORDER BY arrival_date DESC, modal_price_kg DESC LIMIT ?",
        args + [max(1, min(int(limit), 100))])
    return [dict(r) for r in rows]



def status_summary() -> dict:
    ensure_schema()
    last = db.query("SELECT MAX(last_success_at) t FROM market_sync_state WHERE status LIKE 'success%'", one=True)
    totals = db.query(
        "SELECT MAX(arrival_date) latest, COUNT(*) row_count, COUNT(DISTINCT crop) crop_count "
        "FROM mandi_prices", one=True)
    provider_rows = db.query(
        "SELECT provider,label,status,last_attempt_at,last_success_at,records_received,message "
        "FROM market_provider_state ORDER BY CASE provider "
        "WHEN 'agmarknet2' THEN 1 WHEN 'data-gov' THEN 2 WHEN 'tn-agrimarket' THEN 3 WHEN 'enam' THEN 4 ELSE 9 END")
    seen = {r["provider"] for r in provider_rows}
    defaults = [
        ("agmarknet2", AGMARKNET2_SOURCE, "not-tested"),
        ("data-gov", SOURCE_NAME, "not-configured" if not api_key() else "not-tested"),
        ("tn-agrimarket", TN_SOURCE, "not-tested"),
        ("enam", ENAM_SOURCE, "disabled" if os.environ.get("FD_ENAM_ENABLED", "0").strip().lower() in {"0","false","no","off"} else "not-tested"),
    ]
    providers = [dict(r) for r in provider_rows]
    for key, label, status in defaults:
        if key not in seen:
            providers.append({"provider": key, "label": label, "status": status,
                              "last_attempt_at": None, "last_success_at": None,
                              "records_received": 0, "message": None})
    order = {"agmarknet2": 1, "data-gov": 2, "tn-agrimarket": 3, "enam": 4}
    providers.sort(key=lambda r: order.get(r.get("provider"), 9))
    if os.environ.get("VERCEL"):
        interval = 1440  # Vercel Hobby cron minimum: once per day
        sync_mode = "vercel-daily-cron+on-demand"
    else:
        interval = max(int(os.environ.get("FD_MARKET_SYNC_INTERVAL_MIN", "15")), 5)
        sync_mode = "background-daemon+on-demand"
    return {
        "configured": is_configured(),
        "source": "AGMARKNET 2.0 → data.gov.in → Tamil Nadu AgriMarket → optional e-NAM → verified cache",
        "resource_id": "farmdirect-multi-source-v16",
        "data_gov_key_configured": bool(api_key()),
        "last_success_at": last["t"] if last else None,
        "latest_arrival_date": totals["latest"] if totals else None,
        "cached_rows": int(totals["row_count"] if totals else 0),
        "cached_crops": int(totals["crop_count"] if totals else 0),
        "providers": providers,
        "sync_mode": sync_mode,
        "auto_sync_interval_min": interval,
    }


def sync_popular_crops(max_crops: int = 12) -> dict:
    """Refresh popular active marketplace crops within a conservative API budget."""
    if not is_configured():
        return {"ok": False, "status": "api-key-missing", "synced": 0}
    rows = db.query(
        "SELECT crop, COUNT(*) n FROM products WHERE status='active' GROUP BY crop "
        "ORDER BY n DESC, crop LIMIT ?", (max(1, min(int(max_crops), 30)),))
    ok = 0
    failed = 0
    for r in rows:
        result = sync_crop(r["crop"], force=False, limit=100)
        ok += 1 if result.get("ok") else 0
        failed += 0 if result.get("ok") else 1
        time.sleep(0.15)
    return {"ok": ok > 0, "status": "complete", "synced": ok, "failed": failed}


def queue_crops(crops, state: str | None = None) -> int:
    """Queue visible crops for non-blocking refresh on persistent runtimes.

    A short per-crop cooldown prevents repeated page widgets from queueing the
    same government request over and over while a previous refresh is already
    pending or has just run. This matters on Termux/mobile without changing any
    visible UI behavior.
    """
    if os.environ.get("VERCEL") or not is_configured():
        return 0
    added = 0
    now = time.monotonic()
    with _QUEUE_LOCK:
        existing = set(_PENDING_CROPS)
        # Keep the cooldown map bounded for long-running demos.
        stale = [item for item, ts in _RECENTLY_QUEUED.items() if now - ts > QUEUE_COOLDOWN_SECONDS * 4]
        for item in stale:
            _RECENTLY_QUEUED.pop(item, None)
        for crop in crops:
            item = (str(crop), state)
            last = _RECENTLY_QUEUED.get(item, 0.0)
            if item in existing or now - last < QUEUE_COOLDOWN_SECONDS:
                continue
            if len(_PENDING_CROPS) >= 48:
                break
            _PENDING_CROPS.append(item)
            _RECENTLY_QUEUED[item] = now
            existing.add(item)
            added += 1
    return added


def _pop_queued_crop():
    with _QUEUE_LOCK:
        return _PENDING_CROPS.pop(0) if _PENDING_CROPS else None


def start_background_sync() -> bool:
    """Start the lightweight multi-source auto-refresh daemon.

    Disabled on Vercel because function instances are ephemeral.
    """
    global _BG_STARTED
    if os.environ.get("VERCEL") or not is_configured():
        return False
    with _BG_LOCK:
        if _BG_STARTED:
            return True
        _BG_STARTED = True

    def worker():
        # Small startup delay lets Flask finish booting on slower Termux phones.
        time.sleep(3)
        interval = max(int(os.environ.get("FD_MARKET_SYNC_INTERVAL_MIN", "15")), 5) * 60
        max_crops = max(min(int(os.environ.get("FD_MARKET_SYNC_CROPS", "12")), 30), 1)
        # Do not start a full multi-crop network/database refresh while the
        # first screen is still becoming interactive. Visible/explicit crops
        # continue to use the existing queue immediately; the broader periodic
        # refresh begins shortly after startup.
        next_periodic = time.time() + min(interval, 90)
        while True:
            queued = _pop_queued_crop()
            if queued:
                try:
                    sync_crop(queued[0], state=queued[1], force=False, limit=120)
                except Exception:
                    pass
                time.sleep(.25)
                continue
            if time.time() >= next_periodic:
                try:
                    sync_popular_crops(max_crops=max_crops)
                except Exception:
                    pass
                next_periodic = time.time() + interval
            time.sleep(2)

    threading.Thread(target=worker, name="farmdirect-market-sync", daemon=True).start()
    return True
