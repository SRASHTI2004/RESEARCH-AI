import { ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { fieldClass } from "./field";

/**
 * A styled native <select>. Native keeps keyboard/mobile behaviour and
 * accessibility for free (and stays testable with userEvent.selectOptions).
 */
export function NativeSelect({
  className,
  wrapperClassName,
  ...props
}: ComponentProps<"select"> & { wrapperClassName?: string }) {
  return (
    <div className={cn("relative", wrapperClassName)}>
      <select className={cn(fieldClass, "cursor-pointer appearance-none pr-8", className)} {...props} />
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground"
      />
    </div>
  );
}
