import { forwardRef, type TextareaHTMLAttributes } from "react";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
}

/** Mesmo visual do `Input` — design-system.md, seção 14 ("Input /
 * Textarea"). */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { hasError = false, className = "", ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      aria-invalid={hasError || undefined}
      className={`w-full rounded-sm border bg-surface-2 px-3 py-2 text-body text-text-primary placeholder:text-text-tertiary transition-colors duration-fast ease-out focus-visible:border-accent disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
        hasError ? "border-negative" : "border-border"
      } ${className}`}
      {...props}
    />
  );
});
