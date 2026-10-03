import { BadgeCheck, GraduationCap, ShieldAlert, TriangleAlert } from "lucide-react";
import type { JobSummary } from "../api/types";
import { cn } from "../lib/utils";
import { sourceLabel } from "../tracker";
import { Badge } from "./ui/badge";

function scoreLevel(score: number): "high" | "mid" | "low" {
  return score >= 70 ? "high" : score >= 45 ? "mid" : "low";
}

const SCORE_STYLES = {
  high: "bg-success-soft text-success ring-success/25",
  mid: "bg-warning-soft text-warning ring-warning/25",
  low: "bg-muted text-muted-foreground ring-border",
} as const;

export function ScoreBadge({
  job,
  size = "md",
}: {
  job: Pick<JobSummary, "score" | "llm_score">;
  size?: "md" | "lg";
}) {
  const level = scoreLevel(job.score);
  const aiScored = job.llm_score !== null;
  return (
    <span
      className={cn(
        `score-badge score-${level}`,
        "flex shrink-0 flex-col items-center justify-center rounded-xl font-semibold tabular-nums ring-1 ring-inset",
        size === "lg" ? "size-16 text-2xl" : "size-12 text-lg",
        SCORE_STYLES[level],
      )}
      title={aiScored ? "AI fit score (0–100)" : "Rule-based score (not AI-scored yet)"}
    >
      <span className="leading-none">{job.score}</span>
      <span className="mt-0.5 text-[10px] font-medium tracking-wide uppercase opacity-75">
        {aiScored ? "fit" : "rule"}
      </span>
    </span>
  );
}

export function SourceBadge({ job }: { job: Pick<JobSummary, "source" | "official_source"> }) {
  return job.official_source ? (
    <Badge variant="success" title="Posted on the company's own job board">
      <BadgeCheck aria-hidden />
      Official · {sourceLabel(job.source)}
    </Badge>
  ) : (
    <Badge variant="outline" title="Aggregator listing — confirm it on the company's careers page">
      via {sourceLabel(job.source)}
    </Badge>
  );
}

export function FresherBadge() {
  return (
    <Badge variant="info">
      <GraduationCap aria-hidden />
      fresher-friendly
    </Badge>
  );
}

export function RedFlagCount({ flags }: { flags: string[] }) {
  if (flags.length === 0) return null;
  return (
    <Badge variant="warning" title={flags.join("\n")}>
      <TriangleAlert aria-hidden />
      {flags.length} to check
    </Badge>
  );
}

export function RedFlags({ flags }: { flags: string[] }) {
  if (flags.length === 0) return null;
  return (
    <div
      role="note"
      className="red-flags flex gap-3 rounded-xl border border-warning/30 bg-warning-soft p-4 text-sm"
    >
      <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
      <div>
        <p className="font-medium">
          Worth checking{" "}
          <span className="font-normal text-muted-foreground">(heuristics, not a verdict)</span>
        </p>
        <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-muted-foreground marker:text-warning">
          {flags.map((flag) => (
            <li key={flag}>{flag}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
