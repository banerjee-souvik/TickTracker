import { api } from "@/lib/api";
import OverviewClient from "./OverviewClient";

export const revalidate = 0;

export default async function OverviewPage() {
  const [alerts, prices, watchlist] = await Promise.all([
    api.alerts.list({ min_score: 1 }).catch(() => []),
    api.prices.all().catch(() => []),
    api.watchlist.list().catch(() => []),
  ]);
  return <OverviewClient alerts={alerts} prices={prices} watchlist={watchlist} />;
}
