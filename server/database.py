"""
server/database.py
SQLite の初期化・CRUD 操作。
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from .config import settings

DB_PATH = Path(settings["db_path"])


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────
#  スキーマ初期化
# ──────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    jan_code        TEXT PRIMARY KEY,
    product_code    TEXT DEFAULT '',
    product_name    TEXT NOT NULL,
    unit_price      REAL DEFAULT 0,
    supplier        TEXT DEFAULT '',
    unit            TEXT DEFAULT '個',
    updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    created_by      TEXT DEFAULT '',
    status          TEXT DEFAULT 'active',
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    last_activity   TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS session_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    jan_code        TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    unit_price      REAL DEFAULT 0,
    supplier        TEXT DEFAULT '',
    unit            TEXT DEFAULT '個',
    quantity        INTEGER DEFAULT 1,
    is_unknown      INTEGER DEFAULT 0,
    scanned_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS rpa_jobs (
    id              TEXT PRIMARY KEY,
    session_id      TEXT,
    status          TEXT DEFAULT 'queued',
    step            TEXT DEFAULT '',
    error           TEXT DEFAULT '',
    sent_flag       INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def init_db() -> None:
    """DB とテーブルを初期化する（起動時に呼び出す）。"""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)


# ──────────────────────────────────────────────────────────
#  商品マスタ
# ──────────────────────────────────────────────────────────

def get_product(jan_code: str) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE jan_code = ?", (jan_code,)
        ).fetchone()


def upsert_product(jan_code: str, product_name: str, unit_price: float = 0,
                   supplier: str = "", unit: str = "個",
                   product_code: str = "") -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute("""
            INSERT INTO products (jan_code, product_code, product_name, unit_price, supplier, unit, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(jan_code) DO UPDATE SET
                product_code = excluded.product_code,
                product_name = excluded.product_name,
                unit_price   = excluded.unit_price,
                supplier     = excluded.supplier,
                unit         = excluded.unit,
                updated_at   = excluded.updated_at
        """, (jan_code, product_code, product_name, unit_price, supplier, unit, now))


def bulk_upsert_products(rows: list[dict]) -> int:
    """CSV から一括インポート。rows は辞書のリスト。挿入/更新件数を返す。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.executemany("""
            INSERT INTO products (jan_code, product_code, product_name, unit_price, supplier, unit, updated_at)
            VALUES (:jan_code, :product_code, :product_name, :unit_price, :supplier, :unit, :updated_at)
            ON CONFLICT(jan_code) DO UPDATE SET
                product_code = excluded.product_code,
                product_name = excluded.product_name,
                unit_price   = excluded.unit_price,
                supplier     = excluded.supplier,
                unit         = excluded.unit,
                updated_at   = excluded.updated_at
        """, [{**r, "updated_at": now} for r in rows])
    return len(rows)


# ──────────────────────────────────────────────────────────
#  セッション
# ──────────────────────────────────────────────────────────

def create_session(created_by: str = "") -> str:
    session_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_by) VALUES (?, ?)",
            (session_id, created_by)
        )
    return session_id


def get_session(session_id: str) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()


def touch_session(session_id: str) -> None:
    """最終操作時刻を更新する（タイムアウト判定用）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET last_activity = ? WHERE id = ?",
            (now, session_id)
        )


def update_session_status(session_id: str, status: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET status = ? WHERE id = ?",
            (status, session_id)
        )


def get_session_items(session_id: str) -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM session_items WHERE session_id = ? ORDER BY scanned_at",
            (session_id,)
        ).fetchall()


def add_session_item(session_id: str, jan_code: str, product_name: str,
                     unit_price: float, supplier: str, unit: str,
                     quantity: int, is_unknown: bool = False) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO session_items
                (session_id, jan_code, product_name, unit_price, supplier, unit, quantity, is_unknown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, jan_code, product_name, unit_price, supplier, unit, quantity, int(is_unknown)))
        return cur.lastrowid


def delete_session_item(item_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM session_items WHERE id = ?", (item_id,))


# ──────────────────────────────────────────────────────────
#  RPAジョブ
# ──────────────────────────────────────────────────────────

def create_rpa_job(session_id: str) -> str:
    job_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO rpa_jobs (id, session_id) VALUES (?, ?)",
            (job_id, session_id)
        )
    return job_id


def get_rpa_job(job_id: str) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM rpa_jobs WHERE id = ?", (job_id,)
        ).fetchone()


def update_rpa_job(job_id: str, status: str, step: str = "", error: str = "",
                   sent_flag: int | None = None) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        if sent_flag is not None:
            conn.execute(
                "UPDATE rpa_jobs SET status=?, step=?, error=?, sent_flag=?, updated_at=? WHERE id=?",
                (status, step, error, sent_flag, now, job_id)
            )
        else:
            conn.execute(
                "UPDATE rpa_jobs SET status=?, step=?, error=?, updated_at=? WHERE id=?",
                (status, step, error, now, job_id)
            )


def get_pending_rpa_jobs() -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM rpa_jobs WHERE status IN ('queued','failed') AND sent_flag = 0 ORDER BY created_at"
        ).fetchall()
