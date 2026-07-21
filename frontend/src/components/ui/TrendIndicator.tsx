import { ArrowDown, ArrowUp } from "lucide-react";

export interface TrendIndicatorProps {
  /** Variação em pontos percentuais, ex. 12.4 significa "+12,4%". Sinal
   * define cor/direção — nunca calculado no frontend (o valor já vem pronto
   * de onde for consumido). */
  percentual: number;
  className?: string;
}

/** Seta + variação percentual, tons positive/negative — design-system.md,
 * seção 16. Reservado para quando um endpoint expuser uma variação
 * calculada (nenhum dos 11 endpoints desta etapa expõe isso hoje — ver
 * docs/analise-arquitetural-dashboard.md, seção 9.1); construído e pronto
 * para uso futuro, sem inventar cálculo de variação no cliente. */
export function TrendIndicator({ percentual, className = "" }: TrendIndicatorProps) {
  const positivo = percentual >= 0;
  const Icon = positivo ? ArrowUp : ArrowDown;

  return (
    <span
      className={`tabular inline-flex items-center gap-0.5 text-sm font-medium ${
        positivo ? "text-positive" : "text-negative"
      } ${className}`}
    >
      <Icon size={14} aria-hidden="true" />
      {Math.abs(percentual).toFixed(1)}%
    </span>
  );
}
