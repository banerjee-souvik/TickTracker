import type { Sentiment } from "./types";

export function scoreColor(score: number): string {
  if (score >= 9) return "text-red-400";
  if (score >= 7) return "text-amber-400";
  if (score >= 5) return "text-yellow-300";
  return "text-zinc-400";
}

export function scoreBg(score: number): string {
  if (score >= 9) return "bg-red-500/10 border-red-500/30 text-red-400";
  if (score >= 7) return "bg-amber-500/10 border-amber-500/30 text-amber-400";
  if (score >= 5) return "bg-yellow-500/10 border-yellow-500/30 text-yellow-300";
  return "bg-zinc-800 border-zinc-700 text-zinc-400";
}

export function sentimentColor(s: Sentiment): string {
  if (s === "Bullish") return "text-emerald-400";
  if (s === "Bearish") return "text-red-400";
  return "text-zinc-400";
}

export function sentimentDot(s: Sentiment): string {
  if (s === "Bullish") return "bg-emerald-400";
  if (s === "Bearish") return "bg-red-400";
  return "bg-zinc-500";
}

export function changeColor(pct: number): string {
  if (pct > 0) return "text-emerald-400";
  if (pct < 0) return "text-red-400";
  return "text-zinc-400";
}

export function formatChange(pct: number): string {
  return `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%`;
}

export function formatCap(cap: number): string {
  if (!cap) return "—";
  if (cap >= 1e12) return `₹${(cap / 1e12).toFixed(2)}T`;
  if (cap >= 1e9) return `₹${(cap / 1e9).toFixed(2)}B`;
  return `₹${(cap / 1e6).toFixed(0)}M`;
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function symbolOnly(ticker: string): string {
  return ticker.replace(".NS", "").replace(".BO", "");
}
