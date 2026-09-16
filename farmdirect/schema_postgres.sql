-- ============================================================
-- FarmDirect — Digital Agricultural Marketplace
-- PostgreSQL Schema (Vercel / Supabase production)
-- ============================================================


-- ---------- Users & Profiles ----------
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    phone         TEXT,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('farmer','fpo','consumer','buyer','admin')),
    city          TEXT,
    state         TEXT,
    lat           REAL,
    lng           REAL,
    active        INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS farmers (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id),
    farm_name       TEXT,
    farm_size_acres REAL DEFAULT 2.0,
    crops_grown     TEXT,                      -- comma separated
    bio             TEXT,
    rating          REAL DEFAULT 4.5,
    verified        INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fpos (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id),
    fpo_name     TEXT NOT NULL,
    member_count INTEGER DEFAULT 50,
    district     TEXT,
    state        TEXT,
    description  TEXT,
    verified     INTEGER DEFAULT 1
);

-- ---------- Marketplace ----------
CREATE TABLE IF NOT EXISTS products (
    id           BIGSERIAL PRIMARY KEY,
    seller_id    BIGINT NOT NULL REFERENCES users(id),
    crop         TEXT NOT NULL,
    name         TEXT NOT NULL,
    category     TEXT DEFAULT 'Vegetables',
    grade        TEXT NOT NULL CHECK (grade IN ('A','B','C')),
    quantity_kg  REAL NOT NULL,
    price_per_kg REAL NOT NULL,
    harvest_date TEXT,
    organic      INTEGER DEFAULT 0,
    description  TEXT,
    unit_label   TEXT DEFAULT 'kg',
    status       TEXT DEFAULT 'active' CHECK (status IN ('active','sold_out','removed')),
    created_at   TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

-- ---------- Cart ----------
CREATE TABLE IF NOT EXISTS cart_items (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    product_id  BIGINT NOT NULL REFERENCES products(id),
    quantity_kg REAL NOT NULL,
    created_at  TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

-- ---------- Orders ----------
CREATE TABLE IF NOT EXISTS orders (
    id               BIGSERIAL PRIMARY KEY,
    order_code       TEXT UNIQUE NOT NULL,          -- e.g. FD-260831-0142
    buyer_id         BIGINT NOT NULL REFERENCES users(id),
    buyer_type       TEXT DEFAULT 'consumer',       -- consumer / bulk
    total_amount     REAL NOT NULL,
    platform_fee     REAL DEFAULT 0,
    delivery_fee     REAL DEFAULT 0,
    delivery_address TEXT,
    delivery_city    TEXT,
    delivery_pincode TEXT,
    delivery_lat     REAL,
    delivery_lng     REAL,
    order_type       TEXT DEFAULT 'retail',         -- retail / bulk
    status           TEXT DEFAULT 'pending' CHECK (status IN
                       ('pending','confirmed','rejected','picked_up','in_transit','delivered','cancelled')),
    created_at       TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')),
    updated_at       TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES orders(id),
    product_id  BIGINT NOT NULL REFERENCES products(id),
    farmer_id   BIGINT NOT NULL REFERENCES users(id),
    crop        TEXT,
    grade       TEXT,
    quantity_kg REAL NOT NULL,
    unit_price  REAL NOT NULL,
    subtotal    REAL NOT NULL,
    item_status TEXT DEFAULT 'pending' CHECK (item_status IN
                  ('pending','accepted','rejected')),
    farmer_note TEXT
);

-- ---------- Payments & Earnings ----------
CREATE TABLE IF NOT EXISTS payments (
    id           BIGSERIAL PRIMARY KEY,
    order_id     BIGINT NOT NULL REFERENCES orders(id),
    buyer_id     BIGINT,
    farmer_id    BIGINT,
    amount       REAL NOT NULL,        -- total paid by buyer
    farmer_share REAL DEFAULT 0,       -- credited to farmer on delivery
    platform_fee REAL DEFAULT 0,
    delivery_fee REAL DEFAULT 0,
    method       TEXT DEFAULT 'UPI',
    status       TEXT DEFAULT 'pending' CHECK (status IN ('pending','completed','refunded')),
    txn_code     TEXT,
    created_at   TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

-- ---------- Logistics ----------
CREATE TABLE IF NOT EXISTS deliveries (
    id             BIGSERIAL PRIMARY KEY,
    order_id       BIGINT NOT NULL REFERENCES orders(id),
    pickup_name    TEXT,
    pickup_lat     REAL,
    pickup_lng     REAL,
    drop_name      TEXT,
    drop_lat       REAL,
    drop_lng       REAL,
    distance_km    REAL DEFAULT 0,
    eta_minutes    INTEGER DEFAULT 0,
    driver_name    TEXT,
    driver_phone   TEXT,
    vehicle        TEXT,
    status         TEXT DEFAULT 'pending' CHECK (status IN
                     ('pending','confirmed','picked_up','in_transit','delivered')),
    route_id       BIGINT,             -- assigned optimized route
    updated_at     TEXT
);

-- ---------- Quotations (Bulk Buyers) ----------
CREATE TABLE IF NOT EXISTS quotes (
    id          BIGSERIAL PRIMARY KEY,
    buyer_id    BIGINT NOT NULL REFERENCES users(id),
    crop        TEXT NOT NULL,
    quantity_kg REAL NOT NULL,
    grade       TEXT DEFAULT 'A',
    city        TEXT,
    status      TEXT DEFAULT 'open' CHECK (status IN ('open','converted','closed')),
    created_at  TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS quote_responses (
    id           BIGSERIAL PRIMARY KEY,
    quote_id     BIGINT NOT NULL REFERENCES quotes(id),
    seller_id    BIGINT NOT NULL REFERENCES users(id),
    price_per_kg REAL NOT NULL,
    total_amount REAL,
    eta_days     INTEGER DEFAULT 3,
    status       TEXT DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined'))
);

-- ---------- AI: Demand Forecasts ----------
CREATE TABLE IF NOT EXISTS demand_forecasts (
    id               BIGSERIAL PRIMARY KEY,
    crop             TEXT NOT NULL,
    city             TEXT,
    horizon_days     INTEGER NOT NULL,     -- 7 or 30
    current_demand   REAL,                 -- kg / week (last 4 weeks avg)
    predicted_demand REAL,                 -- kg / week (forecast)
    trend            TEXT,                 -- Increasing / Stable / Decreasing
    confidence       REAL,                 -- 0..1
    payload          TEXT,                 -- JSON series for Chart.js
    generated_at     TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

-- ---------- AI: Price Recommendations ----------
CREATE TABLE IF NOT EXISTS price_recommendations (
    id                BIGSERIAL PRIMARY KEY,
    crop              TEXT NOT NULL,
    grade             TEXT,
    quantity_kg       REAL,
    current_price     REAL,
    suggested_price   REAL,
    consumer_price    REAL,
    mandi_price       REAL,
    earnings_gain_pct REAL,
    factors           TEXT,                -- JSON factor breakdown
    created_at        TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

-- ---------- Sales History (feeds the AI engine) ----------
CREATE TABLE IF NOT EXISTS sales_history (
    id          BIGSERIAL PRIMARY KEY,
    crop        TEXT NOT NULL,
    city        TEXT,
    date        TEXT NOT NULL,             -- YYYY-MM-DD
    quantity_kg REAL NOT NULL,
    avg_price   REAL
);

CREATE INDEX IF NOT EXISTS idx_sales_crop_date ON sales_history(crop, date);
CREATE INDEX IF NOT EXISTS idx_users_role_city ON users(role, city);
CREATE INDEX IF NOT EXISTS idx_users_lat_lng ON users(lat, lng);
CREATE INDEX IF NOT EXISTS idx_products_seller_status ON products(seller_id, status);
CREATE INDEX IF NOT EXISTS idx_cart_user ON cart_items(user_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_crop_status ON products(crop, status);
CREATE INDEX IF NOT EXISTS idx_products_category_status ON products(category, status);
CREATE INDEX IF NOT EXISTS idx_orders_buyer    ON orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_items_farmer    ON order_items(farmer_id);

-- ============================================================
-- IVR — Voice channel for farmers without smartphones
-- The IVR re-uses the same products / orders / payments tables;
-- these tables only store IVR sessions, call logs and events.
-- ============================================================

CREATE TABLE IF NOT EXISTS ivr_sessions (
    id              BIGSERIAL PRIMARY KEY,
    session_token   TEXT UNIQUE NOT NULL,
    call_id         TEXT,                       -- provider call id (Twilio etc.)
    caller_number   TEXT NOT NULL,              -- E.164 or simulator caller-id
    user_id         BIGINT,                    -- matched users.id (NULL if not registered)
    farmer_id       BIGINT,                     -- matched users.id (NULL if not a farmer/fpo)
    language        TEXT DEFAULT 'ta',          -- 'ta' or 'en'
    current_menu    TEXT DEFAULT 'language_select',
    current_intent  TEXT,
    conversation_state TEXT,                    -- JSON: partial listing, last prompt, etc.
    auth_status     TEXT DEFAULT 'unverified',   -- unverified / pin_pending / verified
    failure_count   INTEGER DEFAULT 0,          -- consecutive speech-recognition failures
    status          TEXT DEFAULT 'active'       -- active / ended / failed
                       CHECK (status IN ('active','ended','failed')),
    created_at      TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')),
    updated_at      TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS ivr_call_logs (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES ivr_sessions(id),
    caller_number   TEXT NOT NULL,
    user_id         BIGINT,
    farmer_name     TEXT,
    language        TEXT,
    intent          TEXT,
    success         INTEGER DEFAULT 0,           -- 1 = call ended cleanly, 0 = failed/abandoned
    had_error       INTEGER DEFAULT 0,
    duration_sec    INTEGER DEFAULT 0,
    listings_created INTEGER DEFAULT 0,
    bulk_accepted   INTEGER DEFAULT 0,
    price_requests  INTEGER DEFAULT 0,
    order_requests  INTEGER DEFAULT 0,
    earnings_requests INTEGER DEFAULT 0,
    start_time      TEXT,
    end_time        TEXT,
    transcript      TEXT                          -- JSON array of {role, text, intent}
);

CREATE TABLE IF NOT EXISTS ivr_events (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES ivr_sessions(id),
    ts              TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')),
    event_type      TEXT NOT NULL,               -- prompt / dtmf / speech / intent / action / error / hangup
    raw_input       TEXT,
    recognized_text TEXT,
    intent          TEXT,
    intent_payload  TEXT,                         -- JSON: structured intent data
    response_text   TEXT,
    backend_action  TEXT,                         -- e.g. "createProduceListing"
    backend_result  TEXT,                         -- JSON
    error           TEXT
);

CREATE INDEX IF NOT EXISTS idx_ivr_sessions_caller ON ivr_sessions(caller_number);
CREATE INDEX IF NOT EXISTS idx_ivr_events_session ON ivr_events(session_id);

-- ---------- Seed / catalogue version tracking ----------
-- Allows large catalogue upgrades to be applied once to existing demo DBs
-- without deleting user-created listings/orders.
CREATE TABLE IF NOT EXISTS catalog_seed_state (
    seed_key       TEXT PRIMARY KEY,
    version        INTEGER NOT NULL,
    applied_at     TEXT DEFAULT (TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
);

-- ---------- Official mandi market intelligence (AGMARKNET/data.gov.in) ----------
CREATE TABLE IF NOT EXISTS mandi_prices (
    id               BIGSERIAL PRIMARY KEY,
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