import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { ExportButtons } from "../components/ExportButtons";
import type { ResearchJob } from "../api/types";

const baseJob: ResearchJob = {
  id: "job-1",
  company: "Acme Corp",
  research: "r",
  analysis: "a",
  report: "rep",
  final_report: "final report text",
  sources: [],
  status: "done",
  error: null,
  has_export: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("ExportButtons", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not show a server download button when has_export is false", () => {
    render(<ExportButtons job={baseJob} />);
    expect(screen.queryByText("Download server copy")).not.toBeInTheDocument();
  });

  it("fetches and opens the presigned URL when the server copy button is clicked", async () => {
    vi.spyOn(api, "getExportUrl").mockResolvedValue({ url: "https://storage.example.com/signed" });
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<ExportButtons job={{ ...baseJob, has_export: true }} />);

    await userEvent.click(screen.getByText("Download server copy"));

    expect(api.getExportUrl).toHaveBeenCalledWith("job-1");
    expect(openSpy).toHaveBeenCalledWith(
      "https://storage.example.com/signed",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("shows an error message if fetching the server copy fails", async () => {
    vi.spyOn(api, "getExportUrl").mockRejectedValue(new Error("network down"));

    render(<ExportButtons job={{ ...baseJob, has_export: true }} />);
    await userEvent.click(screen.getByText("Download server copy"));

    expect(await screen.findByText("Could not reach the server copy")).toBeInTheDocument();
  });
});
