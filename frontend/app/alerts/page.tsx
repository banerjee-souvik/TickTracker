import { api } from "@/lib/api";
import AlertsClient from "./AlertsClient";

export const revalidate = 0;

export default async function AlertsPage() {
  const alerts = await api.alerts.list({ min_score: 1 }).catch(() => []);
  return <AlertsClient initialAlerts={alerts} />;
}
