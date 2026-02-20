"""Filter & extract pipeline node for TradeSummaryAI.

Derives unique tickers and domains from ingested trades and produces a
slimmed-down list of filtered trades for downstream consumption.
"""

from typing import Any, Dict, List


def filter_extract_node(state: dict) -> dict:
    """LangGraph pipeline node that filters and extracts key data.

    Reads from state:
        trades – list of normalised trade dicts (from ingest node)

    Returns a dict with:
        tickers         – sorted unique ticker symbols (excluding "UNKNOWN")
        domains         – sorted unique domain names (excluding "Unknown")
        filtered_trades – trades trimmed to essential fields only
    """
    trades: List[Dict[str, Any]] = state.get("trades", [])

    tickers: set = set()
    domains: set = set()
    filtered_trades: List[Dict[str, Any]] = []

    keep_fields = (
        "trade_id",
        "timestamp",
        "ticker",
        "company_name",
        "domain",
        "trade_type",
        "quantity",
        "price",
        "total_value",
    )

    for trade in trades:
        ticker = trade.get("ticker", "")
        if ticker and ticker != "UNKNOWN":
            tickers.add(ticker)

        domain = trade.get("domain", "")
        if domain and domain != "Unknown":
            domains.add(domain)

        filtered_trades.append({k: trade.get(k) for k in keep_fields})

    return {
        "tickers": sorted(tickers),
        "domains": sorted(domains),
        "filtered_trades": filtered_trades,
    }
