import { ExternalLink } from "lucide-react";
import { timeAgo, symbolOnly } from "@/lib/utils";
import type { RawNews, PulseStatus } from "@/lib/types";

const STATUS_STYLES: Record<PulseStatus, { dot: string; label: string; text: string }> = {
  pending_analysis: {
    dot: "bg-amber-400 animate-pulse",
    label: "Pending",
    text: "text-amber-400",
  },
  analysed: {
    dot: "bg-emerald-500",
    label: "Analysed",
    text: "text-emerald-400",
  },
  analysis_failed: {
    dot: "bg-red-500",
    label: "Failed",
    text: "text-red-400",
  },
};

export default function PulseCard({ item }: { item: RawNews }) {
  const style = STATUS_STYLES[item.status];
  const sym = symbolOnly(item.ticker);

  return (
    <div className="group flex items-start gap-3 px-4 py-3 rounded-xl border border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-colors">
      {/* Status dot */}
      <span className={`mt-1 shrink-0 w-2 h-2 rounded-full ${style.dot}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="shrink-0 text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
              {sym}
            </span>
            <p className="text-sm text-zinc-300 leading-snug line-clamp-1">{item.headline}</p>
          </div>
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500 hover:text-zinc-300"
          >
            <ExternalLink size={13} />
          </a>
        </div>

        <div className="flex items-center gap-3 mt-1.5">
          <span className={`text-[11px] font-medium ${style.text}`}>{style.label}</span>
          <span className="text-[11px] text-zinc-600">{item.source_name}</span>
          <span className="ml-auto text-[11px] text-zinc-600">{timeAgo(item.scraped_at)}</span>
        </div>
      </div>
    </div>
  );
}
