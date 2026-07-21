export interface DividerProps {
  orientation?: "horizontal" | "vertical";
  className?: string;
}

/** 1px, `--color-border-subtle` — design-system.md, seção 14. */
export function Divider({ orientation = "horizontal", className = "" }: DividerProps) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={
        orientation === "horizontal"
          ? `h-px w-full bg-border-subtle ${className}`
          : `h-full w-px bg-border-subtle ${className}`
      }
    />
  );
}
