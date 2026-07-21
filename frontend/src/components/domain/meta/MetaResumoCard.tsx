import { useMemo, useState, type KeyboardEvent } from "react";
import { ChevronDown, Target } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Card } from "../../ui/Card";
import { Badge } from "../../ui/Badge";
import { ProgressBar } from "../../ui/ProgressBar";
import { AnimatedNumber } from "../../ui/AnimatedNumber";
import { Skeleton } from "../../ui/Skeleton";
import { MetaActionBar } from "./MetaActionBar";
import { MetaCelebracao } from "./MetaCelebracao";
import { MetaAporteDialog, type DirecaoAporteMeta } from "./MetaAporteDialog";
import { useAportesLegadosDaMeta, useTransferenciasDoCofrinho } from "../../../hooks/useMetaQueries";
import { useCelebracaoMeta } from "../../../hooks/useCelebracaoMeta";
import { formatMoney } from "../../../utils/format";
import { formatDate } from "../../../utils/date";
import { tonePorUtilizacao, TEXT_TONE_CLASS } from "../../../utils/status";
import { DURATION, EASE } from "../../../lib/motion";
import {
  formatarPrazoMeta,
  formatarTempoParaConcluir,
  fraseContribuicaoSugerida,
  fraseDiferencaPlanejado,
  frasePrevisaoConclusao,
  situacaoDaMeta,
  SITUACAO_META_LABEL,
  SITUACAO_META_TONE,
  SITUACAO_PLANEJAMENTO_LABEL,
  SITUACAO_PLANEJAMENTO_TONE,
} from "../../../utils/meta";
import type { MetaRead } from "../../../types/meta";

export interface MetaResumoCardProps {
  meta: MetaRead;
  onEditar: (meta: MetaRead) => void;
  onDesativar: (meta: MetaRead) => void;
  onReativar: (meta: MetaRead) => void;
  onExcluir: (meta: MetaRead) => void;
}

interface ItemHistoricoMeta {
  chave: string;
  data: string;
  descricao: string;
  valor: string;
  positivo: boolean;
}

/**
 * Card premium de Meta — visualização principal de `/metas` (pedido do
 * usuário: "cada Meta deve parecer um objetivo em andamento, não apenas um
 * registro"). Mostra, sem precisar abrir nada: percentual, valor
 * acumulado, valor restante, data prevista, situação, planejado x realizado
 * e previsão de conclusão — todos lidos/derivados de `MetaRead` já
 * calculado pelo backend (nunca reproduzidos). Ver
 * docs/analise-arquitetural-metas-frontend.md, seções 3.1 e 4.1, e
 * docs/analise-arquitetural-metas-refinamento.md, seções 1-3.
 *
 * Expande INLINE ao clicar no card (em vez de navegar para outra tela,
 * seção 6 do pedido de refinamento) para revelar o histórico recente de
 * aportes — a única informação que genuinamente não cabe no resumo
 * compacto. `MetaActionBar`/o próprio toggle de expansão sempre chamam
 * `stopPropagation` nos elementos internos que não devem expandir/recolher
 * o card.
 *
 * Histórico combinado (Refatoramento de Metas/Transferências, ver
 * docs/analise-arquitetural-metas-transferencias.md, seção 5): mescla o
 * legado (`useAportesLegadosDaMeta`, `Transacao.meta_id` congelado) com o
 * novo (`useTransferenciasDoCofrinho`, `Transferencia` real do cofrinho),
 * ordenado por data — o usuário nunca precisa saber qual das duas fontes
 * gerou qual linha.
 */
export function MetaResumoCard({ meta, onEditar, onDesativar, onReativar, onExcluir }: MetaResumoCardProps) {
  const [expandido, setExpandido] = useState(false);
  const [aporteAberto, setAporteAberto] = useState(false);
  const [direcaoAporte, setDirecaoAporte] = useState<DirecaoAporteMeta>("APORTE");
  const { data: aportesLegados, isLoading: carregandoLegado } = useAportesLegadosDaMeta(meta.id, expandido);
  const { data: transferencias, isLoading: carregandoTransferencias } = useTransferenciasDoCofrinho(
    meta.conta_id,
    expandido,
  );
  const carregandoAportes = carregandoLegado || carregandoTransferencias;

  const historico = useMemo<ItemHistoricoMeta[]>(() => {
    const doLegado: ItemHistoricoMeta[] = (aportesLegados ?? []).map((transacao) => ({
      chave: `transacao-${transacao.id}`,
      data: transacao.data,
      descricao: transacao.descricao,
      valor: transacao.valor,
      positivo: transacao.tipo === "RECEITA",
    }));
    const doCofrinho: ItemHistoricoMeta[] = (transferencias ?? []).map((transferencia) => ({
      chave: `transferencia-${transferencia.id}`,
      data: transferencia.data,
      descricao: transferencia.descricao ?? (transferencia.conta_destino_id === meta.conta_id ? "Aporte" : "Resgate"),
      valor: transferencia.valor,
      positivo: transferencia.conta_destino_id === meta.conta_id,
    }));
    return [...doLegado, ...doCofrinho].sort((a, b) => b.data.localeCompare(a.data)).slice(0, 10);
  }, [aportesLegados, transferencias, meta.conta_id]);

  const situacao = situacaoDaMeta(meta);
  const percentualNumero = Number(meta.percentual);
  const valorRestante = Math.max(0, Number(meta.valor_alvo) - Number(meta.valor_acumulado));
  const toneProgresso = tonePorUtilizacao(Math.min(percentualNumero, 100));
  const diferencaPlanejado = fraseDiferencaPlanejado(meta);
  const contribuicaoSugerida = fraseContribuicaoSugerida(meta);
  const previsaoConclusao = frasePrevisaoConclusao(meta);
  const tempoParaConcluir = formatarTempoParaConcluir(meta);
  const celebrando = useCelebracaoMeta(meta);

  function alternarExpansao() {
    setExpandido((v) => !v);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      alternarExpansao();
    }
  }

  function abrirAportar() {
    setDirecaoAporte("APORTE");
    setAporteAberto(true);
  }

  function abrirResgatar() {
    setDirecaoAporte("RESGATE");
    setAporteAberto(true);
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={alternarExpansao}
      onKeyDown={onKeyDown}
      aria-expanded={expandido}
      aria-label={`${expandido ? "Recolher" : "Expandir"} detalhes da meta ${meta.descricao}`}
      animateEntrance
      className={`relative flex cursor-pointer flex-col gap-3 ${!meta.ativo ? "opacity-70" : ""}`}
    >
      <MetaCelebracao ativa={celebrando} />

      <div className="flex items-start justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2 text-sm font-medium text-text-primary">
          <Target size={15} className="shrink-0 text-text-tertiary" aria-hidden="true" />
          <span className="truncate">{meta.descricao}</span>
        </span>
        <Badge tone={SITUACAO_META_TONE[situacao]} animateChange className="shrink-0">
          {SITUACAO_META_LABEL[situacao]}
        </Badge>
      </div>

      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-caption text-text-tertiary">Acumulado</p>
          <AnimatedNumber value={meta.valor_acumulado} format="money" className="text-h2 font-semibold text-text-primary" />
          <p className="text-caption text-text-tertiary">de {formatMoney(meta.valor_alvo)}</p>
        </div>
        <div className="text-right">
          <AnimatedNumber
            value={percentualNumero}
            format="percent"
            className={`text-h3 font-semibold ${TEXT_TONE_CLASS[toneProgresso]}`}
          />
        </div>
      </div>

      <ProgressBar
        value={Math.min(percentualNumero, 100)}
        tone={toneProgresso}
        aria-label={`${meta.percentual}% da meta ${meta.descricao}`}
      />

      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-caption text-text-tertiary">
        <span>Faltam {formatMoney(valorRestante)}</span>
        <span>{formatarPrazoMeta(meta.data_alvo)}</span>
      </div>

      {meta.situacao_planejamento && (
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <Badge tone={SITUACAO_PLANEJAMENTO_TONE[meta.situacao_planejamento]} animateChange className="shrink-0">
            {SITUACAO_PLANEJAMENTO_LABEL[meta.situacao_planejamento]}
          </Badge>
          {diferencaPlanejado && <span className="text-caption text-text-secondary">{diferencaPlanejado}</span>}
        </div>
      )}

      {contribuicaoSugerida && <p className="text-caption italic text-text-secondary">{contribuicaoSugerida}</p>}
      {previsaoConclusao && <p className="text-caption italic text-text-secondary">{previsaoConclusao}</p>}

      <AnimatePresence initial={false}>
        {expandido && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto", transition: { duration: DURATION.moderate, ease: EASE.out } }}
            exit={{ opacity: 0, height: 0, transition: { duration: DURATION.fast, ease: EASE.in } }}
            className="overflow-hidden"
          >
            <div
              className="space-y-3 border-t border-border-subtle pt-3"
              onClick={(event) => event.stopPropagation()}
            >
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-caption">
                <dt className="text-text-tertiary">Criada em</dt>
                <dd className="text-right text-text-secondary">{formatDate(meta.criado_em.slice(0, 10))}</dd>
                {meta.concluida_em && (
                  <>
                    <dt className="text-text-tertiary">Concluída em</dt>
                    <dd className="text-right text-text-secondary">{formatDate(meta.concluida_em)}</dd>
                  </>
                )}
                {tempoParaConcluir && (
                  <>
                    <dt className="text-text-tertiary">Tempo até concluir</dt>
                    <dd className="text-right text-text-secondary">{tempoParaConcluir}</dd>
                  </>
                )}
              </dl>

              <p className="text-caption font-medium text-text-tertiary">Aportes e resgates recentes</p>
              {carregandoAportes ? (
                <div className="space-y-1.5">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-full" />
                </div>
              ) : historico.length === 0 ? (
                <p className="text-caption text-text-tertiary">
                  Nenhuma movimentação ainda — use "Aportar" para começar a acompanhar o progresso.
                </p>
              ) : (
                <ul className="space-y-1.5">
                  {historico.map((item) => (
                    <li key={item.chave} className="flex items-center justify-between gap-2 text-sm">
                      <span className="min-w-0 truncate text-text-secondary">
                        {formatDate(item.data)} — {item.descricao}
                      </span>
                      <span
                        className={`tabular shrink-0 font-medium ${item.positivo ? "text-positive" : "text-negative"}`}
                      >
                        {item.positivo ? "+" : "-"} {formatMoney(item.valor)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div onClick={(event) => event.stopPropagation()}>
        <MetaActionBar
          ativo={meta.ativo}
          onEditar={() => onEditar(meta)}
          onAportar={abrirAportar}
          onResgatar={abrirResgatar}
          onDesativar={() => onDesativar(meta)}
          onReativar={() => onReativar(meta)}
          onExcluir={() => onExcluir(meta)}
        />
      </div>

      <ChevronDown
        size={14}
        className={`mx-auto text-text-tertiary transition-transform duration-fast ease-out ${expandido ? "rotate-180" : ""}`}
        aria-hidden="true"
      />

      <div onClick={(event) => event.stopPropagation()}>
        <MetaAporteDialog
          open={aporteAberto}
          meta={meta}
          direcao={direcaoAporte}
          onClose={() => setAporteAberto(false)}
        />
      </div>
    </Card>
  );
}
