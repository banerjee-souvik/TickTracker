import { changeColor, formatChange, formatCap, symbolOnly } from "@/lib/utils";
import type { Price } from "@/lib/types";

export default function PriceWidget({ price }: { price: Price }) {
  const sym = symbolOnly(price.ticker);
  return (
    <div className="flex flex-col gap-2 p-4 rounded-xl border border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-mono font-bold text-zinc-400">{sym}</p>
          <p className="text-xs text-zinc-600 mt-0.5 truncate max-w-[140px]">{price.name}</p>
        </div>
        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${changeColor(price.change_pct)} bg-zinc-800`}>
          {formatChange(price.change_pct)}
        </span>
      </div>

      <p className="text-2xl font-semibold text-zinc-100">
        ₹{price.ltp?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
      </p>

      <div className="flex items-center justify-between text-[11px] text-zinc-600">
        <span>52W: ₹{price.week_52_low?.toFixed(0)} – ₹{price.week_52_high?.toFixed(0)}</span>
        <span>{formatCap(price.market_cap)}</span>
      </div>

      {/* 52-week range bar */}
      {price.week_52_high && price.week_52_low && (
        <div className="relative h-1 rounded-full bg-zinc-800 mt-1">
          <div
            className="absolute left-0 h-full rounded-full bg-emerald-500/60"
            style={{
              width: `${Math.min(100, Math.max(0,
                ((price.ltp - price.week_52_low) / (price.week_52_high - price.week_52_low)) * 100
              ))}%`,
            }}
          />
        </div>
      )}
    </div>
  );
}
