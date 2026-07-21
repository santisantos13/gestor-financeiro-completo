import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";

export interface SwitchProps {
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
  className?: string;
}

/** Trilho `--color-surface-3`/`--color-accent` quando ligado, thumb desliza
 * com spring `snappy` — design-system.md, seção 14. */
export function Switch({
  checked,
  defaultChecked = false,
  onCheckedChange,
  disabled = false,
  id,
  className = "",
  ...props
}: SwitchProps) {
  const [isOn, setIsOn] = useState(checked ?? defaultChecked);

  useEffect(() => {
    if (checked !== undefined) setIsOn(checked);
  }, [checked]);

  function toggle() {
    if (disabled) return;
    const next = !isOn;
    if (checked === undefined) setIsOn(next);
    onCheckedChange?.(next);
  }

  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={isOn}
      disabled={disabled}
      onClick={toggle}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors duration-fast ease-out disabled:cursor-not-allowed disabled:opacity-50 ${
        isOn ? "bg-accent" : "bg-surface-3"
      } ${className}`}
      {...props}
    >
      <motion.span
        className="h-3.5 w-3.5 rounded-full bg-white shadow-xs"
        animate={{ x: isOn ? 18 : 3 }}
        transition={SPRING.snappy}
      />
    </button>
  );
}
