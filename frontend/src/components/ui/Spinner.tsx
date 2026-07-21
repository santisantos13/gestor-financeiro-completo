export interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  /** Cor do traço — `onAccent` para uso sobre um fundo sólido de acento
   * (ex. dentro de um Button `primary` em loading). */
  tone?: "accent" | "onAccent" | "tertiary";
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<SpinnerProps["size"]>, string> = {
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-2",
  lg: "h-10 w-10 border-[3px]",
};

const TONE_CLASSES: Record<NonNullable<SpinnerProps["tone"]>, string> = {
  accent: "border-surface-4 border-t-accent",
  onAccent: "border-white/30 border-t-white",
  tertiary: "border-surface-3 border-t-text-tertiary",
};

/** 20.3 — usado para ações pequenas/rápidas (botão, refresh). Carga de
 * seção/página inteira usa Skeleton, nunca Spinner. */
export function Spinner({ size = "md", tone = "accent", className = "" }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Carregando"
      className={`animate-spin rounded-full ${SIZE_CLASSES[size]} ${TONE_CLASSES[tone]} ${className}`}
    />
  );
}
