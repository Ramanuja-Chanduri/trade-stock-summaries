"""Enrichment building pipeline node for TradeSummaryAI.

Combines raw enrichment data (stock prices, company news, domain trends)
into structured JSON payloads and persists them via ``store_enrichment``.
"""

from typing import Any, Dict, List

from src.database import store_enrichment


def build_enrichment_node(state: dict) -> dict:
    """LangGraph pipeline node that builds and stores enrichment JSONs.

    Reads from state:
        stock_data   – {ticker: {price data}} from fetch_enrichment node
        company_data – {ticker: "news summary"} from fetch_enrichment node
        domain_data  – {domain: "trend summary"} from fetch_enrichment node
        session_id   – current session identifier

    Returns a dict with:
        ticker_enrichment_json – {ticker: {company_performance_summary, stock_performance}}
        domain_enrichment_json – {domain: {domain_performance_summary, tickers_in_domain}}
        enrichment_stored      – ``True`` when finished
    """
    stock_data: Dict[str, Any] = state.get("stock_data", {})
    company_data: Dict[str, str] = state.get("company_data", {})
    domain_data: Dict[str, str] = state.get("domain_data", {})
    session_id: str = state["session_id"]

    # ------------------------------------------------------------------
    # Ticker enrichment
    # ------------------------------------------------------------------
    ticker_enrichment: Dict[str, Dict[str, Any]] = {}

    all_tickers = sorted(set(list(stock_data.keys()) + list(company_data.keys())))
    for ticker in all_tickers:
        ticker_enrichment[ticker] = {
            "company_performance_summary": company_data.get(ticker, ""),
            "stock_performance": stock_data.get(ticker, {}),
        }

        store_enrichment(
            session_id,
            data_type="ticker",
            reference_id=ticker,
            data_json=ticker_enrichment[ticker],
        )

    # ------------------------------------------------------------------
    # Domain enrichment
    # ------------------------------------------------------------------
    # Build a mapping of domain -> tickers present in the trade data
    filtered_trades: list = state.get("filtered_trades", [])
    domain_tickers: Dict[str, List[str]] = {}
    for trade in filtered_trades:
        domain = trade.get("domain", "")
        ticker = trade.get("ticker", "")
        if domain and ticker:
            domain_tickers.setdefault(domain, [])
            if ticker not in domain_tickers[domain]:
                domain_tickers[domain].append(ticker)

    domain_enrichment: Dict[str, Dict[str, Any]] = {}

    for domain in sorted(domain_data.keys()):
        domain_enrichment[domain] = {
            "domain_performance_summary": domain_data.get(domain, ""),
            "tickers_in_domain": sorted(domain_tickers.get(domain, [])),
        }

        store_enrichment(
            session_id,
            data_type="domain",
            reference_id=domain,
            data_json=domain_enrichment[domain],
        )

    return {
        "ticker_enrichment_json": ticker_enrichment,
        "domain_enrichment_json": domain_enrichment,
        "enrichment_stored": True,
    }
