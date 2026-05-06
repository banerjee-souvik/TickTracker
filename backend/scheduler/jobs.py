import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup():
    interval = settings.scan_interval_minutes

    scheduler.add_job(
        _full_scan,
        trigger="interval",
        minutes=interval,
        id="full_scan",
        replace_existing=True,
    )

    scheduler.add_job(
        _refresh_prices,
        trigger="interval",
        minutes=interval,
        id="refresh_prices",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started — scan every %d min", interval)


async def _full_scan():
    from agents import scraper_agent, analysis_agent
    logger.info("Starting scheduled scan")
    await scraper_agent.run()
    await analysis_agent.run()


async def _refresh_prices():
    from services.mongo_service import get_db
    from services.stock_service import refresh_all_prices
    db = get_db()
    tickers = [doc["ticker"] async for doc in db.watchlist.find({"active": True}, {"ticker": 1})]
    if tickers:
        await refresh_all_prices(tickers)
