import { useEffect } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { SPRING } from "../../lib/motion";
import { formatMoney, formatMoneyCompacto, formatPercent, toNumber } from "../../utils/format";

export interface AnimatedNumberProps {
  value: string | number;
  format?: "money" | "percent";
  className?: string;
  /** Etapa de Refinamento UX/UI, item 3 ("valores ultrapassando os
   * cards"): quando `true`, anima em notação compacta ("R$ 1,2 mi") em vez
   * de valor cheio. A decisão de compactar ou não é tomada UMA VEZ pelo
   * valor-alvo final (`formatMoneyInteligente`/`StatCard`), nunca
   * recalculada a cada frame — trocar de formatador no meio do count-up
   * faria o número "pular" de forma estranha. */
  compact?: boolean;
}

/** Count-up spring `gentle` — motion-principles.md, seção 6.1: acontece na
 * primeira renderização real do valor (parte de 0), e em mudanças
 * posteriores interpola diretamente do valor atual para o novo (seção 6.2).
 * Um único `useSpring` cobre os dois casos por natureza (nunca reinicia do
 * zero numa atualização, só na montagem). Formata a cada frame via
 * `useTransform` (nunca só no valor final) — evita o número "pular" de
 * formato. `useReducedMotion` pula a animação por completo quando o usuário
 * prefere motion reduzido (motion-principles.md, seção 8) — `useSpring`
 * roda fora do sistema declarativo do `MotionConfig`, então este é o único
 * lugar do projeto que precisa checar isso manualmente. */
export function AnimatedNumber({ value, format = "money", className = "", compact = false }: AnimatedNumberProps) {
  const alvo = toNumber(value);
  const reduzMotion = useReducedMotion();
  const motionValue = useMotionValue(alvo);
  const spring = useSpring(motionValue, SPRING.gentle);
  const formatter = format === "money" ? (compact ? formatMoneyCompacto : formatMoney) : formatPercent;
  const texto = useTransform(reduzMotion ? motionValue : spring, (valorAtual) => formatter(valorAtual));

  useEffect(() => {
    motionValue.set(alvo);
  }, [alvo, motionValue]);

  return (
    <motion.span className={`tabular ${className}`}>
      {texto}
    </motion.span>
  );
}
