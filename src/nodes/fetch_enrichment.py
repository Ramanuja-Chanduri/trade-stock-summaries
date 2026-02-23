"""Enrichment fetching pipeline node for TradeSummaryAI.

Fetches three types of enrichment data per session:
  1. Stock price data via yfinance (5-day history per ticker)
  2. Company news via LLM + DuckDuckGo search (per ticker)
  3. Domain/sector trends via LLM + DuckDuckGo search (per domain)
"""

from typing import Any, Dict, List

import yfinance as yf

from src.llm_client import call_llm_with_search
from src.logger import get_logger

logger = get_logger(__name__)




def _get_company_name(ticker: str, trades: List[Dict[str, Any]]) -> str:
    """Look up the company name for a ticker from the trade data.

    Falls back to the ticker symbol itself if no company name is found.
    """
    for trade in trades:
        if trade.get("ticker") == ticker and trade.get("company_name"):
            return trade["company_name"]
    return ticker


def _fetch_stock_data(ticker: str) -> Dict[str, Any]:
    """Fetch 5-day price history for *ticker* via yfinance.

    Returns a dict with current_price, week_high, week_low, week_open,
    week_close, week_volume, price_change_pct, and a daily_prices array.
    """
    try:
        logger.debug(f"Fetching stock data for ticker: {ticker}")
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")

        if hist.empty:
            logger.warning(f"No stock data available for ticker: {ticker}")
            return {"error": f"No stock data available for {ticker}"}


        daily_prices = []
        for date, row in hist.iterrows():
            daily_prices.append({
                "date": str(date.date()),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        current_price = round(float(hist["Close"].iloc[-1]), 2)
        week_open = round(float(hist["Open"].iloc[0]), 2)
        week_close = current_price
        week_high = round(float(hist["High"].max()), 2)
        week_low = round(float(hist["Low"].min()), 2)
        week_volume = int(hist["Volume"].sum())

        price_change_pct = 0.0
        if week_open != 0:
            price_change_pct = round(
                ((week_close - week_open) / week_open) * 100, 2
            )

        return {
            "current_price": current_price,
            "week_high": week_high,
            "week_low": week_low,
            "week_open": week_open,
            "week_close": week_close,
            "week_volume": week_volume,
            "price_change_pct": price_change_pct,
            "daily_prices": daily_prices,
        }

    except Exception as e:
        logger.error(f"Failed to fetch stock data for {ticker}: {e}")
        return {"error": f"Failed to fetch stock data for {ticker}: {e}"}



def _fetch_company_news(ticker: str, company_name: str) -> str:
    """Fetch recent company news/analysis via LLM + DuckDuckGo search."""
    logger.info(f"Fetching company news for {ticker} ({company_name})")
    prompt = (
        f"Latest news and analysis for {company_name} ({ticker}): "
        f"recent company news, performance drivers, analyst sentiment, "
        f"and key business developments. "
        f"Provide a concise 150-200 word summary in a factual analyst note style."
    )

    try:
        result = call_llm_with_search(prompt)
        logger.info(f"Successfully fetched company news for {ticker}")
        return result
    except Exception as e:
        logger.error(f"Error fetching company news for {ticker}: {e}")
        return f"Error fetching company news for {ticker}: {e}"



def _fetch_domain_trends(domain: str) -> str:
    """Fetch sector/domain trend analysis via LLM + DuckDuckGo search."""
    logger.info(f"Fetching domain trends for: {domain}")
    prompt = (
        f"{domain} sector analysis: sector performance this week, "
        f"key drivers and headwinds, notable news, and near-term outlook. "
        f"Provide a concise 150-200 word summary in a sector analysis note style."
    )

    try:
        result = call_llm_with_search(prompt)
        logger.info(f"Successfully fetched domain trends for {domain}")
        return result
    except Exception as e:
        logger.error(f"Error fetching domain trends for {domain}: {e}")
        return f"Error fetching domain trends for {domain}: {e}"




def fetch_enrichment_node(state: dict) -> dict:
    """LangGraph pipeline node that fetches enrichment data.

    Reads from state:
        tickers        – list of ticker symbols
        domains        – list of domain/sector names
        session_id     – current session identifier
        filtered_trades – list of trade dicts

    Returns a dict with:
        stock_data   – {ticker: {price data dict}}
        company_data – {ticker: "news summary string"}
        domain_data  – {domain: "trend summary string"}
    """
    tickers: List[str] = state.get("tickers", [])
    domains: List[str] = state.get("domains", [])
    trades: List[Dict[str, Any]] = state.get("filtered_trades", [])
    session_id = state.get("session_id", "unknown")

    logger.info(f"Starting enrichment fetching for session {session_id}: "
                f"{len(tickers)} tickers, {len(domains)} domains")

    stock_data: Dict[str, Any] = {}
    company_data: Dict[str, str] = {}
    domain_data: Dict[str, str] = {}

    # --- Per-ticker enrichment ---
    logger.info(f"Fetching enrichment for {len(tickers)} tickers in session {session_id}")
    for ticker in tickers:
        company_name = _get_company_name(ticker, trades)

        # Stock price data
        stock_data[ticker] = _fetch_stock_data(ticker)

        # Company news via LLM + search
        company_data[ticker] = _fetch_company_news(ticker, company_name)

    logger.info(f"Completed ticker enrichment for session {session_id}: "
                f"{len(stock_data)} stock data, {len(company_data)} company news")

    # --- Per-domain enrichment ---
    logger.info(f"Fetching enrichment for {len(domains)} domains in session {session_id}")
    for domain in domains:
        domain_data[domain] = _fetch_domain_trends(domain)

    logger.info(f"Completed domain enrichment for session {session_id}: "
                f"{len(domain_data)} domain trends")
    logger.info(f"Enrichment fetching completed for session {session_id}")

    return {
        "stock_data": stock_data,
        "company_data": company_data,
        "domain_data": domain_data,
    }
