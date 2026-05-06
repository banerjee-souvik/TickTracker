from fastapi import APIRouter, HTTPException

from services.mongo_service import get_db
from services.stock_service import get_price

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{ticker}")
async def price(ticker: str):
    data = await get_price(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"Could not fetch price for {ticker}")
    data["_id"] = str(data.get("_id", ticker))
    if data.get("fetched_at"):
        data["fetched_at"] = data["fetched_at"].isoformat()
    return data


@router.get("")
async def all_prices():
    db = get_db()
    prices = []
    async for doc in db.price_cache.find():
        doc["_id"] = str(doc["_id"])
        if doc.get("fetched_at"):
            doc["fetched_at"] = doc["fetched_at"].isoformat()
        prices.append(doc)
    return prices
