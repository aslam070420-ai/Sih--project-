"""FarmDirect application factory — local + Vercel production edition."""
from __future__ import annotations

import os
import threading

from flask import Flask, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_INIT_LOCK = threading.Lock()
_APP_READY = False


def _load_local_env():
    """Load a simple project-local .env without adding a dependency."""
    path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                key, value = raw.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


def _truthy(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in {"0", "false", "no", "off"}


def _is_vercel() -> bool:
    return bool(os.environ.get("VERCEL"))


def _ensure_data_ready(app: Flask) -> None:
    """Initialize schema/demo data lazily.

    Vercel discovers/imports the Flask app during deployment, so expensive DB
    work must not happen at import time. The first real request initializes the
    selected database. PostgreSQL uses an advisory lock to prevent duplicate
    first-run seeders across concurrent instances.
    """
    global _APP_READY
    if _APP_READY:
        return
    with _INIT_LOCK:
        if _APP_READY:
            return
        import db as database
        with database.initialization_lock():
            database.init_db(force=False)
            if _truthy("FD_AUTO_SEED", "1") and not database.db_is_seeded():
                import seed
                seed.seed_all()
                app.logger.info("Database seeded with FarmDirect demo data.")

            if database.db_is_seeded():
                import catalog_seed
                catalog_result = catalog_seed.ensure_india_catalog()
                if catalog_result.get("applied"):
                    app.logger.info("India crop catalogue upgraded: %s", catalog_result)

            import market_sync
            market_sync.ensure_schema()

            # A daemon thread is perfect for Termux/Render/Railway, but Vercel
            # functions are ephemeral. Vercel uses the secured cron endpoint +
            # on-demand refresh instead.
            if not _is_vercel():
                if market_sync.start_background_sync():
                    app.logger.info("Multi-source mandi background sync enabled.")
        _APP_READY = True


def create_app():
    _load_local_env()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FD_SECRET", "farmdirect-sih-prototype-key")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = _is_vercel() or _truthy("FD_SECURE_COOKIES", "0")
    # Template auto-reload performs filesystem stat checks on every request.
    # That is especially expensive when FarmDirect is run from Android shared
    # storage in Termux. Keep it off for the demo/runtime; developers can opt in
    # with FD_TEMPLATE_RELOAD=1.
    app.config["TEMPLATES_AUTO_RELOAD"] = _truthy("FD_TEMPLATE_RELOAD", "0")
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = int(os.environ.get("FD_STATIC_CACHE_SECONDS", "86400"))
    from static_assets import install_static_assets
    install_static_assets(app)

    prefix = os.environ.get("FD_URL_PREFIX", "")
    if prefix:
        from wsgi import PrefixMiddleware
        app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=prefix)

    # Register initialization before blueprints because auth has a
    # before_app_request hook that reads the users table.
    @app.before_request
    def initialize_on_first_request():
        if request.endpoint in {"static", "service_worker"}:
            return
        _ensure_data_ready(app)

    from auth import bp as auth_bp
    from views import bp as views_bp
    from api import bp as api_bp
    from ivr_api import bp as ivr_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ivr_bp, url_prefix="/api")

    @app.get("/sw.js")
    def service_worker():
        response = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    from helpers import CROP_META, crop_mark, inr, kg, status_steps, pretty_status, days_ago

    app.jinja_env.filters["inr"] = inr
    app.jinja_env.filters["kg"] = kg
    app.jinja_env.globals.update(
        CROP_META=CROP_META,
        status_steps=status_steps,
        pretty_status=pretty_status,
        days_ago=days_ago,
        crop_mark=crop_mark,
    )

    @app.teardown_appcontext
    def close_database_connection(_exc=None):
        import db as _db
        _db.close_request_connection()

    @app.context_processor
    def inject_globals():
        from flask import g
        count = 0
        if g.get("user") and g.get("role") == "consumer":
            cached = g.get("_farmdirect_cart_count")
            if cached is not None:
                count = int(cached)
            else:
                import db as _db
                row = _db.query(
                    "SELECT COALESCE(SUM(quantity_kg),0) n FROM cart_items WHERE user_id=?",
                    (g.user["id"],),
                    one=True,
                )
                count = int(row["n"]) if row else 0
                g._farmdirect_cart_count = count
        return {
            "cart_count": count,
            "cloud_runtime": "vercel" if _is_vercel() else "local",
        }

    return app
