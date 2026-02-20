"""SQLite database module for TradeSummaryAI.

Provides connection helpers, schema initialization, and CRUD functions
for raw_trades, metrics, enrichment_data, and summaries tables.
"""

import json
import sqlite3
from collections import defaultdict
from typing import Any, Dict, List, Optional

DB_PATH = "trade_summary.db"

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Return a new SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id     TEXT UNIQUE NOT NULL,
    timestamp    TEXT,
    ticker       TEXT NOT NULL,
    company_name TEXT,
    domain       TEXT,
    trade_type   TEXT,
    quantity     INTEGER,
    price        REAL,
    total_value  REAL,
    currency     TEXT DEFAULT 'USD',
    exchange     TEXT,
    trader_id    TEXT,
    session_id   TEXT NOT NULL,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    metric_name  TEXT NOT NULL,
    metric_value TEXT,
    category     TEXT,
    reference_id TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS enrichment_data (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    data_type    TEXT NOT NULL,
    reference_id TEXT,
    data_json    TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    summary_type TEXT NOT NULL,
    reference_id TEXT,
    summary_text TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_session   ON raw_trades (session_id);
CREATE INDEX IF NOT EXISTS idx_trades_ticker    ON raw_trades (ticker);
CREATE INDEX IF NOT EXISTS idx_trades_domain    ON raw_trades (domain);
CREATE INDEX IF NOT EXISTS idx_metrics_session  ON metrics (session_id);
CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries (session_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_session ON enrichment_data (session_id);
"""


def init_db() -> None:
    """Create all tables and indexes if they do not already exist."""
    conn = get_db()
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------

def store_trades(trades: List[Dict[str, Any]], session_id: str) -> int:
    """Insert a batch of trade dicts into raw_trades.

    Uses INSERT OR IGNORE so duplicate trade_ids are silently skipped.
    Returns the number of rows actually inserted.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        inserted = 0
        for t in trades:
            cursor.execute(
                """
                INSERT OR IGNORE INTO raw_trades
                    (trade_id, timestamp, ticker, company_name, domain,
                     trade_type, quantity, price, total_value, currency,
                     exchange, trader_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["trade_id"],
                    t.get("timestamp"),
                    t["ticker"],
                    t.get("company_name"),
                    t.get("domain"),
                    t.get("trade_type"),
                    t.get("quantity"),
                    t.get("price"),
                    t.get("total_value"),
                    t.get("currency", "USD"),
                    t.get("exchange"),
                    t.get("trader_id"),
                    session_id,
                ),
            )
            inserted += cursor.rowcount
        conn.commit()
        return inserted
    finally:
        conn.close()


def store_metric(
    session_id: str,
    metric_name: str,
    metric_value: str,
    category: str,
    reference_id: Optional[str] = None,
) -> None:
    """Insert a single metric row."""
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO metrics (session_id, metric_name, metric_value, category, reference_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, metric_name, metric_value, category, reference_id),
        )
        conn.commit()
    finally:
        conn.close()


def store_enrichment(
    session_id: str,
    data_type: str,
    reference_id: str,
    data_json: Any,
) -> None:
    """Insert an enrichment record. *data_json* is serialised to a JSON string."""
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO enrichment_data (session_id, data_type, reference_id, data_json)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, data_type, reference_id, json.dumps(data_json)),
        )
        conn.commit()
    finally:
        conn.close()


def store_summary(
    session_id: str,
    summary_type: str,
    summary_text: str,
    reference_id: Optional[str] = None,
) -> None:
    """Insert a summary record."""
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO summaries (session_id, summary_type, reference_id, summary_text)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, summary_type, reference_id, summary_text),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_trades_by_session(session_id: str) -> List[Dict[str, Any]]:
    """Return all trades for a given session as a list of dicts."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM raw_trades WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trades_grouped_by_ticker(session_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Return trades for a session grouped by ticker symbol."""
    trades = get_trades_by_session(session_id)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        grouped[t["ticker"]].append(t)
    return dict(grouped)


def get_trades_grouped_by_domain(session_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Return trades for a session grouped by domain."""
    trades = get_trades_by_session(session_id)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        if t.get("domain"):
            grouped[t["domain"]].append(t)
    return dict(grouped)


def get_enrichment(
    session_id: str,
    data_type: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve enrichment records, optionally filtered by data_type and reference_id."""
    conn = get_db()
    try:
        query = "SELECT * FROM enrichment_data WHERE session_id = ?"
        params: List[Any] = [session_id]

        if data_type is not None:
            query += " AND data_type = ?"
            params.append(data_type)
        if reference_id is not None:
            query += " AND reference_id = ?"
            params.append(reference_id)

        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            # Deserialise the JSON payload for convenience
            if d.get("data_json"):
                try:
                    d["data_json"] = json.loads(d["data_json"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results
    finally:
        conn.close()


def get_metrics_by_session(session_id: str) -> List[Dict[str, Any]]:
    """Return all metric rows for a given session."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT metric_name, metric_value, category, reference_id "
            "FROM metrics WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_summary(
    session_id: str,
    summary_type: str,
    reference_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return a single summary matching the criteria, or None."""
    conn = get_db()
    try:
        if reference_id is not None:
            row = conn.execute(
                "SELECT * FROM summaries WHERE session_id = ? AND summary_type = ? AND reference_id = ?",
                (session_id, summary_type, reference_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM summaries WHERE session_id = ? AND summary_type = ? AND reference_id IS NULL",
                (session_id, summary_type),
            ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
