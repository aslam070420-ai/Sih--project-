"""FarmDirect FINAL V16 readiness diagnostics.

Works with local SQLite and cloud PostgreSQL. No external market request is
required; use test_market_sync.py separately for live-source probing.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import db
import market_sync
from india_catalog import CROP_NAMES


def ok(label, value):
    print(f"[ OK ] {label}: {value}")


def warn(label, value):
    print(f"[WARN] {label}: {value}")


def fail(label, value):
    print(f"[FAIL] {label}: {value}")


def main():
    print("FarmDirect FINAL V16 — readiness check\n")
    files = [
        ROOT / "app.py",
        ROOT / "run.py",
        ROOT / "vercel.json",
        ROOT / "schema.sql",
        ROOT / "schema_postgres.sql",
        ROOT / "templates" / "base.html",
        ROOT / "static" / "css" / "final.css",
        ROOT / "static" / "js" / "final.js",
        ROOT / "static" / "manifest.webmanifest",
        ROOT / "static" / "sw.js",
    ]
    missing = [str(p.relative_to(ROOT)) for p in files if not p.exists()]
    if missing:
        fail("Required files", ", ".join(missing))
    else:
        ok("Required files", "present")

    try:
        db.init_db(force=False)
        backend = db.backend_name()
        products = int(db.query("SELECT COUNT(*) n FROM products WHERE status='active'", one=True)["n"])
        users = int(db.query("SELECT COUNT(*) n FROM users", one=True)["n"])
        orders = int(db.query("SELECT COUNT(*) n FROM orders", one=True)["n"])
        if backend == "sqlite":
            ok("Database", f"SQLite · {db.DB_PATH}")
        else:
            ok("Database", "PostgreSQL · DATABASE_URL connected")
        ok("Active marketplace listings", products)
        ok("Users", users)
        ok("Orders", orders)
    except Exception as exc:
        fail("Database", exc)
        return 1

    ok("India crop catalogue", f"{len(CROP_NAMES)} crop/product types")
    try:
        market_sync.ensure_schema()
        status = market_sync.status_summary()
        cached_rows = int(status.get("cached_rows") or 0)
        cached_crops = int(status.get("cached_crops") or 0)
        if cached_rows:
            ok("Verified mandi cache", f"{cached_rows} rows across {cached_crops} crops")
        else:
            warn("Verified mandi cache", "empty — use Live Mandi > Sync official data when internet is available")
        for p in status.get("providers") or []:
            label = p.get("label") or p.get("provider")
            state = p.get("status") or "not-tested"
            print(f"[INFO] Provider {label}: {state}")
    except Exception as exc:
        warn("Market cache", exc)

    print("\nReadiness check complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
