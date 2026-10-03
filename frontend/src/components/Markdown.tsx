import { useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import type { Source } from "@/api/types";
import { cn } from "@/lib/utils";
import { linkCitations } from "@/markdown";

function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function CitationChip({ index, source }: { index: number; source?: Source }) {
  const base =
    "citation-chip mx-0.5 inline-flex h-[1.35em] min-w-[1.35em] -translate-y-px items-center justify-center rounded-md px-1 align-middle text-[0.7rem] leading-none font-semibold no-underline tabular-nums transition-colors";
  if (!source) {
    return (
      <span
        className={cn(base, "bg-muted text-muted-foreground")}
        title="No matching source — the reviewer flags these"
      >
        {index}
      </span>
    );
  }
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      title={`${source.title} — ${hostname(source.url)}`}
      aria-label={`Source ${index}: ${source.title}`}
      className={cn(base, "bg-accent text-accent-foreground hover:bg-primary hover:text-primary-foreground")}
    >
      {index}
    </a>
  );
}

interface MarkdownProps {
  children: string;
  /** When given, `[n]` citations render as chips linking to these sources. */
  sources?: Source[];
  /** Treat single newlines as line breaks (for plain text such as job descriptions). */
  breaks?: boolean;
  /** Render inline (no paragraph wrapper, no prose spacing) — for one-liners. */
  inline?: boolean;
  className?: string;
}

/**
 * Renders LLM output as real Markdown. Raw HTML is never rendered
 * (react-markdown escapes it), so model output can't inject markup.
 */
export function Markdown({ children, sources, breaks, inline, className }: MarkdownProps) {
  const text = sources ? linkCitations(children) : children;

  const components = useMemo<Components>(() => {
    const byIndex = new Map(sources?.map((s) => [s.index, s]));
    return {
      a: ({ href = "", children: label }) => {
        const cite = /^#cite-(\d+)$/.exec(href);
        if (cite) {
          // not-prose: keep the typography plugin's link styles off the chip.
          return (
            <span className="not-prose">
              <CitationChip index={Number(cite[1])} source={byIndex.get(Number(cite[1]))} />
            </span>
          );
        }
        const external = /^https?:/i.test(href);
        return (
          <a href={href} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
            {label}
          </a>
        );
      },
      table: ({ children: rows }) => (
        <div className="overflow-x-auto">
          <table>{rows}</table>
        </div>
      ),
      ...(inline ? { p: ({ children: content }) => <>{content}</> } : {}),
    };
  }, [sources, inline]);

  const plugins = breaks ? [remarkGfm, remarkBreaks] : [remarkGfm];

  if (inline) {
    return (
      <span className={cn("[&_a]:text-primary [&_a]:underline-offset-2 [&_a:hover]:underline", className)}>
        <ReactMarkdown remarkPlugins={plugins} components={components}>
          {text}
        </ReactMarkdown>
      </span>
    );
  }

  return (
    <div
      className={cn(
        "prose prose-sm max-w-none text-foreground sm:prose-base dark:prose-invert",
        "prose-headings:scroll-mt-20 prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-foreground",
        "prose-h1:text-2xl prose-h2:mt-8 prose-h2:border-b prose-h2:pb-2 prose-h2:text-xl prose-h3:text-lg",
        "prose-p:leading-relaxed prose-li:my-1 prose-strong:text-foreground",
        "prose-a:font-medium prose-a:text-primary prose-a:no-underline hover:prose-a:underline",
        "prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-normal prose-code:before:content-none prose-code:after:content-none",
        "prose-pre:bg-muted prose-pre:text-foreground prose-blockquote:border-l-primary/40 prose-hr:border-border",
        "prose-th:text-left [&>:first-child]:mt-0",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={plugins} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
