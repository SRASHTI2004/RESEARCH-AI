import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { Application } from "../api/types";
import { ReferralPanel } from "../components/ReferralPanel";
import { renderWithProviders } from "./renderWithProviders";

const kit = {
  search_strings: [
    {
      label: "Alumni of your college at the company",
      query: '"Acme" "My College"',
      where: "LinkedIn people search",
      url: "https://www.linkedin.com/search/results/people/?keywords=%22Acme%22",
    },
  ],
  checklist: ["Confirm the posting is still open."],
  drafts: [{ kind: "referral_ask", title: "Referral ask", body: "Hi [Name], ...", char_count: 15 }],
  notes: ["Nothing is sent for you."],
};

describe("ReferralPanel", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads the kit only when opened and links to LinkedIn's own search", async () => {
    const get = vi.spyOn(api, "getReferralKit").mockResolvedValue(kit);
    renderWithProviders(<ReferralPanel jobId="job-1" />);

    expect(get).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Show referral helper" }));

    expect(await screen.findByText('"Acme" "My College"')).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open search" })).toHaveAttribute(
      "href",
      kit.search_strings[0].url,
    );
    expect(screen.getByText("Hi [Name], ...")).toBeInTheDocument();
  });

  it("copies a draft to the clipboard", async () => {
    vi.spyOn(api, "getReferralKit").mockResolvedValue(kit);
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    renderWithProviders(<ReferralPanel jobId="job-1" />);

    await user.click(screen.getByRole("button", { name: "Show referral helper" }));
    await screen.findByText("Hi [Name], ...");
    await user.click(screen.getAllByRole("button", { name: "Copy" })[1]);

    expect(writeText).toHaveBeenCalledWith("Hi [Name], ...");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });

  it("marks the job as referral asked, creating a tracker entry if needed", async () => {
    vi.spyOn(api, "getReferralKit").mockResolvedValue(kit);
    const create = vi.spyOn(api, "createApplication").mockResolvedValue({} as Application);
    renderWithProviders(<ReferralPanel jobId="job-1" />);

    await userEvent.click(screen.getByRole("button", { name: "Show referral helper" }));
    await userEvent.click(await screen.findByRole("button", { name: "I asked for a referral" }));

    await waitFor(() => expect(create).toHaveBeenCalledWith({ job_id: "job-1", status: "referral_asked" }));
  });
});
