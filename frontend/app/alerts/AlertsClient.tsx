"use client";

import { useState } from "react";
import { useRealtimeAlerts } from "@/hooks/useAlerts";
import AlertCard from "@/components/AlertCard";
import type { Alert } from "@/lib/types";
import { Search, SlidersHorizontal } from "lucide-react";

interface Props {
  initialAlerts: Alert[];
}

const SENTIMENTS = ["All", "Bullish", "Bearish", "Neutral"] as const;
const SCORES = [
  { label: "All", min: 1 },
  { label: "High (≥7)", min: 7 },
  { label: "Medium (≥5)", min: 5 },
  { label: "Low (<5)", min: 1, max: 4 },
] as const;

export default function AlertsClient({ initialAlerts }: Props) {
  const { alerts } = useRealtimeAlerts(initialAlerts);
  const [search, setSearch] = useState("");
  const [sentiment, setSentiment] = useState<(typeof SENTIMENTS)[number]>("All");
  const [scoreIdx, setScoreIdx] = useState(0);

  const scoreFilter = SCORES[scoreIdx];
  const filtered = alerts.filter((a) => {
    if (sentiment !== "All" && a.sentiment !== sentiment) return false;
    if (a.materiality_score < scoreFilter.min) return false;
    if ("max" in scoreFilter && scoreFilter.max !== undefined && a.materiality_score > scoreFilter.max) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!a.ticker.toLowerCase().includes(q) && !a.headline.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  return (
    <div className="flex flex-col gap-6 p-6 max-w-[1000px] mx-auto w-full">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Alerts</h1>
        <p className="text-sm text-zinc-500 mt-0.5">{alerts.length} total · {filtered.length} shown</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Search ticker or headline…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        {/* Sentiment filter */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-zinc-900 border border-zinc-800">
          {SENTIMENTS.map((s) => (
            <button
              key={s}
              onClick={() => setSentiment(s)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                sentiment === s
                  ? "bg-zinc-700 text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Score filter */}
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={14} className="text-zinc-500 shrink-0" />
          <select
            value={scoreIdx}
            onChange={(e) => setScoreIdx(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-800 text-sm text-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-600 transition-colors"
          >
            {SCORES.map((s, i) => (
              <option key={i} value={i}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Alert list */}
      {filtered.length === 0 ? (
        <div className="flex items-center justify-center h-40 rounded-xl border border-dashed border-zinc-800 text-sm text-zinc-600">
          No alerts match your filters
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((a) => (
            <AlertCard key={a._id} alert={a} />
          ))}
        </div>
      )}
    </div>
  );
}
