import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { TailoredResume } from "../api/types";
import { exportFilename } from "../resume";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function DiffView({ diff }: { diff: TailoredResume["diff"] }) {
  const [changedOnly, setChangedOnly] = useState(true);
  const changed = diff.filter((d) => d.op !== " ").length;
  const lines = changedOnly ? diff.filter((d) => d.op !== " ") : diff;
  return (
    <>
      <label className="checkbox">
        <input type="checkbox" checked={changedOnly} onChange={(e) => setChangedOnly(e.target.checked)} />{" "}
        Only changed lines ({changed})
      </label>
      {lines.length === 0 ? (
        <p className="hint-inline">No changes — your master resume already fits this job.</p>
      ) : (
        <pre className="resume-diff" aria-label="Changes against your master resume">
          {lines.map((d, i) => (
            <span key={i} className={d.op === "+" ? "diff-add" : d.op === "-" ? "diff-del" : undefined}>
              {d.op} {d.text}
              {"\n"}
            </span>
          ))}
        </pre>
      )}
    </>
  );
}

export function ResumePanel({ jobId }: { jobId: string }) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [exportError, setExportError] = useState("");

  const master = useQuery({ queryKey: ["resume-master"], queryFn: () => api.masterResumeStatus() });
  const versions = useQuery({
    queryKey: ["tailored-resumes", jobId],
    queryFn: () => api.listTailoredResumes(jobId),
  });
  const currentId = selectedId ?? versions.data?.[0]?.id ?? null;
  const current = useQuery({
    queryKey: ["tailored-resume", currentId],
    queryFn: () => api.getTailoredResume(currentId!),
    enabled: currentId !== null,
  });

  const tailor = useMutation({
    mutationFn: () => api.tailorResume(jobId),
    onSuccess: (created) => {
      queryClient.setQueryData(["tailored-resume", created.id], created);
      setSelectedId(created.id);
      void queryClient.invalidateQueries({ queryKey: ["tailored-resumes", jobId] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteTailoredResume(id),
    onSuccess: () => {
      setSelectedId(null);
      void queryClient.invalidateQueries({ queryKey: ["tailored-resumes", jobId] });
    },
  });

  async function exportAs(item: TailoredResume, format: "pdf" | "docx") {
    setExportError("");
    try {
      downloadBlob(await api.exportTailoredResume(item.id, format), exportFilename(item.company, format));
    } catch {
      setExportError(`Could not export ${format.toUpperCase()}.`);
    }
  }

  const item = current.data;

  return (
    <section className="panel">
      <h2>Tailored resume</h2>
      {master.data && !master.data.exists ? (
        <p className="hint">{master.data.message}</p>
      ) : (
        <>
          <p className="hint-inline">
            Reorders and rewords your real experience for this job. Nothing is added: rewrites that introduce
            new numbers, tools or names are rejected and the original kept.
          </p>
          <div className="export-buttons">
            <button type="button" onClick={() => tailor.mutate()} disabled={tailor.isPending || !master.data}>
              {tailor.isPending
                ? "Tailoring… (up to ~15 s)"
                : versions.data?.length
                  ? "Tailor again"
                  : "Tailor resume"}
            </button>
            {versions.data && versions.data.length > 1 && (
              <select
                aria-label="Version"
                value={currentId ?? ""}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {versions.data.map((v) => (
                  <option key={v.id} value={v.id}>
                    {new Date(v.created_at).toLocaleString()}
                  </option>
                ))}
              </select>
            )}
          </div>
          {tailor.error && (
            <p className="field-error">
              {tailor.error instanceof ApiError ? tailor.error.message : "Tailoring failed."}
            </p>
          )}
        </>
      )}

      {item && (
        <div className="tailored">
          {!item.used_llm && (
            <p className="hint">
              The AI model was unavailable, so only the keyword-based reordering was applied.
            </p>
          )}
          {item.warnings.length > 0 && (
            <details className="warnings">
              <summary>{item.warnings.length} rewrite(s) rejected — original wording kept</summary>
              <ul>
                {item.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </details>
          )}
          <p>
            <strong>Keywords matched:</strong> {item.keywords_matched.join(", ") || "—"}
          </p>
          {item.keywords_missing.length > 0 && (
            <p className="hint-inline">
              In the posting but not in your resume (only add these if you genuinely have them):{" "}
              {item.keywords_missing.join(", ")}
            </p>
          )}

          <DiffView diff={item.diff} />

          <div className="export-buttons">
            <button type="button" onClick={() => void exportAs(item, "pdf")}>
              Download PDF
            </button>
            <button type="button" className="secondary" onClick={() => void exportAs(item, "docx")}>
              Download DOCX
            </button>
            <button
              type="button"
              className="link-button danger"
              disabled={remove.isPending}
              onClick={() => remove.mutate(item.id)}
            >
              Delete this version
            </button>
          </div>
          {exportError && <p className="field-error">{exportError}</p>}
        </div>
      )}
    </section>
  );
}
