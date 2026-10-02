import type { Source } from "../api/types";

export function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return <p>No sources yet.</p>;

  return (
    <ol className="source-list">
      {sources.map((s) => (
        <li key={s.index} id={`source-${s.index}`}>
          <a href={s.url} target="_blank" rel="noreferrer">
            [{s.index}] {s.title}
          </a>
          <p className="source-snippet">{s.snippet}</p>
        </li>
      ))}
    </ol>
  );
}
