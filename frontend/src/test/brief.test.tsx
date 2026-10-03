import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { ResearchJob } from "../api/types";
import { BriefPanel } from "../components/BriefPanel";
import { renderWithProviders } from "./renderWithProviders";

const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  useNavigate: () => navigate,
}));

describe("BriefPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    navigate.mockReset();
  });

  it("generates a brief for the job's company and opens it", async () => {
    vi.spyOn(api, "getJobBrief").mockResolvedValue(null);
    const gen = vi.spyOn(api, "generateJobBrief").mockResolvedValue({ id: "b-1" } as ResearchJob);
    renderWithProviders(<BriefPanel jobId="job-1" company="Acme" />);

    await userEvent.click(await screen.findByRole("button", { name: "Generate company brief" }));

    expect(gen).toHaveBeenCalledWith("job-1");
    expect(navigate).toHaveBeenCalledWith("/briefs/b-1");
  });

  it("links to an existing brief instead of regenerating by default", async () => {
    vi.spyOn(api, "getJobBrief").mockResolvedValue({
      id: "b-9",
      company: "Acme",
      status: "done",
      created_at: "2026-10-01T10:00:00Z",
    });
    renderWithProviders(<BriefPanel jobId="job-1" company="Acme" />);

    expect(await screen.findByRole("link", { name: /View company brief/ })).toHaveAttribute(
      "href",
      "/briefs/b-9",
    );
    expect(screen.getByRole("button", { name: "Regenerate" })).toBeInTheDocument();
  });
});
