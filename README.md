# TickTracker — Bharat Equity Sentinel

An AI-powered monitoring tool for Indian stock markets (NSE/BSE). Watches your watchlist, scores news for materiality using Claude, and pushes high-signal alerts to Telegram — with a real-time dashboard.

## What it does

- Scrapes SEBI filings, NSE/BSE announcements, Moneycontrol, and ET Markets every 15 minutes
- Scores each news item 1–10 for materiality using Claude Sonnet
- Sends a Telegram alert only when score ≥ 7 — no noise
- Streams live alerts to a Next.js dashboard via WebSocket
- Supports watchlist management via the dashboard or Telegram bot commands

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| AI | FinBERT (`ProsusAI/finbert`) + keyword rules (local, no API key) |
| Database | MongoDB (async via `motor`) |
| Stock data | `yfinance` |
| News | `feedparser` (RSS) + NSE JSON API (`httpx`) |
| Dashboard | Next.js 14 + TailwindCSS + TradingView Charts |
| Telegram | `python-telegram-bot` v21 |
| Scheduler | APScheduler |
| Infra | Docker Compose |

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for MongoDB)
- API keys: Gemini (AI Studio), Telegram Bot

## Setup

**1. Clone and configure**

```bash
git clone <repo>
cd TickTracker
cp .env.example .env
# Fill in your API keys in .env
```

**2. Start MongoDB**

```bash
docker compose up mongo -d
```

**3. Run the backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**4. Run the frontend** *(Phase 3)*

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:3000`.

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key — free at [aistudio.google.com](https://aistudio.google.com) |
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_IDS` | Comma-separated chat IDs to receive alerts |
| `MONGO_URI` | MongoDB connection string (default: `mongodb://localhost:27017`) |
| `MONGO_DB` | Database name (default: `ticktracker`) |
| `SCAN_INTERVAL_MINUTES` | How often to scan for news (default: `15`) |

## API Endpoints

```
GET    /api/watchlist              List active tickers
POST   /api/watchlist              Add ticker (validates against NSE/BSE)
DELETE /api/watchlist/{ticker}     Remove ticker

GET    /api/alerts                 List alerts (filter: ticker, min_score, sentiment)
GET    /api/alerts/{ticker}        Alerts for a specific ticker

GET    /api/prices                 All cached prices
GET    /api/prices/{ticker}        Price for a specific ticker

POST   /api/scan                   Trigger immediate scan

WS     /ws                         Real-time alert stream
```

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome + help |
| `/price RELIANCE.NS` | Current LTP and day change |
| `/latest RELIANCE.NS` | Last 3 alerts for a ticker |
| `/add TATAMOTORS.NS` | Add to watchlist |
| `/remove TATAMOTORS.NS` | Remove from watchlist |
| `/watchlist` | List all monitored tickers |
| `/scan` | Trigger an immediate scan |

## Alert Format

High-materiality events (score ≥ 7) are sent to Telegram in this format:

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
| 7–8 | Important | Earnings miss/beat >10%, large capex, key management change |
| 9–10 | Critical | Auditor resignation, SEBI probe, promoter pledge surge, M&A, insolvency |

## Project Structure

```
TickTracker/
├── backend/
│   ├── agents/          # scraper, analysis, alert agents
│   ├── services/        # mongo, stock, telegram services
│   ├── scheduler/       # APScheduler job definitions
│   ├── api/             # FastAPI routes + WebSocket manager
│   ├── main.py
│   └── config.py
├── frontend/            # Next.js dashboard (Phase 3)
├── APPROACH.md          # Architecture decisions and data models
├── AGENTS.md            # Agent specs: inputs, outputs, prompts, failure behaviour
├── docker-compose.yml
└── .env.example
```

## Build Phases

- [x] **Phase 1** — Core pipeline: MongoDB, stock service, scraper, Claude analysis, alert storage
- [ ] **Phase 2** — Telegram bot command handlers
- [ ] **Phase 3** — Next.js dashboard with real-time WebSocket feed
- [ ] **Phase 4** — Docker Compose packaging, error handling, optional VPS deploy
