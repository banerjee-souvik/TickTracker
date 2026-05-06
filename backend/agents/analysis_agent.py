from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import MATERIALITY_THRESHOLD
from services.finbert_service import get_sentiment
from services.mongo_service import get_db
from services.scorer_service import score, watch_for

logger = logging.getLogger(__name__)


async def process_article(doc: dict):
    db = get_db()

    materiality_score = score(doc["headline"], doc["raw_content"])
    sentiment = await get_sentiment(doc["headline"] + " " + doc["raw_content"][:512])

    ticker = doc["ticker"].replace(".NS", "").replace(".BO", "")
    summary = (
        f"{ticker} — {doc['headline']} "
        f"(Source: {doc['source_name']}). "
        f"Materiality rated {materiality_score}/10 based on event classification."
    )

    alert = {
        "ticker": doc["ticker"],
        "headline": doc["headline"],
        "materiality_score": materiality_score,
        "sentiment": sentiment,
        "summary": summary,
        "watch": watch_for(materiality_score),
        "source_url": doc["source_url"],
        "source_name": doc["source_name"],
        "telegram_sent": False,
        "created_at": datetime.now(timezone.utc),
    }

    await db.alerts.insert_one(alert)
    await db.raw_news.update_one({"_id": doc["_id"]}, {"$set": {"status": "analysed"}})
    logger.info("Scored %s: %d/10 %s — %s", doc["ticker"], materiality_score, sentiment, doc["headline"][:60])

    if materiality_score >= MATERIALITY_THRESHOLD:
        from agents.alert_agent import dispatch
        await dispatch(alert)


async def run():
    db = get_db()
    cursor = db.raw_news.find({"status": "pending_analysis"})
    count = 0
    async for doc in cursor:
        await process_article(doc)
        count += 1
    logger.info("Analysis complete: %d articles processed", count)
