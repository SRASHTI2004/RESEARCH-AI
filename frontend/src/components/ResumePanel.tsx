import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Info, Loader2, ShieldCheck, Trash2, TriangleAlert, Wand2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import type { TailoredResume } from "../api/types";
import { cn, errorMessage, formatDateTime } from "../lib/utils";
import { exportFilename } from "../resume";
import { InlineError } from "./states";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Checkbox, Label } from "./ui/label";
import { NativeSelect } from "./ui/select";
import { Skeleton } from "./ui/skeleton";

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
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Changes</h3>
        <Label className="cursor-pointer text-xs font-normal text-muted-foreground">
          <Checkbox checked={changedOnly} onChange={(e) => setChangedOnly(e.target.checked)} />
          Only changed lines ({changed})
        </Label>
      </div>
      {lines.length === 0 ? (
        <p className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
          No changes — your master resume already fits this job.
        </p>
      ) : (
        <pre
          className="resume-diff max-h-[28rem] overflow-auto rounded-lg border bg-muted/40 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap"
          aria-label="Changes against your master resume"
        >
          {lines.map((d, i) => (
            <span
              key={i}
              className={cn(
                "block border-l-2 px-3",
                d.op === "+" && "diff-add border-success bg-success-soft text-success",
                d.op === "-" && "diff-del border-destructive bg-danger-soft text-destructive",
                d.op === " " && "border-transparent text-muted-foreground",
              )}
            >
              {d.op} {d.text}
              {"\n"}
            </span>
          ))}
        </pre>
      )}
    </div>
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
      toast.success("Resume tailored", {
        description: `${created.keywords_matched.length} keywords matched · review the changes below.`,
      });
      void queryClient.invalidateQueries({ queryKey: ["tailored-resumes", jobId] });
    },
    onError: (err) => toast.error(errorMessage(err, "Tailoring failed.")),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteTailoredResume(id),
    onSuccess: () => {
      setSelectedId(null);
      toast.success("Version deleted");
      void queryClient.invalidateQueries({ queryKey: ["tailored-resumes", jobId] });
    },
    onError: (err) => toast.error(errorMessage(err, "Could not delete this version")),
  });

  async function exportAs(item: TailoredResume, format: "pdf" | "docx") {
    setExportError("");
    try {
      downloadBlob(await api.exportTailoredResume(item.id, format), exportFilename(item.company, format));
      toast.success(`${format.toUpperCase()} downloaded`);
    } catch {
      const message = `Could not export ${format.toUpperCase()}.`;
      setExportError(message);
      toast.error(message);
    }
  }

  const item = current.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="flex size-7 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <Wand2 className="size-4" aria-hidden />
          </span>
          Tailored resume
        </CardTitle>
        <CardDescription>
          Reorders and rewords your real experience for this job. Nothing is added: rewrites that introduce
          new numbers, tools or names are rejected and the original kept.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {master.isLoading ? (
          <Skeleton className="h-9 w-40" />
        ) : master.data && !master.data.exists ? (
          <div className="flex gap-3 rounded-lg border border-dashed p-4 text-sm">
            <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
            <div>
              <p className="font-medium">Add your master resume first</p>
              <p className="mt-1 text-muted-foreground">{master.data.message}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => tailor.mutate()} disabled={tailor.isPending || !master.data}>
                {tailor.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Wand2 aria-hidden />}
                {tailor.isPending
                  ? "Tailoring… (up to ~15 s)"
                  : versions.data?.length
                    ? "Tailor again"
                    : "Tailor resume"}
              </Button>
              {versions.data && versions.data.length > 1 && (
                <NativeSelect
                  aria-label="Version"
                  wrapperClassName="w-full sm:w-56"
                  value={currentId ?? ""}
                  onChange={(e) => setSelectedId(e.target.value)}
                >
                  {versions.data.map((v) => (
                    <option key={v.id} value={v.id}>
                      {formatDateTime(v.created_at)}
                    </option>
                  ))}
                </NativeSelect>
              )}
            </div>
            {tailor.error && (
              <InlineError>
                {tailor.error instanceof ApiError ? tailor.error.message : "Tailoring failed."}
              </InlineError>
            )}
          </div>
        )}

        {currentId !== null && current.isLoading && <Skeleton className="h-40 w-full" />}

        {item && (
          <div className="tailored flex flex-col gap-5 border-t pt-5">
            {!item.used_llm && (
              <p className="flex gap-2 rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
                <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
                The AI model was unavailable, so only the keyword-based reordering was applied.
              </p>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
                  <ShieldCheck className="size-4 text-success" aria-hidden /> Keywords matched
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {item.keywords_matched.length ? (
                    item.keywords_matched.map((k) => (
                      <Badge key={k} variant="success">
                        {k}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">—</span>
                  )}
                </div>
              </div>
              {item.keywords_missing.length > 0 && (
                <div>
                  <h3 className="mb-1 text-sm font-semibold">In the posting, not in your resume</h3>
                  <p className="mb-2 text-xs text-muted-foreground">
                    Only add these if you genuinely have them.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {item.keywords_missing.map((k) => (
                      <Badge key={k} variant="outline">
                        {k}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {item.warnings.length > 0 && (
              <details className="warnings group rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-sm">
                <summary className="flex cursor-pointer list-none items-center gap-2 font-medium">
                  <TriangleAlert className="size-4 text-warning" aria-hidden />
                  {item.warnings.length} rewrite(s) rejected — original wording kept
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-6 text-muted-foreground">
                  {item.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </details>
            )}

            <DiffView diff={item.diff} />

            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => void exportAs(item, "pdf")}>
                <Download aria-hidden /> Download PDF
              </Button>
              <Button variant="outline" onClick={() => void exportAs(item, "docx")}>
                <Download aria-hidden /> Download DOCX
              </Button>
              <Button
                variant="ghost-destructive"
                className="sm:ml-auto"
                disabled={remove.isPending}
                onClick={() => remove.mutate(item.id)}
              >
                <Trash2 aria-hidden /> Delete this version
              </Button>
            </div>
            {exportError && <InlineError>{exportError}</InlineError>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
