import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Briefcase, ExternalLink, Inbox, Plus, Search, SearchX, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import type { ApplicationFilters, ApplicationStatus } from "../api/types";
import { ApplicationEditor } from "../components/ApplicationEditor";
import { ScoreBadge } from "../components/JobBadges";
import { PageHeader } from "../components/layout/PageHeader";
import { EmptyState, ErrorState, InlineError, ListSkeleton } from "../components/states";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { NativeSelect } from "../components/ui/select";
import { cn, errorMessage } from "../lib/utils";
import { STATUS_LABELS, STATUSES } from "../tracker";

function AddManualForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => api.createApplication({ title, company, url }),
    onSuccess: () => {
      toast.success("Added to your tracker", { description: `${title} · ${company}` });
      setTitle("");
      setCompany("");
      setUrl("");
      onClose();
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not add"),
  });

  return (
    <Card className="mb-6 border-primary/30 shadow-md">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Track a role found elsewhere</CardTitle>
        <Button variant="ghost" size="icon-sm" aria-label="Cancel" onClick={onClose}>
          <X aria-hidden />
        </Button>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim() && company.trim()) create.mutate();
          }}
        >
          <Input
            aria-label="Job title"
            placeholder="Job title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Input
            aria-label="Company"
            placeholder="Company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />
          <Input
            aria-label="Link"
            placeholder="Link (optional)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <Button type="submit" disabled={create.isPending || !title.trim() || !company.trim()}>
            Add
          </Button>
          {error && <InlineError className="sm:col-span-4">{error}</InlineError>}
        </form>
      </CardContent>
    </Card>
  );
}

export function TrackerPage() {
  const [params] = useSearchParams();
  const focus = params.get("focus");
  const [filters, setFilters] = useState<ApplicationFilters>({});
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["applications", filters],
    queryFn: () => api.listApplications(filters),
  });

  useEffect(() => {
    if (focus && data) document.getElementById(`app-${focus}`)?.scrollIntoView({ block: "center" });
  }, [focus, data]);

  const total = Object.values(data?.counts ?? {}).reduce((a, b) => a + (b ?? 0), 0);
  const filtered = !!(filters.status || filters.q || filters.due);

  return (
    <div>
      <PageHeader
        title="Application tracker"
        description="Every role you're pursuing, from saved to offer — with notes and follow-up reminders."
        actions={
          !adding && (
            <Button onClick={() => setAdding(true)}>
              <Plus aria-hidden /> Track a role found elsewhere
            </Button>
          )
        }
      />

      {adding && <AddManualForm onClose={() => setAdding(false)} />}

      <div
        className="status-chips -mx-4 mb-4 flex gap-1.5 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0"
        role="group"
        aria-label="Filter by status"
      >
        {[undefined, ...STATUSES].map((s?: ApplicationStatus) => {
          const active = filters.status === s;
          return (
            <button
              key={s ?? "all"}
              type="button"
              aria-pressed={active}
              className={cn(
                "chip shrink-0 cursor-pointer rounded-full border px-3.5 py-1.5 text-sm font-medium tabular-nums transition-colors",
                active
                  ? "active border-primary bg-primary text-primary-foreground shadow-xs"
                  : "bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground",
              )}
              onClick={() => setFilters((f) => ({ ...f, status: s }))}
            >
              {s ? `${STATUS_LABELS[s]} (${data?.counts[s] ?? 0})` : `All (${total})`}
            </button>
          );
        })}
      </div>

      <form
        role="search"
        className="mb-6 flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          setFilters((f) => ({ ...f, q: search.trim() || undefined }));
        }}
      >
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            aria-label="Search tracker"
            placeholder="Search title, company, notes…"
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <NativeSelect
          aria-label="Follow-ups"
          wrapperClassName="sm:w-48"
          value={filters.due ?? ""}
          onChange={(e) =>
            setFilters((f) => ({ ...f, due: (e.target.value || undefined) as ApplicationFilters["due"] }))
          }
        >
          <option value="">All follow-ups</option>
          <option value="overdue">Overdue</option>
          <option value="today">Due by today</option>
          <option value="week">Due this week</option>
        </NativeSelect>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {isLoading && <ListSkeleton rows={3} />}
      {error && (
        <ErrorState
          title="Could not load your tracker."
          message={errorMessage(error, "The API didn't respond.")}
          onRetry={() => void refetch()}
        />
      )}
      {data &&
        data.items.length === 0 &&
        (filtered ? (
          <EmptyState
            icon={SearchX}
            title="Nothing matches these filters"
            description="Try another status or clear the search."
            action={
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("");
                  setFilters({});
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={Inbox}
            title="Your tracker is empty"
            description="Save jobs from the Jobs page, or track a role you found elsewhere."
            action={
              <Button asChild>
                <Link to="/jobs">
                  <Briefcase aria-hidden /> Browse jobs
                </Link>
              </Button>
            }
          />
        ))}

      {data && data.items.length > 0 && (
        <ul className="tracker-list flex flex-col gap-4">
          {data.items.map((a) => (
            <li key={a.id} id={`app-${a.id}`} className="scroll-mt-24">
              <Card className={cn("p-4 sm:p-5", a.id === focus && "focused ring-2 ring-primary")}>
                <div className="tracker-heading mb-4 flex items-start gap-3">
                  {a.job_score !== null && (
                    <ScoreBadge job={{ score: a.job_score, llm_score: a.job_score }} />
                  )}
                  <div className="min-w-0 flex-1">
                    {a.job_id ? (
                      <Link
                        to={`/jobs/${a.job_id}`}
                        className="job-title font-semibold tracking-tight hover:text-primary"
                      >
                        {a.title}
                      </Link>
                    ) : a.url ? (
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="job-title inline-flex items-center gap-1 font-semibold tracking-tight hover:text-primary"
                      >
                        {a.title} <ExternalLink className="size-3.5" aria-hidden />
                      </a>
                    ) : (
                      <span className="job-title font-semibold tracking-tight">{a.title}</span>
                    )}
                    <p className="job-meta mt-0.5 text-sm text-muted-foreground">
                      {a.company}
                      {a.location && ` · ${a.location}`}
                    </p>
                  </div>
                </div>
                <ApplicationEditor key={`${a.id}-${a.updated_at}`} application={a} />
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
