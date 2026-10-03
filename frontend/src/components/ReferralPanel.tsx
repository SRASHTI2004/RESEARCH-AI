import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { Application } from "../api/types";
import { CopyButton } from "./CopyButton";

export function ReferralPanel({ jobId, application }: { jobId: string; application?: Application }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const { data, isLoading, error } = useQuery({
    queryKey: ["referral", jobId],
    queryFn: () => api.getReferralKit(jobId),
    enabled: open,
  });

  const markAsked = useMutation({
    mutationFn: async () =>
      application
        ? api.updateApplication(application.id, { status: "referral_asked" })
        : api.createApplication({ job_id: jobId, status: "referral_asked" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  return (
    <section className="panel">
      <h2>Referral helper</h2>
      {!open ? (
        <>
          <p className="hint-inline">
            Search strings to paste into LinkedIn, where to look, and message drafts. Nothing is sent for you.
          </p>
          <button type="button" className="secondary" onClick={() => setOpen(true)}>
            Show referral helper
          </button>
        </>
      ) : (
        <>
          {isLoading && <p>Loading…</p>}
          {error && <p className="field-error">Could not build the referral kit.</p>}
          {data && (
            <div className="referral">
              {data.notes.map((n) => (
                <p key={n} className="hint-inline">
                  {n}
                </p>
              ))}

              <h3>1. Find people</h3>
              <ul className="search-strings">
                {data.search_strings.map((s) => (
                  <li key={s.query}>
                    <div>
                      <strong>{s.label}</strong> <small className="hint-inline">({s.where})</small>
                      <code>{s.query}</code>
                    </div>
                    <div className="row-actions">
                      <CopyButton text={s.query} />
                      <a
                        className="button secondary small"
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open search ↗
                      </a>
                    </div>
                  </li>
                ))}
              </ul>

              <h3>2. Where to look</h3>
              <ul className="checklist">
                {data.checklist.map((item) => (
                  <li key={item}>
                    <label className="checkbox">
                      <input type="checkbox" /> {item}
                    </label>
                  </li>
                ))}
              </ul>

              <h3>3. Message drafts</h3>
              {data.drafts.map((d) => (
                <div key={d.kind} className="draft">
                  <div className="draft-header">
                    <strong>{d.title}</strong>
                    <span className="hint-inline">{d.char_count} chars</span>
                    <CopyButton text={d.body} />
                  </div>
                  <pre className="report-text">{d.body}</pre>
                </div>
              ))}

              <div className="export-buttons">
                <button
                  type="button"
                  disabled={markAsked.isPending || application?.status === "referral_asked"}
                  onClick={() => markAsked.mutate()}
                >
                  {application?.status === "referral_asked"
                    ? "Marked as referral asked"
                    : "I asked for a referral"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
