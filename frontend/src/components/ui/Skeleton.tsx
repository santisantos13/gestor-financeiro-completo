import { type HTMLAttributes } from "react";

export type SkeletonProps = HTMLAttributes<HTMLDivElement>;

/** Retângulo no formato exato do conteúdo final — nunca um placeholder
 * genérico (design-system.md, seção 20.2). Shimmer sutil via gradiente
 * animado (`.skeleton-shimmer` em `index.css`), desligado sob
 * `prefers-reduced-motion` (só a cor estática permanece). Dimensione via
 * `className` (ex. `h-8 w-32`) no formato do conteúdo real. */
export function Skeleton({ className = "", ...props }: SkeletonProps) {
  return (
    <div
      role="presentation"
      aria-hidden="true"
      className={`skeleton-shimmer rounded-md ${className}`}
      {...props}
    />
  );
}
