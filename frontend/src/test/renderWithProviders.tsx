import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { JobSummary } from "../api/types";

export function renderWithProviders(ui: ReactElement, { path = "/", route = "/" } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export const sampleJob: JobSummary = {
  id: "job-1",
  title: "Junior Full Stack Developer",
  company: "Acme",
  location: "Pune, India",
  is_remote: false,
  url: "https://boards.greenhouse.io/acme/jobs/1",
  source: "greenhouse",
  official_source: true,
  salary_text: "",
  posted_at: null,
  first_seen_at: "2026-10-03T08:00:00Z",
  passed_prefilter: true,
  prefilter_reason: "preferred city",
  rule_score: 60,
  red_flags: [],
  llm_score: 82,
  llm_reason: "Python + React match, fresher-friendly.",
  fresher_friendly: true,
  score: 82,
};
