import type { ApplicationStatus } from "./api/types";

/** Pipeline order — mirrors APPLICATION_STATUSES in app/models/application.py. */
export const STATUSES: ApplicationStatus[] = [
  "saved",
  "applied",
  "referral_asked",
  "interview",
  "rejected",
  "offer",
];

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  referral_asked: "Referral asked",
  interview: "Interview",
  rejected: "Rejected",
  offer: "Offer",
};

const ACTIVE: ApplicationStatus[] = ["saved", "applied", "referral_asked", "interview"];

export type FollowUpState = "none" | "overdue" | "today" | "upcoming";

/** Local-date "YYYY-MM-DD" (not toISOString, which is UTC and can be a day off in IST). */
export function localIsoDate(date: Date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function followUpState(
  followUpOn: string | null,
  status: ApplicationStatus,
  today: string = localIsoDate(),
): FollowUpState {
  if (!followUpOn || !ACTIVE.includes(status)) return "none";
  // ISO dates compare correctly as strings.
  if (followUpOn < today) return "overdue";
  if (followUpOn === today) return "today";
  return "upcoming";
}

export function sourceLabel(source: string): string {
  const names: Record<string, string> = {
    greenhouse: "Greenhouse",
    lever: "Lever",
    ashby: "Ashby",
    remotive: "Remotive",
    remoteok: "Remote OK",
    weworkremotely: "We Work Remotely",
    himalayas: "Himalayas",
    arbeitnow: "Arbeitnow",
    adzuna: "Adzuna",
  };
  return names[source] ?? source;
}
