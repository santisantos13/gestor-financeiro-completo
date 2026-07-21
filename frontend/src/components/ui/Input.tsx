import { forwardRef, type InputHTMLAttributes } from "react";
import { AlertCircle } from "lucide-react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
}

/**
 * Input base do Design System — design-system.md, seção 14. `forwardRef`
 * é obrigatório (react-hook-form `register()` precisa de um ref nativo).
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { hasError = false, className = "", ...props },
  ref,
) {
  return (
    <div className="relative">
      <input
        ref={ref}
        aria-invalid={hasError || undefined}
        className={`h-9 w-full rounded-sm border bg-surface-2 px-3 text-body text-text-primary placeholder:text-text-tertiary transition-colors duration-fast ease-out focus-visible:border-accent disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
          hasError ? "border-negative pr-9" : "border-border"
        } ${className}`}
        {...props}
      />
      {hasError && (
        <AlertCircle
          size={16}
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-negative"
          aria-hidden="true"
        />
      )}
    </div>
  );
});
