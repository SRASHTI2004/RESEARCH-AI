import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { ApplicationEditor } from "../components/ApplicationEditor";
import { BriefPanel } from "../components/BriefPanel";
import { RedFlags, ScoreBadge, SourceBadge } from "../components/JobBadges";
import { ReferralPanel } from "../components/ReferralPanel";
import { ResumePanel } from "../components/ResumePanel";

export function JobDetailPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();

  const { data: job, isLoading, error } = useQuery({ queryKey: ["job", id], queryFn: () => api.getJob(id) });
  const { data: tracked } = useQuery({
    queryKey: ["applications", {}],
    queryFn: () => api.listApplications(),
  });
  const application = tracked?.items.find((a) => a.job_id === id);

  const save = useMutation({
    mutationFn: () => api.createApplication({ job_id: id }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  if (isLoading) return <p>Loading…</p>;
  if (error || !job) {
    return (
      <p className="field-error">
        {error instanceof ApiError && error.status === 404 ? "Job not found." : "Could not load this job."}
      </p>
    );
  }

  return (
    <div className="wide job-detail">
      <p>
        <Link to="/jobs">← All jobs</Link>
      </p>
      <div className="job-header">
        <ScoreBadge job={job} />
        <div>
          <h1>{job.title}</h1>
          <p className="job-meta">
            <strong>{job.company}</strong> · {job.location || (job.is_remote ? "Remote" : "—")} ·{" "}
            <SourceBadge job={job} />
            {job.fresher_friendly && <span className="tag tag-fresher">fresher-friendly</span>}
          </p>
          {job.salary_text && <p className="hint-inline">Pay: {job.salary_text}</p>}
        </div>
      </div>

      {job.llm_reason && <p className="job-reason">{job.llm_reason}</p>}
      {!job.passed_prefilter && <p className="hint">Filtered out by your rules: {job.prefilter_reason}</p>}
      <RedFlags flags={job.red_flags} />

      <div className="export-buttons">
        <a className="button" href={job.url} target="_blank" rel="noopener noreferrer">
          Open posting / apply ↗
        </a>
      </div>

      <section className="panel">
        <h2>Tracker</h2>
        {application ? (
          <ApplicationEditor key={application.id} application={application} />
        ) : (
          <button type="button" onClick={() => save.mutate()} disabled={save.isPending}>
            Save to tracker
          </button>
        )}
      </section>

      <BriefPanel jobId={job.id} company={job.company} />

      <ReferralPanel jobId={job.id} application={application} />

      <ResumePanel jobId={job.id} />

      <section className="panel">
        <h2>Job description</h2>
        <pre className="report-text">{job.description || "No description provided by the source."}</pre>
        <p className="hint-inline">
          First seen {new Date(job.first_seen_at).toLocaleDateString()}
          {job.posted_at && <> · posted {new Date(job.posted_at).toLocaleDateString()}</>}
        </p>
      </section>
    </div>
  );
}
