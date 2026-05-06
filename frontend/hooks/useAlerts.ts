"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/types";

const POLL_INTERVAL_MS = 60_000;

export function useRealtimeAlerts(initial: Alert[]) {
  const [alerts, setAlerts] = useState<Alert[]>(initial);
  const cancelledRef = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const fresh = await api.alerts.list({ min_score: 1 });
      if (!cancelledRef.current) setAlerts(fresh);
    } catch {}
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      cancelledRef.current = true;
      clearInterval(id);
    };
  }, [refresh]);

  return { alerts, refresh };
}
