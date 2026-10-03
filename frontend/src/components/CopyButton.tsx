import { useState } from "react";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked (http origin, permissions) — fall back to a prompt to copy manually.
      window.prompt("Copy this text:", text);
    }
  }

  return (
    <button type="button" className="secondary small" onClick={() => void copy()}>
      {copied ? "Copied ✓" : label}
    </button>
  );
}
