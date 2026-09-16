"""FarmDirect database layer.

Local / Termux development uses SQLite by default.
Vercel / cloud deployment can use PostgreSQL (Supabase, Neon, etc.) by setting
DATABASE_URL (or FARMDIRECT_DATABASE_URL) to a postgres connection string.

The rest of FarmDirect intentionally keeps SQLite-style ``?`` placeholders.
This module translates the small SQLite SQL subset used by the app so the same
business logic works on both backends.
"""
from __future__ import annotations

import contextlib
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SQLITE_PATH = ("/tmp/farmdirect.db" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "data", "farmdirect.db"))
DB_PATH = os.environ.get("FARMDIRECT_DB", _DEFAULT_SQLITE_PATH)
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
PG_SCHEMA_PATH = os.path.join(BASE_DIR, "schema_postgres.sql")


def _database_url() -> str:
    return (
        os.environ.get("FARMDIRECT_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or ""
    ).strip()


def backend_name() -> str:
    url = _database_url().lower()
    return "postgres" if url.startswith(("postgres://", "postgresql://")) else "sqlite"


def is_postgres() -> bool:
    return backend_name() == "postgres"


class HybridRow(dict):
    """Dictionary row that also supports SQLite-style numeric indexing."""

    def __init__(self, columns: list[str], values: Iterable[Any]):
        vals = list(values)
        super().__init__(zip(columns, vals))
        self._values = vals

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


_SQLITE_NOW = re.compile(r"datetime\(\s*'now'\s*(?:,\s*'localtime'\s*)?\)", re.I)
_SQLITE_DATE_MINUS = re.compile(r"date\(\s*'now'\s*,\s*'-(\d+)\s+days?'\s*\)", re.I)
_SQLITE_DATE_MAX_MINUS = re.compile(
    r"date\(\s*\((SELECT\s+MAX\([^)]*\)\s+FROM\s+[^)]*)\)\s*,\s*'-(\d+)\s+day[s]?'\s*\)",
    re.I,
)


def _translate_runtime_sql(sql: str) -> str:
    """Translate the SQLite expressions/placeholders used by FarmDirect."""
    if not is_postgres():
        return sql
    s = sql
    # The app stores timestamps as TEXT for portability; keep that contract.
    s = _SQLITE_NOW.sub("TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')", s)
    s = _SQLITE_DATE_MINUS.sub(
        lambda m: f"TO_CHAR(CURRENT_DATE - INTERVAL '{m.group(1)} days', 'YYYY-MM-DD')", s
    )
    s = _SQLITE_DATE_MAX_MINUS.sub(
        lambda m: f"TO_CHAR((({m.group(1)})::date - INTERVAL '{m.group(2)} days'), 'YYYY-MM-DD')", s
    )
    # qmark placeholders are the only positional placeholders used by the app.
    s = s.replace("?", "%s")
    return s


def _split_sql_script(script: str) -> list[str]:
    """Simple SQL script splitter; FarmDirect schemas contain no procedure bodies."""
    out: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(script):
        ch = script[i]
        if ch == "'" and not in_double:
            if in_single and i + 1 < len(script) and script[i + 1] == "'":
                buf.extend([ch, script[i + 1]])
                i += 2
                continue
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


class PostgresCursorAdapter:
    def __init__(self, conn):
        self._conn = conn
        self._cur = conn.cursor()
        self.lastrowid = None

    def _columns(self) -> list[str]:
        return [d.name if hasattr(d, "name") else d[0] for d in (self._cur.description or [])]

    def execute(self, sql: str, args=()):
        translated = _translate_runtime_sql(sql)
        self._cur.execute(translated, tuple(args or ()))
        self.lastrowid = None
        if translated.lstrip().upper().startswith("INSERT "):
            # LASTVAL() is sequence-backed and gives us the SQLite-compatible
            # lastrowid expected by the existing seed/order code. Upserts whose
            # caller ignores lastrowid are safe even when no new row is created.
            try:
                with self._conn.cursor() as c2:
                    c2.execute("SELECT LASTVAL()")
                    row = c2.fetchone()
                    if row:
                        self.lastrowid = int(row[0])
            except Exception:
                self.lastrowid = None
        return self

    def executemany(self, sql: str, seq):
        self._cur.executemany(_translate_runtime_sql(sql), list(seq))
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return HybridRow(self._columns(), row)

    def fetchall(self):
        cols = self._columns()
        return [HybridRow(cols, row) for row in self._cur.fetchall()]

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class PostgresConnectionAdapter:
    def __init__(self, raw):
        self._raw = raw

    def cursor(self):
        return PostgresCursorAdapter(self._raw)

    def execute(self, sql: str, args=()):
        cur = self.cursor()
        return cur.execute(sql, args)

    def executemany(self, sql: str, seq):
        cur = self.cursor()
        return cur.executemany(sql, seq)

    def executescript(self, script: str):
        cur = self.cursor()
        try:
            for stmt in _split_sql_script(script):
                if stmt.lstrip().upper().startswith("PRAGMA "):
                    continue
                # Dynamic schemas (market_sync/catalog migration) still use
                # SQLite's AUTOINCREMENT spelling.
                stmt = re.sub(
                    r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
                    "BIGSERIAL PRIMARY KEY",
                    stmt,
                    flags=re.I,
                )
                stmt = _translate_runtime_sql(stmt)
                cur._cur.execute(stmt)
        finally:
            cur.close()

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()



def get_db():
    """Open a DB connection. Caller must close it."""
    if is_postgres():
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - deployment guard
            raise RuntimeError("PostgreSQL selected but psycopg is not installed") from exc
        raw = psycopg.connect(_database_url(), connect_timeout=10, prepare_threshold=None)
        return PostgresConnectionAdapter(raw)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _operation_connection():
    """Return (connection, close_after). Reuse one connection per Flask request."""
    try:
        from flask import g, has_request_context
        if has_request_context():
            conn = g.get("_farmdirect_db_conn")
            if conn is None:
                conn = get_db()
                g._farmdirect_db_conn = conn
            return conn, False
    except Exception:
        pass
    return get_db(), True


def close_request_connection() -> None:
    """Close a connection cached on Flask's request context, if present."""
    try:
        from flask import g, has_app_context
        if not has_app_context():
            return
        conn = g.pop("_farmdirect_db_conn", None)
        if conn is not None:
            conn.close()
    except Exception:
        pass


def query(sql, args=(), one=False):
    conn, close_after = _operation_connection()
    try:
        cur = conn.execute(sql, args)
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        if close_after:
            conn.close()


def execute(sql, args=()):
    """Run one write statement and commit. Returns SQLite-compatible lastrowid."""
    conn, close_after = _operation_connection()
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        return getattr(cur, "lastrowid", None)
    finally:
        if close_after:
            conn.close()


def executemany(sql, seq):
    conn, close_after = _operation_connection()
    try:
        conn.executemany(sql, seq)
        conn.commit()
    finally:
        if close_after:
            conn.close()


def init_db(force=False):
    """Create the database schema for the selected backend."""
    if is_postgres():
        schema = Path(PG_SCHEMA_PATH).read_text(encoding="utf-8")
        conn = get_db()
        try:
            conn.executescript(schema)
            conn.commit()
        finally:
            conn.close()
        return

    if force and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()


def db_is_seeded():
    # Use an independent connection because this check also runs during
    # first-request initialization before the request-scoped DB lifecycle.
    conn = None
    try:
        conn = get_db()
        rows = conn.execute("SELECT COUNT(*) AS n FROM users").fetchall()
        row = rows[0] if rows else None
        return bool(row and row["n"] > 0)
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()


@contextlib.contextmanager
def initialization_lock():
    """Serialize first-run seeding across concurrent cloud function instances."""
    if not is_postgres():
        yield
        return
    conn = get_db()
    try:
        # Stable arbitrary app-level key. pg_advisory_lock is released when
        # the connection closes even if initialization raises.
        lock_cur = conn.execute("SELECT pg_advisory_lock(7461726D)")
        lock_cur.close()
        yield
        unlock_cur = conn.execute("SELECT pg_advisory_unlock(7461726D)")
        unlock_cur.close()
        conn.commit()
    finally:
        conn.close()
