import { ExternalLink } from "lucide-react";
import type { Source } from "../api/types";

function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return <p className="text-sm text-muted-foreground">No sources yet.</p>;

  return (
    <ol className="source-list flex flex-col gap-2">
      {sources.map((s) => (
        <li key={s.index} id={`source-${s.index}`} className="scroll-mt-24">
          <a
            href={s.url}
            target="_blank"
            rel="noreferrer"
            className="group flex gap-3 rounded-lg border bg-card p-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
          >
            <span className="flex h-6 min-w-6 shrink-0 items-center justify-center rounded-md bg-accent px-1 text-xs font-semibold text-accent-foreground tabular-nums">
              {s.index}
            </span>
            <span className="min-w-0 flex-1">
              <span className="line-clamp-2 text-sm font-medium group-hover:text-primary">{s.title}</span>
              <span className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                {hostname(s.url)}
                <ExternalLink
                  className="size-3 opacity-0 transition-opacity group-hover:opacity-100"
                  aria-hidden
                />
              </span>
              {s.snippet && (
                <span className="source-snippet mt-1.5 line-clamp-2 block text-xs leading-relaxed text-muted-foreground">
                  {s.snippet}
                </span>
              )}
            </span>
          </a>
        </li>
      ))}
    </ol>
  );
}
