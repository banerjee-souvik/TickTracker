# TickTracker — Bharat Equity Sentinel

An AI-powered Indian stock market monitoring tool. Watches NSE/BSE tickers, scores news for materiality using Claude, pushes high-signal alerts to Telegram, and surfaces everything on a real-time dashboard.

## Key Docs
- [APPROACH.md](APPROACH.md) — Full architecture, data models, build phases
- [AGENTS.md](AGENTS.md) — Every AI agent: inputs, outputs, prompts, failure behaviour

## Stack
- **Backend:** Python 3.12 + FastAPI
- **AI:** FinBERT (`ProsusAI/finbert`) for sentiment + keyword rules for materiality scoring — runs locally, no API key
- **DB:** MongoDB with `motor` (async driver)
- **Stock data:** `yfinance`
- **News:** `feedparser` (RSS) + Firecrawl (scraping)
- **Dashboard:** Next.js 14 (App Router) + TailwindCSS + TradingView Lightweight Charts
- **Telegram:** `python-telegram-bot` v21 (async)
- **Scheduler:** APScheduler
- **Infra:** Docker Compose

## Core Rules
- Tickers always carry exchange suffix: `.NS` for NSE, `.BO` for BSE
- Materiality score ≥ 7 triggers a Telegram alert — below that, silently store only
- Agents communicate via MongoDB document status fields, not a message queue
- Analysis Agent uses structured JSON output from Claude — never free-text parse
- Deduplicate news by SHA-256 hash of `source_url` before analysis

## MongoDB Collections
| Collection | Purpose |
|---|---|
| `watchlist` | Active tickers to monitor |
| `raw_news` | Scraped articles, status: `pending_analysis` → `analysed` / `analysis_failed` |
| `alerts` | Scored + summarised events, `telegram_sent` flag |
| `price_cache` | LTP + OHLCV, refreshed every 15 min |

## Project Structure
```
backend/
  agents/          # scraper_agent.py, analysis_agent.py, alert_agent.py
  services/        # stock_service.py, telegram_service.py, mongo_service.py
  scheduler/       # jobs.py (APScheduler)
  api/             # FastAPI routes + websocket.py
  main.py
  config.py
frontend/
  app/             # Next.js App Router pages
  components/      # AlertCard, PriceWidget, WatchlistTable, Chart
  lib/api.ts
```

## Build Phases
1. **Phase 1** — Core pipeline: MongoDB, stock service, RSS scraper, Claude analysis, alert storage
2. **Phase 2** — Telegram bot: push alerts + command handlers
3. **Phase 3** — Dashboard: FastAPI REST + WebSocket, Next.js UI
4. **Phase 4** — Polish: Docker Compose, error handling, optional VPS deploy
