from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import TelegramError

from config import settings
from services.mongo_service import get_db

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


def _format_message(alert: dict) -> str:
    score = alert["materiality_score"]
    sentiment = alert["sentiment"]
    ticker = alert["ticker"].replace(".NS", "").replace(".BO", "")
    return (
        f"🚨 *{ticker}* \\- *{_escape(alert['headline'])}*\n\n"
        f"*Signal:* {score}/10 \\({sentiment}\\)\n"
        f"*Context:* {_escape(alert['summary'])}\n"
        f"*Watch:* {_escape(alert['watch'])}"
    )


def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


async def dispatch(alert: dict):
    db = get_db()

    if not settings.telegram_bot_token or not settings.chat_id_list:
        logger.info("Telegram not configured — skipping push for %s", alert["ticker"])
        return

    bot = get_bot()
    message = _format_message(alert)
    sent = False

    for chat_id in settings.chat_id_list:
        for attempt in range(3):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="MarkdownV2",
                )
                sent = True
                break
            except TelegramError:
                if attempt == 2:
                    logger.exception("Telegram send failed for chat %s after 3 attempts", chat_id)
                else:
                    import asyncio
                    await asyncio.sleep(10 * (attempt + 1))

    await db.alerts.update_one(
        {"_id": alert["_id"]},
        {"$set": {"telegram_sent": sent, "sent_at": datetime.now(timezone.utc)}},
    )

    # Broadcast to dashboard via WebSocket
    try:
        from api.websocket import manager
        await manager.broadcast({"type": "new_alert", "data": _serialise(alert)})
    except Exception:
        logger.warning("WebSocket broadcast failed — dashboard will catch up on poll")


def _serialise(alert: dict) -> dict:
    out = dict(alert)
    out["_id"] = str(out.get("_id", ""))
    if isinstance(out.get("created_at"), datetime):
        out["created_at"] = out["created_at"].isoformat()
    if isinstance(out.get("sent_at"), datetime):
        out["sent_at"] = out["sent_at"].isoformat()
    return out
