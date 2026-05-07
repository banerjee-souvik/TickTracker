from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from config import settings

logger = logging.getLogger(__name__)


def build() -> Application | None:
    if not settings.telegram_bot_token:
        logger.info("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return None

    from .commands import (
        cmd_add, cmd_latest, cmd_price, cmd_remove,
        cmd_scan, cmd_start, cmd_watchlist,
    )

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("latest", cmd_latest))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("scan", cmd_scan))

    logger.info("Telegram bot configured")
    return app


async def start(app: Application):
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot polling started")


async def stop(app: Application):
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Telegram bot stopped")
