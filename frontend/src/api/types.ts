// Mirrors app/schemas/research.py and app/schemas/auth.py — keep in sync by hand
// (see docs/DECISIONS.md Phase 6 for why this isn't codegen'd from OpenAPI).

export type JobStatus = "pending" | "researching" | "analyzing" | "writing" | "done" | "failed";

export interface Source {
  index: number;
  title: string;
  url: string;
  snippet: string;
}

export interface ResearchJob {
  id: string;
  company: string;
  research: string;
  analysis: string;
  report: string;
  final_report: string;
  sources: Source[];
  status: JobStatus;
  error: string | null;
  has_export: boolean;
  created_at: string;
  updated_at: string;
}

export interface ResearchSummary {
  id: string;
  company: string;
  status: JobStatus;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// --- Job Search Assistant (mirrors app/schemas/job.py, application.py) ---

export interface JobSummary {
  id: string;
  title: string;
  company: string;
  location: string;
  is_remote: boolean;
  url: string;
  source: string;
  official_source: boolean;
  salary_text: string;
  posted_at: string | null;
  first_seen_at: string;
  passed_prefilter: boolean;
  prefilter_reason: string;
  rule_score: number;
  red_flags: string[];
  llm_score: number | null;
  llm_reason: string | null;
  fresher_friendly: boolean | null;
  /** llm_score when present, else rule_score */
  score: number;
}

export interface JobDetail extends JobSummary {
  description: string;
  employment_type: string;
  tags: string[];
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  last_seen_at: string;
}

export interface JobList {
  items: JobSummary[];
  total: number;
}

export interface JobFilters {
  q?: string;
  min_score?: number;
  source?: string;
  fresher_only?: boolean;
  include_filtered?: boolean;
  days?: number;
  limit?: number;
  offset?: number;
}

export interface SourceRun {
  source: string;
  started_at: string;
  finished_at: string | null;
  status: "ok" | "error" | "skipped";
  fetched_count: number;
  new_count: number;
  message: string;
}

export type ApplicationStatus = "saved" | "applied" | "referral_asked" | "interview" | "rejected" | "offer";

export interface Application {
  id: string;
  job_id: string | null;
  title: string;
  company: string;
  url: string;
  location: string;
  status: ApplicationStatus;
  notes: string;
  applied_on: string | null;
  follow_up_on: string | null;
  created_at: string;
  updated_at: string;
  job_score: number | null;
}

export interface ApplicationList {
  items: Application[];
  counts: Partial<Record<ApplicationStatus, number>>;
}

export interface ApplicationCreate {
  job_id?: string;
  title?: string;
  company?: string;
  url?: string;
  location?: string;
  status?: ApplicationStatus;
  notes?: string;
  follow_up_on?: string | null;
}

export interface ApplicationUpdate {
  status?: ApplicationStatus;
  notes?: string;
  follow_up_on?: string | null;
  applied_on?: string | null;
}

export interface ApplicationFilters {
  status?: ApplicationStatus;
  q?: string;
  due?: "overdue" | "today" | "week";
}

export interface ReferralKit {
  search_strings: { label: string; query: string; where: string; url: string }[];
  checklist: string[];
  drafts: { kind: string; title: string; body: string; char_count: number }[];
  notes: string[];
}

export interface MasterResumeStatus {
  exists: boolean;
  message: string;
  name: string;
  experience: number;
  projects: number;
  skills: number;
}

export interface TailoredResumeSummary {
  id: string;
  job_id: string | null;
  job_title: string;
  company: string;
  used_llm: boolean;
  created_at: string;
}

export interface TailoredResume extends TailoredResumeSummary {
  /** Structured resume (mirrors app/core/resume.py); only exported, never edited here. */
  content: unknown;
  diff: { op: " " | "-" | "+"; text: string }[];
  warnings: string[];
  keywords_matched: string[];
  keywords_missing: string[];
}
