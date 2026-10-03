/** Download name for an exported tailored resume, e.g. "Acme_Corp_resume.pdf". */
export function exportFilename(company: string, format: "pdf" | "docx"): string {
  const safe = company.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "") || "job";
  return `${safe}_resume.${format}`;
}
