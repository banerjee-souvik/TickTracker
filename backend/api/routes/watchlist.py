from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from services.mongo_service import get_db
from services.stock_service import validate_ticker

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


async def _scrape_and_analyse(ticker: str):
    from agents import scraper_agent, analysis_agent
    await scraper_agent.scrape_ticker(ticker)
    await analysis_agent.run()


async def _cleanup_pulse(ticker: str):
    db = get_db()
    await db.raw_news.delete_many({"ticker": ticker})


@router.get("")
async def list_watchlist():
    db = get_db()
    tickers = []
    async for doc in db.watchlist.find({"active": True}):
        doc["_id"] = str(doc["_id"])
        tickers.append(doc)
    return tickers


@router.post("")
async def add_ticker(body: AddTickerRequest, background_tasks: BackgroundTasks):
    result = await validate_ticker(body.ticker)
    if not result:
        raise HTTPException(status_code=422, detail=f"Ticker '{body.ticker}' not found on NSE/BSE")
    ticker, company_name = result
    db = get_db()
    await db.watchlist.update_one(
        {"ticker": ticker},
        {"$set": {"ticker": ticker, "name": company_name, "active": True, "added_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    background_tasks.add_task(_scrape_and_analyse, ticker)
    return {"ticker": ticker, "status": "added"}


@router.delete("/{ticker}")
async def remove_ticker(ticker: str, background_tasks: BackgroundTasks):
    db = get_db()
    result = await db.watchlist.update_one({"ticker": ticker.upper()}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist")
    background_tasks.add_task(_cleanup_pulse, ticker.upper())
    return {"ticker": ticker.upper(), "status": "removed"}
