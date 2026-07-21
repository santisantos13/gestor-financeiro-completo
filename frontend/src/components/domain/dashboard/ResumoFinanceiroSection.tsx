import type { KeyboardEvent } from "react";
import { Scale, Target, Wallet } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { StatCard } from "../../ui/StatCard";
import { Card } from "../../ui/Card";
import { Gauge } from "../../ui/Gauge";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { formatMoney, formatPercent, toNumber } from "../../../utils/format";
import {
  useMetasQuery,
  useResumoFinanceiroQuery,
  useVisaoMensalQuery,
} from "../../../hooks/useCentralFinanceiraQueries";
import type { MetaRead } from "../../../types/centralFinanceira";

export interface ResumoFinanceiroSectionProps {
  ano: number;
  mes: number;
}

/** Mini-linha de tendência do Saldo Total — 2 pontos reais (início do
 * período → agora), NUNCA uma série diária fabricada (não existe endpoint
 * de série histórica, ver docs/analise-arquitetural-dashboard-hero-redesign.md,
 * decisão 1). Puramente decorativa/direcional: a inclinação não é
 * proporcional à magnitude real, só ao sinal — rotulada explicitamente
 * "desde o início do período" para nunca insinuar granularidade diária. */
function MiniTendenciaSaldo({ crescente }: { crescente: boolean }) {
  const corStroke = crescente ? "stroke-positive" : "stroke-negative";
  const corFill = crescente ? "fill-positive/10" : "fill-negative/10";
  const y0 = crescente ? 26 : 6;
  const y1 = crescente ? 6 : 26;

  return (
    <svg viewBox="0 0 100 32" className="h-8 w-full" preserveAspectRatio="none" aria-hidden="true">
      <path d={`M0,${y0} L100,${y1} L100,32 L0,32 Z`} className={`${corFill} stroke-none`} />
      <path d={`M0,${y0} L100,${y1}`} className={`${corStroke} fill-none`} strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

/** Linha de hero cards do topo do Dashboard — Refinamento Visual (pedido
 * explícito do usuário, com uma referência visual de outro app): Saldo
 * Total (tendência derivada), Visão Mensal (entradas/saídas/fluxo) e Metas
 * Ativas (anel de progresso da meta mais perto de concluir). Ver
 * docs/analise-arquitetural-dashboard-hero-redesign.md.
 *
 * "Visão Mensal" é o mesmo StatCard de "Fluxo de caixa" de antes, só
 * restilizado como um dos 3 heroes — continua sem duplicar
 * `entradas_mes`/`saidas_mes` em outro card (decisão original já registrada
 * aqui, "Fusão Entradas × Saídas"). "Metas Ativas" reaproveita a mesma
 * seleção de "mais perto de concluir" de `MetasCard.tsx` (percentual < 100,
 * desc, primeira) — sem meta ativa incompleta, o card retorna `null`
 * (mesma regra de "esconder card vazio" do resto do Dashboard) e a linha
 * cai para 2 cards, sem placeholder vazio.
 */
export function ResumoFinanceiroSection({ ano, mes }: ResumoFinanceiroSectionProps) {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useResumoFinanceiroQuery(ano, mes);
  const { data: visaoMensal } = useVisaoMensalQuery(ano, mes);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <LoadingCard key={index} lines={2} />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-border bg-surface-2 p-4">
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </div>
    );
  }

  const entradas = visaoMensal ? toNumber(visaoMensal.entradas) : 0;
  const saidas = visaoMensal ? toNumber(visaoMensal.saidas) : 0;
  const maior = Math.max(entradas, saidas, 1);

  const comparativoEntradasSaidas = visaoMensal ? (
    <div className="mt-3 space-y-1.5 border-t border-border-subtle pt-3">
      <div className="flex items-center justify-between text-caption text-text-tertiary">
        <span>Entradas {formatMoney(visaoMensal.entradas)}</span>
        <span>Saídas {formatMoney(visaoMensal.saidas)}</span>
      </div>
      <div className="flex h-1.5 gap-1 overflow-hidden rounded-full bg-surface-3">
        <div className="h-full rounded-full bg-positive" style={{ width: `${(entradas / maior) * 50}%` }} />
        <div className="h-full rounded-full bg-negative" style={{ width: `${(saidas / maior) * 50}%` }} />
      </div>
    </div>
  ) : undefined;

  // Tendência do saldo: derivada de dois números REAIS já devolvidos por
  // `resumo` (nunca fabricada) — saldo no início do período = saldo agora
  // menos o fluxo líquido do período. `trend` (percentual) ativa o
  // `TrendIndicator` já existente em `StatCard` (construído desde a Etapa
  // do Dashboard, nunca usado até agora por falta de dado real).
  const saldoAtual = toNumber(data.saldo_total);
  const fluxoCaixa = toNumber(data.fluxo_caixa_mes);
  const saldoInicioPeriodo = saldoAtual - fluxoCaixa;
  const trendPercentual = saldoInicioPeriodo !== 0 ? (fluxoCaixa / Math.abs(saldoInicioPeriodo)) * 100 : undefined;

  const extraSaldoTotal = (
    <div className="mt-3 border-t border-border-subtle pt-3">
      <MiniTendenciaSaldo crescente={fluxoCaixa >= 0} />
      <p className="mt-1 text-caption text-text-tertiary">
        {fluxoCaixa >= 0 ? "+" : ""}
        {formatMoney(fluxoCaixa)} desde o início do período
      </p>
    </div>
  );

  return (
    // `items-stretch` (default do Grid, explícito aqui - bug relatado pelo
    // usuário, 2026-07-21): os 3 heroes têm alturas de conteúdo diferentes
    // ("Saldo total"/"Visão mensal" têm bloco `extra` com gráfico/barra,
    // "Metas ativas" não) - com `items-start` cada card só tinha a altura
    // do PRÓPRIO conteúdo, deixando as bordas inferiores desalinhadas
    // (degrau visual). Esticando os 3 para a altura da linha, o topo
    // (label/ícone/valor) sempre alinha e a diferença de conteúdo vira só
    // espaço em branco no rodapé do card mais curto - nunca um problema
    // aqui porque nenhum dos 3 tem ação/rodapé que precise ficar colado
    // embaixo.
    <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-3">
      <StatCard
        label="Saldo total"
        value={data.saldo_total}
        trend={trendPercentual}
        icon={<Wallet size={16} className="text-text-tertiary" aria-hidden="true" />}
        onClick={() => navigate("/contas")}
        aria-label="Ver contas"
        extra={extraSaldoTotal}
      />
      <StatCard
        label="Visão mensal"
        value={data.fluxo_caixa_mes}
        icon={<Scale size={16} className="text-text-tertiary" aria-hidden="true" />}
        onClick={() => navigate("/transacoes")}
        aria-label="Ver transações"
        extra={comparativoEntradasSaidas}
      />
      <MetasAtivasHero />
    </div>
  );
}

function MetasAtivasHero() {
  const navigate = useNavigate();
  const { data, isLoading } = useMetasQuery();

  if (isLoading) return <LoadingCard lines={2} />;
  if (!data || data.metas.length === 0) return null;

  const metaMaisPertoDeConcluir = [...data.metas]
    .filter((meta) => Number(meta.percentual) < 100)
    .sort((a, b) => Number(b.percentual) - Number(a.percentual))[0] as MetaRead | undefined;

  if (!metaMaisPertoDeConcluir) return null;

  const percentual = Number(metaMaisPertoDeConcluir.percentual);

  function abrirMetas() {
    navigate("/metas");
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      abrirMetas();
    }
  }

  return (
    <Card
      role="link"
      tabIndex={0}
      onClick={abrirMetas}
      onKeyDown={onKeyDown}
      aria-label="Ver metas"
      animateEntrance
      className="cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">Metas ativas</p>
        <Target size={16} className="text-text-tertiary" aria-hidden="true" />
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Gauge value={percentual} tone="accent" aria-label={`${metaMaisPertoDeConcluir.descricao}, ${formatPercent(percentual)} concluído`}>
          <span className="text-caption font-semibold text-text-primary">{formatPercent(percentual)}</span>
        </Gauge>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">{metaMaisPertoDeConcluir.descricao}</p>
          <p className="text-caption text-text-tertiary">
            {formatMoney(metaMaisPertoDeConcluir.valor_acumulado)} de {formatMoney(metaMaisPertoDeConcluir.valor_alvo)}
          </p>
        </div>
      </div>
    </Card>
  );
}
