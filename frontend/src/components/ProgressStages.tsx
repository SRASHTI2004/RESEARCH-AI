import type { JobStatus } from "../api/types";

const STAGES: { key: JobStatus; label: string }[] = [
  { key: "researching", label: "Researching" },
  { key: "analyzing", label: "Analyzing" },
  { key: "writing", label: "Writing" },
  { key: "done", label: "Done" },
];

const ORDER: JobStatus[] = ["pending", "researching", "analyzing", "writing", "done"];

export function ProgressStages({ status }: { status: JobStatus }) {
  if (status === "failed") {
    return (
      <p role="alert" className="stage-failed">
        Failed
      </p>
    );
  }

  const currentIndex = ORDER.indexOf(status);

  return (
    <ol className="progress-stages">
      {STAGES.map((stage) => {
        const stageIndex = ORDER.indexOf(stage.key);
        const isComplete = status === "done" || stageIndex < currentIndex;
        // Once the whole job is done, nothing is "in progress" anymore —
        // the final stage should read as complete, not active.
        const isActive = status !== "done" && stage.key === status;
        const className = isActive ? "stage active" : isComplete ? "stage complete" : "stage pending";
        return (
          <li key={stage.key} className={className}>
            {isComplete ? "✓ " : isActive ? "… " : ""}
            {stage.label}
          </li>
        );
      })}
    </ol>
  );
}
