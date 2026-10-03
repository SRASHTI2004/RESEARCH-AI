import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";

/** Reuses the Company Research Brief pipeline for this job's company. */
export function BriefPanel({ jobId, company }: { jobId: string; company: string }) {
  const navigate = useNavigate();
  const { data: latest, isLoading } = useQuery({
    queryKey: ["job-brief", jobId],
    queryFn: () => api.getJobBrief(jobId),
  });

  const generate = useMutation({
    mutationFn: () => api.generateJobBrief(jobId),
    onSuccess: (brief) => navigate(`/briefs/${brief.id}`),
  });

  const usable = latest && latest.status !== "failed";

  return (
    <section className="panel">
      <h2>Company brief</h2>
      <p className="hint-inline">
        A cited research brief on {company} (overview, products, recent news) — useful before applying or an
        interview. Uses several LLM calls, so an existing brief is reused.
      </p>
      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <div className="export-buttons">
          {usable && (
            <Link className="button" to={`/briefs/${latest.id}`}>
              View company brief ({new Date(latest.created_at).toLocaleDateString()})
            </Link>
          )}
          <button
            type="button"
            className={usable ? "secondary" : undefined}
            disabled={generate.isPending}
            onClick={() => generate.mutate()}
          >
            {generate.isPending ? "Starting…" : usable ? "Regenerate" : "Generate company brief"}
          </button>
        </div>
      )}
      {latest?.status === "failed" && <p className="hint-inline">The last attempt failed; try again.</p>}
      {generate.error && (
        <p className="field-error">
          {generate.error instanceof ApiError ? generate.error.message : "Could not start the brief."}
        </p>
      )}
    </section>
  );
}
