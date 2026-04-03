"""SQLite database helpers for the Market Regime Dashboard."""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "screener.db")


@contextmanager
def get_connection(db_path: str | None = None):
    """Yield a SQLite connection, committing on success."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_regime_tables(db_path: str | None = None):
    """Create regime_signals and regime_caution tables if they don't exist."""
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regime_signals (
                date            TEXT PRIMARY KEY,
                spx_close       REAL,
                spx_near_52w_high INTEGER,
                pct_above_200d  REAL,
                nh_nl_ratio_20d REAL,
                ad_line_20d_roc REAL,
                breadth_score   REAL,
                shiller_cape    REAL,
                cape_pctile_30y REAL,
                buffett_indicator REAL,
                fwd_pe          REAL,
                valuation_score REAL,
                hy_oas          REAL,
                hy_oas_pctile_5y REAL,
                ccc_bb_ratio    REAL,
                credit_score    REAL,
                aaii_bull_bear_4w REAL,
                aaii_weeks_above_25 INTEGER,
                fear_greed      REAL,
                sentiment_score REAL,
                lei_6m_roc      REAL,
                ism_new_orders  REAL,
                claims_4w_vs_26w REAL,
                macro_score     REAL,
                margin_debt_yoy REAL,
                free_credit_declining INTEGER,
                leverage_score  REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regime_caution (
                date            TEXT PRIMARY KEY,
                caution_level   REAL,
                regime          TEXT,
                stale_flag      INTEGER,
                breadth_contrib REAL,
                valuation_contrib REAL,
                credit_contrib  REAL,
                sentiment_contrib REAL,
                macro_contrib   REAL,
                leverage_contrib REAL
            )
        """)


def upsert_regime_signals(date: str, data: dict, db_path: str | None = None):
    """Insert or replace a row in regime_signals."""
    cols = ["date"] + list(data.keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    values = [date] + list(data.values())
    with get_connection(db_path) as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO regime_signals ({col_str}) VALUES ({placeholders})",
            values,
        )


def upsert_regime_caution(date: str, data: dict, db_path: str | None = None):
    """Insert or replace a row in regime_caution."""
    cols = ["date"] + list(data.keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    values = [date] + list(data.values())
    with get_connection(db_path) as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO regime_caution ({col_str}) VALUES ({placeholders})",
            values,
        )


def fetch_regime_caution_history(db_path: str | None = None) -> list[dict]:
    """Return all regime_caution rows ordered by date."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM regime_caution ORDER BY date"
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_regime_signals_history(db_path: str | None = None) -> list[dict]:
    """Return all regime_signals rows ordered by date."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM regime_signals ORDER BY date"
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_latest_regime_caution(db_path: str | None = None) -> dict | None:
    """Return the most recent regime_caution row."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM regime_caution ORDER BY date DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
