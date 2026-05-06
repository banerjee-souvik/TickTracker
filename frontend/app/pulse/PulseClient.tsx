"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { RefreshCw, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import PulseCard from "@/components/PulseCard";
import type { RawNews, PulseStatus } from "@/lib/types";

const POLL_MS = 15_000; // faster than alerts — shows scraping in near-real-time

const STATUS_FILTERS: { label: string; value: PulseStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending_analysis" },
  { label: "Analysed", value: "analysed" },
  { label: "Failed", value: "analysis_failed" },
];

export default function PulseClient({ initialItems }: { initialItems: RawNews[] }) {
  const [items, setItems] = useState<RawNews[]>(initialItems);
  const [statusFilter, setStatusFilter] = useState<PulseStatus | "all">("all");
  const [refreshing, setRefreshing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [retryMsg, setRetryMsg] = useState("");
  const cancelledRef = useRef(false);

  const fetchItems = useCallback(async () => {
    try {
      const fresh = await api.pulse.list();
      if (!cancelledRef.current) setItems(fresh);
    } catch {}
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    const id = setInterval(fetchItems, POLL_MS);
    return () => {
      cancelledRef.current = true;
      clearInterval(id);
    };
  }, [fetchItems]);

  async function handleRefresh() {
    setRefreshing(true);
    await fetchItems();
    setRefreshing(false);
  }

  async function handleRetry() {
    setRetrying(true);
    setRetryMsg("");
    try {
      const res = await api.pulse.retryFailed();
      setRetryMsg(res.message);
    } catch {
      setRetryMsg("Retry failed — is the backend running?");
    } finally {
      setRetrying(false);
      setTimeout(() => setRetryMsg(""), 6000);
    }
  }

  const filtered = statusFilter === "all"
    ? items
    : items.filter((i) => i.status === statusFilter);

  const counts = {
    all: items.length,
    pending_analysis: items.filter((i) => i.status === "pending_analysis").length,
    analysed: items.filter((i) => i.status === "analysed").length,
    analysis_failed: items.filter((i) => i.status === "analysis_failed").length,
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-[900px] mx-auto w-full">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Pulse</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Raw scraped articles — updates every 15s</p>
        </div>
        <div className="flex items-center gap-3">
          {retryMsg && (
            <span className="text-xs text-zinc-400 animate-pulse">{retryMsg}</span>
          )}
          {counts.analysis_failed > 0 && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-950 hover:bg-red-900 disabled:opacity-50 text-xs font-medium text-red-300 transition-colors border border-red-800"
            >
              <RotateCcw size={12} className={retrying ? "animate-spin" : ""} />
              {retrying ? "Retrying…" : `Retry Failed (${counts.analysis_failed})`}
            </button>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-xs font-medium text-zinc-200 transition-colors border border-zinc-700"
          >
            <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </div>
        </div>
      </div>

      {/* Stat chips */}
      <div className="flex flex-wrap gap-3">
        <StatChip label="Total" value={counts.all} color="zinc" />
        <StatChip label="Pending" value={counts.pending_analysis} color="amber" />
        <StatChip label="Analysed" value={counts.analysed} color="emerald" />
        <StatChip label="Failed" value={counts.analysis_failed} color="red" />
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-zinc-900 border border-zinc-800 w-fit">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {f.label}
            <span className="ml-1.5 text-zinc-600">
              {f.value === "all" ? counts.all : counts[f.value]}
            </span>
          </button>
        ))}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 h-40 rounded-xl border border-dashed border-zinc-800 text-sm text-zinc-600">
          <span>No articles yet</span>
          <span className="text-xs">Add tickers to your watchlist and run a scan</span>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((item) => (
            <PulseCard key={item._id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatChip({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: "zinc" | "amber" | "emerald" | "red";
}) {
  const colors = {
    zinc: "text-zinc-400 border-zinc-800",
    amber: "text-amber-400 border-amber-900/50",
    emerald: "text-emerald-400 border-emerald-900/50",
    red: "text-red-400 border-red-900/50",
  };
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-zinc-900 ${colors[color]}`}>
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </div>
  );
}
