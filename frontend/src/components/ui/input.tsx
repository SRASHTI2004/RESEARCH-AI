import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { fieldClass } from "./field";

export function Input({ className, type, ...props }: ComponentProps<"input">) {
  return <input type={type} className={cn(fieldClass, className)} {...props} />;
}

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn(fieldClass, "h-auto min-h-20 resize-y py-2", className)} {...props} />;
}
