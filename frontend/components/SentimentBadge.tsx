import { sentimentColor, sentimentDot } from "@/lib/utils";
import type { Sentiment } from "@/lib/types";

export default function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${sentimentColor(sentiment)}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${sentimentDot(sentiment)}`} />
      {sentiment}
    </span>
  );
}
