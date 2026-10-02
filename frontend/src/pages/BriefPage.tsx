import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { ExportButtons } from "../components/ExportButtons";
import { ProgressStages } from "../components/ProgressStages";
import { SourceList } from "../components/SourceList";

export function BriefPage() {
  const { id } = useParams<{ id: string }>();

  const {
    data: job,
    isLoading,
    error,
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

  if (isLoading) return <p>Loading…</p>;
  if (error || !job) return <p className="field-error">Could not load this brief.</p>;

  return (
    <div>
      <h1>{job.company}</h1>
      <ProgressStages status={job.status} />

      {job.status === "failed" && <p className="field-error">{job.error}</p>}

      {job.status === "done" ? (
        <>
          <ExportButtons job={job} />
          <section>
            <h2>Final Report</h2>
            <pre className="report-text">{job.final_report}</pre>
          </section>
          <section>
            <h2>Sources</h2>
            <SourceList sources={job.sources} />
          </section>
        </>
      ) : (
        job.status !== "failed" &&
        job.research && (
          <section>
            <h2>Research so far</h2>
            <pre className="report-text">{job.research}</pre>
          </section>
        )
      )}
    </div>
  );
}
