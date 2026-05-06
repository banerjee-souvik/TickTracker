# TickTracker — Bharat Equity Sentinel
## Approach Document

---

## 1. Problem Statement

Indian retail investors lack a tool that separates **material corporate events** (SEBI filings, auditor resignations, earnings misses) from market noise (analyst price targets, generic upgrades). This tool monitors NSE/BSE stocks, scores news for materiality using an AI engine, surfaces alerts on a real-time dashboard, and pushes high-signal events to Telegram.

---

## 2. Goals

- **Real-time awareness** of material events for a personal watchlist of NSE/BSE tickers
- **AI-powered materiality scoring** — no alert fatigue, only score ≥ 7 triggers a notification
- **Unified dashboard** — prices, alerts timeline, news feed, watchlist management
- **Telegram bot** — passive alerts + interactive queries (price, latest news, add/remove tickers)
- **Extensible** — new data sources or scoring rules should require minimal code changes

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        SCHEDULER                            │
│              (APScheduler — every 15 min)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │      SCRAPER AGENT      │
              │  Firecrawl + RSS Feeds  │
              │  (SEBI, NSE, BSE,       │
              │   Moneycontrol, ET)     │
              └────────────┬────────────┘
                           │  raw news docs
              ┌────────────▼────────────┐
              │    ANALYSIS AGENT       │
              │   Gemini 2.0 Flash       │
              │  Materiality Score 1-10 │
              │  Sentiment + Summary    │
              └──────┬─────────┬────────┘
                     │         │
           score≥7   │         │  always
                     │         │
       ┌─────────────▼──┐  ┌───▼──────────────┐
       │  TELEGRAM BOT  │  │    MONGODB        │
       │  Alert Push    │  │  alerts collection│
       │  + Query Mode  │  │  watchlist        │
       └────────────────┘  │  raw_news         │
                           └───────┬───────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   FASTAPI BACKEND   │
                        │   REST + WebSocket  │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   NEXT.JS DASHBOARD │
                        │   Real-time UI      │
                        └─────────────────────┘
```

---

## 4. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Async-first, great financial lib support |
| **AI Engine** | FinBERT (`ProsusAI/finbert`) + keyword rules | Sentiment via finance-tuned BERT, materiality via rules — local, free, no rate limits |
| **Stock Data** | `yfinance` + NSE India unofficial API | Free, covers NSE/BSE, OHLCV + metadata |
| **News Scraping** | `feedparser` (RSS) + NSE JSON API via `httpx` | No API key needed, free, structured data |
| **Database** | MongoDB (via `motor` async driver) | Schema-flexible alert documents, raw JSON storage |
| **Dashboard** | Next.js 14 (App Router) + TailwindCSS | SSR + real-time WebSocket support |
| **Charts** | TradingView Lightweight Charts | Professional-grade financial charting, free |
| **Telegram** | `python-telegram-bot` v21 (async) | Mature, supports inline queries + webhooks |
| **Scheduler** | APScheduler 3.x | In-process job scheduling, no extra infra |
| **Deployment** | Docker Compose (local-first) | Reproducible, easy to push to VPS later |

---

## 5. Data Model (MongoDB Collections)

### `watchlist`
```json
{
  "_id": "RELIANCE.NS",
  "name": "Reliance Industries Ltd",
  "exchange": "NSE",
  "sector": "Energy",
  "added_at": "2026-05-06T00:00:00Z",
  "active": true
}
```

### `alerts`
```json
{
  "_id": "ObjectId",
  "ticker": "RELIANCE.NS",
  "headline": "Auditor flags going-concern doubt in Q4 notes",
  "materiality_score": 9,
  "sentiment": "Bearish",
  "summary": "...",
  "watch": "Q1 FY27 cash flow statement",
  "source_url": "https://...",
  "raw_content": "...",
  "telegram_sent": true,
  "created_at": "2026-05-06T10:30:00Z"
}
```

### `price_cache`
```json
{
  "_id": "RELIANCE.NS",
  "ltp": 2945.50,
  "change_pct": -1.23,
  "volume": 4821034,
  "52w_high": 3217.00,
  "52w_low": 2220.10,
  "fetched_at": "2026-05-06T10:00:00Z"
}
```

---

## 6. News Sources & RSS Feeds

| Source | Type | URL Pattern |
|---|---|---|
| SEBI Corporate Filings | RSS | `https://www.sebi.gov.in/rss.html` |
| NSE Announcements | JSON API | `https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={SYMBOL}` |
| Moneycontrol News | RSS | `https://www.moneycontrol.com/rss/results.xml` |
| ET Markets | RSS | `https://economictimes.indiatimes.com/markets/rss.cms` |
| BSE Filings | Scrape | `https://www.bseindia.com/corporates/ann.html` |

---

## 7. Materiality Scoring Rules (passed to Claude)

```
Score 1-4  → Routine: price targets, generic upgrades, FII/DII data
Score 5-6  → Notable: new product launch, management commentary, block deals
Score 7    → Alert threshold
Score 7-8  → Important: earnings miss/beat >10%, large capex announcement, key management change
Score 9-10 → Critical: auditor resignation, SEBI investigation, promoter pledge increase >5%, 
             M&A announcement, fraud allegation, insolvency filing
```

---

## 8. Dashboard Pages

| Page | Description |
|---|---|
| `/` | Overview — watchlist prices, recent high-score alerts, market breadth |
| `/alerts` | Full alert log with filters (ticker, score, sentiment, date) |
| `/ticker/[symbol]` | Per-ticker view — price chart, all alerts, latest filings |
| `/settings` | Manage watchlist, Telegram config, scan interval |

---

## 9. Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome + help |
| `/price RELIANCE.NS` | Get current LTP + day change |
| `/latest RELIANCE.NS` | Last 3 alerts for a ticker |
| `/add TATAMOTORS.NS` | Add ticker to watchlist |
| `/remove TATAMOTORS.NS` | Remove ticker from watchlist |
| `/watchlist` | List all monitored tickers |
| `/scan` | Trigger a manual scan now |

---

## 10. Project Directory Structure

```
TickTracker/
├── backend/
│   ├── agents/
│   │   ├── scraper_agent.py
│   │   ├── analysis_agent.py
│   │   └── alert_agent.py
│   ├── services/
│   │   ├── stock_service.py       # yfinance wrapper
│   │   ├── telegram_service.py    # bot + push notifications
│   │   └── mongo_service.py       # DB operations
│   ├── scheduler/
│   │   └── jobs.py                # APScheduler job definitions
│   ├── api/
│   │   ├── routes/
│   │   │   ├── watchlist.py
│   │   │   ├── alerts.py
│   │   │   └── prices.py
│   │   └── websocket.py           # real-time alert push to dashboard
│   ├── main.py                    # FastAPI app entrypoint
│   └── config.py                  # env vars, constants
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Dashboard overview
│   │   ├── alerts/page.tsx
│   │   └── ticker/[symbol]/page.tsx
│   ├── components/
│   │   ├── AlertCard.tsx
│   │   ├── PriceWidget.tsx
│   │   ├── WatchlistTable.tsx
│   │   └── Chart.tsx
│   └── lib/
│       └── api.ts                 # API client
├── APPROACH.md
├── AGENTS.md
├── docker-compose.yml
└── .env.example
```

---

## 11. Build Phases

### Phase 1 — Core Pipeline (Week 1)
- [ ] MongoDB setup + data models
- [ ] `yfinance` stock service
- [ ] RSS news scraper
- [ ] Claude analysis agent (materiality scoring)
- [ ] Alert storage pipeline

### Phase 2 — Telegram Bot (Week 2)
- [ ] Bot setup + command handlers
- [ ] Alert push on score ≥ 7
- [ ] Watchlist management via bot

### Phase 3 — Dashboard (Week 3)
- [ ] FastAPI REST + WebSocket endpoints
- [ ] Next.js dashboard — overview, alerts, ticker pages
- [ ] TradingView chart integration

### Phase 4 — Polish & Deploy (Week 4)
- [ ] Docker Compose setup
- [ ] `.env` configuration management
- [ ] Rate limiting, error handling, retries
- [ ] Optional: VPS deployment (Railway / Render / DigitalOcean)
