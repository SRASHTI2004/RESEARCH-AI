import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Inbox } from "lucide-react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import type { ResearchJob } from "../api/types";
import { EmptyState, ErrorState } from "../components/states";
import { BriefPage } from "../pages/BriefPage";
import { HistoryPage } from "../pages/HistoryPage";
import { JobsPage } from "../pages/JobsPage";
import { TrackerPage } from "../pages/TrackerPage";
import { AuthProvider } from "../auth/AuthContext";
import { LoginPage } from "../pages/LoginPage";
import { useTheme } from "../theme/context";
import { ThemeProvider } from "../theme/ThemeProvider";
import { renderWithProviders } from "./renderWithProviders";

describe("state components", () => {
  it("EmptyState shows its message and action", () => {
    render(
      <EmptyState
        icon={Inbox}
        title="Nothing here"
        description="Add something"
        action={<button>Add</button>}
      />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Add something")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });

  it("ErrorState is announced and retries", async () => {
    const retry = vi.fn();
    render(<ErrorState title="Broke" message="Server down" onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Broke");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });
});

describe("ThemeProvider", () => {
  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  function Toggle() {
    const { resolvedTheme, setTheme } = useTheme();
    return (
      <button onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>{resolvedTheme}</button>
    );
  }

  it("applies and persists the chosen theme", async () => {
    render(
      <ThemeProvider>
        <Toggle />
      </ThemeProvider>,
    );
    expect(screen.getByRole("button")).toHaveTextContent("light");

    await userEvent.click(screen.getByRole("button"));

    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("researchai_theme")).toBe("dark");
  });

  it("restores a saved theme", () => {
    localStorage.setItem("researchai_theme", "dark");
    render(
      <ThemeProvider>
        <Toggle />
      </ThemeProvider>,
    );
    expect(screen.getByRole("button")).toHaveTextContent("dark");
    expect(document.documentElement).toHaveClass("dark");
  });
});

describe("page states", () => {
  afterEach(() => vi.restoreAllMocks());

  it("JobsPage explains how to fetch when nothing was ever fetched", async () => {
    vi.spyOn(api, "listJobs").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(api, "jobSources").mockResolvedValue([]);
    vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });
    renderWithProviders(<JobsPage />);

    expect(await screen.findByText("No jobs fetched yet")).toBeInTheDocument();
    expect(screen.getByText("python -m app.cli fetch")).toBeInTheDocument();
  });

  it("JobsPage offers to reset filters when filters exclude everything", async () => {
    const list = vi.spyOn(api, "listJobs").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(api, "jobSources").mockResolvedValue([
      {
        source: "lever",
        started_at: "2026-10-03T06:00:00Z",
        finished_at: null,
        status: "ok",
        fetched_count: 3,
        new_count: 1,
        message: "",
      },
    ]);
    vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });
    renderWithProviders(<JobsPage />);

    await userEvent.click(await screen.findByLabelText("Fresher-friendly only"));
    await userEvent.click(await screen.findByRole("button", { name: "Reset filters" }));

    await waitFor(() =>
      expect(list).toHaveBeenLastCalledWith(expect.not.objectContaining({ fresher_only: true })),
    );
  });

  it("JobsPage shows an error state that can retry", async () => {
    const list = vi
      .spyOn(api, "listJobs")
      .mockRejectedValueOnce(new ApiError(500, "Internal error"))
      .mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(api, "jobSources").mockResolvedValue([]);
    vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });
    renderWithProviders(<JobsPage />);

    expect(await screen.findByText("Could not load jobs.")).toBeInTheDocument();
    expect(screen.getByText("Internal error")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
  });

  it("TrackerPage has a helpful empty state", async () => {
    vi.spyOn(api, "listApplications").mockResolvedValue({ items: [], counts: {} });
    renderWithProviders(<TrackerPage />);
    expect(await screen.findByText("Your tracker is empty")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse jobs" })).toHaveAttribute("href", "/jobs");
  });

  it("HistoryPage links to starting a brief when empty", async () => {
    vi.spyOn(api, "listResearch").mockResolvedValue([]);
    renderWithProviders(<HistoryPage />);
    expect(await screen.findByText("No research jobs yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Research a company" })).toHaveAttribute("href", "/briefs/new");
  });
});

describe("BriefPage", () => {
  afterEach(() => vi.restoreAllMocks());

  const done: ResearchJob = {
    id: "b-1",
    company: "Acme",
    research: "",
    analysis: "",
    report: "",
    final_report:
      "## Company Overview\n\nAcme builds **developer tools** [1].\n\n## Sources\n\n[1] Acme — https://acme.dev",
    sources: [{ index: 1, title: "Acme homepage", url: "https://acme.dev", snippet: "Tools for devs" }],
    status: "done",
    error: null,
    has_export: false,
    created_at: "2026-10-03T08:00:00Z",
    updated_at: "2026-10-03T08:02:00Z",
  };

  it("renders the final report as Markdown with citation chips and a source list", async () => {
    vi.spyOn(api, "getResearch").mockResolvedValue(done);
    renderWithProviders(<BriefPage />, { path: "/briefs/:id", route: "/briefs/b-1" });

    expect(await screen.findByRole("heading", { name: "Company Overview" })).toBeInTheDocument();
    expect(screen.getByText("developer tools").tagName).toBe("STRONG");
    expect(screen.getByRole("link", { name: "Source 1: Acme homepage" })).toHaveAttribute(
      "href",
      "https://acme.dev",
    );
    // The Writer's own "Sources" block is replaced by the structured list.
    expect(screen.queryByRole("heading", { name: "Sources" })).not.toBeInTheDocument();
    expect(screen.getByText("Acme homepage")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("shows live progress and partial research while running", async () => {
    vi.spyOn(api, "getResearch").mockResolvedValue({
      ...done,
      status: "analyzing",
      research: "- Acme was founded in 2019 [1]",
      final_report: "",
    });
    renderWithProviders(<BriefPage />, { path: "/briefs/:id", route: "/briefs/b-1" });

    expect(await screen.findByText("Research so far")).toBeInTheDocument();
    expect(screen.getByText(/Analyzing/, { selector: "li" })).toHaveClass("active");
    expect(screen.getByText(/Acme was founded in 2019/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Source 1: Acme homepage" })).toBeInTheDocument();
  });
});

describe("LoginPage", () => {
  it("doubles as the landing page and explains the app in one sentence", async () => {
    renderWithProviders(
      <ThemeProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </ThemeProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getAllByText(/ResearchAI finds fresh developer jobs every day/).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create one" })).toHaveAttribute("href", "/register");
  });

  it("offers the demo and hides sign-up on a public deployment", async () => {
    vi.spyOn(api, "publicConfig").mockResolvedValue({
      registration_enabled: false,
      demo_enabled: true,
      llm_actions_left_today: 4,
    });
    const demoLogin = vi.spyOn(api, "demoLogin").mockResolvedValue({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    vi.spyOn(api, "me").mockResolvedValue({
      id: "u1",
      email: "demo@researchai.local",
      role: "user",
      created_at: "2026-10-06T00:00:00Z",
      is_demo: true,
    });
    renderWithProviders(
      <ThemeProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </ThemeProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Try the demo" }));
    expect(demoLogin).toHaveBeenCalledOnce();
    expect(screen.queryByRole("link", { name: "Create one" })).not.toBeInTheDocument();
  });

  it("shows validation errors inline", async () => {
    renderWithProviders(
      <ThemeProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </ThemeProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Enter a valid email")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });
});
