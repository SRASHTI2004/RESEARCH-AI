import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { Application, ApplicationStatus, ApplicationUpdate } from "../api/types";
import { followUpState, STATUS_LABELS, STATUSES } from "../tracker";

const FOLLOW_UP_TEXT = { none: "", overdue: "Overdue", today: "Due today", upcoming: "" } as const;

export function ApplicationEditor({ application }: { application: Application }) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState(application.notes);
  const [error, setError] = useState<string | null>(null);

  const update = useMutation({
    mutationFn: (body: ApplicationUpdate) => api.updateApplication(application.id, body),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save"),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteApplication(application.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const state = followUpState(application.follow_up_on, application.status);

  return (
    <div className="application-editor">
      <div className="editor-row">
        <label>
          Status
          <select
            value={application.status}
            onChange={(e) => update.mutate({ status: e.target.value as ApplicationStatus })}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Follow up on
          <input
            type="date"
            value={application.follow_up_on ?? ""}
            onChange={(e) => update.mutate({ follow_up_on: e.target.value || null })}
          />
        </label>
        {FOLLOW_UP_TEXT[state] && (
          <span className={`follow-up follow-up-${state}`}>{FOLLOW_UP_TEXT[state]}</span>
        )}
        {application.applied_on && <span className="hint-inline">Applied {application.applied_on}</span>}
      </div>
      <label>
        Notes
        <textarea
          rows={3}
          value={notes}
          placeholder="Who you contacted, interview dates, what to prepare…"
          onChange={(e) => setNotes(e.target.value)}
          onBlur={() => notes !== application.notes && update.mutate({ notes })}
        />
      </label>
      <div className="editor-row">
        <span className="hint-inline">
          {update.isPending ? "Saving…" : "Notes save when you click away."}
        </span>
        <button
          type="button"
          className="link-button danger"
          onClick={() => {
            if (window.confirm(`Stop tracking "${application.title}"?`)) remove.mutate();
          }}
        >
          Remove from tracker
        </button>
      </div>
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}
