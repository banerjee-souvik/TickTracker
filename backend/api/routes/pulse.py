from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query

from services.mongo_service import get_db

router = APIRouter(prefix="/pulse", tags=["pulse"])


@router.get("")
async def list_pulse(
    ticker: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, le=500),
):
    db = get_db()
    query: dict = {}
    if ticker:
        query["ticker"] = ticker.upper()
    if status:
        query["status"] = status

    docs = []
    async for doc in db.raw_news.find(query).sort("scraped_at", -1).limit(limit):
        doc["_id"] = str(doc["_id"])
        doc.pop("raw_content", None)  # don't send full content to the UI
        if doc.get("scraped_at"):
            doc["scraped_at"] = doc["scraped_at"].isoformat()
        docs.append(doc)
    return docs


@router.post("/retry")
async def retry_failed(background_tasks: BackgroundTasks):
    db = get_db()
    result = await db.raw_news.update_many(
        {"status": "analysis_failed"},
        {"$set": {"status": "pending_analysis"}},
    )
    if result.modified_count == 0:
        return {"reset": 0, "message": "No failed articles to retry"}
    background_tasks.add_task(_run_analysis)
    return {"reset": result.modified_count, "message": f"Retrying {result.modified_count} article(s)"}


async def _run_analysis():
    from agents import analysis_agent
    await analysis_agent.run()
