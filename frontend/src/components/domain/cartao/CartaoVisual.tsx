import { useRef, type MouseEvent } from "react";
import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { BandeiraBadge } from "../../ui/BandeiraBadge";
import { ProgressBar } from "../../ui/ProgressBar";
import { StatusChip } from "../../ui/StatusChip";
import { resolveCardTheme } from "../../../lib/cardThemes";
import { SPRING } from "../../../lib/motion";
import { formatMoney } from "../../../utils/format";
import { diasAte, proximaOcorrenciaDoDia } from "../../../utils/date";
import { tonePorUtilizacao, tonePorPrazo } from "../../../utils/status";
import type { Bandeira } from "../../../types/enums";

export interface CartaoVisualProps {
  nome: string;
  instituicao: string | null;
  bandeira: Bandeira;
  ultimosQuatroDigitos: string;
  /** Strings Decimal, mesmo tratamento de `formatMoney` — nunca convertidas
   * e guardadas como `number` fora da hora de exibir. */
  limite: string;
  limiteDisponivel: string;
  diaFechamento?: number;
  diaVencimento?: number;
  /** `id` da variante de tema escolhida (`lib/cardThemes.ts`) — `null`/
   * ausente usa a primeira variante disponível para a instituição. */
  variantId?: string | null;
  className?: string;
}

/**
 * "Cartão visual" — peça central dos ajustes de UX/UI que precederam a
 * Etapa F9. Componente de apresentação puro (nunca acoplado a `CartaoRead`,
 * ver seção 9 da análise arquitetural), sempre no formato "cartão físico
 * premium" (proporção real ~1.586:1, gradiente da instituição, tilt 3D +
 * glow seguindo o mouse). Usado no preview do `CartaoFormDialog`, no
 * `CartaoResumoCard` (grid de `/cartoes`) e na página de detalhes.
 *
 * O `layout="compact"` que existia até a revisão de UX de Cartões (linha
 * horizontal para a coluna "Cartão" do antigo `DataTable`) foi removido
 * junto com a migração de `/cartoes` para grid de cards —
 * `docs/analise-arquitetural-revisao-ux-cartoes.md`, seções 2 e 9: sem
 * `DataTable`, não sobra nenhum consumidor do layout compacto.
 *
 * Tilt 3D + glow seguindo o mouse: implementado com `useMotionValue`/
 * `useSpring` do Framer Motion, nunca `useState` a cada `mousemove` (evita
 * re-render de componente React a cada frame — só a `motion.div` atualiza
 * via transform/CSS, mesmo princípio que já rege `Button`/`Card`).
 * Desligado inteiramente sob `prefers-reduced-motion` (`useReducedMotion`),
 * mesmo tratamento de `.skeleton-shimmer` em `index.css` — o cartão
 * continua legível e estático, só perde o movimento.
 */
export function CartaoVisual({
  nome,
  instituicao,
  bandeira,
  ultimosQuatroDigitos,
  limite,
  limiteDisponivel,
  diaFechamento,
  diaVencimento,
  variantId,
  className = "",
}: CartaoVisualProps) {
  const tema = resolveCardTheme(instituicao, variantId);
  const limiteNumero = Number(limite);
  const disponivelNumero = Number(limiteDisponivel);
  const utilizadoNumero = Number.isNaN(limiteNumero) || Number.isNaN(disponivelNumero) ? 0 : limiteNumero - disponivelNumero;
  const percentual = limiteNumero > 0 ? (utilizadoNumero / limiteNumero) * 100 : 0;
  // Correção de UX (docs/analise-arquitetural-revisao-ux-cartoes.md, seção
  // 6): "accent" é reservado para interação (design-system.md, seção 6.3),
  // nunca para dado financeiro — `tonePorUtilizacao` (utils/status.ts,
  // sistema semântico formalizado na revisão de UX) decide
  // `positive`/`warning`/`negative` a partir do percentual, mesma régua
  // reutilizada por `CartaoResumoCard`/`CartoesCard`.
  const tone = tonePorUtilizacao(percentual);

  // "Faltam N dia(s)" em vez do dia-do-mês cru — mesma aritmética de
  // calendário do `CartoesCard` do Dashboard (`utils/date.ts`), unifica a
  // linguagem entre as duas telas (ponto 6 dos ajustes de UX/UI: consistência).
  // Guardado contra valores temporariamente inválidos durante a digitação no
  // formulário de criação (`NumberField` pode passar por `0`/vazio).
  const fechamentoValido = typeof diaFechamento === "number" && diaFechamento >= 1 && diaFechamento <= 31;
  const vencimentoValido = typeof diaVencimento === "number" && diaVencimento >= 1 && diaVencimento <= 31;
  const diasParaFechar = fechamentoValido ? diasAte(proximaOcorrenciaDoDia(diaFechamento!)) : null;
  const diasParaVencer = vencimentoValido ? diasAte(proximaOcorrenciaDoDia(diaVencimento!)) : null;

  const prefereReduzido = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  // Cache do `getBoundingClientRect()` — lido uma vez por hover
  // (`onMouseEnter`), nunca por `mousemove` (correção de performance: o
  // card não muda de tamanho/posição durante o próprio hover, então
  // recalcular o rect a cada pixel de movimento do mouse era um "layout
  // thrashing" forçado sem necessidade — a causa real da lentidão
  // percebida ao passar o mouse sobre o cartão).
  const rectRef = useRef<DOMRect | null>(null);

  // Tilt 3D + glow — desligado quando motion está reduzido.
  // `useMotionValue` nunca dispara re-render React; `useSpring` suaviza o
  // movimento (mesmo spring "gentle" já usado por `ProgressBar`).
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);
  const rotateXRaw = useMotionValue(0);
  const rotateYRaw = useMotionValue(0);
  const rotateX = useSpring(rotateXRaw, SPRING.gentle);
  const rotateY = useSpring(rotateYRaw, SPRING.gentle);
  const mouseXPercent = useTransform(mouseX, (v) => `${v * 100}%`);
  const mouseYPercent = useTransform(mouseY, (v) => `${v * 100}%`);
  const glowBackground = useMotionTemplate`radial-gradient(240px circle at ${mouseXPercent} ${mouseYPercent}, rgba(255,255,255,0.22), transparent 70%)`;

  const tiltAtivo = !prefereReduzido;

  function onMouseEnter() {
    if (!tiltAtivo || !ref.current) return;
    rectRef.current = ref.current.getBoundingClientRect();
  }

  function onMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (!tiltAtivo) return;
    // Fallback defensivo (ex. o próprio `onMouseEnter` não ter disparado a
    // tempo) — nunca força um reflow síncrono no caminho quente do
    // `mousemove`, só no pior caso, uma vez.
    const rect = rectRef.current ?? ref.current?.getBoundingClientRect();
    if (!rect) return;
    rectRef.current = rect;
    const relX = (event.clientX - rect.left) / rect.width;
    const relY = (event.clientY - rect.top) / rect.height;
    mouseX.set(relX);
    mouseY.set(relY);
    rotateYRaw.set((relX - 0.5) * 10);
    rotateXRaw.set((0.5 - relY) * 10);
  }

  function onMouseLeave() {
    if (!tiltAtivo) return;
    rectRef.current = null;
    rotateXRaw.set(0);
    rotateYRaw.set(0);
    mouseX.set(0.5);
    mouseY.set(0.5);
  }

  const gradienteCss = `linear-gradient(135deg, ${tema.gradiente[0]}, ${tema.gradiente[1]})`;
  const digitosMascarados = `•••• ${ultimosQuatroDigitos}`;

  return (
    <motion.div
      ref={ref}
      onMouseEnter={onMouseEnter}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      whileHover={tiltAtivo ? { scale: 1.02 } : undefined}
      transition={SPRING.gentle}
      className={`relative aspect-[1.586/1] w-full max-w-sm overflow-hidden rounded-xl shadow-lg ${className}`}
      style={{
        // Gradiente de marca em saturação total como o fundo de verdade —
        // pedido explícito do usuário (2026-07-20): a versão "harmonizada"
        // (base escura + tinta translúcida soft-light) deixou os cartões
        // sem graça. Projeto de uso pessoal, nunca vai ao ar - nenhuma
        // preocupação de direito autoral sobre usar a cor de marca real de
        // cada instituição (`lib/cardThemes.ts`) como já era antes da
        // etapa de harmonização de paleta.
        background: gradienteCss,
        color: tema.corTexto,
        ...(tiltAtivo ? { rotateX, rotateY, transformPerspective: 800 } : {}),
      }}
    >
      {/* Brilho sutil diagonal (textura de superfície) — camada estática,
          não anima; só o glow que segue o mouse é dinâmico. */}
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background: "linear-gradient(115deg, rgba(255,255,255,0.16) 0%, transparent 35%, transparent 65%, rgba(255,255,255,0.08) 100%)",
        }}
        aria-hidden="true"
      />
      {tiltAtivo && (
        <motion.div
          className="pointer-events-none absolute inset-0"
          style={{
            background: glowBackground,
          }}
          aria-hidden="true"
        />
      )}

      <div className="relative flex h-full flex-col justify-between p-4 sm:p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <InstitutionBadge nome={instituicao} size="md" />
            <BandeiraBadge bandeira={bandeira} size="md" />
          </div>
          {(diasParaFechar != null || diasParaVencer != null) && (
            // `StatusChip` (fundo sólido) em vez de texto translúcido
            // herdando `tema.corTexto` — correção de "cores como
            // informação" (revisão de UX de Cartões): a informação de
            // prazo nunca deve "sumir" por causa da cor do cartão.
            // Fechamento é só informativo (`info`); vencimento escala de
            // urgência de verdade via `tonePorPrazo`.
            <div className="flex flex-col items-end gap-1">
              {diasParaFechar != null && (
                <StatusChip tone="info" className="whitespace-nowrap">
                  Fecha em {diasParaFechar}d
                </StatusChip>
              )}
              {diasParaVencer != null && (
                <StatusChip tone={tonePorPrazo(diasParaVencer)} className="whitespace-nowrap">
                  Vence em {diasParaVencer}d
                </StatusChip>
              )}
            </div>
          )}
        </div>

        <div>
          <p className="truncate text-body font-semibold">{nome}</p>
          <p className="font-mono tabular text-sm tracking-widest opacity-90">{digitosMascarados}</p>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-micro opacity-90">
            <span>Utilizado: {formatMoney(utilizadoNumero)}</span>
            <span>Disponível: {formatMoney(limiteDisponivel)}</span>
          </div>
          <ProgressBar
            value={Math.max(0, Math.min(100, percentual))}
            tone={tone}
            aria-label={`Limite utilizado do cartão ${nome}`}
            className="bg-white/20"
          />
        </div>
      </div>
    </motion.div>
  );
}
