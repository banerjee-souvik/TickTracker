export type Sentiment = "Bullish" | "Bearish" | "Neutral";

export type PulseStatus = "pending_analysis" | "analysed" | "analysis_failed";

export interface RawNews {
  _id: string;
  ticker: string;
  headline: string;
  source_url: string;
  source_name: string;
  status: PulseStatus;
  scraped_at: string;
  url_hash: string;
}

export interface Alert {
  _id: string;
  ticker: string;
  headline: string;
  materiality_score: number;
  sentiment: Sentiment;
  summary: string;
  watch: string;
  source_url: string;
  source_name: string;
  telegram_sent: boolean;
  created_at: string;
}

export interface Price {
  _id: string;
  ticker: string;
  name: string;
  ltp: number;
  change_pct: number;
  volume: number;
  week_52_high: number;
  week_52_low: number;
  market_cap: number;
  sector: string;
  fetched_at: string;
}

export interface WatchlistItem {
  _id: string;
  ticker: string;
  active: boolean;
  added_at: string;
}
