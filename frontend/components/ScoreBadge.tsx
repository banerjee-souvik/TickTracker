import { scoreBg } from "@/lib/utils";

export default function ScoreBadge({ score }: { score: number }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-bold border ${scoreBg(score)}`}>
      {score}/10
    </span>
  );
}
