"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Bell, Radio, Settings, TrendingUp } from "lucide-react";

const nav = [
  { href: "/", icon: TrendingUp, label: "Overview" },
  { href: "/alerts", icon: Bell, label: "Alerts" },
  { href: "/pulse", icon: Radio, label: "Pulse" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-zinc-800 bg-zinc-950 h-full">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-zinc-800">
        <div className="w-7 h-7 rounded-lg bg-emerald-500 flex items-center justify-center">
          <BarChart2 size={15} className="text-black" />
        </div>
        <div>
          <p className="text-sm font-semibold text-zinc-100 leading-none">TickTracker</p>
          <p className="text-[10px] text-zinc-500 mt-0.5">Equity Sentinel</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, icon: Icon, label }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-zinc-800 text-zinc-100 font-medium"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-zinc-800">
        <p className="text-[10px] text-zinc-600">NSE · BSE · FinBERT</p>
      </div>
    </aside>
  );
}
