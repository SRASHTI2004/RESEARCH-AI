import { Check, Loader2, XCircle } from "lucide-react";
import type { JobStatus } from "../api/types";
import { cn } from "../lib/utils";

const STAGES: { key: JobStatus; label: string; hint: string }[] = [
  { key: "researching", label: "Researching", hint: "Searching the web, taking cited notes" },
  { key: "analyzing", label: "Analyzing", hint: "Organizing into sections" },
  { key: "writing", label: "Writing", hint: "Drafting the brief, then a citation review" },
  { key: "done", label: "Done", hint: "Brief ready" },
];

const ORDER: JobStatus[] = ["pending", "researching", "analyzing", "writing", "done"];

export function ProgressStages({ status, error }: { status: JobStatus; error?: string | null }) {
  if (status === "failed") {
    return (
      <div
        role="alert"
        className="stage-failed flex items-start gap-3 rounded-xl border border-destructive/30 bg-danger-soft p-4"
      >
        <XCircle className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden />
        <div>
          <p className="font-semibold text-destructive">Failed</p>
          {error && <p className="mt-0.5 text-sm text-muted-foreground">{error}</p>}
        </div>
      </div>
    );
  }

  const currentIndex = ORDER.indexOf(status);

  return (
    <ol className="progress-stages grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Research progress">
      {STAGES.map((stage) => {
        const stageIndex = ORDER.indexOf(stage.key);
        const isComplete = status === "done" || stageIndex < currentIndex;
        // Once the whole job is done, nothing is "in progress" anymore —
        // the final stage should read as complete, not active.
        const isActive = status !== "done" && stage.key === status;
        const state = isActive ? "active" : isComplete ? "complete" : "pending";
        return (
          <li
            key={stage.key}
            aria-current={isActive ? "step" : undefined}
            className={cn(
              `stage ${state}`,
              "relative flex items-center gap-2.5 overflow-hidden rounded-lg border bg-card px-3 py-2.5 text-sm font-medium",
              isActive && "border-primary/40 text-foreground ring-2 ring-primary/15",
              isComplete && "text-foreground",
              state === "pending" && "text-muted-foreground",
            )}
            title={stage.hint}
          >
            <span
              aria-hidden
              className={cn(
                "flex size-6 shrink-0 items-center justify-center rounded-full text-xs",
                isComplete && "bg-success text-white dark:text-background",
                isActive && "bg-primary/10 text-primary",
                state === "pending" && "border border-dashed border-muted-foreground/40",
              )}
            >
              {isComplete ? (
                <Check className="size-3.5" strokeWidth={3} />
              ) : isActive ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : null}
            </span>
            {stage.label}
            {isActive && (
              <span aria-hidden className="absolute inset-x-0 bottom-0 h-0.5 animate-pulse bg-primary/60" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
