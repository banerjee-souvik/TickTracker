"use client";

import { useState } from "react";
import { useRealtimeAlerts } from "@/hooks/useAlerts";
import AlertCard from "@/components/AlertCard";
import PriceWidget from "@/components/PriceWidget";
import TickerSearch from "@/components/TickerSearch";
import { api } from "@/lib/api";
import type { Alert, Price, WatchlistItem } from "@/lib/types";
import { TrendingUp, Bell, Activity, X } from "lucide-react";

interface Props {
  alerts: Alert[];
  prices: Price[];
  watchlist: WatchlistItem[];
}

export default function OverviewClient({ alerts: initial, prices: initialPrices, watchlist: initialWatchlist }: Props) {
  const { alerts } = useRealtimeAlerts(initial);
  const [prices, setPrices] = useState<Price[]>(initialPrices);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(initialWatchlist);

  const bullish = alerts.filter((a) => a.sentiment === "Bullish").length;
  const bearish = alerts.filter((a) => a.sentiment === "Bearish").length;
  const highMat = alerts.filter((a) => a.materiality_score >= 7).length;

  async function addTicker(sym: string) {
    await api.watchlist.add(sym);
    const [updated, updatedPrices] = await Promise.all([
      api.watchlist.list(),
      api.prices.all(),
    ]);
    setWatchlist(updated);
    setPrices(updatedPrices);
  }

  async function removeTicker(ticker: string) {
    try {
      await api.watchlist.remove(ticker);
      setWatchlist((prev) => prev.filter((w) => w.ticker !== ticker));
      setPrices((prev) => prev.filter((p) => p.ticker !== ticker));
    } catch {}
  }

  return (
    <div className="flex flex-col gap-8 p-6 max-w-[1400px] mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Market Overview</h1>
          <p className="text-sm text-zinc-500 mt-0.5">NSE/BSE intelligence feed · refreshes every 60s</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Live
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          icon={<Bell size={16} className="text-zinc-400" />}
          label="Total alerts"
          value={alerts.length}
        />
        <StatCard
          icon={<TrendingUp size={16} className="text-emerald-400" />}
          label="High materiality (≥7)"
          value={highMat}
          accent="emerald"
        />
        <StatCard
          icon={<Activity size={16} className="text-zinc-400" />}
          label="Bullish / Bearish"
          value={`${bullish} / ${bearish}`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        {/* Alert feed */}
        <section className="flex flex-col gap-4">
          <SectionHeader title="Latest Alerts" count={alerts.length} />
          {alerts.length === 0 ? (
            <EmptyState message="No alerts yet — add tickers to get started" />
          ) : (
            <div className="flex flex-col gap-3">
              {alerts.slice(0, 20).map((a) => (
                <AlertCard key={a._id} alert={a} />
              ))}
            </div>
          )}
        </section>

        {/* Right column */}
        <aside className="flex flex-col gap-6">
          {/* Watchlist manager */}
          <section className="flex flex-col gap-3">
            <SectionHeader title="Watchlist" count={watchlist.length} />

            <TickerSearch onAdd={addTicker} />

            {/* Ticker list */}
            {watchlist.length === 0 ? (
              <EmptyState message="No tickers yet" />
            ) : (
              <div className="flex flex-col divide-y divide-zinc-800 rounded-xl border border-zinc-800 overflow-hidden">
                {watchlist.map((w) => (
                  <div
                    key={w.ticker}
                    className="flex items-center justify-between px-3 py-2.5 bg-zinc-900 hover:bg-zinc-800/60 transition-colors"
                  >
                    <span className="text-xs font-mono font-bold text-zinc-200">{w.ticker}</span>
                    <button
                      onClick={() => removeTicker(w.ticker)}
                      className="text-zinc-600 hover:text-red-400 transition-colors p-0.5"
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Prices */}
          {prices.length > 0 && (
            <section className="flex flex-col gap-3">
              <SectionHeader title="Prices" count={prices.length} />
              <div className="flex flex-col gap-3">
                {prices.map((p) => (
                  <PriceWidget key={p.ticker} price={p} />
                ))}
              </div>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  accent?: "emerald";
}) {
  return (
    <div className="flex flex-col gap-2 p-4 rounded-xl border border-zinc-800 bg-zinc-900">
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        {icon}
        {label}
      </div>
      <p className={`text-2xl font-semibold ${accent === "emerald" ? "text-emerald-400" : "text-zinc-100"}`}>
        {value}
      </p>
    </div>
  );
}

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">{title}</h2>
      <span className="text-xs text-zinc-600 tabular-nums">{count}</span>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-20 rounded-xl border border-dashed border-zinc-800 text-xs text-zinc-600">
      {message}
    </div>
  );
}
