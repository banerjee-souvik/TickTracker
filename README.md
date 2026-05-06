# TickTracker — Bharat Equity Sentinel

An AI-powered monitoring tool for Indian stock markets (NSE/BSE). Watches your watchlist, scores news for materiality using FinBERT + keyword rules, and pushes high-signal alerts to Telegram — with a real-time dashboard.

## What it does

- Scrapes SEBI filings, NSE announcements, Moneycontrol, and ET Markets every 15 minutes
- Scores each news item 1–10 for materiality using keyword rules (local, no API key)
- Analyses sentiment using FinBERT (`ProsusAI/finbert`) running locally
- Sends a Telegram alert when score ≥ 7 — no noise
- Polls for live alerts on the Next.js dashboard every 60 seconds
- Supports watchlist management via the dashboard Settings page

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+ + FastAPI |
| AI — Sentiment | FinBERT (`ProsusAI/finbert`) — local, no API key |
| AI — Materiality | Keyword rule engine (`scorer_service.py`) |
| Database | MongoDB (async via `motor`) |
| Stock data | `yfinance` |
| News | `feedparser` (RSS) + NSE JSON API (`httpx`) |
| Dashboard | Next.js 16 (App Router) + TailwindCSS |
| Telegram | `python-telegram-bot` v21 |
| Scheduler | APScheduler |
| Package manager | Yarn 4 (pinned via Volta) |
| Infra | Docker Compose (MongoDB) |

## Prerequisites

- Python 3.9+
- [Volta](https://volta.sh) (auto-pins Node 22 + Yarn 4)
- Docker (for MongoDB)
- Telegram Bot token (from [@BotFather](https://t.me/BotFather))

## Setup

**1. Clone and configure**

```bash
git clone <repo>
cd TickTracker
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS
```

**2. Start MongoDB**

```bash
docker compose up mongo -d
```

**3. Install Python dependencies**

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

FinBERT (~440 MB) downloads automatically on first run and is cached in `~/.cache/huggingface/`.

**4. Run both apps together**

```bash
make dev
```

This starts the backend on `http://localhost:8000` and the dashboard on `http://localhost:3000`. Ctrl+C stops both.

Or run them separately:

```bash
make backend    # FastAPI only
make frontend   # Next.js only
```

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_IDS` | Comma-separated chat IDs to receive alerts |
| `MONGO_URI` | MongoDB connection string (default: `mongodb://localhost:27017`) |
| `MONGO_DB` | Database name (default: `ticktracker`) |
| `SCAN_INTERVAL_MINUTES` | How often to scan for news (default: `15`) |

No paid API keys required.

## Dashboard Pages

| Page | Description |
|---|---|
| `/` | Overview — stat cards, live alert feed, watchlist prices |
| `/alerts` | Full alert log with search, sentiment filter, and score filter |
| `/ticker/[symbol]` | Per-ticker alert history with price widget |
| `/settings` | Add/remove watchlist tickers, trigger manual scan |

## API Endpoints

```
GET    /api/watchlist              List active tickers
POST   /api/watchlist              Add ticker
DELETE /api/watchlist/{ticker}     Remove ticker

GET    /api/alerts                 List alerts (filter: ticker, min_score, sentiment)
GET    /api/alerts/{ticker}        Alerts for a specific ticker

GET    /api/prices                 All cached prices
GET    /api/prices/{ticker}        Price for a specific ticker

POST   /api/scan                   Trigger immediate scan

WS     /ws                         Real-time WebSocket stream (backend ready, not used by dashboard)
```

API docs at `http://localhost:8000/docs`.

## Telegram Alerts

High-materiality events (score ≥ 7) are pushed automatically:

```
🚨 RELIANCE - Auditor flags going-concern doubt in Q4 notes

Signal: 9/10 (Bearish)
Context: The statutory auditor has included a going-concern emphasis paragraph
         in the Q4 FY26 audit report, citing deteriorating cash flow metrics.
Watch: Q1 FY27 cash flow statement and debt refinancing disclosures
```

## Materiality Scoring Guide

| Score | Category | Examples |
|---|---|---|
| 1–4 | Routine | Price targets, FII/DII data, generic upgrades |
| 5–6 | Notable | Product launches, management commentary, block deals |
| 7–8 | Important | Earnings miss/beat, large capex, key management change |
| 9–10 | Critical | Auditor resignation, SEBI probe, promoter pledge surge, M&A, insolvency |

## Project Structure

```
TickTracker/
├── backend/
│   ├── agents/          # scraper_agent.py, analysis_agent.py, alert_agent.py
│   ├── services/        # mongo_service.py, stock_service.py, telegram_service.py
│   │                    # finbert_service.py, scorer_service.py
│   ├── scheduler/       # jobs.py (APScheduler)
│   ├── api/             # FastAPI routes + websocket.py
│   ├── main.py
│   └── config.py
├── frontend/
│   ├── app/             # page.tsx, OverviewClient.tsx
│   │   ├── alerts/      # AlertsClient.tsx
│   │   ├── settings/    # SettingsClient.tsx
│   │   └── ticker/[symbol]/
│   ├── components/      # AlertCard, PriceWidget, ScoreBadge, SentimentBadge, Sidebar
│   ├── hooks/           # useAlerts.ts (60s polling)
│   └── lib/             # api.ts, types.ts, utils.ts
├── Makefile
├── APPROACH.md
├── AGENTS.md
├── docker-compose.yml
└── .env.example
```

## Build Phases

- [x] **Phase 1** — Core pipeline: MongoDB, stock service, scraper, FinBERT analysis, alert storage
- [x] **Phase 3** — Next.js dashboard: overview, alerts, ticker, settings pages
- [ ] **Phase 2** — Telegram bot command handlers (`/price`, `/latest`, `/add`, `/remove`, etc.)
- [ ] **Phase 4** — Docker Compose full packaging, error handling, optional VPS deploy
