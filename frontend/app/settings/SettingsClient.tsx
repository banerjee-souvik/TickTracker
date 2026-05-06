"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { WatchlistItem } from "@/lib/types";
import TickerSearch from "@/components/TickerSearch";
import { Trash2, RefreshCw } from "lucide-react";

interface Props {
  initialWatchlist: WatchlistItem[];
}

export default function SettingsClient({ initialWatchlist }: Props) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(initialWatchlist);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState("");

  async function addTicker(sym: string) {
    await api.watchlist.add(sym);
    const updated = await api.watchlist.list();
    setWatchlist(updated);
  }

  async function removeTicker(ticker: string) {
    try {
      await api.watchlist.remove(ticker);
      setWatchlist((prev) => prev.filter((w) => w.ticker !== ticker));
    } catch {}
  }

  async function triggerScan() {
    setScanning(true);
    setScanMsg("");
    try {
      const res = await api.scan.trigger();
      setScanMsg(res.message ?? "Scan started");
    } catch {
      setScanMsg("Scan failed — is the backend running?");
    } finally {
      setScanning(false);
    }
  }

  return (
    <div className="flex flex-col gap-8 p-6 max-w-[700px] mx-auto w-full">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Settings</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Manage your watchlist and manual controls</p>
      </div>

      {/* Watchlist management */}
      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Watchlist</h2>

        <TickerSearch onAdd={addTicker} />

        {watchlist.length === 0 ? (
          <div className="flex items-center justify-center h-24 rounded-xl border border-dashed border-zinc-800 text-sm text-zinc-600">
            No tickers yet
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-zinc-800 rounded-xl border border-zinc-800 overflow-hidden">
            {watchlist.map((w) => (
              <div key={w.ticker} className="flex items-center justify-between px-4 py-3 bg-zinc-900 hover:bg-zinc-800/60 transition-colors">
                <span className="text-sm font-mono font-bold text-zinc-200">{w.ticker}</span>
                <button
                  onClick={() => removeTicker(w.ticker)}
                  className="text-zinc-600 hover:text-red-400 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Manual scan */}
      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Manual Controls</h2>
        <div className="flex flex-col gap-3 p-4 rounded-xl border border-zinc-800 bg-zinc-900">
          <p className="text-sm text-zinc-400">
            Trigger an immediate news scan without waiting for the 15-minute scheduler cycle.
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={triggerScan}
              disabled={scanning}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-sm font-medium text-zinc-100 transition-colors"
            >
              <RefreshCw size={14} className={scanning ? "animate-spin" : ""} />
              {scanning ? "Scanning…" : "Run Scan Now"}
            </button>
            {scanMsg && <p className="text-xs text-zinc-500">{scanMsg}</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
