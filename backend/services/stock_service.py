from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
import yfinance as yf

from services.mongo_service import get_db

logger = logging.getLogger(__name__)

# ── NSE session ───────────────────────────────────────────────────────────────
# NSE requires a valid browser session (cookies from homepage) before the API
# works. We keep a single shared client and refresh it every 30 minutes.

_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
_NSE_SESSION_TTL = 1800  # seconds
_nse_client: httpx.AsyncClient | None = None
_nse_client_born: datetime | None = None
_nse_lock = asyncio.Lock()


async def _get_nse_client() -> httpx.AsyncClient:
    global _nse_client, _nse_client_born
    now = datetime.now(timezone.utc)
    async with _nse_lock:
        age = (now - _nse_client_born).total_seconds() if _nse_client_born else _NSE_SESSION_TTL + 1
        if _nse_client is None or age > _NSE_SESSION_TTL:
            if _nse_client:
                await _nse_client.aclose()
            client = httpx.AsyncClient(
                headers=_NSE_HEADERS, timeout=15, follow_redirects=True
            )
            await client.get("https://www.nseindia.com/")  # seed cookies
            _nse_client = client
            _nse_client_born = now
            logger.debug("NSE session refreshed")
    return _nse_client


async def _fetch_nse_price(symbol: str) -> dict | None:
    """Fetch live quote from NSE equity API. symbol is bare (no .NS suffix)."""
    client = await _get_nse_client()
    try:
        resp = await client.get(
            f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
            headers={"Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("NSE price API failed for %s: %s", symbol, exc)
        return None

    price_info = data.get("priceInfo", {})
    week_hl = price_info.get("weekHighLow", {})
    intraday = price_info.get("intraDayHighLow", {})

    ltp = price_info.get("lastPrice")
    if not ltp:
        return None

    return {
        "ltp": ltp,
        "change_pct": round(float(price_info.get("pChange", 0)), 2),
        "volume": 0,  # NSE quote endpoint doesn't expose traded volume
        "week_52_high": week_hl.get("max"),
        "week_52_low": week_hl.get("min"),
        "market_cap": None,  # NSE API doesn't expose market cap in quote endpoint
        "name": data.get("info", {}).get("companyName") or symbol,
    }


def _fetch_yfinance_bse(ticker: str) -> dict | None:
    """Fallback price fetch for .BO tickers via yfinance."""
    t = yf.Ticker(ticker)
    info = t.info
    ltp = info.get("currentPrice") or info.get("regularMarketPrice")
    if not ltp:
        return None
    prev_close = info.get("previousClose") or ltp
    change_pct = round(((ltp - prev_close) / prev_close) * 100, 2) if prev_close else 0
    return {
        "ltp": ltp,
        "change_pct": change_pct,
        "volume": info.get("regularMarketVolume", 0),
        "week_52_high": info.get("fiftyTwoWeekHigh"),
        "week_52_low": info.get("fiftyTwoWeekLow"),
        "market_cap": info.get("marketCap"),
        "name": info.get("longName", ticker),
    }


# ── public API ─────────────────────────────────────────────────────────────────

async def get_price(ticker: str) -> dict | None:
    db = get_db()
    cached = await db.price_cache.find_one({"_id": ticker})
    if cached:
        age = (datetime.now(timezone.utc) - cached["fetched_at"]).total_seconds()
        if age < 300:
            return cached
    return await refresh_price(ticker)


async def refresh_price(ticker: str) -> dict | None:
    try:
        if ticker.endswith(".NS"):
            info = await _fetch_nse_price(ticker[:-3])
        else:
            info = await asyncio.to_thread(_fetch_yfinance_bse, ticker)

        if not info:
            return None

        info["_id"] = ticker
        info["ticker"] = ticker
        info["fetched_at"] = datetime.now(timezone.utc)

        # Ensure name is populated even if API didn't return one
        if not info.get("name"):
            db = get_db()
            existing = await db.price_cache.find_one({"_id": ticker}, {"name": 1})
            if existing and existing.get("name"):
                info["name"] = existing["name"]
            else:
                wl = await db.watchlist.find_one({"ticker": ticker}, {"name": 1})
                info["name"] = (wl or {}).get("name") or ticker

        db = get_db()
        await db.price_cache.update_one({"_id": ticker}, {"$set": info}, upsert=True)
        return info

    except Exception as exc:
        db = get_db()
        cached = await db.price_cache.find_one({"_id": ticker})
        if cached:
            logger.warning("Price refresh failed for %s (%s) — serving stale cache", ticker, exc)
            return cached
        logger.error("Price refresh failed for %s and no cache available: %s", ticker, exc)
        return None


async def validate_ticker(ticker: str) -> tuple[str, str] | None:
    """Returns (normalised_ticker, company_name) if valid, None if not found."""
    ticker = ticker.upper()
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker += ".NS"

    if ticker.endswith(".NS"):
        # Use NSE API for validation — also confirms the ticker exists
        symbol = ticker[:-3]
        data = await _fetch_nse_price(symbol)
        if data:
            return (ticker, data.get("name") or ticker)
        return None

    # BSE: fall back to yfinance (called once per add, not rate-limited)
    try:
        info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
        long_name = info.get("longName", "")
        return (ticker, long_name) if long_name else None
    except Exception:
        logger.warning("yfinance BSE validation failed for %s", ticker)
        return None


async def refresh_all_prices(tickers: list[str]):
    await asyncio.gather(*[refresh_price(t) for t in tickers])
