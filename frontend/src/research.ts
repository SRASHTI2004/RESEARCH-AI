import type { JobStatus } from "./api/types";
import type { BadgeVariant } from "./components/ui/badge";

/** How each research job status is shown as a badge. */
export const RESEARCH_STATUS: Record<JobStatus, { label: string; variant: BadgeVariant }> = {
  pending: { label: "Queued", variant: "secondary" },
  researching: { label: "Researching", variant: "info" },
  analyzing: { label: "Analyzing", variant: "info" },
  writing: { label: "Writing", variant: "info" },
  done: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
};
