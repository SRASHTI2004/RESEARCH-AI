import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProgressStages } from "../components/ProgressStages";

describe("ProgressStages", () => {
  it("shows the failed message when status is failed", () => {
    render(<ProgressStages status="failed" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Failed");
  });

  it("marks the current stage active and earlier stages complete", () => {
    render(<ProgressStages status="writing" />);

    expect(screen.getByText(/Researching/)).toHaveClass("complete");
    expect(screen.getByText(/Analyzing/)).toHaveClass("complete");
    expect(screen.getByText(/Writing/)).toHaveClass("active");
    expect(screen.getByText(/Done/)).toHaveClass("pending");
  });

  it("marks every stage complete once status is done", () => {
    render(<ProgressStages status="done" />);

    for (const label of ["Researching", "Analyzing", "Writing", "Done"]) {
      expect(screen.getByText(new RegExp(label))).toHaveClass("complete");
    }
  });
});
