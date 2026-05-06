"""
Quick scraper test — run from the backend/ directory:
    python test_scraper.py [TICKER ...]

Examples:
    python test_scraper.py                  # scrape all watchlist tickers
    python test_scraper.py RELIANCE INFY    # scrape specific tickers (auto-appends .NS)
    python test_scraper.py --dry-run        # fetch articles but don't save to MongoDB
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from config import RSS_FEEDS, NEWS_LOOKBACK_HOURS


# ── helpers ──────────────────────────────────────────────────────────────────

def _sym(ticker: str) -> str:
    return ticker.replace(".NS", "").replace(".BO", "")


def _ensure_suffix(raw: str) -> str:
    raw = raw.upper()
    return raw if raw.endswith((".NS", ".BO")) else raw + ".NS"


def _cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)


# ── per-source fetchers (read-only, no DB) ────────────────────────────────

async def _test_rss(feed: dict, ticker: str, search_terms: list[str]) -> list[dict]:
    try:
        t0 = time.perf_counter()
        parsed = await asyncio.to_thread(feedparser.parse, feed["url"])
        elapsed = time.perf_counter() - t0
        total = len(parsed.entries)
        recent = [
            e for e in parsed.entries
            if not e.get("published_parsed")
            or time.mktime(e["published_parsed"]) >= _cutoff().timestamp()
        ]
        matched = [
            e for e in recent
            if any(term in (e.get("title", "") + e.get("summary", "")).lower() for term in search_terms)
        ]
        print(f"  [{feed['name']}] {elapsed:.1f}s — {total} entries, "
              f"{len(recent)} within {NEWS_LOOKBACK_HOURS}h, {len(matched)} matched")
        for e in matched[:3]:
            print(f"    • {e.get('title', '')[:90]}")
        return matched
    except Exception as exc:
        print(f"  [{feed['name']}] FAILED — {exc}")
        return []


async def _test_nse(ticker: str) -> list[dict]:
    symbol = _sym(ticker)
    url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/",
    }
    cutoff = _cutoff()
    try:
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            await client.get("https://www.nseindia.com/", follow_redirects=True)
            resp = await client.get(url)
            resp.raise_for_status()
        elapsed = time.perf_counter() - t0
        all_items = resp.json()
        # Apply same date filter as the real scraper (newest-first, stop at cutoff)
        matched = []
        for item in all_items:
            from agents.scraper_agent import _parse_nse_date
            pub_dt = _parse_nse_date(item.get("an_dt", ""))
            if pub_dt and pub_dt < cutoff:
                break
            desc = item.get("desc", "").strip()
            if desc:
                matched.append(item)
        print(f"  [NSE API] {elapsed:.1f}s — {len(all_items)} total, {len(matched)} within {NEWS_LOOKBACK_HOURS}h")
        for item in matched[:3]:
            print(f"    • [{item.get('an_dt', '?')}] {item.get('desc', '')[:80]}")
        return matched
    except Exception as exc:
        print(f"  [NSE API] FAILED — {exc}")
        return []


# ── main ──────────────────────────────────────────────────────────────────────

async def test_ticker(ticker: str, company_name: str = ""):
    from agents.scraper_agent import _build_search_terms
    search_terms = _build_search_terms(ticker, company_name)

    print(f"\n{'─'*60}")
    print(f"Ticker : {ticker}")
    print(f"Name   : {company_name or '(unknown — add to watchlist first)'}")
    print(f"Terms  : {search_terms}")
    print(f"{'─'*60}")

    rss_tasks = [_test_rss(feed, ticker, search_terms) for feed in RSS_FEEDS]
    nse_task = _test_nse(ticker)
    results = await asyncio.gather(*rss_tasks, nse_task)

    total = sum(len(r) for r in results)
    print(f"  → {total} article(s) found total for {ticker}")


async def test_from_watchlist():
    from services.mongo_service import get_db, setup_indexes
    await setup_indexes()
    db = get_db()
    docs = [doc async for doc in db.watchlist.find({"active": True}, {"ticker": 1, "name": 1})]
    if not docs:
        print("Watchlist is empty — add tickers first via the dashboard or Settings page.")
        return
    print(f"Watchlist tickers: {', '.join(d['ticker'] for d in docs)}")
    for doc in docs:
        await test_ticker(doc["ticker"], doc.get("name", ""))


async def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]

    print(f"Scraper test — lookback window: {NEWS_LOOKBACK_HOURS}h")
    print(f"Cutoff: {_cutoff().strftime('%Y-%m-%d %H:%M UTC')}")

    if args:
        # Try to look up company names from watchlist for provided tickers
        try:
            from services.mongo_service import get_db, setup_indexes
            await setup_indexes()
            db = get_db()
            names = {}
            async for doc in db.watchlist.find({"active": True}, {"ticker": 1, "name": 1}):
                names[doc["ticker"]] = doc.get("name", "")
        except Exception:
            names = {}

        tickers = [_ensure_suffix(a) for a in args]
        for ticker in tickers:
            await test_ticker(ticker, names.get(ticker, ""))
    else:
        await test_from_watchlist()

    print(f"\n{'─'*60}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
