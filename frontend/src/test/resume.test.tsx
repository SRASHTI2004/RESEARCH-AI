import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { TailoredResume } from "../api/types";
import { ResumePanel } from "../components/ResumePanel";
import { exportFilename } from "../resume";
import { renderWithProviders } from "./renderWithProviders";

const master = { exists: true, message: "", name: "Test User", experience: 1, projects: 2, skills: 8 };

const tailored: TailoredResume = {
  id: "r-1",
  job_id: "job-1",
  job_title: "Junior Developer",
  company: "Acme Corp.",
  used_llm: true,
  created_at: "2026-10-03T10:00:00Z",
  content: {},
  diff: [
    { op: " ", text: "Test User" },
    { op: "-", text: "Built a dashboard" },
    { op: "+", text: "Built a React dashboard" },
  ],
  warnings: ["Kept original: rewrite added a number (40%)"],
  keywords_matched: ["React", "Python"],
  keywords_missing: ["Kubernetes"],
};

describe("ResumePanel", () => {
  afterEach(() => vi.restoreAllMocks());

  it("explains how to add a master resume when none exists", async () => {
    vi.spyOn(api, "masterResumeStatus").mockResolvedValue({
      ...master,
      exists: false,
      message: "No master resume at data/private/master_resume.yaml.",
    });
    vi.spyOn(api, "listTailoredResumes").mockResolvedValue([]);
    renderWithProviders(<ResumePanel jobId="job-1" />);

    expect(await screen.findByText(/No master resume/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tailor resume" })).not.toBeInTheDocument();
  });

  it("tailors, shows only changed lines, rejected rewrites and keywords", async () => {
    vi.spyOn(api, "masterResumeStatus").mockResolvedValue(master);
    vi.spyOn(api, "listTailoredResumes").mockResolvedValue([]);
    const tailor = vi.spyOn(api, "tailorResume").mockResolvedValue(tailored);
    renderWithProviders(<ResumePanel jobId="job-1" />);

    await userEvent.click(await screen.findByRole("button", { name: "Tailor resume" }));

    expect(tailor).toHaveBeenCalledWith("job-1");
    expect(await screen.findByText(/\+ Built a React dashboard/)).toBeInTheDocument();
    expect(screen.getByText(/- Built a dashboard/)).toBeInTheDocument();
    expect(screen.queryByText(/Test User/)).not.toBeInTheDocument(); // unchanged line hidden
    expect(screen.getByText("1 rewrite(s) rejected — original wording kept")).toBeInTheDocument();
    expect(screen.getByText(/Kubernetes/)).toBeInTheDocument();
  });

  it("downloads the PDF through the authenticated client", async () => {
    vi.spyOn(api, "masterResumeStatus").mockResolvedValue(master);
    vi.spyOn(api, "listTailoredResumes").mockResolvedValue([tailored]);
    vi.spyOn(api, "getTailoredResume").mockResolvedValue(tailored);
    const exp = vi.spyOn(api, "exportTailoredResume").mockResolvedValue(new Blob(["%PDF"]));
    URL.createObjectURL = vi.fn(() => "blob:x");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderWithProviders(<ResumePanel jobId="job-1" />);

    await userEvent.click(await screen.findByRole("button", { name: "Download PDF" }));

    expect(exp).toHaveBeenCalledWith("r-1", "pdf");
    expect(click).toHaveBeenCalled();
  });

  it("builds a safe filename", () => {
    expect(exportFilename("Acme Corp.", "docx")).toBe("Acme_Corp_resume.docx");
  });
});
