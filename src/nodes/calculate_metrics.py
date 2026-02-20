"""Metrics calculation pipeline node for TradeSummaryAI.

Computes overall, per-ticker, and per-domain trading metrics and persists
each via ``store_metric``.
"""

import json
from collections import Counter, defaultdict
from typing import Any, Dict, List

from src.database import store_metric


def calculate_metrics_node(state: dict) -> dict:
    """LangGraph pipeline node that computes and stores trading metrics.

    Reads from state:
        filtered_trades – list of trade dicts
        session_id      – current session identifier
        tickers         – sorted unique ticker list
        domains         – sorted unique domain list

    Returns a dict with:
        metrics_computed – ``True`` when finished
    """
    trades: List[Dict[str, Any]] = state.get("filtered_trades", [])
    session_id: str = state["session_id"]
    tickers: List[str] = state.get("tickers", [])
    domains: List[str] = state.get("domains", [])

    # ------------------------------------------------------------------
    # Overall metrics
    # ------------------------------------------------------------------
    total_trades = len(trades)
    total_volume = sum(t.get("total_value", 0) for t in trades)
    buy_volume = sum(
        t.get("total_value", 0) for t in trades if t.get("trade_type") == "BUY"
    )
    sell_volume = sum(
        t.get("total_value", 0) for t in trades if t.get("trade_type") == "SELL"
    )
    buy_count = sum(1 for t in trades if t.get("trade_type") == "BUY")
    sell_count = sum(1 for t in trades if t.get("trade_type") == "SELL")
    unique_tickers = len(tickers)
    unique_domains = len(domains)
    avg_trade_size = total_volume / total_trades if total_trades else 0.0

    # Top traded ticker (by trade count)
    ticker_counter: Counter = Counter(t.get("ticker") for t in trades)
    top_traded_ticker = ticker_counter.most_common(1)[0][0] if ticker_counter else ""

    # Top traded domain (by trade count)
    domain_counter: Counter = Counter(t.get("domain") for t in trades)
    top_traded_domain = domain_counter.most_common(1)[0][0] if domain_counter else ""

    overall_metrics = {
        "total_trades": str(total_trades),
        "total_volume": f"{total_volume:.2f}",
        "buy_volume": f"{buy_volume:.2f}",
        "sell_volume": f"{sell_volume:.2f}",
        "buy_count": str(buy_count),
        "sell_count": str(sell_count),
        "unique_tickers": str(unique_tickers),
        "unique_domains": str(unique_domains),
        "avg_trade_size": f"{avg_trade_size:.2f}",
        "top_traded_ticker": top_traded_ticker,
        "top_traded_domain": top_traded_domain,
    }

    for name, value in overall_metrics.items():
        store_metric(session_id, name, value, category="overall")

    # ------------------------------------------------------------------
    # Per-ticker metrics
    # ------------------------------------------------------------------
    ticker_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        ticker_trades[t.get("ticker", "")].append(t)

    for ticker in tickers:
        t_trades = ticker_trades.get(ticker, [])
        t_buy = [x for x in t_trades if x.get("trade_type") == "BUY"]
        t_sell = [x for x in t_trades if x.get("trade_type") == "SELL"]
        prices = [x.get("price", 0) for x in t_trades if x.get("price")]

        buy_qty = sum(x.get("quantity", 0) for x in t_buy)
        sell_qty = sum(x.get("quantity", 0) for x in t_sell)

        ticker_metric = {
            "trade_count": len(t_trades),
            "buy_count": len(t_buy),
            "sell_count": len(t_sell),
            "total_volume": f"{sum(x.get('total_value', 0) for x in t_trades):.2f}",
            "buy_volume": f"{sum(x.get('total_value', 0) for x in t_buy):.2f}",
            "sell_volume": f"{sum(x.get('total_value', 0) for x in t_sell):.2f}",
            "avg_price": f"{(sum(prices) / len(prices)) if prices else 0:.2f}",
            "min_price": f"{min(prices) if prices else 0:.2f}",
            "max_price": f"{max(prices) if prices else 0:.2f}",
            "net_position": buy_qty - sell_qty,
        }

        store_metric(
            session_id,
            "ticker_metrics",
            json.dumps(ticker_metric),
            category="ticker",
            reference_id=ticker,
        )

    # ------------------------------------------------------------------
    # Per-domain metrics
    # ------------------------------------------------------------------
    domain_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        domain_trades[t.get("domain", "")].append(t)

    for domain in domains:
        d_trades = domain_trades.get(domain, [])
        d_buy = sum(1 for x in d_trades if x.get("trade_type") == "BUY")
        d_sell = sum(1 for x in d_trades if x.get("trade_type") == "SELL")
        d_tickers = sorted({x.get("ticker") for x in d_trades if x.get("ticker")})

        domain_metric = {
            "trade_count": len(d_trades),
            "total_volume": f"{sum(x.get('total_value', 0) for x in d_trades):.2f}",
            "ticker_count": len(d_tickers),
            "tickers": d_tickers,
            "buy_sell_ratio": f"{(d_buy / d_sell) if d_sell else d_buy:.2f}",
        }

        store_metric(
            session_id,
            "domain_metrics",
            json.dumps(domain_metric),
            category="domain",
            reference_id=domain,
        )

    return {"metrics_computed": True}
