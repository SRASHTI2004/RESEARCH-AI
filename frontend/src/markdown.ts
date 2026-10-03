/**
 * Text transforms applied to LLM output before it is rendered as Markdown.
 * Kept separate from the component so they are easy to unit test.
 */

const FENCE = /(```[\s\S]*?```|`[^`\n]*`)/g;
// [1], [1, 2], [1-3] — but not a Markdown link's text ("[1](…)").
const CITATION = /\[(\d{1,3}(?:\s*[,–-]\s*\d{1,3})*)\](?!\()/g;

function expand(group: string): number[] {
  const numbers: number[] = [];
  for (const part of group.split(",")) {
    const [start, end] = part.split(/[–-]/).map((n) => Number(n.trim()));
    if (end !== undefined && end >= start && end - start < 50) {
      for (let n = start; n <= end; n++) numbers.push(n);
    } else {
      numbers.push(start);
    }
  }
  return numbers;
}

/**
 * Rewrite numbered citations as links to `#cite-n`, which the Markdown
 * renderer turns into source chips. Code spans and fences are left alone.
 */
export function linkCitations(markdown: string): string {
  return markdown
    .split(FENCE)
    .map((chunk, i) =>
      i % 2 === 1
        ? chunk
        : chunk.replace(CITATION, (_, group: string) =>
            expand(group)
              .map((n) => `[${n}](#cite-${n})`)
              .join(""),
          ),
    )
    .join("");
}

const SOURCES_PATTERN = String.raw`^[ \t]*(?:#{1,6}[ \t]*)?(?:\d+[.)][ \t]*)?(?:\*\*)?Sources(?:\*\*)?:?[ \t]*$`;
const SOURCES_HEADING = new RegExp(SOURCES_PATTERN, "gim");
const SOURCES_LINE = new RegExp(SOURCES_PATTERN, "im");

/**
 * The Writer appends its own "Sources" list to the report. When the page
 * already shows the structured source list, drop the duplicate from the end.
 */
export function stripSourcesSection(markdown: string): string {
  let last = -1;
  for (const match of markdown.matchAll(SOURCES_HEADING)) last = match.index;
  if (last < 0) return markdown;
  // Only strip the final section: if another heading follows, "Sources" is
  // part of the content rather than the bibliography.
  if (/^#{1,6}\s/m.test(markdown.slice(last).replace(SOURCES_LINE, ""))) return markdown;
  return markdown.slice(0, last).trimEnd();
}
