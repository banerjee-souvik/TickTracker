from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db():
    return get_client()[settings.mongo_db]


async def close():
    global _client
    if _client:
        _client.close()
        _client = None


async def setup_indexes():
    db = get_db()
    await db.watchlist.create_index("ticker", unique=True)
    await db.raw_news.create_index("url_hash", unique=True)
    await db.raw_news.create_index("status")
    await db.raw_news.create_index("ticker")
    await db.alerts.create_index([("ticker", 1), ("created_at", -1)])
    await db.alerts.create_index("materiality_score")
    await db.price_cache.create_index("ticker", unique=True)
