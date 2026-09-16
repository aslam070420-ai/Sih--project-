# 🌱 FarmDirect — FINAL V16 Web Edition

**From Farm to Consumer — Better Prices for Everyone.**

This is the consolidated FarmDirect SIH build for **local/Termux use and Vercel deployment**. It preserves the complete marketplace, multilingual IVR, India-wide catalogue, AI modules, PWA/mobile experience and resilient mandi-price engine while adding a cloud-safe database/runtime layer.

## What is included

- 212 canonical Indian crop/product types and hundreds of regional listings.
- Farmer/FPO → consumer/bulk-buyer marketplace.
- Cart, checkout, orders, tracking, payments and deliveries.
- Farmer listings, earnings, AI demand forecast and fair-price recommendation.
- Bulk quote workflow, admin dashboard and logistics tools.
- 23 IVR languages (English + 22 Scheduled Indian languages).
- Order-first IVR with real order creation, A/B/C grades and corrected-price persistence.
- Browser multilingual speech-to-text with keypad/text fallback.
- Multi-source mandi intelligence: e-NAM → AGMARKNET 2.0 → Tamil Nadu AgriMarket → optional data.gov.in → verified DB cache → clearly labelled estimate.
- Responsive cinematic UI, unique animated crop identities and mobile bottom navigation.
- PWA manifest, service worker and offline fallback.
- `/api/system/health` diagnostics.

## V16 cloud changes

- **Zero-config Flask entrypoint for Vercel:** `app.py`.
- **Dual database:** SQLite locally, PostgreSQL when `DATABASE_URL` is set.
- Designed for Supabase/Neon pooled PostgreSQL connections on serverless hosting.
- Lazy first-request initialization so Vercel builds do not run expensive DB setup.
- PostgreSQL initialization lock prevents duplicate first-run seeders.
- Vercel-safe mandi synchronization: no background daemon inside ephemeral functions.
- Secure `/api/cron/market-sync` endpoint + daily Hobby-compatible cron in `vercel.json`.
- Secure cookies automatically enabled on Vercel HTTPS.
- If Vercel is deployed before a PostgreSQL URL is added, V16 falls back to `/tmp` SQLite as a **non-persistent preview/demo mode**.

## Local / Termux

```bash
cd farmdirect
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Local mode uses `data/farmdirect.db` automatically and keeps the persistent background mandi worker.

## Vercel — easiest path

1. Extract this ZIP.
2. Upload the **files inside the `farmdirect` folder** to your GitHub repository (not the ZIP itself).
3. In Vercel choose **Add New → Project → Import** that GitHub repository.
4. Deploy. Vercel recognizes `app.py` as Flask.
5. For permanent data, add these Vercel Environment Variables and redeploy:

```text
DATABASE_URL=<Supabase/Neon pooled PostgreSQL URL>
FD_SECRET=<long random secret>
CRON_SECRET=<long random secret>
```

Optional:

```text
DATA_GOV_IN_API_KEY=<key if available>
FD_MARKET_SYNC_CROPS=12
```

The Vercel free/Hobby cron runs once per day. Users can still manually refresh a selected crop from **Live Mandi**, so official data does not have to wait for the next cron run.

## Important URLs

```text
/                    Home
/marketplace          Marketplace
/market-intelligence  Mandi intelligence
/ivr/simulator        Multilingual IVR simulator
/api/system/health    Runtime/database health
/api/market/status    Mandi provider/cache status
/api/cron/market-sync Scheduled market refresh
```

## Demo accounts

- Farmer: `vikram@farmdirect.in` / `farm123`
- FPO: `fpo@farmdirect.in` / `farm123`
- Consumer: `priya@example.in` / `farm123`
- Bulk buyer: `buy@annapurna.in` / `farm123`
- Admin: `admin@farmdirect.in` / `admin123`

## Database behavior

### Local
SQLite is persistent and stored at `data/farmdirect.db`.

### Vercel without `DATABASE_URL`
FarmDirect uses `/tmp/farmdirect.db`. This is useful to prove the web deployment works, but **data can disappear when a Vercel function instance is replaced**.

### Vercel with `DATABASE_URL`
FarmDirect uses PostgreSQL and accounts/orders/listings/market cache persist normally. This is the recommended final SIH/public configuration.

See `VERCEL_DEPLOY.md` for the short hosting checklist and `IVR_README.md` for IVR details.


This optimized build preserves the existing animations and visual styling. See
[OPTIMIZATION_NOTES.md](OPTIMIZATION_NOTES.md) for changes, measurements, checks,
and the static-asset rebuild command. Prebuilt assets are included.
