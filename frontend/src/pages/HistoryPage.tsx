import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export function HistoryPage() {
  const {
    data: jobs,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research-history"],
    queryFn: api.listResearch,
  });

  if (isLoading) return <p>Loading…</p>;
  if (error) return <p className="field-error">Could not load history.</p>;

  return (
    <div>
      <h1>History</h1>
      {jobs && jobs.length === 0 && <p>No research jobs yet.</p>}
      <ul className="history-list">
        {jobs?.map((job) => (
          <li key={job.id}>
            <Link to={`/briefs/${job.id}`}>{job.company}</Link> — {job.status} (
            {new Date(job.created_at).toLocaleString()})
          </li>
        ))}
      </ul>
    </div>
  );
}
