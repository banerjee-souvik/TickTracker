from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf

from services.mongo_service import get_db

logger = logging.getLogger(__name__)


async def get_price(ticker: str) -> dict | None:
    db = get_db()
    cached = await db.price_cache.find_one({"_id": ticker})
    if cached:
        age_seconds = (datetime.now(timezone.utc) - cached["fetched_at"]).total_seconds()
        if age_seconds < 300:  # 5-minute cache
            return cached
    return await refresh_price(ticker)


async def refresh_price(ticker: str) -> dict | None:
    try:
        info = await asyncio.to_thread(_fetch_yfinance, ticker)
        if not info:
            return None
        db = get_db()
        await db.price_cache.update_one(
            {"_id": ticker},
            {"$set": info},
            upsert=True,
        )
        return info
    except Exception as exc:
        # 429 / transient errors — return stale cache rather than None
        db = get_db()
        cached = await db.price_cache.find_one({"_id": ticker})
        if cached:
            logger.warning("Price refresh failed for %s (%s) — serving stale cache", ticker, exc)
            return cached
        logger.error("Price refresh failed for %s and no cache available: %s", ticker, exc)
        return None


def _fetch_yfinance(ticker: str) -> dict | None:
    t = yf.Ticker(ticker)
    info = t.info
    if not info.get("regularMarketPrice") and not info.get("currentPrice"):
        return None
    ltp = info.get("currentPrice") or info.get("regularMarketPrice")
    prev_close = info.get("previousClose") or ltp
    change_pct = round(((ltp - prev_close) / prev_close) * 100, 2) if prev_close else 0
    return {
        "_id": ticker,
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "ltp": ltp,
        "change_pct": change_pct,
        "volume": info.get("regularMarketVolume", 0),
        "week_52_high": info.get("fiftyTwoWeekHigh"),
        "week_52_low": info.get("fiftyTwoWeekLow"),
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
        "fetched_at": datetime.now(timezone.utc),
    }


async def validate_ticker(ticker: str) -> tuple[str, str] | None:
    """Returns (normalised_ticker, company_name) if valid, None if not found."""
    ticker = ticker.upper()
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker += ".NS"
    try:
        info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
        long_name = info.get("longName", "")
        return (ticker, long_name) if long_name else None
    except Exception:
        logger.warning("yfinance validation failed for %s, accepting ticker anyway", ticker)
        return (ticker, ticker)


async def refresh_all_prices(tickers: list[str]):
    for i, ticker in enumerate(tickers):
        await refresh_price(ticker)
        if i < len(tickers) - 1:
            await asyncio.sleep(1.5)  # avoid Yahoo Finance 429 rate limits
