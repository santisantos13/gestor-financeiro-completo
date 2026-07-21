import { type KeyboardEvent, type ReactNode } from "react";
import { motion } from "motion/react";
import { Card } from "./Card";
import { AnimatedNumber } from "./AnimatedNumber";
import { TrendIndicator } from "./TrendIndicator";
import { SPRING } from "../../lib/motion";
import {
  deveCompactarMoney,
  formatMoney,
  formatMoneyInteligente,
  formatPercent,
  tamanhoValorHero,
  toNumber,
} from "../../utils/format";

export interface StatCardProps {
  label: string;
  value: string | number;
  format?: "money" | "percent";
  /** Variação em pontos percentuais — ver `TrendIndicatorProps`. Omitido
   * por padrão (nenhum dos 11 endpoints desta etapa expõe variação). */
  trend?: number;
  icon?: ReactNode;
  className?: string;
  /** Etapa de Refinamento de UX/Dashboard (seção 1, "Dashboard como hub de
   * navegação"): quando presente, o card inteiro vira uma superfície
   * clicável (mesmo padrão `role="link"` + teclado já usado em
   * `CartaoResumoCard`) — nenhum botão visível extra, o próprio card já é
   * o convite à navegação. `aria-label` describe o destino para leitor de
   * tela (o card já não tem texto de link explícito). */
  onClick?: () => void;
  "aria-label"?: string;
  /** Conteúdo extra no rodapé do card (ex. mini-comparação Entradas ×
   * Saídas embutida no StatCard "Fluxo de caixa" — seção 3, fusão que
   * substitui o antigo `VisaoMensalCard` isolado). */
  extra?: ReactNode;
}

/** label + valor "hero" (`AnimatedNumber`, tamanho adaptativo — ver abaixo)
 * + variação opcional — design-system.md, seção 16. O card de destaque do
 * topo do Dashboard (Resumo Financeiro). `animateEntrance` no `Card` de
 * base (fade+slide na primeira montagem real, mesmo mount que já protege o
 * count-up de `AnimatedNumber` de reanimar em dado de cache — ambos
 * dependem da mesma garantia de "só remonta quando os dados chegam pela
 * primeira vez"). Ícone ganha uma reação sutil de escala+rotação no
 * próprio hover (`SPRING.snappy`, o preset de microinteração de
 * motion-principles.md, seção 4.3) — número em si permanece intocado,
 * seguindo o padrão já existente (`AnimatedNumber` não foi alterado nesta
 * etapa).
 *
 * Ajustes de UX/UI pós-F9, ponto 1 ("valores estourando os cards"): o
 * tamanho do valor não é mais fixo em `--text-display` — `tamanhoValorHero`
 * (utils/format.ts) calcula o tier certo a partir do comprimento do
 * valor-alvo já formatado, uma única vez (nunca recalculado a cada frame
 * do count-up, o que faria a fonte "pular" de tamanho durante a animação).
 * Combinado com o alargamento dos cards "hero" em
 * `ResumoFinanceiroSection` (grid de 12 colunas) — na prática a imensa
 * maioria dos valores reais nunca sai de `text-display`; os tiers menores
 * só entram para números realmente grandes. Deliberadamente NÃO é uma
 * redução uniforme de fonte para todos os cards. `min-w-0` é o que de fato
 * impede o overflow de flexbox (filho de `flex` ignora a largura do pai
 * sem isso); `whitespace-nowrap` mantém o valor como uma unidade só —
 * nunca quebra no meio de "R$ 1.234,56". */
export function StatCard({
  label,
  value,
  format = "money",
  trend,
  icon,
  className = "",
  onClick,
  "aria-label": ariaLabel,
  extra,
}: StatCardProps) {
  const numero = toNumber(value);
  const compact = format === "money" && deveCompactarMoney(numero);
  const formatado = format === "money" ? formatMoneyInteligente(numero) : formatPercent(numero);
  const tamanho = tamanhoValorHero(formatado);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!onClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  }

  return (
    <Card
      className={`${onClick ? "cursor-pointer" : ""} ${className}`}
      animateEntrance
      {...(onClick
        ? { role: "link", tabIndex: 0, onClick, onKeyDown, "aria-label": ariaLabel }
        : {})}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">{label}</p>
        {icon && (
          <motion.span
            whileHover={{ scale: 1.15, rotate: -6 }}
            transition={SPRING.snappy}
            className="inline-flex"
          >
            {icon}
          </motion.span>
        )}
      </div>
      <div
        className="mt-2 flex min-w-0 items-baseline gap-2"
        {...(compact ? { title: formatMoney(numero) } : {})}
      >
        <AnimatedNumber
          value={value}
          format={format}
          compact={compact}
          className={`${tamanho} min-w-0 whitespace-nowrap font-semibold text-text-primary`}
        />
        {trend !== undefined && <TrendIndicator percentual={trend} />}
      </div>
      {extra}
    </Card>
  );
}
