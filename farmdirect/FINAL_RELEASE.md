# FarmDirect FINAL V16 — Vercel + Local Integrated Release

V16 is the final consolidated FarmDirect web build. It keeps the V15 judge-ready product and adds the production/runtime work required to deploy the same application from GitHub to Vercel.

## Final architecture

```text
Browser / Installed PWA
        ↓ HTTPS
      Vercel
  Flask application
        ↓
PostgreSQL (recommended)
Supabase / Neon pooled URL
        ↓
Marketplace · Orders · IVR · AI · Mandi cache
```

Local Termux remains supported with SQLite and the persistent background market-sync worker.

## Vercel behavior

- `app.py` is the cloud Flask entrypoint.
- Initialization is lazy, not performed while Vercel is discovering/building the app.
- `DATABASE_URL` switches the app to PostgreSQL automatically.
- No `DATABASE_URL` on Vercel means ephemeral `/tmp` SQLite preview mode.
- `vercel.json` schedules one official mandi refresh per day, compatible with Vercel Hobby.
- `CRON_SECRET` protects the scheduled refresh endpoint.
- Manual Live Mandi refresh remains available at any time.

## No feature downgrade

The web, 23-language IVR, real ordering, A/B/C grade fix, corrected-price fix, India-wide catalogue, crop identity system, AI modules, PWA and multi-source market intelligence all remain included.
