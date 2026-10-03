import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { JobFilters } from "../api/types";
import { ScoreBadge, SourceBadge } from "../components/JobBadges";
import { sourceLabel } from "../tracker";

const PAGE_SIZE = 50;
const SOURCES = [
  "greenhouse",
  "lever",
  "ashby",
  "remotive",
  "remoteok",
  "weworkremotely",
  "himalayas",
  "arbeitnow",
  "adzuna",
];

function SourceStatus() {
  const { data } = useQuery({ queryKey: ["job-sources"], queryFn: api.jobSources });
  if (!data || data.length === 0) {
    return (
      <p className="hint">
        No jobs fetched yet — run <code>python -m app.cli fetch</code> (or wait for the daily task).
      </p>
    );
  }
  const latest = data.reduce((a, b) => (a.started_at > b.started_at ? a : b));
  const failed = data.filter((r) => r.status === "error");
  return (
    <p className="hint">
      Last fetch {new Date(latest.started_at).toLocaleString()}
      {failed.length > 0 && (
        <span className="field-error-inline">
          {" "}
          · failed: {failed.map((r) => sourceLabel(r.source)).join(", ")}
        </span>
      )}
    </p>
  );
}

export function JobsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<JobFilters>({ min_score: undefined, days: 14 });
  const [offset, setOffset] = useState(0);

  const query = { ...filters, limit: PAGE_SIZE, offset };
  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs", query],
    queryFn: () => api.listJobs(query),
  });
  const { data: tracked } = useQuery({
    queryKey: ["applications", {}],
    queryFn: () => api.listApplications(),
  });
  const trackedJobIds = new Set(tracked?.items.map((a) => a.job_id).filter(Boolean));

  const save = useMutation({
    mutationFn: (jobId: string) => api.createApplication({ job_id: jobId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  function update(patch: Partial<JobFilters>) {
    setOffset(0);
    setFilters((f) => ({ ...f, ...patch }));
  }

  return (
    <div className="wide">
      <h1>Jobs</h1>
      <SourceStatus />

      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          update({ q: search.trim() || undefined });
        }}
      >
        <input
          aria-label="Search title or company"
          placeholder="Search title or company…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Minimum score"
          value={filters.min_score ?? ""}
          onChange={(e) => update({ min_score: e.target.value ? Number(e.target.value) : undefined })}
        >
          <option value="">Any score</option>
          <option value="40">40+</option>
          <option value="60">60+</option>
          <option value="75">75+</option>
        </select>
        <select
          aria-label="Source"
          value={filters.source ?? ""}
          onChange={(e) => update({ source: e.target.value || undefined })}
        >
          <option value="">All sources</option>
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {sourceLabel(s)}
            </option>
          ))}
        </select>
        <select
          aria-label="First seen"
          value={filters.days ?? ""}
          onChange={(e) => update({ days: e.target.value ? Number(e.target.value) : undefined })}
        >
          <option value="1">Last 24h</option>
          <option value="7">Last 7 days</option>
          <option value="14">Last 14 days</option>
          <option value="">Any time</option>
        </select>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={!!filters.fresher_only}
            onChange={(e) => update({ fresher_only: e.target.checked })}
          />
          Fresher-friendly only
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={!!filters.include_filtered}
            onChange={(e) => update({ include_filtered: e.target.checked })}
          />
          Show filtered-out
        </label>
        <button type="submit">Search</button>
      </form>

      {isLoading && <p>Loading…</p>}
      {error && <p className="field-error">Could not load jobs.</p>}
      {data && data.items.length === 0 && <p>No jobs match these filters.</p>}

      <ul className="job-list">
        {data?.items.map((job) => (
          <li key={job.id} className={job.passed_prefilter ? "" : "filtered-out"}>
            <ScoreBadge job={job} />
            <div className="job-main">
              <Link to={`/jobs/${job.id}`} className="job-title">
                {job.title}
              </Link>
              <div className="job-meta">
                <strong>{job.company}</strong> · {job.location || (job.is_remote ? "Remote" : "—")} ·{" "}
                <SourceBadge job={job} />
                {job.fresher_friendly && <span className="tag tag-fresher">fresher-friendly</span>}
                {job.red_flags.length > 0 && (
                  <span className="tag tag-flag" title={job.red_flags.join("\n")}>
                    ⚠ {job.red_flags.length} to check
                  </span>
                )}
              </div>
              <p className="job-reason">
                {job.passed_prefilter ? job.llm_reason : `Filtered out: ${job.prefilter_reason}`}
              </p>
            </div>
            <div className="job-actions">
              {trackedJobIds.has(job.id) ? (
                <Link to="/tracker" className="tag tag-tracked">
                  Tracked
                </Link>
              ) : (
                <button
                  type="button"
                  className="secondary"
                  disabled={save.isPending}
                  onClick={() => save.mutate(job.id)}
                >
                  Save
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {data && data.total > PAGE_SIZE && (
        <div className="pager">
          <button
            type="button"
            className="secondary"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </button>
          <span>
            {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
          </span>
          <button
            type="button"
            className="secondary"
            disabled={offset + PAGE_SIZE >= data.total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
