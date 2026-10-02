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
