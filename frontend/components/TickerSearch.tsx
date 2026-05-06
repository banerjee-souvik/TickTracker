"use client";

import { useRef, useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { NSE_STOCKS, type NSEStock } from "@/lib/nse-stocks";

interface Props {
  onAdd: (ticker: string) => Promise<void>;
}

function filterStocks(query: string): NSEStock[] {
  if (!query) return [];
  const q = query.toLowerCase();
  return NSE_STOCKS.filter(
    (s) =>
      s.symbol.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q)
  ).slice(0, 8);
}

export default function TickerSearch({ onAdd }: Props) {
  const [value, setValue] = useState("");
  const [suggestions, setSuggestions] = useState<NSEStock[]>([]);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  function handleChange(raw: string) {
    setValue(raw);
    setError("");
    setSuggestions(filterStocks(raw));
    setActiveIdx(-1);
  }

  function pick(stock: NSEStock) {
    setValue(stock.symbol);
    setSuggestions([]);
    setActiveIdx(-1);
    inputRef.current?.focus();
  }

  async function submit(ticker = value) {
    const sym = ticker.trim().toUpperCase();
    if (!sym) return;
    setSuggestions([]);
    setActiveIdx(-1);
    setError("");
    setAdding(true);
    try {
      await onAdd(sym);
      setValue("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add ticker");
    } finally {
      setAdding(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIdx >= 0 && suggestions[activeIdx]) {
        pick(suggestions[activeIdx]);
      } else {
        submit();
      }
    } else if (e.key === "Escape") {
      setSuggestions([]);
      setActiveIdx(-1);
    }
  }

  const open = suggestions.length > 0;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="relative flex gap-2">
        <div className="relative flex-1 min-w-0">
          <input
            ref={inputRef}
            type="text"
            placeholder="Search symbol or company…"
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => setTimeout(() => setSuggestions([]), 150)}
            disabled={adding}
            autoComplete="off"
            spellCheck={false}
            className="w-full px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors disabled:opacity-50"
          />

          {/* Dropdown */}
          {open && (
            <div
              ref={listRef}
              className="absolute top-full left-0 right-0 mt-1 z-20 rounded-lg border border-zinc-700 bg-zinc-950 shadow-2xl overflow-hidden"
            >
              {suggestions.map((s, i) => {
                const sym = s.symbol.replace(/\.(NS|BO)$/, "");
                return (
                  <button
                    key={s.symbol}
                    onMouseDown={() => pick(s)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                      i === activeIdx ? "bg-zinc-800" : "hover:bg-zinc-800/70"
                    }`}
                  >
                    <span className="shrink-0 font-mono text-xs font-bold text-zinc-100 w-24 truncate">
                      {sym}
                    </span>
                    <span className="text-xs text-zinc-500 truncate">{s.name}</span>
                    <span className="ml-auto shrink-0 text-[10px] text-zinc-700 font-mono">
                      {s.symbol.endsWith(".BO") ? "BSE" : "NSE"}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <button
          onClick={() => submit()}
          disabled={adding || !value.trim()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-xs font-semibold text-white transition-colors shrink-0"
        >
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          Add
        </button>
      </div>

      {error && <p className="text-xs text-red-400 px-0.5">{error}</p>}
    </div>
  );
}
