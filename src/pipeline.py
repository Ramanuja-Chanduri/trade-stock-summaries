"""LangGraph pipeline orchestration for TradeSummaryAI.

Defines the PipelineState schema, builds the sequential LangGraph
StateGraph, and provides a convenience ``run_pipeline`` coroutine.
"""

from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from src.logger import get_logger
from src.nodes.ingest import ingest_node

logger = get_logger(__name__)

from src.nodes.filter_extract import filter_extract_node
from src.nodes.calculate_metrics import calculate_metrics_node
from src.nodes.fetch_enrichment import fetch_enrichment_node
from src.nodes.build_enrichment import build_enrichment_node
from src.nodes.generate_summaries import generate_summaries_node


class PipelineState(TypedDict, total=False):
    # Input
    raw_content: bytes
    file_type: str
    session_id: str

    # After ingest
    trades: List[Dict[str, Any]]
    trade_count: int

    # After filter_extract
    tickers: List[str]
    domains: List[str]
    filtered_trades: List[Dict[str, Any]]

    # After calculate_metrics
    metrics_computed: bool

    # After fetch_enrichment
    stock_data: Dict[str, Any]
    company_data: Dict[str, str]
    domain_data: Dict[str, str]

    # After build_enrichment
    ticker_enrichment_json: Dict[str, Dict[str, Any]]
    domain_enrichment_json: Dict[str, Dict[str, Any]]
    enrichment_stored: bool

    # After generate_summaries
    overall_summary: str
    ticker_summaries: Dict[str, str]
    domain_summaries: Dict[str, str]
    summaries_stored: bool


def build_pipeline() -> StateGraph:
    """Build and compile the sequential LangGraph pipeline.

    Node order:
        ingest → filter_extract → calculate_metrics →
        fetch_enrichment → build_enrichment → generate_summaries → END
    """
    logger.info("Building LangGraph pipeline")
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("ingest", ingest_node)

    graph.add_node("filter_extract", filter_extract_node)
    graph.add_node("calculate_metrics", calculate_metrics_node)
    graph.add_node("fetch_enrichment", fetch_enrichment_node)
    graph.add_node("build_enrichment", build_enrichment_node)
    graph.add_node("generate_summaries", generate_summaries_node)

    # Sequential edges
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "filter_extract")
    graph.add_edge("filter_extract", "calculate_metrics")
    graph.add_edge("calculate_metrics", "fetch_enrichment")
    graph.add_edge("fetch_enrichment", "build_enrichment")
    graph.add_edge("build_enrichment", "generate_summaries")
    graph.add_edge("generate_summaries", END)

    compiled = graph.compile()
    logger.info("Pipeline compiled successfully")
    return compiled



async def run_pipeline(
    content: bytes,
    file_type: str,
    session_id: str,
) -> dict:
    """Execute the full pipeline and return key results.

    Args:
        content: Raw file content (CSV or JSON bytes).
        file_type: ``"csv"`` or ``"json"``.
        session_id: Unique session identifier for this upload.

    Returns:
        A dict with ``trade_count``, ``tickers``, and ``domains``.
    """
    logger.info(f"Starting pipeline execution for session {session_id}")
    pipeline = build_pipeline()

    initial_state: Dict[str, Any] = {
        "raw_content": content,
        "file_type": file_type,
        "session_id": session_id,
    }

    try:
        result = await pipeline.ainvoke(initial_state)
        logger.info(f"Pipeline execution completed for session {session_id}: "
                   f"trade_count={result.get('trade_count', 0)}, "
                   f"tickers={len(result.get('tickers', []))}, "
                   f"domains={len(result.get('domains', []))}")
        return {
            "trade_count": result.get("trade_count", 0),
            "tickers": result.get("tickers", []),
            "domains": result.get("domains", []),
        }
    except Exception as e:
        logger.error(f"Pipeline execution failed for session {session_id}: {e}")
        raise
