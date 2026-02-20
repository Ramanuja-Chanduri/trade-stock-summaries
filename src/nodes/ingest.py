"""Ingestion pipeline node for TradeSummaryAI.

Parses raw CSV or JSON bytes into normalised trade dicts and persists them.
"""

import csv
import io
import json
import uuid
from typing import Any, Dict, List

from src.database import store_trades


def _normalize_trade(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a single raw trade row into a consistent dict.

    Handles missing fields, type coercion, and field-name aliases so that
    downstream nodes always receive a uniform structure.
    """
    trade: Dict[str, Any] = {}

    # trade_id — auto-generate if missing
    trade["trade_id"] = (
        str(row.get("trade_id") or "").strip() or uuid.uuid4().hex[:12]
    )

    trade["timestamp"] = str(row.get("timestamp") or "").strip()

    # ticker — uppercase, stripped
    trade["ticker"] = (
        str(row.get("ticker") or "UNKNOWN").strip().upper()
    )

    trade["company_name"] = str(row.get("company_name") or "").strip() or None

    # domain — fall back to "sector" field
    domain = row.get("domain") or row.get("sector") or "Unknown"
    trade["domain"] = str(domain).strip()

    # trade_type — fall back to "side" field, uppercase
    trade_type = row.get("trade_type") or row.get("side") or "UNKNOWN"
    trade["trade_type"] = str(trade_type).strip().upper()

    # Numeric fields
    try:
        trade["quantity"] = int(float(row.get("quantity", 0)))
    except (ValueError, TypeError):
        trade["quantity"] = 0

    try:
        trade["price"] = float(row.get("price", 0))
    except (ValueError, TypeError):
        trade["price"] = 0.0

    # total_value — calculate from quantity * price if missing/zero
    try:
        total_value = float(row.get("total_value", 0))
    except (ValueError, TypeError):
        total_value = 0.0
    if not total_value:
        total_value = trade["quantity"] * trade["price"]
    trade["total_value"] = total_value

    # currency — default to USD
    trade["currency"] = str(row.get("currency") or "USD").strip().upper()

    trade["exchange"] = str(row.get("exchange") or "").strip() or None
    trade["trader_id"] = str(row.get("trader_id") or "").strip() or None

    return trade


def ingest_node(state: dict) -> dict:
    """LangGraph pipeline node that ingests raw trade data.

    Reads from state:
        raw_content – file content as bytes
        file_type   – ``"csv"`` or ``"json"``
        session_id  – current session identifier

    Returns a dict with:
        trades      – list of normalised trade dicts
        trade_count – number of trades ingested
    """
    raw_content: bytes = state["raw_content"]
    file_type: str = state["file_type"]
    session_id: str = state["session_id"]

    text = raw_content.decode("utf-8")

    raw_rows: List[Dict[str, Any]] = []

    if file_type == "csv":
        reader = csv.DictReader(io.StringIO(text))
        raw_rows = list(reader)
    else:
        data = json.loads(text)
        if isinstance(data, list):
            raw_rows = data
        elif isinstance(data, dict) and "trades" in data:
            raw_rows = data["trades"]
        else:
            raw_rows = [data]

    trades = [_normalize_trade(row) for row in raw_rows]

    store_trades(trades, session_id)

    return {
        "trades": trades,
        "trade_count": len(trades),
    }
