import { api } from "@/lib/api";
import SettingsClient from "./SettingsClient";

export const revalidate = 0;

export default async function SettingsPage() {
  const watchlist = await api.watchlist.list().catch(() => []);
  return <SettingsClient initialWatchlist={watchlist} />;
}
