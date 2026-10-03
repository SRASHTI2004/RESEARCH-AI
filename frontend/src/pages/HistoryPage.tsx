import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, FileSearch, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { EmptyState, ErrorState } from "../components/states";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { errorMessage, timeAgo } from "../lib/utils";
import { RESEARCH_STATUS } from "../research";

export function HistoryPage() {
  const {
    data: jobs,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["research-history"],
    queryFn: api.listResearch,
  });

  return (
    <div>
      <PageHeader
        title="Company briefs"
        description="Cited research on the companies you're applying to — overview, news, tech stack and interview prep."
        actions={
          <Button asChild>
            <Link to="/briefs/new">
              <Sparkles aria-hidden /> New brief
            </Link>
          </Button>
        }
      />

      {isLoading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Loading">
          {Array.from({ length: 6 }, (_, i) => (
            <Card key={i} className="flex flex-col gap-3 p-5">
              <Skeleton className="size-10 rounded-lg" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-1/3" />
            </Card>
          ))}
        </div>
      )}

      {error && (
        <ErrorState
          title="Could not load history."
          message={errorMessage(error, "The API didn't respond.")}
          onRetry={() => void refetch()}
        />
      )}

      {jobs && jobs.length === 0 && (
        <EmptyState
          icon={FileSearch}
          title="No research jobs yet."
          description="Generate a brief from any job page, or start one here for any company."
          action={
            <Button asChild>
              <Link to="/briefs/new">
                <Sparkles aria-hidden /> Research a company
              </Link>
            </Button>
          }
        />
      )}

      {jobs && jobs.length > 0 && (
        <ul className="history-list grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job) => {
            const status = RESEARCH_STATUS[job.status];
            return (
              <li key={job.id}>
                <Link
                  to={`/briefs/${job.id}`}
                  className="group block h-full rounded-xl focus-visible:ring-[3px] focus-visible:ring-ring/40 focus-visible:outline-none"
                >
                  <Card className="flex h-full flex-col gap-4 p-5 transition-all group-hover:border-primary/30 group-hover:shadow-md">
                    <div className="flex items-start justify-between">
                      <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-base font-semibold text-accent-foreground uppercase">
                        {job.company.slice(0, 1)}
                      </span>
                      <ArrowUpRight
                        className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary"
                        aria-hidden
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-semibold tracking-tight">{job.company}</p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <Badge variant={status.variant}>{status.label}</Badge>
                        <span className="text-xs text-muted-foreground">{timeAgo(job.created_at)}</span>
                      </div>
                    </div>
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
