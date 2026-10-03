import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, toQuery } from "../api/client";
import type { Application } from "../api/types";
import { RedFlags, ScoreBadge } from "../components/JobBadges";
import { JobsPage } from "../pages/JobsPage";
import { TrackerPage } from "../pages/TrackerPage";
import { followUpState, localIsoDate } from "../tracker";
import { renderWithProviders, sampleJob } from "./renderWithProviders";
import { render } from "@testing-library/react";

const application: Application = {
  id: "app-1",
  job_id: "job-1",
  title: "Junior Full Stack Developer",
  company: "Acme",
  url: "https://example.com",
  location: "Pune",
  status: "applied",
  notes: "Applied via careers page",
  applied_on: "2026-10-01",
  follow_up_on: "2026-10-02",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  job_score: 82,
};

describe("followUpState", () => {
  it("classifies reminders relative to today", () => {
    expect(followUpState("2026-10-02", "applied", "2026-10-03")).toBe("overdue");
    expect(followUpState("2026-10-03", "interview", "2026-10-03")).toBe("today");
    expect(followUpState("2026-10-09", "saved", "2026-10-03")).toBe("upcoming");
    expect(followUpState(null, "applied", "2026-10-03")).toBe("none");
  });

  it("ignores reminders on closed applications", () => {
    expect(followUpState("2026-10-01", "rejected", "2026-10-03")).toBe("none");
    expect(followUpState("2026-10-01", "offer", "2026-10-03")).toBe("none");
  });

  it("formats local dates without UTC drift", () => {
    expect(localIsoDate(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
  });
});

describe("toQuery", () => {
  it("drops empty values and encodes the rest", () => {
    expect(toQuery({ q: "react dev", min_score: 60, fresher_only: true, source: "", days: undefined })).toBe(
      "?q=react+dev&min_score=60&fresher_only=true",
    );
    expect(toQuery({ include_filtered: false })).toBe("");
  });
});

describe("job badges", () => {
  it("labels rule-only scores", () => {
    render(<ScoreBadge job={{ score: 55, llm_score: null }} />);
    expect(screen.getByText("rule")).toBeInTheDocument();
  });

  it("frames red flags as heuristics", () => {
    render(<RedFlags flags={["Mentions a fee or deposit"]} />);
    expect(screen.getByText(/heuristics, not a verdict/)).toBeInTheDocument();
    expect(screen.getByText("Mentions a fee or deposit")).toBeInTheDocument();
  });

  it("renders nothing without flags", () => {
    const { container } = render(<RedFlags flags={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("JobsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lists jobs and saves one to the tracker", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValue({ items: [sampleJob], total: 1 });
    vi.spyOn(api, "jobSources").mockResolvedValue([]);
    vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });
    const create = vi.spyOn(api, "createApplication").mockResolvedValue(application);

    renderWithProviders(<JobsPage />);

    expect(await screen.findByText("Junior Full Stack Developer")).toBeInTheDocument();
    expect(screen.getByText("Python + React match, fresher-friendly.")).toBeInTheDocument();
    expect(screen.getByText("fresher-friendly")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ job_id: "job-1" }));
  });

  it("sends filter changes to the API", async () => {
    const list = vi.spyOn(api, "listJobs").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(api, "jobSources").mockResolvedValue([]);
    vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });

    renderWithProviders(<JobsPage />);
    await userEvent.click(await screen.findByLabelText("Fresher-friendly only"));

    await waitFor(() =>
      expect(list).toHaveBeenLastCalledWith(expect.objectContaining({ fresher_only: true, offset: 0 })),
    );
  });
});

describe("TrackerPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows counts, overdue reminders, and updates status", async () => {
    vi.spyOn(api, "listApplications").mockResolvedValue({
      items: [application],
      counts: { applied: 1 },
    });
    const update = vi
      .spyOn(api, "updateApplication")
      .mockResolvedValue({ ...application, status: "interview" });

    renderWithProviders(<TrackerPage />);

    expect(await screen.findByText("Applied (1)")).toBeInTheDocument();
    expect(screen.getByText("All (1)")).toBeInTheDocument();
    expect(screen.getByText("Overdue", { selector: ".follow-up" })).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Status"), "interview");
    await waitFor(() => expect(update).toHaveBeenCalledWith("app-1", { status: "interview" }));
  });

  it("filters by status chip", async () => {
    const list = vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });
    renderWithProviders(<TrackerPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Interview (0)" }));
    await waitFor(() => expect(list).toHaveBeenLastCalledWith({ status: "interview" }));
  });
});
