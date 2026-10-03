import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bookmark,
  BookmarkCheck,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Search,
  SearchX,
  Terminal,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../api/client";
import type { JobFilters, JobSummary } from "../api/types";
import { FresherBadge, RedFlagCount, ScoreBadge, SourceBadge } from "../components/JobBadges";
import { PageHeader } from "../components/layout/PageHeader";
import { Markdown } from "../components/Markdown";
import { EmptyState, ErrorState, ListSkeleton } from "../components/states";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Checkbox, Label } from "../components/ui/label";
import { NativeSelect } from "../components/ui/select";
import { cn, errorMessage, formatDateTime, timeAgo } from "../lib/utils";
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
const DEFAULT_FILTERS: JobFilters = { min_score: undefined, days: 14 };

function SourceStatus() {
  const { data } = useQuery({ queryKey: ["job-sources"], queryFn: api.jobSources });
  if (!data || data.length === 0) return null;
  const latest = data.reduce((a, b) => (a.started_at > b.started_at ? a : b));
  const failed = data.filter((r) => r.status === "error");
  return (
    <span className="inline-flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      <span className="inline-flex items-center gap-1.5" title={formatDateTime(latest.started_at)}>
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-success/60" />
          <span className="relative inline-flex size-2 rounded-full bg-success" />
        </span>
        Last fetch {timeAgo(latest.started_at)}
      </span>
      {failed.length > 0 && (
        <Badge variant="destructive" title={failed.map((r) => r.message).join("\n")}>
          Failed: {failed.map((r) => sourceLabel(r.source)).join(", ")}
        </Badge>
      )}
    </span>
  );
}

function JobCard({
  job,
  tracked,
  onSave,
  saving,
}: {
  job: JobSummary;
  tracked: boolean;
  onSave: () => void;
  saving: boolean;
}) {
  const location = job.location || (job.is_remote ? "Remote" : "—");
  return (
    <li>
      <Card
        className={cn(
          "group flex flex-col gap-4 p-4 transition-all hover:border-primary/30 hover:shadow-md sm:flex-row sm:items-start sm:p-5",
          !job.passed_prefilter && "opacity-60 hover:opacity-100",
        )}
      >
        <div className="flex min-w-0 flex-1 gap-4">
          <ScoreBadge job={job} />
          <div className="min-w-0 flex-1">
            <Link
              to={`/jobs/${job.id}`}
              className="job-title line-clamp-2 font-semibold tracking-tight text-foreground transition-colors hover:text-primary"
            >
              {job.title}
            </Link>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
              <span className="font-medium text-foreground/80">{job.company}</span>
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5" aria-hidden />
                {location}
              </span>
              <span>{timeAgo(job.first_seen_at)}</span>
            </div>
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              <SourceBadge job={job} />
              {job.fresher_friendly && <FresherBadge />}
              <RedFlagCount flags={job.red_flags} />
            </div>
            {(job.passed_prefilter ? job.llm_reason : job.prefilter_reason) && (
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {job.passed_prefilter ? (
                  <Markdown inline>{job.llm_reason ?? ""}</Markdown>
                ) : (
                  `Filtered out: ${job.prefilter_reason}`
                )}
              </p>
            )}
          </div>
        </div>
        <div className="flex shrink-0 justify-end sm:pt-0.5">
          {tracked ? (
            <Button asChild variant="secondary" size="sm">
              <Link to="/tracker" className="tag-tracked">
                <BookmarkCheck aria-hidden className="text-primary" />
                Tracked
              </Link>
            </Button>
          ) : (
            <Button variant="outline" size="sm" disabled={saving} onClick={onSave}>
              <Bookmark aria-hidden />
              Save
            </Button>
          )}
        </div>
      </Card>
    </li>
  );
}

export function JobsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<JobFilters>(DEFAULT_FILTERS);
  const [offset, setOffset] = useState(0);

  const query = { ...filters, limit: PAGE_SIZE, offset };
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["jobs", query],
    queryFn: () => api.listJobs(query),
  });
  const { data: sourceRuns } = useQuery({ queryKey: ["job-sources"], queryFn: api.jobSources });
  const { data: tracked } = useQuery({
    queryKey: ["applications", {}],
    queryFn: () => api.listApplications(),
  });
  const trackedJobIds = new Set(tracked?.items.map((a) => a.job_id).filter(Boolean));

  const save = useMutation({
    mutationFn: (jobId: string) => api.createApplication({ job_id: jobId }),
    onSuccess: (_, jobId) => {
      const job = data?.items.find((j) => j.id === jobId);
      toast.success("Saved to your tracker", {
        description: job ? `${job.title} · ${job.company}` : undefined,
        action: { label: "View", onClick: () => navigate("/tracker") },
      });
      return queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => toast.error(errorMessage(err, "Could not save this job")),
  });

  function update(patch: Partial<JobFilters>) {
    setOffset(0);
    setFilters((f) => ({ ...f, ...patch }));
  }

  function resetFilters() {
    setSearch("");
    setOffset(0);
    setFilters(DEFAULT_FILTERS);
  }

  const neverFetched = sourceRuns !== undefined && sourceRuns.length === 0;

  return (
    <div>
      <PageHeader
        title="Jobs"
        description="Fresh postings from official job boards and free job APIs, scored against your profile."
        actions={<SourceStatus />}
      />

      <Card className="mb-6 p-3 sm:p-4">
        <form
          role="search"
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: search.trim() || undefined });
          }}
        >
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                aria-label="Search title or company"
                placeholder="Search title or company…"
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Button type="submit" className="sm:w-auto">
              Search
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
            <NativeSelect
              aria-label="Minimum score"
              wrapperClassName="sm:w-36"
              value={filters.min_score ?? ""}
              onChange={(e) => update({ min_score: e.target.value ? Number(e.target.value) : undefined })}
            >
              <option value="">Any score</option>
              <option value="40">Score 40+</option>
              <option value="60">Score 60+</option>
              <option value="75">Score 75+</option>
            </NativeSelect>
            <NativeSelect
              aria-label="Source"
              wrapperClassName="sm:w-44"
              value={filters.source ?? ""}
              onChange={(e) => update({ source: e.target.value || undefined })}
            >
              <option value="">All sources</option>
              {SOURCES.map((s) => (
                <option key={s} value={s}>
                  {sourceLabel(s)}
                </option>
              ))}
            </NativeSelect>
            <NativeSelect
              aria-label="First seen"
              wrapperClassName="sm:w-40"
              value={filters.days ?? ""}
              onChange={(e) => update({ days: e.target.value ? Number(e.target.value) : undefined })}
            >
              <option value="1">Last 24h</option>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="">Any time</option>
            </NativeSelect>
            <div className="col-span-2 flex flex-wrap items-center gap-x-5 gap-y-2 px-1 sm:ml-2">
              <Label className="cursor-pointer font-normal text-muted-foreground">
                <Checkbox
                  checked={!!filters.fresher_only}
                  onChange={(e) => update({ fresher_only: e.target.checked })}
                />
                Fresher-friendly only
              </Label>
              <Label className="cursor-pointer font-normal text-muted-foreground">
                <Checkbox
                  checked={!!filters.include_filtered}
                  onChange={(e) => update({ include_filtered: e.target.checked })}
                />
                Show filtered-out
              </Label>
            </div>
          </div>
        </form>
      </Card>

      {data && data.total > 0 && (
        <p className="mb-3 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{data.total}</span>{" "}
          {data.total === 1 ? "job" : "jobs"}
        </p>
      )}

      {isLoading && <ListSkeleton rows={5} />}

      {error && (
        <ErrorState
          title="Could not load jobs."
          message={errorMessage(error, "The API didn't respond.")}
          onRetry={() => void refetch()}
        />
      )}

      {data &&
        data.items.length === 0 &&
        (neverFetched ? (
          <EmptyState
            icon={Terminal}
            title="No jobs fetched yet"
            description={
              <>
                Run <code className="rounded bg-muted px-1.5 py-0.5 text-xs">python -m app.cli fetch</code>,
                or wait for the daily task — new postings will show up here, scored and ranked.
              </>
            }
          />
        ) : (
          <EmptyState
            icon={SearchX}
            title="No jobs match these filters"
            description="Try lowering the minimum score, widening the date range, or including filtered-out jobs."
            action={
              <Button variant="outline" onClick={resetFilters}>
                Reset filters
              </Button>
            }
          />
        ))}

      {data && data.items.length > 0 && (
        <ul className="job-list flex flex-col gap-3">
          {data.items.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              tracked={trackedJobIds.has(job.id)}
              saving={save.isPending}
              onSave={() => save.mutate(job.id)}
            />
          ))}
        </ul>
      )}

      {data && data.total > PAGE_SIZE && (
        <nav aria-label="Pagination" className="mt-6 flex items-center justify-between gap-4">
          <Button
            variant="outline"
            size="sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            <ChevronLeft aria-hidden /> Previous
          </Button>
          <span className="text-sm text-muted-foreground tabular-nums">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={offset + PAGE_SIZE >= data.total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next <ChevronRight aria-hidden />
          </Button>
        </nav>
      )}
    </div>
  );
}
