import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "./ui/button";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success("Copied to clipboard");
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked (http origin, permissions) — fall back to a prompt to copy manually.
      window.prompt("Copy this text:", text);
    }
  }

  return (
    <Button variant="outline" size="sm" onClick={() => void copy()}>
      {copied ? <Check aria-hidden className="text-success" /> : <Copy aria-hidden />}
      {copied ? "Copied" : label}
    </Button>
  );
}
