import type { Alert, Price, RawNews, WatchlistItem } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  alerts: {
    list: (params?: { ticker?: string; min_score?: number; sentiment?: string }) => {
      const q = new URLSearchParams();
      if (params?.ticker) q.set("ticker", params.ticker);
      if (params?.min_score) q.set("min_score", String(params.min_score));
      if (params?.sentiment) q.set("sentiment", params.sentiment);
      const qs = q.toString();
      return get<Alert[]>(`/api/alerts${qs ? `?${qs}` : ""}`);
    },
    byTicker: (ticker: string) => get<Alert[]>(`/api/alerts/${ticker}`),
  },
  prices: {
    all: () => get<Price[]>("/api/prices"),
    one: (ticker: string) => get<Price>(`/api/prices/${ticker}`),
  },
  watchlist: {
    list: () => get<WatchlistItem[]>("/api/watchlist"),
    add: (ticker: string) => post<{ ticker: string; status: string }>("/api/watchlist", { ticker }),
    remove: (ticker: string) => del<{ ticker: string; status: string }>(`/api/watchlist/${ticker}`),
  },
  scan: {
    trigger: () => post<{ status: string; message?: string }>("/api/scan"),
  },
  pulse: {
    list: (params?: { ticker?: string; status?: string }) => {
      const q = new URLSearchParams();
      if (params?.ticker) q.set("ticker", params.ticker);
      if (params?.status) q.set("status", params.status);
      const qs = q.toString();
      return get<RawNews[]>(`/api/pulse${qs ? `?${qs}` : ""}`);
    },
    retryFailed: () => post<{ reset: number; message: string }>("/api/pulse/retry"),
  },
};
