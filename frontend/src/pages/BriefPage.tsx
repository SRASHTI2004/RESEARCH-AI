import { useQuery } from "@tanstack/react-query";
import { FileSearch, Library } from "lucide-react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { ExportButtons } from "../components/ExportButtons";
import { PageHeader } from "../components/layout/PageHeader";
import { Markdown } from "../components/Markdown";
import { ProgressStages } from "../components/ProgressStages";
import { SourceList } from "../components/SourceList";
import { ErrorState, ProseSkeleton } from "../components/states";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { errorMessage, formatDateTime } from "../lib/utils";
import { stripSourcesSection } from "../markdown";
import { RESEARCH_STATUS } from "../research";

export function BriefPage() {
  const { id } = useParams<{ id: string }>();

  const {
    data: job,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["research", id],
    queryFn: () => api.getResearch(id!),
    enabled: !!id,
    // Poll until the job settles — this is what shows live per-stage
    // progress from the backend's status field (see Phase 5).
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
  });

  if (isLoading) {
    return (
      <div aria-busy="true" aria-label="Loading">
        <Skeleton className="mb-6 h-4 w-28" />
        <Skeleton className="mb-8 h-9 w-1/2" />
        <Card className="p-6">
          <ProseSkeleton lines={10} />
        </Card>
      </div>
    );
  }
  if (error || !job) {
    return (
      <>
        <PageHeader title="Company brief" back={{ to: "/history", label: "All briefs" }} />
        <ErrorState
          title="Could not load this brief."
          message={errorMessage(error, "The API didn't respond.")}
          onRetry={() => void refetch()}
        />
      </>
    );
  }

  const status = RESEARCH_STATUS[job.status];
  const running = job.status !== "done" && job.status !== "failed";

  return (
    <div>
      <PageHeader
        back={{ to: "/history", label: "All briefs" }}
        eyebrow={
          <span className="flex items-center gap-2">
            <Badge variant={status.variant}>{status.label}</Badge>
            <span className="text-xs text-muted-foreground">Started {formatDateTime(job.created_at)}</span>
          </span>
        }
        title={job.company}
        description="Company research brief — every claim is cited; click a number to open its source."
        actions={job.status === "done" && <ExportButtons job={job} />}
      />

      {job.status !== "done" && (
        <div className="mb-6">
          <ProgressStages status={job.status} error={job.error} />
        </div>
      )}

      {job.status === "done" ? (
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <Card>
            <CardContent className="sm:px-8 sm:py-7">
              <Markdown sources={job.sources}>
                {job.sources.length > 0 ? stripSourcesSection(job.final_report) : job.final_report}
              </Markdown>
            </CardContent>
          </Card>
          <aside className="xl:sticky xl:top-8">
            <Card>
              <CardHeader className="pb-0 sm:pb-0">
                <CardTitle>
                  <Library className="size-4 text-muted-foreground" aria-hidden />
                  Sources
                  <Badge variant="secondary" className="ml-auto">
                    {job.sources.length}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="xl:max-h-[calc(100vh-10rem)] xl:overflow-y-auto">
                <SourceList sources={job.sources} />
              </CardContent>
            </Card>
          </aside>
        </div>
      ) : (
        running && (
          <Card>
            <CardHeader>
              <CardTitle>
                <FileSearch className="size-4 text-muted-foreground" aria-hidden />
                {job.research ? "Research so far" : "Gathering sources…"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {job.research ? (
                <Markdown sources={job.sources}>{job.research}</Markdown>
              ) : (
                <ProseSkeleton lines={6} />
              )}
            </CardContent>
          </Card>
        )
      )}
    </div>
  );
}
