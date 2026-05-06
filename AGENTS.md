# AGENTS.md — Bharat Equity Sentinel

This file defines every AI agent and automated worker in TickTracker. Each entry covers its responsibility, inputs, outputs, tools it may call, and failure behaviour.

---

## Agent Index

| Agent | File | Trigger | Output |
|---|---|---|---|
| Scraper Agent | `backend/agents/scraper_agent.py` | Scheduler / manual | Raw news documents → MongoDB `raw_news` |
| Analysis Agent | `backend/agents/analysis_agent.py` | Per raw news doc | Scored alert document → MongoDB `alerts` |
| Alert Agent | `backend/agents/alert_agent.py` | Per scored alert | Telegram push |
| Telegram Bot | `backend/services/telegram_service.py` | User commands | Bot responses + watchlist mutations *(Phase 2 — not yet built)* |

---

## 1. Scraper Agent

**Role:** Fetches fresh news and filings for every ticker in the active watchlist.

**Trigger:** APScheduler job every 15 minutes, or `POST /api/scan` (manual).

**Inputs:**
- Active watchlist from MongoDB `watchlist` collection
- Configured news sources (RSS feeds from `config.py`)

**Steps:**
1. Fetch all active tickers from `watchlist`.
2. For each ticker, query the following:
   - RSS feeds: SEBI, Moneycontrol, ET Markets — parsed with `feedparser`
   - NSE Announcements JSON API — `nseindia.com/api/corporate-announcements` per symbol via `httpx`
3. Apply a **24-hour lookback filter** (`NEWS_LOOKBACK_HOURS = 24`). Articles older than 24 hours are discarded before any DB write.
4. Deduplicate against `raw_news` collection by URL hash (SHA-256 of `source_url`).
5. Persist new documents to `raw_news` with status `pending_analysis`.
6. Call Analysis Agent for each new document.

**Output document (`raw_news`):**
```json
{
  "url_hash": "sha256_of_url",
  "ticker": "RELIANCE.NS",
  "headline": "...",
  "source_url": "...",
  "source_name": "Moneycontrol",
  "raw_content": "...",
  "status": "pending_analysis",
  "scraped_at": "ISO8601"
}
```

**Failure behaviour:**
- Individual source failure → log warning, skip source, continue with others
- NSE API rate limited → log and skip, RSS feeds still run
- If entire run fails → APScheduler retries on next interval

**Tools used:** `feedparser`, `httpx`, `motor` (MongoDB async driver)

---

## 2. Analysis Agent

**Role:** Scores each raw news document for materiality and sentiment, then builds a structured alert.

**Trigger:** New document inserted into `raw_news` with status `pending_analysis`.

**Inputs:**
- Raw news document (`headline` + `raw_content`) from `raw_news` collection

**Steps:**
1. Fetch raw doc from `raw_news`.
2. Score materiality via keyword rules (`scorer_service.py`): first-match wins across ordered keyword groups (score 10 → 3), default 4 if nothing matches.
3. Score sentiment via FinBERT (`ProsusAI/finbert`) running locally in a thread pool: input is `headline + raw_content[:512]`, label mapped to Bullish / Bearish / Neutral.
4. Build a template-based summary (no LLM call): `"{ticker} — {headline} (Source: {source_name}). Materiality rated {score}/10."`.
5. Write scored alert to `alerts` collection.
6. Update `raw_news` status to `analysed`.
7. If `materiality_score >= MATERIALITY_THRESHOLD` → pass alert to Alert Agent.

**Materiality keyword groups** (see `scorer_service.py` for full list):

| Score | Trigger examples |
|---|---|
| 10 | auditor resign, going concern, fraud, insolvency |
| 9 | sebi probe, sebi investigation, sebi notice, M&A, delisting, promoter pledge |
| 8 | ceo steps down, cfo steps down, rating downgrade, order win, earnings miss |
| 7 | dividend, buyback, quarterly results, earnings beat |
| 5 | product launch, block deal, MOU |
| 3 | price target, analyst upgrade, market wrap |
| 4 | *(default)* |

**Output document (`alerts`):**
```json
{
  "ticker": "RELIANCE.NS",
  "headline": "...",
  "materiality_score": 9,
  "sentiment": "Bearish",
  "summary": "...",
  "watch": "...",
  "source_url": "...",
  "source_name": "...",
  "telegram_sent": false,
  "created_at": "ISO8601"
}
```

**Failure behaviour:**
- FinBERT inference error → default sentiment to `Neutral`, continue
- Unhandled exception → mark doc `analysis_failed`, log error, move on
- `analysis_failed` docs are visible in dashboard for awareness

**Tools used:** `transformers` (FinBERT `ProsusAI/finbert` via `pipeline`), `scorer_service.py`, `motor`

**Cost note:** Completely free — no API calls. FinBERT downloads once (~440 MB) on first run and is cached in `~/.cache/huggingface/`.

---

## 3. Alert Agent

**Role:** Dispatches high-materiality alerts to Telegram.

**Trigger:** Analysis Agent passes an alert with `materiality_score >= MATERIALITY_THRESHOLD` (default 7; currently 4 for testing).

**Inputs:**
- Alert document from `alerts` collection
- Telegram `chat_id` list from `config.py` (supports multiple subscribers)

**Steps:**
1. Format Telegram message using the defined template:
   ```
   🚨 *[TICKER]* - *[HEADLINE]*
   *Signal:* [SCORE]/10 ([SENTIMENT])
   *Context:* [SUMMARY]
   *Watch:* [WATCH]
   ```
2. Send to all configured `chat_id`s via `python-telegram-bot`.
3. Update alert document: `telegram_sent: true`, `sent_at: ISO8601`.

**Failure behaviour:**
- Telegram API error → retry after 10s, max 3 retries
- If all retries fail → mark `telegram_sent: false`, log error
- Missing / empty `TELEGRAM_BOT_TOKEN` → skip silently (bot is optional)

**Tools used:** `python-telegram-bot`, `motor`

---

## 4. Telegram Bot (Interactive) — Phase 2, not yet built

**Role:** Handles user commands for on-demand queries and watchlist management.

**Trigger:** Incoming Telegram update (polling or webhook).

**Planned commands:**

| Command | Handler | Description |
|---|---|---|
| `/start` | `cmd_start` | Welcome message + command list |
| `/price <TICKER>` | `cmd_price` | Fetch LTP from `price_cache`, refresh if stale (>5 min) |
| `/latest <TICKER>` | `cmd_latest` | Return last 3 alerts for ticker from `alerts` |
| `/add <TICKER>` | `cmd_add` | Validate ticker with `yfinance`, insert into `watchlist` |
| `/remove <TICKER>` | `cmd_remove` | Set `active: false` in `watchlist` |
| `/watchlist` | `cmd_watchlist` | List all active tickers with LTP |
| `/scan` | `cmd_scan` | Trigger immediate scraper run for all tickers |

**Ticker validation (`/add`):**
1. Check if ticker ends with `.NS` or `.BO`. If not, append `.NS` by default.
2. Call `yfinance.Ticker(symbol).info`. If `longName` is missing → invalid ticker, reject with message.
3. Insert to `watchlist` if valid.

**Failure behaviour:**
- Unknown command → reply with help text
- Invalid ticker → friendly error message, no DB write
- DB unreachable → reply "Service temporarily unavailable"

**Tools used:** `python-telegram-bot`, `yfinance`, `motor`

---

## Agent Communication Pattern

Agents communicate via **MongoDB document state** rather than an internal queue or message broker. This avoids operational overhead.

```
raw_news.status:
  "pending_analysis"  → waiting for Analysis Agent
  "analysed"          → processed successfully
  "analysis_failed"   → failed after retries, needs manual review

alerts.telegram_sent:
  false               → waiting for / failed Alert Agent dispatch
  true                → successfully sent
```

The dashboard fetches alerts via REST (`GET /api/alerts`) on a 60-second poll cycle. A WebSocket endpoint (`/ws`) exists on the backend but is not consumed by the dashboard — it is reserved for a future live price streaming feature.

---

## Adding a New Agent

1. Create `backend/agents/your_agent.py`
2. Define an async `run(doc_id: str)` entrypoint
3. Register it in `backend/scheduler/jobs.py` or wire it to an existing agent's output
4. Document it in this file following the same structure
