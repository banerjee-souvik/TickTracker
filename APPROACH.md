# TickTracker — Bharat Equity Sentinel
## Approach Document

---

## 1. Problem Statement

Indian retail investors lack a tool that separates **material corporate events** (SEBI filings, auditor resignations, earnings misses) from market noise (analyst price targets, generic upgrades). This tool monitors NSE/BSE stocks, scores news for materiality using a local AI stack, surfaces alerts on a real-time dashboard, and pushes high-signal events to Telegram.

---

## 2. Goals

- **Real-time awareness** of material events for a personal watchlist of NSE/BSE tickers
- **AI-powered materiality scoring** — no alert fatigue, only score ≥ 7 triggers a notification
- **Unified dashboard** — prices, alert timeline, watchlist management
- **Telegram bot** — passive alerts + interactive queries (price, latest news, add/remove tickers)
- **Zero paid API dependencies** — runs entirely on local models and free data sources

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
              │  RSS Feeds + NSE API    │
              │  (SEBI, NSE,            │
              │   Moneycontrol, ET)     │
              └────────────┬────────────┘
                           │  raw news docs (24h lookback)
              ┌────────────▼────────────┐
              │    ANALYSIS AGENT       │
              │  FinBERT (sentiment)    │
              │  + keyword rules        │
              │  Materiality Score 1-10 │
              └──────┬─────────┬────────┘
                     │         │
           score≥7   │         │  always
                     │         │
       ┌─────────────▼──┐  ┌───▼──────────────┐
       │  TELEGRAM BOT  │  │    MONGODB        │
       │  Alert Push    │  │  alerts collection│
       │  + Query Mode* │  │  watchlist        │
       └────────────────┘  │  raw_news         │
                           └───────┬───────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   FASTAPI BACKEND   │
                        │   REST API          │
                        └──────────┬──────────┘
                                   │  HTTP polling (60s)
                        ┌──────────▼──────────┐
                        │   NEXT.JS DASHBOARD │
                        │   Dark UI           │
                        └─────────────────────┘

* Telegram query commands — Phase 2 (not yet built)
```

---

## 4. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3.9+ + FastAPI | Async-first, great financial lib support |
| **AI — Sentiment** | FinBERT (`ProsusAI/finbert`) | Finance-tuned BERT, runs locally, free, no rate limits |
| **AI — Materiality** | Keyword rule engine (`scorer_service.py`) | Deterministic, explainable, zero latency |
| **Stock Data** | `yfinance` | Free, covers NSE/BSE, OHLCV + metadata |
| **News Scraping** | `feedparser` (RSS) + NSE JSON API via `httpx` | No API key needed, 24h lookback filter applied |
| **Database** | MongoDB (via `motor` async driver) | Schema-flexible alert documents, raw JSON storage |
| **Dashboard** | Next.js 16 (App Router) + TailwindCSS | SSR + client polling, dark theme |
| **Telegram** | `python-telegram-bot` v21 (async) | Mature, supports inline queries + webhooks |
| **Scheduler** | APScheduler 3.x | In-process job scheduling, no extra infra |
| **Package manager** | Yarn 4 + Volta | Reproducible Node/Yarn versions, fast installs |
| **Deployment** | Docker Compose (MongoDB only for now) | Easy local setup, VPS-ready later |

### Why no paid AI API?

We evaluated Claude API, Groq, and Gemini before settling on a local stack:

| Option | Problem |
|---|---|
| Anthropic API | Costs money, not included in Pro subscription |
| Groq free tier | Rate limits hit quickly during testing |
| Gemini free tier | 20 RPD hard limit on 2.5 Flash; exhausted in one session |
| **FinBERT + keywords** | Local, free, finance-specialised, zero latency |

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

### `raw_news`
```json
{
  "_id": "ObjectId",
  "ticker": "RELIANCE.NS",
  "headline": "...",
  "raw_content": "...",
  "source_url": "https://...",
  "source_name": "ET Markets",
  "url_hash": "sha256-of-source_url",
  "status": "pending_analysis | analysed | analysis_failed",
  "published_at": "2026-05-06T09:00:00Z",
  "created_at": "2026-05-06T09:05:00Z"
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
  "source_name": "ET Markets",
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
  "week_52_high": 3217.00,
  "week_52_low": 2220.10,
  "market_cap": 19842300000000,
  "fetched_at": "2026-05-06T10:00:00Z"
}
```

Ticker deduplication: SHA-256 hash of `source_url` stored in `raw_news.url_hash` — articles already seen are skipped before analysis.

---

## 6. News Sources

| Source | Type | Notes |
|---|---|---|
| SEBI Corporate Filings | RSS | `https://www.sebi.gov.in/rss.html` |
| NSE Announcements | JSON API | `nseindia.com/api/corporate-announcements` per symbol |
| Moneycontrol News | RSS | Results + corporate feed |
| ET Markets | RSS | `economictimes.indiatimes.com/markets/rss.cms` |

All sources apply a **24-hour lookback filter** (`NEWS_LOOKBACK_HOURS = 24`) — stale articles from prior days are discarded before any processing.

---

## 7. Materiality Scoring Rules

Implemented in `backend/services/scorer_service.py`. First-match-wins across keyword groups, checked against both headline and content (lowercased).

| Score | Trigger keywords | Category |
|---|---|---|
| 10 | auditor resign, going concern, fraud, insolvency | Existential |
| 9 | sebi probe, sebi investigation, sebi notice, M&A, delisting, promoter pledge | Regulatory / structural |
| 8 | ceo steps down, cfo steps down, rating downgrade, order win, earnings miss | Key event |
| 7 | dividend, buyback, quarterly results, earnings beat | Regular material |
| 5 | product launch, block deal, MOU | Notable |
| 3 | price target, analyst upgrade, market wrap | Routine |
| 4 | *(default — no keyword matched)* | Background |

**Alert threshold:** score ≥ 7 triggers Telegram. Currently set to 4 in `.env` / `config.py` for testing.

---

## 8. Dashboard Pages

All pages are dark-themed (zinc-950 background), server-rendered with a 60-second client polling cycle for new alerts.

| Page | Route | Description |
|---|---|---|
| Overview | `/` | Stat cards (total alerts, high-mat, bullish/bearish), live alert feed, price widgets, watchlist chips |
| Alerts | `/alerts` | Full log with free-text search, sentiment pill filter, score range filter |
| Ticker | `/ticker/[symbol]` | Per-ticker alert history + price widget |
| Settings | `/settings` | Add/remove watchlist tickers, manual scan trigger |

### Component structure

```
components/
  AlertCard.tsx      — full alert card with clickable ticker badge
  PriceWidget.tsx    — LTP, change%, 52-week range bar, market cap
  ScoreBadge.tsx     — colour-coded score (red ≥9, amber ≥7, yellow ≥5, gray)
  SentimentBadge.tsx — dot + label (emerald=Bullish, red=Bearish, gray=Neutral)
  Sidebar.tsx        — fixed left nav with active route highlight
hooks/
  useAlerts.ts       — polls /api/alerts every 60 seconds, merges with SSR initial state
```

### Why polling over WebSocket?

The scanner runs every 15 minutes. A WebSocket connection (with reconnect logic) adds complexity for a benefit that's invisible at that cadence. 60-second polling is simpler, and the backend WebSocket endpoint (`/ws`) remains available if live price streaming is added later.

---

## 9. Telegram Bot

### Push alerts (Phase 1 — complete)

When `alert_agent.py` stores a new alert with `materiality_score ≥ threshold`, it calls `telegram_service.py` which formats and sends a message to all `TELEGRAM_CHAT_IDS`.

### Interactive commands (Phase 2 — not yet built)

| Command | Description |
|---|---|
| `/start` | Welcome + help |
| `/price RELIANCE.NS` | Current LTP + day change |
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
│   │   ├── scraper_agent.py      # RSS + NSE API, 24h filter, dedup by URL hash
│   │   ├── analysis_agent.py     # FinBERT sentiment + keyword materiality scoring
│   │   └── alert_agent.py        # Stores alert, triggers Telegram push
│   ├── services/
│   │   ├── finbert_service.py    # FinBERT inference (thread pool)
│   │   ├── scorer_service.py     # Keyword materiality rule engine
│   │   ├── stock_service.py      # yfinance wrapper, 5-min price cache
│   │   ├── telegram_service.py   # Bot init + push notifications
│   │   └── mongo_service.py      # DB connection + index setup
│   ├── scheduler/
│   │   └── jobs.py               # APScheduler: full_scan every 15min, price refresh
│   ├── api/
│   │   ├── routes/
│   │   │   ├── alerts.py
│   │   │   ├── prices.py
│   │   │   ├── scan.py
│   │   │   └── watchlist.py
│   │   └── websocket.py          # WebSocket manager (backend ready, unused by dashboard)
│   ├── main.py                   # FastAPI app, CORS, lifespan
│   └── config.py                 # Settings, RSS feeds, thresholds
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Overview (SSR)
│   │   ├── OverviewClient.tsx    # Client shell with polling
│   │   ├── alerts/
│   │   │   ├── page.tsx
│   │   │   └── AlertsClient.tsx  # Search + filter UI
│   │   ├── settings/
│   │   │   ├── page.tsx
│   │   │   └── SettingsClient.tsx
│   │   └── ticker/[symbol]/
│   │       └── page.tsx
│   ├── components/
│   │   ├── AlertCard.tsx
│   │   ├── PriceWidget.tsx
│   │   ├── ScoreBadge.tsx
│   │   ├── SentimentBadge.tsx
│   │   └── Sidebar.tsx
│   ├── hooks/
│   │   └── useAlerts.ts          # 60s polling hook
│   ├── lib/
│   │   ├── api.ts                # fetch wrappers for all endpoints
│   │   ├── types.ts              # Alert, Price, WatchlistItem interfaces
│   │   └── utils.ts              # formatters + colour helpers
│   ├── .yarnrc.yml               # nodeLinker: node-modules (Turbopack compat)
│   └── next.config.ts            # turbopack.root set explicitly
├── Makefile                      # make dev / make backend / make frontend / make kill
├── APPROACH.md
├── AGENTS.md
├── docker-compose.yml
└── .env.example
```

---

## 11. Build Phases

### Phase 1 — Core Pipeline ✅
- [x] MongoDB setup + data models
- [x] `yfinance` stock service with 5-min cache
- [x] RSS + NSE JSON API scraper with 24h lookback
- [x] FinBERT sentiment analysis (local)
- [x] Keyword materiality scoring
- [x] Alert storage pipeline
- [x] Telegram push alerts

### Phase 3 — Dashboard ✅
- [x] FastAPI REST endpoints (alerts, prices, watchlist, scan)
- [x] Next.js 16 dark dashboard — overview, alerts, ticker, settings
- [x] 60-second polling for live alert feed
- [x] Score badges, sentiment badges, 52-week range bars

### Phase 2 — Telegram Command Handlers ✅
- [x] `/price`, `/latest`, `/add`, `/remove`, `/watchlist`, `/scan` handlers
- [x] Inline watchlist management via bot (`backend/bot/`)

### Phase 4 — Polish & Deploy
- [ ] Full Docker Compose (backend + frontend containers)
- [ ] Rate limiting, retries, error handling hardening
- [ ] Reset `MATERIALITY_THRESHOLD` from 4 (test) back to 7 (production)
- [ ] Optional: VPS deployment (Railway / Render / DigitalOcean)
