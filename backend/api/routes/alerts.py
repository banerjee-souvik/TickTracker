from __future__ import annotations

from fastapi import APIRouter, Query

from services.mongo_service import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    ticker: str | None = None,
    min_score: int = Query(default=1, ge=1, le=10),
    sentiment: str | None = None,
    limit: int = Query(default=50, le=200),
):
    db = get_db()
    query: dict = {}
    if ticker:
        query["ticker"] = ticker.upper()
    if min_score > 1:
        query["materiality_score"] = {"$gte": min_score}
    if sentiment:
        query["sentiment"] = sentiment

    alerts = []
    async for doc in db.alerts.find(query).sort("created_at", -1).limit(limit):
        doc["_id"] = str(doc["_id"])
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat()
        alerts.append(doc)
    return alerts


@router.get("/{ticker}")
async def ticker_alerts(ticker: str, limit: int = Query(default=10, le=50)):
    db = get_db()
    alerts = []
    async for doc in db.alerts.find({"ticker": ticker.upper()}).sort("created_at", -1).limit(limit):
        doc["_id"] = str(doc["_id"])
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat()
        alerts.append(doc)
    return alerts
