# AGENTS.md — Bharat Equity Sentinel

This file defines every AI agent and automated worker in TickTracker. Each entry covers its responsibility, inputs, outputs, tools it may call, and failure behaviour.

---

## Agent Index

| Agent | File | Trigger | Output |
|---|---|---|---|
| Scraper Agent | `backend/agents/scraper_agent.py` | Scheduler / manual | Raw news documents → MongoDB `raw_news` |
| Analysis Agent | `backend/agents/analysis_agent.py` | Per raw news doc | Scored alert document → MongoDB `alerts` |
| Alert Agent | `backend/agents/alert_agent.py` | Per scored alert | Telegram push + WebSocket event |
| Telegram Bot | `backend/services/telegram_service.py` | User commands | Bot responses + watchlist mutations |

---

## 1. Scraper Agent

**Role:** Fetches fresh news and filings for every ticker in the active watchlist.

**Trigger:** APScheduler job every 15 minutes, or `POST /api/scan` (manual).

**Inputs:**
- Active watchlist from MongoDB `watchlist` collection
- Configured news sources (RSS feeds + Firecrawl URLs from `config.py`)

**Steps:**
1. Fetch all active tickers from `watchlist`.
2. For each ticker, query the following in parallel:
   - RSS feeds: SEBI, NSE, Moneycontrol, ET Markets — parsed with `feedparser`
   - Firecrawl scrape of NSE announcements page filtered by ticker
   - BSE filing page scrape (if ticker has `.BO` suffix)
3. Deduplicate against `raw_news` collection by URL hash (SHA-256 of `source_url`).
4. Persist new documents to `raw_news` with status `pending_analysis`.
5. Emit each new doc ID to the Analysis Agent queue.

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
- Firecrawl rate limit → exponential backoff (2s, 4s, 8s), max 3 retries
- If entire run fails → APScheduler retries on next interval, alert not lost

**Tools used:** `feedparser`, Firecrawl API, `motor` (MongoDB async driver)

---

## 2. Analysis Agent

**Role:** Scores each raw news document for materiality and generates an engineer-grade summary using Claude.

**Trigger:** New document inserted into `raw_news` with status `pending_analysis`.

**Inputs:**
- Raw news document from `raw_news` collection
- Ticker context (sector, recent price) from `price_cache`
- Scoring rubric (defined in `config.py`, injected into system prompt)

**System Prompt Injected to Claude:**
```
You are a senior equity analyst specialising in Indian listed companies (NSE/BSE).
Given a news item, return a JSON object with:
  - materiality_score: integer 1-10
  - sentiment: "Bullish" | "Bearish" | "Neutral"
  - summary: 2-sentence plain-English explanation of the event
  - watch: one key metric or price level to monitor next
  - reasoning: one sentence explaining the score

Scoring guide:
  1-4: Routine (price targets, FII data, generic upgrades)
  5-6: Notable (product launches, management commentary, block deals)
  7-8: Important (earnings miss/beat >10%, large capex, key management change)
  9-10: Critical (auditor resignation, SEBI probe, promoter pledge surge, M&A, insolvency)

Return ONLY valid JSON. No preamble.
```

**Steps:**
1. Fetch raw doc from `raw_news`.
2. Build user message: headline + raw_content (truncated to 4000 tokens).
3. Score materiality via keyword rules (`scorer_service.py`) — first-match wins, rules ordered 10→3.
4. Score sentiment via FinBERT (`ProsusAI/finbert`) running locally in a thread pool.
4. Parse response. If JSON invalid → retry once with a stricter prompt.
5. Write scored alert to `alerts` collection.
6. Update `raw_news` status to `analysed`.
7. If `materiality_score >= 7` → pass alert to Alert Agent.

**Output document (`alerts`):**
```json
{
  "ticker": "RELIANCE.NS",
  "headline": "...",
  "materiality_score": 9,
  "sentiment": "Bearish",
  "summary": "...",
  "watch": "...",
  "reasoning": "...",
  "source_url": "...",
  "source_name": "...",
  "telegram_sent": false,
  "created_at": "ISO8601"
}
```

**Failure behaviour:**
- Groq API timeout → retry once with stricter prompt, then mark doc `analysis_failed`
- Invalid JSON response → one retry, then mark `analysis_failed`
- `analysis_failed` docs are visible in dashboard for manual review

**Tools used:** `transformers` (FinBERT `ProsusAI/finbert`), keyword scorer, `motor`

**Cost note:** Completely free. Runs locally with no API calls. FinBERT model downloads once (~440MB) on first run and is cached.

---

## 3. Alert Agent

**Role:** Dispatches high-materiality alerts to Telegram and pushes a WebSocket event to the dashboard.

**Trigger:** Analysis Agent passes an alert with `materiality_score >= 7`.

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
4. Emit WebSocket event `new_alert` to all connected dashboard clients.

**Failure behaviour:**
- Telegram API error → retry after 10s, max 3 retries
- If all retries fail → mark `telegram_sent: false`, log error, dashboard still receives WebSocket event
- WebSocket broadcast failure → non-fatal, dashboard polling fallback handles it

**Tools used:** `python-telegram-bot`, FastAPI WebSocket manager, `motor`

---

## 4. Telegram Bot (Interactive)

**Role:** Handles user commands for on-demand queries and watchlist management.

**Trigger:** Incoming Telegram update (polling or webhook).

**Commands and handlers:**

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

Agents communicate via **MongoDB document state** (simple and reliable) rather than an internal queue or message broker. This avoids operational overhead.

```
raw_news.status:
  "pending_analysis"  → waiting for Analysis Agent
  "analysed"          → processed successfully
  "analysis_failed"   → failed after retries, needs manual review

alerts.telegram_sent:
  false               → waiting for / failed Alert Agent dispatch
  true                → successfully sent
```

For the WebSocket real-time push, FastAPI maintains an in-memory connection manager. This is intentionally not persisted — if a dashboard client is disconnected, it catches up on reconnect via a REST call to `GET /api/alerts?limit=20`.

---

## Adding a New Agent

1. Create `backend/agents/your_agent.py`
2. Define an async `run(doc_id: str)` entrypoint
3. Register it in `backend/scheduler/jobs.py` or wire it to an existing agent's output
4. Document it in this file following the same structure
