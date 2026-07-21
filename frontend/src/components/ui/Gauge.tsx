import type { ReactNode } from "react";
import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";

export interface GaugeProps {
  /** 0-100. Valores fora da faixa são presos (clamped) — mesmo contrato de `ProgressBar`. */
  value: number;
  size?: number;
  strokeWidth?: number;
  /** Mesmos tokens semânticos de `ProgressBar` — nenhuma cor nova. */
  tone?: "accent" | "positive" | "info" | "warning" | "negative";
  className?: string;
  /** Conteúdo centralizado dentro do anel (ex. percentual como texto). */
  children?: ReactNode;
  "aria-label"?: string;
}

const TONE_STROKE: Record<NonNullable<GaugeProps["tone"]>, string> = {
  accent: "stroke-accent",
  positive: "stroke-positive",
  info: "stroke-info",
  warning: "stroke-warning",
  negative: "stroke-negative",
};

/**
 * Anel de progresso circular — versão radial de `ProgressBar.tsx` (mesmo
 * trilho `--color-surface-3`, mesmo mapa de `tone`, mesma animação
 * `SPRING.gentle`), construído do zero em SVG cru: nenhuma biblioteca de
 * gráfico foi adicionada ao projeto (`docs/analise-arquitetural-dashboard.md`,
 * seção 0.3, já registrava essa escolha como deliberadamente adiada — este
 * componente é simples o bastante para não precisar dela). Ver
 * docs/analise-arquitetural-dashboard-hero-redesign.md.
 *
 * Gira -90° para o traço começar no topo (12h), preenchendo no sentido
 * horário — leitura mais natural de "progresso" do que o padrão de SVG
 * (0° = 3h). `strokeLinecap="round"` para a ponta do traço não ficar
 * cortada reta em valores baixos.
 */
export function Gauge({
  value,
  size = 64,
  strokeWidth = 6,
  tone = "accent",
  className = "",
  children,
  ...props
}: GaugeProps) {
  const clamped = Math.min(100, Math.max(0, value));
  const raio = (size - strokeWidth) / 2;
  const centro = size / 2;
  const circunferencia = 2 * Math.PI * raio;
  const offset = circunferencia * (1 - clamped / 100);

  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`relative inline-flex shrink-0 items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      {...props}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={centro}
          cy={centro}
          r={raio}
          strokeWidth={strokeWidth}
          className="fill-none stroke-surface-3"
        />
        <motion.circle
          cx={centro}
          cy={centro}
          r={raio}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className={`fill-none ${TONE_STROKE[tone]}`}
          style={{ strokeDasharray: circunferencia }}
          initial={false}
          animate={{ strokeDashoffset: offset }}
          transition={SPRING.gentle}
        />
      </svg>
      {children && <div className="absolute inset-0 flex items-center justify-center">{children}</div>}
    </div>
  );
}
