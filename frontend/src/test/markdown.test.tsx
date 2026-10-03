import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Source } from "../api/types";
import { Markdown } from "../components/Markdown";
import { linkCitations, stripSourcesSection } from "../markdown";

const sources: Source[] = [
  { index: 1, title: "Acme raises Series B", url: "https://news.example.com/acme", snippet: "" },
  { index: 2, title: "Acme engineering blog", url: "https://acme.dev/blog", snippet: "" },
  { index: 3, title: "Acme careers", url: "https://acme.dev/careers", snippet: "" },
];

describe("linkCitations", () => {
  it("turns single, grouped and ranged citations into cite links", () => {
    expect(linkCitations("Founded 2019 [1].")).toBe("Founded 2019 [1](#cite-1).");
    expect(linkCitations("Uses Go [1, 2]")).toBe("Uses Go [1](#cite-1)[2](#cite-2)");
    expect(linkCitations("Big [1-3]")).toBe("Big [1](#cite-1)[2](#cite-2)[3](#cite-3)");
    expect(linkCitations("Twice [1][2]")).toBe("Twice [1](#cite-1)[2](#cite-2)");
  });

  it("leaves existing links and code alone", () => {
    expect(linkCitations("[1](https://x.y)")).toBe("[1](https://x.y)");
    expect(linkCitations("`arr[0]` and `x[1]`")).toBe("`arr[0]` and `x[1]`");
    expect(linkCitations("```\nlist[2]\n```")).toBe("```\nlist[2]\n```");
  });
});

describe("stripSourcesSection", () => {
  it("drops a trailing Sources section", () => {
    const md = "## Overview\nAcme [1].\n\n## Sources\n[1] Acme — https://acme.dev";
    expect(stripSourcesSection(md)).toBe("## Overview\nAcme [1].");
  });

  it("handles numbered and bold headings", () => {
    expect(stripSourcesSection("Body\n\n6. **Sources**\n[1] x")).toBe("Body");
  });

  it("keeps a Sources heading that is followed by more sections", () => {
    const md = "## Sources\nWhere data came from\n\n## Overview\nText";
    expect(stripSourcesSection(md)).toBe(md);
  });

  it("returns text without a Sources heading unchanged", () => {
    expect(stripSourcesSection("Just text [1]")).toBe("Just text [1]");
  });
});

describe("<Markdown>", () => {
  it("renders headings, lists, bold and links instead of raw symbols", () => {
    render(<Markdown>{"## Overview\n\n- **Founded** in 2019\n- See [the site](https://acme.dev)"}</Markdown>);
    expect(screen.getByRole("heading", { level: 2, name: "Overview" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Founded").tagName).toBe("STRONG");
    const link = screen.getByRole("link", { name: "the site" });
    expect(link).toHaveAttribute("href", "https://acme.dev");
    expect(link).toHaveAttribute("target", "_blank");
    expect(document.body.textContent).not.toMatch(/##|\*\*/);
  });

  it("renders citations as chips that open the source", () => {
    render(<Markdown sources={sources}>{"Acme raised money [1] and blogs about Go [2, 3]."}</Markdown>);
    const chip = screen.getByRole("link", { name: "Source 1: Acme raises Series B" });
    expect(chip).toHaveAttribute("href", "https://news.example.com/acme");
    expect(chip).toHaveClass("citation-chip");
    expect(chip).toHaveTextContent("1");
    expect(screen.getByRole("link", { name: /Source 3/ })).toHaveAttribute(
      "href",
      "https://acme.dev/careers",
    );
    expect(document.body.textContent).not.toContain("[1]");
  });

  it("shows an unknown citation number as an inert chip", () => {
    render(<Markdown sources={sources}>{"Unverified claim [9]."}</Markdown>);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("9")).toHaveClass("citation-chip");
  });

  it("never renders raw HTML from model output", () => {
    const { container } = render(<Markdown>{'Hello <img src=x onerror="alert(1)"> world'}</Markdown>);
    expect(container.querySelector("img")).toBeNull();
  });

  it("renders inline without a paragraph wrapper", () => {
    const { container } = render(<Markdown inline>{"Strong **React** match"}</Markdown>);
    expect(container.querySelector("p")).toBeNull();
    expect(screen.getByText("React").tagName).toBe("STRONG");
  });
});
