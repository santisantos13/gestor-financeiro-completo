import type { ReactNode } from "react";
import type { ToneSemantico } from "../../utils/status";

export interface StatusChipProps {
  tone: ToneSemantico;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}

// Fundo SÓLIDO (não `-subtle`/translúcido como `Badge`) + texto do token
// `--color-text-on-{tone}` — contraste garantido por construção, mesmo
// quando o chip é desenhado sobre um fundo imprevisível (gradiente de
// marca de um cartão, foto, etc.). Ver index.css, seção 6.4 (tokens
// `--color-text-on-positive/negative/warning/info`).
const CHIP_CLASSES: Record<ToneSemantico, string> = {
  positive: "bg-positive text-text-onPositive",
  negative: "bg-negative text-text-onNegative",
  warning: "bg-warning text-text-onWarning",
  info: "bg-info text-text-onInfo",
};

/**
 * Chip de status com fundo sólido — revisão de UX de Cartões, "cores como
 * informação" / "cores adaptativas": diferente de `Badge` (fundo
 * translúcido, pensado para viver sobre a superfície neutra do app),
 * `StatusChip` carrega seu PRÓPRIO fundo opaco, então nunca perde
 * contraste ao ser desenhado em cima de uma cor de fundo que o
 * componente não controla — o caso concreto que motivou sua criação:
 * "Vence em X dias" dentro do `CartaoVisual`, que antes herdava a cor de
 * texto do tema do cartão e podia "sumir" num cartão da cor errada.
 * Reutilizável por qualquer entidade futura com o mesmo problema
 * (qualquer indicador sobre uma superfície de cor variável).
 */
export function StatusChip({ tone, children, icon, className = "" }: StatusChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-micro font-semibold leading-none ${CHIP_CLASSES[tone]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
}
