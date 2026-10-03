import type { JobSummary } from "../api/types";
import { sourceLabel } from "../tracker";

export function ScoreBadge({ job }: { job: Pick<JobSummary, "score" | "llm_score"> }) {
  const level = job.score >= 70 ? "high" : job.score >= 45 ? "mid" : "low";
  const aiScored = job.llm_score !== null;
  return (
    <span
      className={`score-badge score-${level}`}
      title={aiScored ? "AI fit score" : "Rule-based score (not AI-scored yet)"}
    >
      {job.score}
      {!aiScored && <small> rule</small>}
    </span>
  );
}

export function SourceBadge({ job }: { job: Pick<JobSummary, "source" | "official_source"> }) {
  return job.official_source ? (
    <span className="tag tag-official" title="Posted on the company's own job board">
      Official · {sourceLabel(job.source)}
    </span>
  ) : (
    <span className="tag" title="Aggregator listing — confirm it on the company's careers page">
      via {sourceLabel(job.source)}
    </span>
  );
}

export function RedFlags({ flags }: { flags: string[] }) {
  if (flags.length === 0) return null;
  return (
    <div className="red-flags" role="note">
      <strong>Worth checking</strong> <small>(heuristics, not a verdict)</small>
      <ul>
        {flags.map((flag) => (
          <li key={flag}>{flag}</li>
        ))}
      </ul>
    </div>
  );
}
