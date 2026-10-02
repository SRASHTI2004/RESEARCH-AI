import type { ResearchJob } from "../api/types";

function buildMarkdown(job: ResearchJob): string {
  return [`# ${job.company} — Company Research Brief`, "", job.final_report, ""].join("\n");
}

function download(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function exportPdf(job: ResearchJob) {
  // Dynamically imported: jsPDF (plus its html2canvas/purify dependencies)
  // added ~230KB gzipped to the main bundle — not worth paying on every
  // page load just for a feature most visits won't use.
  const { default: jsPDF } = await import("jspdf");

  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const margin = 40;
  const maxWidth = doc.internal.pageSize.getWidth() - margin * 2;
  const pageHeight = doc.internal.pageSize.getHeight();
  const lineHeight = 14;
  let y = margin;

  doc.setFontSize(16);
  doc.text(`${job.company} — Company Research Brief`, margin, y);
  y += lineHeight * 2;

  doc.setFontSize(10);
  const lines: string[] = doc.splitTextToSize(job.final_report, maxWidth);
  for (const line of lines) {
    if (y > pageHeight - margin) {
      doc.addPage();
      y = margin;
    }
    doc.text(line, margin, y);
    y += lineHeight;
  }

  doc.save(`${job.company}-brief.pdf`);
}

export function ExportButtons({ job }: { job: ResearchJob }) {
  return (
    <div className="export-buttons">
      <button type="button" onClick={() => download(`${job.company}-brief.md`, buildMarkdown(job), "text/markdown")}>
        Export Markdown
      </button>
      <button type="button" onClick={() => void exportPdf(job)}>
        Export PDF
      </button>
    </div>
  );
}
