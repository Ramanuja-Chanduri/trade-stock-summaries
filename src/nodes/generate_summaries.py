"""Summary generation pipeline node for TradeSummaryAI.

Uses the LLM to produce three types of summaries:
  1. Overall daily trade summary
  2. Per-ticker summaries (with enrichment context)
  3. Per-domain summaries (with enrichment context)
"""

import json
from collections import defaultdict
from typing import Any, Dict, List

from src.database import store_summary
from src.llm_client import call_llm
from src.logger import get_logger

logger = get_logger(__name__)


def _build_overall_context(
    trades: List[Dict[str, Any]],
    state: dict,
) -> Dict[str, Any]:
    """Build an aggregated context dict for the overall summary prompt."""
    total_trades = len(trades)
    total_volume = sum(t.get("total_value", 0) for t in trades)
    buy_volume = sum(
        t.get("total_value", 0) for t in trades if t.get("trade_type") == "BUY"
    )
    sell_volume = sum(
        t.get("total_value", 0) for t in trades if t.get("trade_type") == "SELL"
    )
    unique_tickers = state.get("tickers", [])
    unique_domains = state.get("domains", [])

    trades_by_ticker: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "volume": 0.0}
    )
    for t in trades:
        ticker = t.get("ticker", "UNKNOWN")
        trades_by_ticker[ticker]["count"] += 1
        trades_by_ticker[ticker]["volume"] += t.get("total_value", 0)

    trades_by_domain: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "volume": 0.0}
    )
    for t in trades:
        domain = t.get("domain", "Unknown")
        trades_by_domain[domain]["count"] += 1
        trades_by_domain[domain]["volume"] += t.get("total_value", 0)

    sample_trades = trades[:10]

    return {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "unique_tickers": unique_tickers,
        "unique_domains": unique_domains,
        "trades_by_ticker": dict(trades_by_ticker),
        "trades_by_domain": dict(trades_by_domain),
        "sample_trades": sample_trades,
    }


def generate_summaries_node(state: dict) -> dict:
    """LangGraph pipeline node that generates AI-powered trade summaries.

    Reads from state:
        filtered_trades        – list of trade dicts
        tickers                – sorted unique ticker list
        domains                – sorted unique domain list
        session_id             – current session identifier
        ticker_enrichment_json – {ticker: {company_performance_summary, stock_performance}}
        domain_enrichment_json – {domain: {domain_performance_summary, tickers_in_domain}}

    Returns a dict with:
        overall_summary   – the overall summary text
        ticker_summaries  – {ticker: summary text}
        domain_summaries  – {domain: summary text}
        summaries_stored  – True when finished
    """
    trades: List[Dict[str, Any]] = state.get("filtered_trades", [])
    tickers: List[str] = state.get("tickers", [])
    domains: List[str] = state.get("domains", [])
    session_id: str = state["session_id"]
    ticker_enrichment: Dict[str, Any] = state.get("ticker_enrichment_json", {})
    domain_enrichment: Dict[str, Any] = state.get("domain_enrichment_json", {})

    logger.info(f"Starting summary generation for session {session_id}: "
                f"{len(trades)} trades, {len(tickers)} tickers, {len(domains)} domains")

    overall_context = _build_overall_context(trades, state)

    overall_system = "You are a senior financial analyst."
    overall_prompt = (
        "Generate a comprehensive daily trade summary based on the following data.\n\n"
        f"--- Trade Data ---\n{json.dumps(overall_context, indent=2, default=str)}\n\n"
        "Include the following sections:\n"
        "- **Executive Summary**\n"
        "- **Volume Analysis**\n"
        "- **Notable Activity**\n"
        "- **Sector Overview**\n"
        "- **Key Observations**\n"
        "- **Risk Flags**\n\n"
        "Write 300-400 words in clean markdown format."
    )

    logger.info(f"Generating overall summary for session {session_id}")
    try:
        overall_summary = call_llm(overall_prompt, system_prompt=overall_system)
        store_summary(session_id, "overall", overall_summary)
        logger.info(f"Generated and stored overall summary for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to generate overall summary for session {session_id}: {e}")
        overall_summary = f"Error generating summary: {e}"

    # Group trades by ticker
    ticker_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        ticker_trades[t.get("ticker", "")].append(t)

    ticker_summaries: Dict[str, str] = {}

    logger.info(f"Generating summaries for {len(tickers)} tickers in session {session_id}")

    for ticker in tickers:
        t_trades = ticker_trades.get(ticker, [])
        enrichment = ticker_enrichment.get(ticker, {})

        ticker_system = "You are a senior financial analyst."
        ticker_prompt = (
            f"Generate a trade summary for ticker **{ticker}** based on the data below.\n\n"
            f"--- Today's Trades ---\n{json.dumps(t_trades, indent=2, default=str)}\n\n"
            f"--- Enrichment Data ---\n{json.dumps(enrichment, indent=2, default=str)}\n\n"
            "Include the following sections:\n"
            "- **Trading Activity**\n"
            "- **Market Context**\n"
            "- **Position Analysis**\n"
            "- **Key Insight**\n\n"
            "Write 150-200 words in clean markdown format."
        )

        try:
            summary = call_llm(ticker_prompt, system_prompt=ticker_system)
            ticker_summaries[ticker] = summary
            store_summary(session_id, "ticker", summary, reference_id=ticker)
            logger.debug(f"Generated summary for ticker {ticker} in session {session_id}")
        except Exception as e:
            logger.error(f"Failed to generate summary for ticker {ticker} in session {session_id}: {e}")
            ticker_summaries[ticker] = f"Error generating summary: {e}"

    logger.info(f"Generated summaries for {len(ticker_summaries)} tickers in session {session_id}")

    # Group trades by domain
    domain_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        domain = t.get("domain", "")
        if domain:
            domain_trades[domain].append(t)

    domain_summaries: Dict[str, str] = {}

    logger.info(f"Generating summaries for {len(domains)} domains in session {session_id}")

    for domain in domains:
        d_trades = domain_trades.get(domain, [])
        enrichment = domain_enrichment.get(domain, {})

        domain_system = "You are a senior financial analyst."
        domain_prompt = (
            f"Generate a sector summary for the **{domain}** domain based on the data below.\n\n"
            f"--- Today's Trades ---\n{json.dumps(d_trades, indent=2, default=str)}\n\n"
            f"--- Enrichment Data ---\n{json.dumps(enrichment, indent=2, default=str)}\n\n"
            "Include the following sections:\n"
            "- **Sector Activity**\n"
            "- **Sector Context**\n"
            "- **Buy/Sell Sentiment**\n"
            "- **Sector Insight**\n\n"
            "Write 150-200 words in clean markdown format."
        )

        try:
            summary = call_llm(domain_prompt, system_prompt=domain_system)
            domain_summaries[domain] = summary
            store_summary(session_id, "domain", summary, reference_id=domain)
            logger.debug(f"Generated summary for domain {domain} in session {session_id}")
        except Exception as e:
            logger.error(f"Failed to generate summary for domain {domain} in session {session_id}: {e}")
            domain_summaries[domain] = f"Error generating summary: {e}"

    logger.info(f"Generated summaries for {len(domain_summaries)} domains in session {session_id}")
    logger.info(f"Summary generation completed for session {session_id}")

    return {
        "overall_summary": overall_summary,
        "ticker_summaries": ticker_summaries,
        "domain_summaries": domain_summaries,
        "summaries_stored": True,
    }
