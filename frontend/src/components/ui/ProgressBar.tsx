import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";

export interface ProgressBarProps {
  /** 0-100. Valores fora da faixa são presos (clamped). */
  value: number;
  /** Cor do preenchimento — só tokens semânticos já existentes do Design
   * System (design-system.md, seção 6.4), nunca uma cor nova. Adicionado
   * nos ajustes de UX/UI que precederam a Etapa F9 (Cartão): "progresso do
   * limite" precisa reagir à proximidade do limite (normal/perto/
   * estourado) — evolução do componente existente, não um componente
   * paralelo (nenhum outro consumidor de `ProgressBar` precisa mudar,
   * `tone` tem default `"accent"`, o mesmo comportamento de sempre).
   *
   * `"positive"` adicionado na revisão de UX de Cartões
   * (`docs/analise-arquitetural-revisao-ux-cartoes.md`, seção 6): achado de
   * auditoria — `--color-accent` é "reservado para interação, nunca para
   * dado financeiro" (design-system.md, seção 6.3), então usá-lo para
   * "utilização saudável" (dado financeiro) violava a própria regra do
   * Design System desde a Etapa F9. `"positive"` é o tone correto para
   * esse caso — mesmo verde de saldo positivo/fatura paga (seção 6.4). */
  tone?: "accent" | "positive" | "info" | "warning" | "negative";
  className?: string;
  "aria-label"?: string;
}

const TONE_CLASSES: Record<NonNullable<ProgressBarProps["tone"]>, string> = {
  accent: "bg-accent",
  positive: "bg-positive",
  info: "bg-info",
  warning: "bg-warning",
  negative: "bg-negative",
};

/**
 * Trilho `--color-surface-3`, preenchimento `--color-accent` por padrão —
 * design-system.md, seção 14. Usado em progresso de formulário (ex. Meta) e,
 * desde os ajustes de UX/UI, em "progresso do limite" de Cartão (`tone`
 * reagindo a `warning`/`negative` conforme a % utilizada).
 *
 * A barra fina de navegação entre páginas (padrão Vercel/Linear, também
 * citada na seção 14) fica para quando o roteamento tiver um estado real
 * de transição em andamento para observar (hoje as rotas trocam
 * instantaneamente, sem loader/suspense) — implementá-la agora seria um
 * componente sem nenhum evento real para disparar.
 */
export function ProgressBar({ value, tone = "accent", className = "", ...props }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`h-1.5 w-full overflow-hidden rounded-full bg-surface-3 ${className}`}
      {...props}
    >
      <motion.div
        className={`h-full rounded-full ${TONE_CLASSES[tone]}`}
        initial={false}
        animate={{ width: `${clamped}%` }}
        transition={SPRING.gentle}
      />
    </div>
  );
}
