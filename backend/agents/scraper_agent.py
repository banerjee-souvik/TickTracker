from __future__ import annotations

import asyncio
import calendar
import hashlib
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone

import feedparser
import httpx

from config import RSS_FEEDS, NEWS_LOOKBACK_HOURS as _LOOKBACK_HOURS
from services.mongo_service import get_db

logger = logging.getLogger(__name__)

_STRIP_SUFFIXES = re.compile(
    r"\b(limited|ltd|corp(?:oration)?|co\.?|plc|inc\.?|industries|india|and|of|the)\b\.?",
    re.I,
)


def _build_search_terms(ticker: str, company_name: str) -> list[str]:
    """Return lowercase search terms for article matching: symbol + cleaned company name."""
    symbol = ticker.replace(".NS", "").replace(".BO", "").lower()
    terms = [symbol]
    if company_name:
        cleaned = _STRIP_SUFFIXES.sub("", company_name).strip().lower()
        cleaned = " ".join(cleaned.split())  # normalise whitespace
        if cleaned and cleaned != symbol:
            terms.append(cleaned)
    return terms


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _is_recent(published_parsed: time.struct_time | None) -> bool:
    """Return True if the entry was published within the lookback window."""
    if not published_parsed:
        return True  # no date info — include it rather than silently drop
    pub_ts = calendar.timegm(published_parsed)  # UTC timestamp
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_LOOKBACK_HOURS)
    return pub_ts >= cutoff.timestamp()


async def _fetch_rss(feed: dict, ticker: str, search_terms: list[str]) -> list[dict]:
    try:
        parsed = await asyncio.to_thread(feedparser.parse, feed["url"])
        articles = []
        for entry in parsed.entries:
            if not _is_recent(entry.get("published_parsed")):
                continue
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            if not link:
                continue
            text = (title + " " + summary).lower()
            if not any(term in text for term in search_terms):
                continue
            articles.append({
                "headline": title,
                "raw_content": summary,
                "source_url": link,
                "source_name": feed["name"],
            })
        return articles
    except Exception:
        logger.warning("RSS fetch failed for %s / %s", feed["name"], ticker)
        return []


def _parse_nse_date(an_dt: str) -> datetime | None:
    """Parse NSE date strings like '06-May-2026 10:30:00' or '2026-05-06'."""
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(an_dt, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


async def _fetch_nse_announcements(ticker: str) -> list[dict]:
    symbol = ticker.replace(".NS", "").replace(".BO", "")
    api_url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/",
    }
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_LOOKBACK_HOURS)
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            await client.get("https://www.nseindia.com/", follow_redirects=True)
            resp = await client.get(api_url)
            resp.raise_for_status()
            announcements = resp.json()
            articles = []
            for item in announcements:  # sorted newest-first by NSE
                an_dt = item.get("an_dt", "")
                pub_dt = _parse_nse_date(an_dt)
                if pub_dt and pub_dt < cutoff:
                    break  # everything after this is older — stop early
                desc = item.get("desc", "").strip()
                if not desc:
                    continue
                body = item.get("attchmntText", "").strip() or desc
                att_url = item.get("attchmntFile", "")
                source_url = att_url or f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"
                articles.append({
                    "headline": f"{symbol}: {desc}",
                    "raw_content": body[:3000],
                    "source_url": source_url,
                    "source_name": "NSE Announcements",
                })
            return articles
    except Exception:
        logger.warning("NSE API fetch failed for %s", ticker)
        return []


async def _save_articles(ticker: str, articles: list[dict]):
    db = get_db()
    new_count = 0
    for article in articles:
        url_hash = _url_hash(article["source_url"])
        doc = {
            "url_hash": url_hash,
            "ticker": ticker,
            "headline": article["headline"],
            "source_url": article["source_url"],
            "source_name": article["source_name"],
            "raw_content": article["raw_content"],
            "status": "pending_analysis",
            "scraped_at": datetime.now(timezone.utc),
        }
        try:
            await db.raw_news.insert_one(doc)
            new_count += 1
        except Exception:
            pass  # duplicate key — already seen this URL
    return new_count


async def scrape_ticker(ticker: str) -> int:
    db = get_db()
    doc = await db.watchlist.find_one({"ticker": ticker}, {"name": 1})
    company_name = (doc or {}).get("name", "")
    search_terms = _build_search_terms(ticker, company_name)
    logger.debug("Search terms for %s: %s", ticker, search_terms)

    rss_tasks = [_fetch_rss(feed, ticker, search_terms) for feed in RSS_FEEDS]
    nse_task = _fetch_nse_announcements(ticker)
    results = await asyncio.gather(*rss_tasks, nse_task)
    articles = [a for batch in results for a in batch]
    return await _save_articles(ticker, articles)


async def run() -> int:
    """Scrape all active watchlist tickers. Returns total new articles found."""
    db = get_db()
    tickers = [doc["ticker"] async for doc in db.watchlist.find({"active": True}, {"ticker": 1})]
    if not tickers:
        logger.info("Watchlist is empty, nothing to scrape")
        return 0
    counts = await asyncio.gather(*[scrape_ticker(t) for t in tickers])
    total = sum(counts)
    logger.info("Scrape complete: %d new articles across %d tickers", total, len(tickers))
    return total
