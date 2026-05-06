from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_chat_ids: str = ""
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "ticktracker"
    scan_interval_minutes: int = 15

    @property
    def chat_id_list(self) -> list[int]:
        if not self.telegram_chat_ids:
            return []
        return [int(cid.strip()) for cid in self.telegram_chat_ids.split(",") if cid.strip().lstrip("-").isdigit()]

    class Config:
        env_file = ("../.env", ".env")


settings = Settings()

RSS_FEEDS = [
    {"name": "ET Markets", "url": "https://economictimes.indiatimes.com/markets/rss.cms"},
    {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/results.xml"},
    {"name": "SEBI", "url": "https://www.sebi.gov.in/sebirss.xml"},
]

MATERIALITY_THRESHOLD = 4
NEWS_LOOKBACK_HOURS = 24  # only process articles published within this window

ANALYSIS_SYSTEM_PROMPT = """You are a senior equity analyst specialising in Indian listed companies (NSE/BSE).
Given a news headline and article content, return a JSON object with exactly these fields:
  - materiality_score: integer 1-10
  - sentiment: one of "Bullish", "Bearish", "Neutral"
  - summary: 2-sentence plain-English explanation of the event and its impact
  - watch: one key metric or price level to monitor next
  - reasoning: one sentence explaining your score

Scoring guide:
  1-4: Routine (price targets, FII/DII data, generic analyst upgrades, market wraps)
  5-6: Notable (new product launches, management commentary, block deals, minor order wins)
  7-8: Important (earnings miss/beat >10%, large capex announcement, key management change, major order win)
  9-10: Critical (auditor resignation, SEBI investigation, promoter pledge increase >5%, M&A, fraud allegation, insolvency)

Return ONLY valid JSON. No preamble, no markdown fences."""
