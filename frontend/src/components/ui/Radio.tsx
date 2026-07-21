import { forwardRef, type InputHTMLAttributes } from "react";

export interface RadioProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size" | "type"> {}

/** Par de `Checkbox` (design-system.md, seção 14: "Checkbox / Radio" são
 * especificados juntos) — 16px, borda `--color-border-strong`, marcado
 * usa `--color-accent` sólido com um ponto central. CSS puro (sem
 * `motion`): a transição de marcado/desmarcado é instantânea o bastante
 * (`--duration-fast`) para não precisar de física de spring como o check
 * do `Checkbox`. Base de `RadioGroupField`. */
export const Radio = forwardRef<HTMLInputElement, RadioProps>(function Radio(
  { className = "", disabled, ...props },
  ref,
) {
  return (
    <span className={`relative inline-flex h-4 w-4 shrink-0 ${className}`}>
      <input
        ref={ref}
        type="radio"
        disabled={disabled}
        className="peer h-4 w-4 cursor-pointer appearance-none rounded-full border border-border-strong bg-surface-2 transition-colors duration-fast ease-out checked:border-accent disabled:cursor-not-allowed disabled:opacity-50"
        {...props}
      />
      <span className="pointer-events-none absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 scale-0 rounded-full bg-accent transition-transform duration-fast ease-out peer-checked:scale-100" />
    </span>
  );
});
