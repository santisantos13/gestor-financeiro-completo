import type { ToneSemantico } from "../../utils/status";

export interface StatusDotProps {
  tone: ToneSemantico | "neutral";
  className?: string;
  /** Só quando o ponto aparece SOZINHO, sem texto adjacente que já
   * descreva o estado (ex. dentro de um `RowAction`/legenda) — o padrão
   * do projeto é cor nunca ser o único portador de informação
   * (design-system.md, seção 23), então a maioria dos usos tem `aria-hidden`
   * implícito por já haver um rótulo textual do lado. */
  "aria-label"?: string;
}

const DOT_CLASSES: Record<NonNullable<StatusDotProps["tone"]>, string> = {
  positive: "bg-positive",
  negative: "bg-negative",
  warning: "bg-warning",
  info: "bg-info",
  neutral: "bg-text-tertiary",
};

/**
 * Microindicador — ponto colorido discreto (revisão de UX de Cartões,
 * "microindicadores"), o "● " citado no pedido do usuário. Sempre pequeno
 * (6px) e nunca a única fonte de informação — usado ao lado de um rótulo
 * textual (ex. `AtivoBadge`), nunca substituindo-o.
 */
export function StatusDot({ tone, className = "", ...props }: StatusDotProps) {
  return (
    <span
      aria-hidden={props["aria-label"] ? undefined : true}
      aria-label={props["aria-label"]}
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${DOT_CLASSES[tone]} ${className}`}
    />
  );
}
