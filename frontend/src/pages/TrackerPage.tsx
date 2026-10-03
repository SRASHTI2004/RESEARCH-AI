import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { ApplicationFilters, ApplicationStatus } from "../api/types";
import { ApplicationEditor } from "../components/ApplicationEditor";
import { STATUS_LABELS, STATUSES } from "../tracker";

function AddManualForm() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => api.createApplication({ title, company, url }),
    onSuccess: () => {
      setTitle("");
      setCompany("");
      setUrl("");
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not add"),
  });

  if (!open) {
    return (
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        + Track a role found elsewhere
      </button>
    );
  }
  return (
    <form
      className="filter-bar"
      onSubmit={(e) => {
        e.preventDefault();
        if (title.trim() && company.trim()) create.mutate();
      }}
    >
      <input
        aria-label="Job title"
        placeholder="Job title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <input
        aria-label="Company"
        placeholder="Company"
        value={company}
        onChange={(e) => setCompany(e.target.value)}
      />
      <input
        aria-label="Link"
        placeholder="Link (optional)"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      <button type="submit" disabled={create.isPending || !title.trim() || !company.trim()}>
        Add
      </button>
      <button type="button" className="secondary" onClick={() => setOpen(false)}>
        Cancel
      </button>
      {error && <p className="field-error">{error}</p>}
    </form>
  );
}

export function TrackerPage() {
  const [params] = useSearchParams();
  const focus = params.get("focus");
  const [filters, setFilters] = useState<ApplicationFilters>({});
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["applications", filters],
    queryFn: () => api.listApplications(filters),
  });

  useEffect(() => {
    if (focus && data) document.getElementById(`app-${focus}`)?.scrollIntoView({ block: "center" });
  }, [focus, data]);

  const total = Object.values(data?.counts ?? {}).reduce((a, b) => a + (b ?? 0), 0);

  return (
    <div className="wide">
      <h1>Application tracker</h1>

      <div className="status-chips" role="group" aria-label="Filter by status">
        <button
          type="button"
          className={filters.status ? "chip" : "chip active"}
          onClick={() => setFilters((f) => ({ ...f, status: undefined }))}
        >
          All ({total})
        </button>
        {STATUSES.map((s: ApplicationStatus) => (
          <button
            key={s}
            type="button"
            className={filters.status === s ? "chip active" : "chip"}
            onClick={() => setFilters((f) => ({ ...f, status: s }))}
          >
            {STATUS_LABELS[s]} ({data?.counts[s] ?? 0})
          </button>
        ))}
      </div>

      <form
        className="filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setFilters((f) => ({ ...f, q: search.trim() || undefined }));
        }}
      >
        <input
          aria-label="Search tracker"
          placeholder="Search title, company, notes…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Follow-ups"
          value={filters.due ?? ""}
          onChange={(e) =>
            setFilters((f) => ({ ...f, due: (e.target.value || undefined) as ApplicationFilters["due"] }))
          }
        >
          <option value="">All follow-ups</option>
          <option value="overdue">Overdue</option>
          <option value="today">Due by today</option>
          <option value="week">Due this week</option>
        </select>
        <button type="submit">Search</button>
      </form>

      <AddManualForm />

      {isLoading && <p>Loading…</p>}
      {error && <p className="field-error">Could not load your tracker.</p>}
      {data && data.items.length === 0 && (
        <p className="hint">
          Nothing here yet. Save jobs from the <Link to="/jobs">Jobs</Link> page.
        </p>
      )}

      <ul className="tracker-list">
        {data?.items.map((a) => (
          <li key={a.id} id={`app-${a.id}`} className={a.id === focus ? "focused" : ""}>
            <div className="tracker-heading">
              {a.job_id ? (
                <Link to={`/jobs/${a.job_id}`} className="job-title">
                  {a.title}
                </Link>
              ) : a.url ? (
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="job-title">
                  {a.title} ↗
                </a>
              ) : (
                <span className="job-title">{a.title}</span>
              )}
              <span className="job-meta">
                {a.company}
                {a.location && ` · ${a.location}`}
                {a.job_score !== null && ` · score ${a.job_score}`}
              </span>
            </div>
            <ApplicationEditor key={`${a.id}-${a.updated_at}`} application={a} />
          </li>
        ))}
      </ul>
    </div>
  );
}
