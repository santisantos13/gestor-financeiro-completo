import { forwardRef, useEffect, useState, type InputHTMLAttributes } from "react";
import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {}

/**
 * 16px, borda `--color-border-strong`; marcado usa `--color-accent` sólido
 * com o check desenhado via `pathLength` (spring `snappy`) —
 * design-system.md, seção 14. Mesmo path do ícone `Check` do
 * `lucide-react`, para ficar visualmente idêntico ao resto do set.
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className = "", checked, defaultChecked, onChange, disabled, ...props },
  ref,
) {
  const [isChecked, setIsChecked] = useState(checked ?? defaultChecked ?? false);

  // Sincroniza com uso controlado (checked passado explicitamente).
  useEffect(() => {
    if (checked !== undefined) setIsChecked(checked);
  }, [checked]);

  return (
    <span className={`relative inline-flex h-4 w-4 shrink-0 ${className}`}>
      <input
        ref={ref}
        type="checkbox"
        checked={checked}
        defaultChecked={defaultChecked}
        disabled={disabled}
        onChange={(event) => {
          if (checked === undefined) setIsChecked(event.target.checked);
          onChange?.(event);
        }}
        className="peer absolute inset-0 h-4 w-4 cursor-pointer appearance-none rounded-xs border border-border-strong bg-surface-2 transition-colors duration-fast ease-out checked:border-accent checked:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
        {...props}
      />
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="white"
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="pointer-events-none absolute inset-0 h-4 w-4 p-[2px]"
        aria-hidden="true"
      >
        <motion.path
          d="M20 6 9 17l-5-5"
          initial={false}
          animate={{ pathLength: isChecked ? 1 : 0, opacity: isChecked ? 1 : 0 }}
          transition={SPRING.snappy}
        />
      </svg>
    </span>
  );
});
