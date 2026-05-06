import { ExternalLink } from "lucide-react";
import Link from "next/link";
import ScoreBadge from "./ScoreBadge";
import SentimentBadge from "./SentimentBadge";
import { timeAgo, symbolOnly } from "@/lib/utils";
import type { Alert } from "@/lib/types";

export default function AlertCard({ alert }: { alert: Alert }) {
  const sym = symbolOnly(alert.ticker);
  return (
    <div className="alert-enter group relative flex flex-col gap-3 p-4 rounded-xl border border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-colors">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Link
            href={`/ticker/${sym}`}
            className="shrink-0 text-xs font-mono font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-zinc-100 transition-colors"
          >
            {sym}
          </Link>
          <span className="text-zinc-300 text-sm font-medium leading-snug line-clamp-2">
            {alert.headline}
          </span>
        </div>
        <a
          href={alert.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500 hover:text-zinc-300"
        >
          <ExternalLink size={14} />
        </a>
      </div>

      {/* Badges */}
      <div className="flex items-center gap-3">
        <ScoreBadge score={alert.materiality_score} />
        <SentimentBadge sentiment={alert.sentiment} />
        <span className="ml-auto text-[11px] text-zinc-600">{timeAgo(alert.created_at)}</span>
      </div>

      {/* Summary */}
      <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">{alert.summary}</p>

      {/* Watch */}
      <div className="flex items-start gap-1.5 text-xs">
        <span className="text-zinc-600 shrink-0">Watch:</span>
        <span className="text-zinc-400">{alert.watch}</span>
      </div>

      {/* Source */}
      <p className="text-[11px] text-zinc-700">{alert.source_name}</p>
    </div>
  );
}
