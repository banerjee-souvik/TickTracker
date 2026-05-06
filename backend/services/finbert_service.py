from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_pipeline = None


def _load_pipeline():
    from transformers import pipeline
    return pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        truncation=True,
        max_length=512,
    )


def _infer(text: str) -> str:
    global _pipeline
    if _pipeline is None:
        logger.info("Loading FinBERT model (first run — one-time download ~440MB)")
        _pipeline = _load_pipeline()
    result = _pipeline(text[:2000], truncation=True)[0]
    label = result["label"].lower()
    return {"positive": "Bullish", "negative": "Bearish", "neutral": "Neutral"}.get(label, "Neutral")


async def get_sentiment(text: str) -> str:
    return await asyncio.to_thread(_infer, text)
