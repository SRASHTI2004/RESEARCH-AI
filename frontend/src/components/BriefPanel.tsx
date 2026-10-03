import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, FileSearch, Loader2, RefreshCw } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import { formatDate } from "../lib/utils";
import { InlineError } from "./states";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Skeleton } from "./ui/skeleton";

/** Reuses the Company Research Brief pipeline for this job's company. */
export function BriefPanel({ jobId, company }: { jobId: string; company: string }) {
  const navigate = useNavigate();
  const { data: latest, isLoading } = useQuery({
    queryKey: ["job-brief", jobId],
    queryFn: () => api.getJobBrief(jobId),
  });

  const generate = useMutation({
    mutationFn: () => api.generateJobBrief(jobId),
    onSuccess: (brief) => {
      toast.success(`Researching ${company}…`, { description: "Follow the agents live on the brief page." });
      navigate(`/briefs/${brief.id}`);
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "Could not start the brief."),
  });

  const usable = latest && latest.status !== "failed";

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>
          <span className="flex size-7 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <FileSearch className="size-4" aria-hidden />
          </span>
          Company brief
        </CardTitle>
        <CardDescription>
          A cited research brief on {company} (overview, products, recent news) — useful before applying or an
          interview. Uses several LLM calls, so an existing brief is reused.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {isLoading ? (
          <Skeleton className="h-9 w-full" />
        ) : (
          <>
            {usable && (
              <Button asChild className="w-full">
                <Link to={`/briefs/${latest.id}`}>
                  View company brief ({formatDate(latest.created_at)})
                  <ArrowRight aria-hidden />
                </Link>
              </Button>
            )}
            <Button
              variant={usable ? "ghost" : "default"}
              className="w-full"
              disabled={generate.isPending}
              onClick={() => generate.mutate()}
            >
              {generate.isPending ? (
                <Loader2 className="animate-spin" aria-hidden />
              ) : (
                usable && <RefreshCw aria-hidden />
              )}
              {generate.isPending ? "Starting…" : usable ? "Regenerate" : "Generate company brief"}
            </Button>
          </>
        )}
        {latest?.status === "failed" && (
          <p className="text-xs text-muted-foreground">The last attempt failed; try again.</p>
        )}
        {generate.error && (
          <InlineError>
            {generate.error instanceof ApiError ? generate.error.message : "Could not start the brief."}
          </InlineError>
        )}
      </CardContent>
    </Card>
  );
}
