import { useId, type ComponentProps, type ReactNode } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Label + input + error message, wired together for screen readers. */
export function FormField({
  label,
  error,
  hint,
  ...inputProps
}: ComponentProps<"input"> & { label: string; error?: string; hint?: ReactNode }) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...inputProps}
      />
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && (
        <p id={errorId} className="field-error text-xs font-medium text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
