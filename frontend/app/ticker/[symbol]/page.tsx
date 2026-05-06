import { api } from "@/lib/api";
import AlertCard from "@/components/AlertCard";
import PriceWidget from "@/components/PriceWidget";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export const revalidate = 0;

interface Props {
  params: { symbol: string };
}

export default async function TickerPage({ params }: Props) {
  const symbol = params.symbol.toUpperCase();

  const [alerts, prices] = await Promise.all([
    api.alerts.list({ ticker: symbol, min_score: 1 }).catch(() => []),
    api.prices.all().catch(() => []),
  ]);

  const price = prices.find((p) => p.ticker.includes(symbol));

  return (
    <div className="flex flex-col gap-6 p-6 max-w-[900px] mx-auto w-full">
      {/* Back */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors w-fit"
      >
        <ArrowLeft size={14} />
        Overview
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight font-mono">{symbol}</h1>
          <p className="text-sm text-zinc-500 mt-0.5">{alerts.length} alerts on record</p>
        </div>
        {price && (
          <div className="w-64 shrink-0">
            <PriceWidget price={price} />
          </div>
        )}
      </div>

      {/* Alerts */}
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Alert History</h2>
        {alerts.length === 0 ? (
          <div className="flex items-center justify-center h-32 rounded-xl border border-dashed border-zinc-800 text-sm text-zinc-600">
            No alerts for {symbol}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {alerts.map((a) => (
              <AlertCard key={a._id} alert={a} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
