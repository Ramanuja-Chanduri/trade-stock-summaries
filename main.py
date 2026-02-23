"""TradeSummaryAI — FastAPI application entry point.

Serves the frontend, handles trade data uploads, and exposes
summary / metrics / ticker / domain query endpoints.
"""

import uuid

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.database import get_db, get_metrics_by_session, get_summary, init_db
from src.logger import get_logger
from src.models import (
    DomainsResponse,
    MetricItem,
    MetricsResponse,
    SummaryResponse,
    TickersResponse,
    UploadResponse,
)
from src.pipeline import run_pipeline

logger = get_logger(__name__)


app = FastAPI(title="TradeSummaryAI", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup() -> None:
    logger.info("Starting up TradeSummaryAI application")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise



@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    logger.info(f"Received file upload: {file.filename}")
    
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ("csv", "json"):
        logger.warning(f"Unsupported file type: {ext}")
        raise HTTPException(status_code=400, detail="Only CSV and JSON files supported")

    session_id = str(uuid.uuid4())
    logger.info(f"Starting pipeline for session {session_id}, file type: {ext}")

    try:
        contents = await file.read()
        result = await run_pipeline(contents, ext, session_id)
        
        logger.info(f"Pipeline completed for session {session_id}: "
                   f"{result['trade_count']} trades, "
                   f"{len(result['tickers'])} tickers, "
                   f"{len(result['domains'])} domains")

        return UploadResponse(
            session_id=session_id,
            status="success",
            trade_count=result["trade_count"],
            tickers=result["tickers"],
            domains=result["domains"],
        )
    except Exception as e:
        logger.error(f"Pipeline failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")



@app.get("/api/summary/overall/{session_id}", response_model=SummaryResponse)
async def summary_overall(session_id: str):
    logger.info(f"Fetching overall summary for session {session_id}")
    row = get_summary(session_id, "overall")
    if not row:
        logger.warning(f"Overall summary not found for session {session_id}")
        raise HTTPException(status_code=404, detail="Summary not found")
    logger.info(f"Returning overall summary for session {session_id}")
    return SummaryResponse(
        summary=row["summary_text"],
        summary_type="overall",
        reference_id=row.get("reference_id"),
    )



@app.get("/api/summary/ticker/{session_id}/{ticker}", response_model=SummaryResponse)
async def summary_ticker(session_id: str, ticker: str):
    logger.info(f"Fetching ticker summary for session {session_id}, ticker: {ticker.upper()}")
    row = get_summary(session_id, "ticker", reference_id=ticker.upper())
    if not row:
        logger.warning(f"Ticker summary not found for session {session_id}, ticker: {ticker.upper()}")
        raise HTTPException(status_code=404, detail="Summary not found")
    logger.info(f"Returning ticker summary for session {session_id}, ticker: {ticker.upper()}")
    return SummaryResponse(
        summary=row["summary_text"],
        summary_type="ticker",
        reference_id=row.get("reference_id"),
    )



@app.get("/api/summary/domain/{session_id}/{domain}", response_model=SummaryResponse)
async def summary_domain(session_id: str, domain: str):
    logger.info(f"Fetching domain summary for session {session_id}, domain: {domain}")
    row = get_summary(session_id, "domain", reference_id=domain)
    if not row:
        logger.warning(f"Domain summary not found for session {session_id}, domain: {domain}")
        raise HTTPException(status_code=404, detail="Summary not found")
    logger.info(f"Returning domain summary for session {session_id}, domain: {domain}")
    return SummaryResponse(
        summary=row["summary_text"],
        summary_type="domain",
        reference_id=row.get("reference_id"),
    )




@app.get("/api/metrics/{session_id}", response_model=MetricsResponse)
async def metrics(session_id: str):
    logger.info(f"Fetching metrics for session {session_id}")
    rows = get_metrics_by_session(session_id)
    logger.info(f"Returning {len(rows)} metrics for session {session_id}")
    return MetricsResponse(
        metrics=[MetricItem(**r) for r in rows],
    )



@app.get("/api/tickers/{session_id}", response_model=TickersResponse)
async def tickers(session_id: str):
    logger.info(f"Fetching tickers for session {session_id}")
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM raw_trades WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        tickers_list = [r["ticker"] for r in rows]
        logger.info(f"Returning {len(tickers_list)} tickers for session {session_id}")
        return TickersResponse(tickers=tickers_list)
    finally:
        conn.close()



@app.get("/api/domains/{session_id}", response_model=DomainsResponse)
async def domains(session_id: str):
    logger.info(f"Fetching domains for session {session_id}")
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT domain FROM raw_trades WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        domains_list = [r["domain"] for r in rows]
        logger.info(f"Returning {len(domains_list)} domains for session {session_id}")
        return DomainsResponse(domains=domains_list)
    finally:
        conn.close()



if __name__ == "__main__":
    logger.info("Starting uvicorn server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
