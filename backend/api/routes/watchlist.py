from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.mongo_service import get_db
from services.stock_service import validate_ticker

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("")
async def list_watchlist():
    db = get_db()
    tickers = []
    async for doc in db.watchlist.find({"active": True}):
        doc["_id"] = str(doc["_id"])
        tickers.append(doc)
    return tickers


@router.post("")
async def add_ticker(body: AddTickerRequest):
    ticker = await validate_ticker(body.ticker)
    if not ticker:
        raise HTTPException(status_code=422, detail=f"Ticker '{body.ticker}' not found on NSE/BSE")
    db = get_db()
    await db.watchlist.update_one(
        {"ticker": ticker},
        {"$set": {"ticker": ticker, "active": True, "added_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"ticker": ticker, "status": "added"}


@router.delete("/{ticker}")
async def remove_ticker(ticker: str):
    db = get_db()
    result = await db.watchlist.update_one({"ticker": ticker.upper()}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist")
    return {"ticker": ticker.upper(), "status": "removed"}
