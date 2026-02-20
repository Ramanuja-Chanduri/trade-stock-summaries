# CLAUDE.md — AI Assistant Guide for TradeSummaryAI

## Project Overview

**TradeSummaryAI** — an app that ingests trade CSV/JSON data, enriches it with market intelligence, and generates AI-powered summaries. Both frontend and backend must conform to the API contract defined below.

- **Remote**: GitHub — `Ramanuja-Chanduri/tcs-ai-hackathon`
- **Branch strategy**: Feature branches prefixed with `claude/` for AI-assisted development

## API Contract

**Base URL:** `http://localhost:8000`

Static files are served at `/static/` and the root `GET /` serves the frontend.

### POST /api/upload

Upload trade data as CSV or JSON.

- **Body:** `multipart/form-data` with field `file` (CSV or JSON)
- **Response 200:**
  ```json
  {
    "session_id": "uuid-string",
    "status": "success",
    "trade_count": 20,
    "tickers": ["AAPL", "GOOGL"],
    "domains": ["Technology", "Finance"]
  }
  ```
- **Response 400:**
  ```json
  { "detail": "Only CSV and JSON files supported" }
  ```

### GET /api/summary/overall/{session_id}

- **Response 200:**
  ```json
  { "summary": "markdown string", "summary_type": "overall", "reference_id": null }
  ```
- **Response 404:**
  ```json
  { "detail": "Summary not found" }
  ```

### GET /api/summary/ticker/{session_id}/{ticker}

- **Response 200:**
  ```json
  { "summary": "markdown string", "summary_type": "ticker", "reference_id": "AAPL" }
  ```

### GET /api/summary/domain/{session_id}/{domain}

- **Response 200:**
  ```json
  { "summary": "markdown string", "summary_type": "domain", "reference_id": "Technology" }
  ```

### GET /api/metrics/{session_id}

- **Response 200:**
  ```json
  {
    "metrics": [
      { "metric_name": "total_trades", "metric_value": "20", "category": "overall", "reference_id": null },
      { "metric_name": "total_volume", "metric_value": "1028188.00", "category": "overall", "reference_id": null },
      { "metric_name": "buy_volume", "metric_value": "634968.00", "category": "overall", "reference_id": null },
      { "metric_name": "sell_volume", "metric_value": "393220.00", "category": "overall", "reference_id": null },
      { "metric_name": "buy_count", "metric_value": "14", "category": "overall", "reference_id": null },
      { "metric_name": "sell_count", "metric_value": "6", "category": "overall", "reference_id": null },
      { "metric_name": "unique_tickers", "metric_value": "12", "category": "overall", "reference_id": null },
      { "metric_name": "unique_domains", "metric_value": "5", "category": "overall", "reference_id": null },
      { "metric_name": "avg_trade_size", "metric_value": "51409.40", "category": "overall", "reference_id": null },
      { "metric_name": "top_traded_ticker", "metric_value": "AAPL", "category": "overall", "reference_id": null },
      { "metric_name": "top_traded_domain", "metric_value": "Technology", "category": "overall", "reference_id": null },
      { "metric_name": "ticker_metrics", "metric_value": "{json}", "category": "ticker", "reference_id": "AAPL" },
      { "metric_name": "domain_metrics", "metric_value": "{json}", "category": "domain", "reference_id": "Technology" }
    ]
  }
  ```

### GET /api/tickers/{session_id}

- **Response 200:**
  ```json
  { "tickers": ["AAPL", "GOOGL"] }
  ```

### GET /api/domains/{session_id}

- **Response 200:**
  ```json
  { "domains": ["Technology", "Finance"] }
  ```

## Sample CSV (for testing)

```csv
trade_id,timestamp,ticker,company_name,domain,trade_type,quantity,price,total_value,currency,exchange,trader_id
T001,2026-02-20T09:30:00Z,AAPL,Apple Inc.,Technology,BUY,500,182.50,91250.00,USD,NASDAQ,TR001
T002,2026-02-20T09:31:00Z,GOOGL,Alphabet Inc.,Technology,BUY,200,141.20,28240.00,USD,NASDAQ,TR002
T003,2026-02-20T09:32:00Z,JPM,JPMorgan Chase,Finance,SELL,300,195.80,58740.00,USD,NYSE,TR001
T004,2026-02-20T09:35:00Z,MSFT,Microsoft Corp.,Technology,BUY,150,415.30,62295.00,USD,NASDAQ,TR003
T005,2026-02-20T09:40:00Z,JNJ,Johnson & Johnson,Healthcare,BUY,400,155.60,62240.00,USD,NYSE,TR002
```

**CSV columns:** `trade_id`, `timestamp`, `ticker`, `company_name`, `domain`, `trade_type` (BUY/SELL), `quantity`, `price`, `total_value`, `currency`, `exchange`, `trader_id`

## File Organization

```
tcs-ai-hackathon/
├── CLAUDE.md          # This file — AI assistant context & API contract
├── README.md          # Project description, setup instructions, usage
├── .gitignore         # Language/framework-specific ignores
├── src/               # Source code
├── tests/             # Test files
├── static/            # Frontend static files (served at /static/)
├── docs/              # Documentation (if needed)
└── data/              # Data files (if needed, .gitignore large files)
```

## Development Guidelines

### Git Workflow

- **Default branch**: `main`
- **Feature branches**: Use descriptive branch names (e.g., `feature/auth`, `fix/parsing-bug`)
- **Commits**: Write clear, concise commit messages describing the "why" not just the "what"
- **Push**: Always use `git push -u origin <branch-name>`

### Code Quality

- Keep code simple and focused — hackathon code should prioritize working solutions
- Add comments only where logic is non-obvious
- Avoid over-engineering; build the minimum viable solution first
- Do not commit secrets, API keys, or credentials — use environment variables

### Security

- Never commit `.env` files, API keys, tokens, or credentials
- Use environment variables for all sensitive configuration (e.g., `ANTHROPIC_API_KEY`)
- Validate all external input at system boundaries
- Be cautious with dependencies — only add what is necessary

## Conventions for AI Assistants

- **Read before modifying**: Always read existing files before suggesting changes
- **Minimal changes**: Only modify what is necessary to accomplish the task
- **No speculative features**: Do not add functionality beyond what is requested
- **Preserve existing style**: Match the coding style already present in the file
- **Test awareness**: If tests exist, run them after making changes
- **API contract is authoritative**: All endpoints must match the contract above exactly
- **Update this file**: When significant project structure or tooling decisions are made, update this CLAUDE.md to reflect the current state

## Build & Run Commands

- **Install dependencies**: `pip install -r requirements.txt`
- **Run dev server**: `uvicorn src.main:app --reload --port 8000`
- **Run tests**: `pytest`

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: SQLite (via stdlib `sqlite3`)
- **Orchestration**: LangGraph + LangChain
- **LLM**: ChatOpenAI (via `langchain-openai`)
- **Market data**: yfinance
- **Web search**: DuckDuckGo Search (via `langchain-community`)
- **Validation**: Pydantic v2
