import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function scoreTone(score: number | null | undefined) {
  if (score == null) return "text-muted";
  if (score >= 75) return "text-success";
  if (score >= 55) return "text-accent";
  return "text-warning";
}

/** Circular score. A missing score is shown as "?" with an explanation, never as 0%. */
export function MatchScore({ score, size = 52, className, label = true }: { score: number | null | undefined; size?: number; className?: string; label?: boolean }) {
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const value = score ?? 0;
  return (
    <div className={cn("flex items-center gap-2", className)} title={score == null ? t("match.insufficientHelp") : undefined}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" aria-hidden>
          <circle cx={size / 2} cy={size / 2} r={r} strokeWidth="5" className="fill-none stroke-surface-2" />
          {score != null && (
            <circle cx={size / 2} cy={size / 2} r={r} strokeWidth="5" strokeLinecap="round" className={cn("fill-none stroke-current", scoreTone(score))}
              strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} />
          )}
        </svg>
        <span className={cn("absolute inset-0 flex items-center justify-center font-semibold tabular-nums", size < 60 ? "text-xs" : "text-sm", scoreTone(score))}>
          {score == null ? "?" : `${score}%`}
        </span>
      </div>
      {label && <span className="sr-only">{score == null ? t("match.insufficient") : `Match ${score}%`}</span>}
    </div>
  );
}
