from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from services.mongo_service import get_db

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "*TickTracker* — Bharat Equity Sentinel\n\n"
    "`/price TICKER` — Current LTP \\+ day change\n"
    "`/latest TICKER` — Last 3 alerts for a ticker\n"
    "`/add TICKER` — Add ticker to watchlist\n"
    "`/remove TICKER` — Remove ticker from watchlist\n"
    "`/watchlist` — List all monitored tickers with prices\n"
    "`/scan` — Trigger an immediate scan"
)


# ── commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/price RELIANCE\\.NS`", parse_mode="MarkdownV2"
        )
        return

    ticker = _normalise(context.args[0])
    msg = await update.message.reply_text(f"Fetching `{ticker}`…", parse_mode="MarkdownV2")

    from services.stock_service import get_price
    try:
        price = await get_price(ticker)
    except Exception:
        await msg.edit_text(f"Failed to fetch price for `{_esc(ticker)}`", parse_mode="MarkdownV2")
        return

    if not price:
        await msg.edit_text(f"No price data for `{_esc(ticker)}`", parse_mode="MarkdownV2")
        return

    sign = "\\+" if price["change_pct"] >= 0 else "\\-"
    change = abs(price["change_pct"])
    await msg.edit_text(
        f"*{_esc(ticker)}*\n"
        f"_{_esc(price.get('name', ticker))}_\n\n"
        f"₹{price['ltp']:,.2f}   {sign}{change:.2f}%",
        parse_mode="MarkdownV2",
    )


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/latest RELIANCE\\.NS`", parse_mode="MarkdownV2"
        )
        return

    ticker = _normalise(context.args[0])
    db = get_db()
    docs = [doc async for doc in db.alerts.find({"ticker": ticker}).sort("created_at", -1).limit(3)]

    if not docs:
        await update.message.reply_text(
            f"No alerts found for `{_esc(ticker)}`", parse_mode="MarkdownV2"
        )
        return

    lines = [f"*Latest alerts — {_esc(ticker)}*\n"]
    for doc in docs:
        score = doc["materiality_score"]
        sentiment = doc["sentiment"]
        headline = doc["headline"][:80]
        lines.append(f"*{score}/10* {_esc(sentiment)} — {_esc(headline)}")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/add RELIANCE\\.NS`", parse_mode="MarkdownV2"
        )
        return

    raw = context.args[0]
    msg = await update.message.reply_text(
        f"Validating `{_esc(raw.upper())}`…", parse_mode="MarkdownV2"
    )

    from services.stock_service import validate_ticker
    result = await validate_ticker(raw)

    if not result:
        await msg.edit_text(
            f"❌ `{_esc(raw.upper())}` not found on NSE/BSE\nTry appending `.NS` or `.BO`",
            parse_mode="MarkdownV2",
        )
        return

    ticker, company_name = result
    db = get_db()
    await db.watchlist.update_one(
        {"ticker": ticker},
        {"$set": {
            "ticker": ticker,
            "name": company_name,
            "active": True,
            "added_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

    asyncio.create_task(_scrape_and_analyse(ticker))

    await msg.edit_text(
        f"✅ *{_esc(ticker)}* added to watchlist\n"
        f"_{_esc(company_name)}_\n"
        f"Scraping news in background…",
        parse_mode="MarkdownV2",
    )


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/remove RELIANCE\\.NS`", parse_mode="MarkdownV2"
        )
        return

    ticker = _normalise(context.args[0])
    db = get_db()
    result = await db.watchlist.update_one({"ticker": ticker}, {"$set": {"active": False}})

    if result.matched_count == 0:
        await update.message.reply_text(
            f"❌ `{_esc(ticker)}` not in watchlist", parse_mode="MarkdownV2"
        )
        return

    await db.raw_news.delete_many({"ticker": ticker})
    await update.message.reply_text(
        f"✅ *{_esc(ticker)}* removed from watchlist", parse_mode="MarkdownV2"
    )


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    docs = [doc async for doc in db.watchlist.find({"active": True})]

    if not docs:
        await update.message.reply_text(
            "Watchlist is empty\\.\nUse `/add TICKER` to start monitoring\\.",
            parse_mode="MarkdownV2",
        )
        return

    from services.stock_service import get_price
    lines = ["*Watchlist*\n"]
    for doc in docs:
        ticker = doc["ticker"]
        price = await get_price(ticker)
        if price:
            sign = "\\+" if price["change_pct"] >= 0 else "\\-"
            change = abs(price["change_pct"])
            lines.append(
                f"`{_esc(ticker)}` — ₹{price['ltp']:,.2f}  {sign}{change:.2f}%"
            )
        else:
            name = doc.get("name", "")
            lines.append(f"`{_esc(ticker)}`  _{_esc(name)}_")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scan started — alerts will be pushed when ready")
    asyncio.create_task(_run_full_scan())


# ── helpers ───────────────────────────────────────────────────────────────────

def _normalise(ticker: str) -> str:
    ticker = ticker.upper()
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker += ".NS"
    return ticker


def _esc(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    for ch in r"_*[]()~`>#+-=|{}.!\\":
        text = text.replace(ch, f"\\{ch}")
    return text


async def _scrape_and_analyse(ticker: str):
    from agents import scraper_agent, analysis_agent
    try:
        await scraper_agent.scrape_ticker(ticker)
        await analysis_agent.run()
    except Exception:
        logger.exception("Background scrape/analyse failed for %s", ticker)


async def _run_full_scan():
    from agents import scraper_agent, analysis_agent
    try:
        await scraper_agent.run()
        await analysis_agent.run()
    except Exception:
        logger.exception("Full scan task failed")
