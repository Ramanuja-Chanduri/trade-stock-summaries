"""Pydantic models for TradeSummaryAI API request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel


class TradeRecord(BaseModel):
    """Represents a single trade parsed from CSV/JSON input."""

    trade_id: str
    timestamp: str
    ticker: str
    company_name: Optional[str] = None
    domain: str
    trade_type: str
    quantity: int
    price: float
    total_value: float
    currency: str = "USD"
    exchange: Optional[str] = None
    trader_id: Optional[str] = None


class UploadResponse(BaseModel):
    """Response returned after successful trade data upload."""

    session_id: str
    status: str
    trade_count: int
    tickers: List[str]
    domains: List[str]


class SummaryResponse(BaseModel):
    """Response for overall, ticker, or domain summary endpoints."""

    summary: str
    summary_type: str
    reference_id: Optional[str] = None


class MetricItem(BaseModel):
    """A single metric entry."""

    metric_name: str
    metric_value: str
    category: str
    reference_id: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response for the metrics endpoint."""

    metrics: List[MetricItem]


class TickersResponse(BaseModel):
    """Response for the tickers list endpoint."""

    tickers: List[str]


class DomainsResponse(BaseModel):
    """Response for the domains list endpoint."""

    domains: List[str]
