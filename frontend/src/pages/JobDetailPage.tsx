import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bookmark,
  Building2,
  CalendarDays,
  ExternalLink,
  FilterX,
  MapPin,
  Sparkles,
  Wallet,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import { ApplicationEditor } from "../components/ApplicationEditor";
import { BriefPanel } from "../components/BriefPanel";
import { FresherBadge, RedFlags, ScoreBadge, SourceBadge } from "../components/JobBadges";
import { PageHeader } from "../components/layout/PageHeader";
import { Markdown } from "../components/Markdown";
import { ReferralPanel } from "../components/ReferralPanel";
import { ResumePanel } from "../components/ResumePanel";
import { EmptyState, ErrorState, ProseSkeleton } from "../components/states";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { errorMessage, formatDate } from "../lib/utils";

function JobDetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading">
      <Skeleton className="mb-6 h-4 w-24" />
      <div className="mb-8 flex gap-4">
        <Skeleton className="size-16 rounded-xl" />
        <div className="flex flex-1 flex-col gap-3">
          <Skeleton className="h-7 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <ProseSkeleton />
        </Card>
        <Card className="h-48 p-6">
          <Skeleton className="h-4 w-1/2" />
        </Card>
      </div>
    </div>
  );
}

export function JobDetailPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();

  const {
    data: job,
    isLoading,
    error,
    refetch,
  } = useQuery({ queryKey: ["job", id], queryFn: () => api.getJob(id) });
  const { data: tracked } = useQuery({
    queryKey: ["applications", {}],
    queryFn: () => api.listApplications(),
  });
  const application = tracked?.items.find((a) => a.job_id === id);

  const save = useMutation({
    mutationFn: () => api.createApplication({ job_id: id }),
    onSuccess: () => {
      toast.success("Saved to your tracker");
      return queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => toast.error(errorMessage(err, "Could not save this job")),
  });

  if (isLoading) return <JobDetailSkeleton />;
  if (error || !job) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <>
        <PageHeader title="Job" back={{ to: "/jobs", label: "All jobs" }} />
        {notFound ? (
          <EmptyState
            icon={FilterX}
            title="Job not found."
            description="It may have been removed from the source, or the link is wrong."
            action={
              <Button asChild variant="outline">
                <Link to="/jobs">Back to jobs</Link>
              </Button>
            }
          />
        ) : (
          <ErrorState
            title="Could not load this job."
            message={errorMessage(error, "The API didn't respond.")}
            onRetry={() => void refetch()}
          />
        )}
      </>
    );
  }

  const location = job.location || (job.is_remote ? "Remote" : "—");

  return (
    <div className="job-detail">
      <PageHeader
        back={{ to: "/jobs", label: "All jobs" }}
        title={
          <span className="flex items-start gap-4">
            <ScoreBadge job={job} size="lg" />
            <span className="min-w-0 pt-1">{job.title}</span>
          </span>
        }
        description={
          <div className="mt-3 flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
              <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                <Building2 className="size-4 text-muted-foreground" aria-hidden />
                {job.company}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="size-4" aria-hidden />
                {location}
              </span>
              {job.salary_text && (
                <span className="inline-flex items-center gap-1.5">
                  <Wallet className="size-4" aria-hidden />
                  {job.salary_text}
                </span>
              )}
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="size-4" aria-hidden />
                First seen {formatDate(job.first_seen_at)}
                {job.posted_at && <> · posted {formatDate(job.posted_at)}</>}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <SourceBadge job={job} />
              {job.fresher_friendly && <FresherBadge />}
              {job.employment_type && <Badge variant="outline">{job.employment_type}</Badge>}
            </div>
          </div>
        }
        actions={
          <>
            {!application && (
              <Button variant="outline" onClick={() => save.mutate()} disabled={save.isPending}>
                <Bookmark aria-hidden /> Save
              </Button>
            )}
            <Button asChild>
              <a href={job.url} target="_blank" rel="noopener noreferrer">
                Open posting / apply <ExternalLink aria-hidden />
              </a>
            </Button>
          </>
        }
      />

      <div className="mb-6 flex flex-col gap-3">
        {job.llm_reason && (
          <Alert variant="info">
            <Sparkles aria-hidden />
            <AlertTitle>Why it fits</AlertTitle>
            <AlertDescription className="job-reason text-foreground/80">
              <Markdown inline>{job.llm_reason}</Markdown>
            </AlertDescription>
          </Alert>
        )}
        {!job.passed_prefilter && (
          <Alert variant="warning">
            <FilterX aria-hidden />
            <AlertTitle>Filtered out by your rules</AlertTitle>
            <AlertDescription>{job.prefilter_reason}</AlertDescription>
          </Alert>
        )}
        <RedFlags flags={job.red_flags} />
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-3">
        <div className="flex min-w-0 flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Job description</CardTitle>
              {job.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {job.tags.slice(0, 12).map((t) => (
                    <Badge key={t} variant="secondary">
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
            </CardHeader>
            <CardContent>
              {job.description ? (
                <Markdown breaks className="max-h-[36rem] overflow-y-auto pr-2">
                  {job.description}
                </Markdown>
              ) : (
                <p className="text-sm text-muted-foreground">No description provided by the source.</p>
              )}
            </CardContent>
          </Card>

          <ResumePanel jobId={job.id} />
          <ReferralPanel jobId={job.id} application={application} />
        </div>

        <aside className="flex flex-col gap-6 lg:sticky lg:top-8">
          <Card>
            <CardHeader>
              <CardTitle>Tracker</CardTitle>
              {!application && <CardDescription>Track this application through to an offer.</CardDescription>}
            </CardHeader>
            <CardContent>
              {application ? (
                <ApplicationEditor key={application.id} application={application} compact />
              ) : (
                <Button className="w-full" onClick={() => save.mutate()} disabled={save.isPending}>
                  <Bookmark aria-hidden /> Save to tracker
                </Button>
              )}
            </CardContent>
          </Card>
          <BriefPanel jobId={job.id} company={job.company} />
        </aside>
      </div>
    </div>
  );
}
