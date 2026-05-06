import { api } from "@/lib/api";
import PulseClient from "./PulseClient";

export const revalidate = 0;

export default async function PulsePage() {
  const items = await api.pulse.list().catch(() => []);
  return <PulseClient initialItems={items} />;
}
