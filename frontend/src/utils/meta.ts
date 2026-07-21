/**
 * Funções puras de APRESENTAÇÃO sobre uma `MetaRead` já calculada pelo
 * backend — nenhuma delas recalcula `valor_acumulado`/`percentual` (esses
 * continuam sendo sempre lidos prontos, nunca reproduzidos, ver
 * docs/analise-arquitetural-metas-frontend.md, seção 1 e resumo de decisões
 * item 5). Tudo aqui é classificação/projeção sobre um número que já veio
 * pronto — mesmo espírito de `utils/status.ts` (`tonePorUtilizacao`/
 * `tonePorPrazo`, que já documentavam desde que foram escritas que a mesma
 * régua serviria para Meta) e do preview não-autoritativo de
 * `utils/fatura.ts` (`preverStatusPosPagamento`).
 *
 * Refinamento de Metas (`docs/analise-arquitetural-metas-refinamento.md`,
 * seção 0): `calcularVelocidadeMeta`/`VelocidadeMeta` foram REMOVIDOS daqui —
 * toda a matemática de planejamento (contribuição sugerida, planejado x
 * realizado, previsão de conclusão) passou a ser calculada pelo
 * `MetaService` e chega pronta em `MetaRead`. As funções abaixo só formatam
 * esses campos prontos em frases — nunca os recalculam.
 */
import type { BadgeTone } from "../components/ui/Badge";
import type { FrequenciaContribuicao, MetaRead, SituacaoPlanejamentoMeta } from "../types/meta";
import { diferencaEmDias, formatDate } from "./date";
import { formatMoney } from "./format";

const DIAS_POR_MES = 30;

// ---- Situação (estado derivado, nunca uma coluna nova do backend) ----

export type SituacaoMeta = "CONCLUIDA" | "ATRASADA" | "EM_ANDAMENTO" | "DESATIVADA";

/** Ordem de prioridade: desativada > concluída > atrasada > em andamento —
 * mesma ordem em que cada estado "vence" visualmente (uma meta desativada
 * nunca aparece como "atrasada", por exemplo, mesmo que a data já tenha
 * passado). */
export function situacaoDaMeta(meta: MetaRead, hoje: Date = new Date()): SituacaoMeta {
  if (!meta.ativo) return "DESATIVADA";
  if (Number(meta.percentual) >= 100) return "CONCLUIDA";
  if (meta.data_alvo != null && diferencaEmDias(meta.data_alvo, hoje) < 0) return "ATRASADA";
  return "EM_ANDAMENTO";
}

export const SITUACAO_META_TONE: Record<SituacaoMeta, BadgeTone> = {
  CONCLUIDA: "positive",
  ATRASADA: "negative",
  EM_ANDAMENTO: "info",
  DESATIVADA: "neutral",
};

export const SITUACAO_META_LABEL: Record<SituacaoMeta, string> = {
  CONCLUIDA: "Concluída",
  ATRASADA: "Atrasada",
  EM_ANDAMENTO: "Em andamento",
  DESATIVADA: "Desativada",
};

// ---- Prazo (formatação de "tempo restante") ----

/** "Faltam N dias" / "Faltam ~N meses" / "Atrasada há N dias" / "Sem prazo
 * definido" — nunca a data crua sozinha (mais fácil de processar de
 * relance, a data completa continua disponível ao abrir/expandir o card). */
export function formatarPrazoMeta(dataAlvo: string | null, hoje: Date = new Date()): string {
  if (!dataAlvo) return "Sem prazo definido";
  const dias = diferencaEmDias(dataAlvo, hoje);
  if (dias < 0) {
    const atraso = Math.abs(dias);
    return `Atrasada há ${atraso} dia${atraso === 1 ? "" : "s"}`;
  }
  if (dias === 0) return "Vence hoje";
  if (dias <= 60) return `Faltam ${dias} dia${dias === 1 ? "" : "s"}`;
  const meses = Math.round(dias / DIAS_POR_MES);
  return `Faltam ~${meses} ${meses === 1 ? "mês" : "meses"}`;
}

// ---- Frequência de contribuição (seção 1 do refinamento) ----

/** Rótulo para o seletor do formulário (`MetaFormDialog`) — a opção "sem
 * frequência" é responsabilidade do próprio campo (`optional`), não desta
 * tabela. */
export const FREQUENCIA_CONTRIBUICAO_LABEL: Record<FrequenciaContribuicao, string> = {
  DIARIA: "Diária",
  SEMANAL: "Semanal",
  QUINZENAL: "Quinzenal",
  MENSAL: "Mensal",
};

/** Sufixo "por período" para compor a frase de contribuição sugerida (ex.
 * "R$1.000 por mês") — mesma tabela de frequências, texto adequado a uma
 * frase em vez de um rótulo de formulário. */
const FREQUENCIA_CONTRIBUICAO_SUFIXO: Record<FrequenciaContribuicao, string> = {
  DIARIA: "por dia",
  SEMANAL: "por semana",
  QUINZENAL: "a cada 15 dias",
  MENSAL: "por mês",
};

/** "Você precisa guardar aproximadamente R$1.000 por mês." — só existe
 * quando o backend já calculou `contribuicao_sugerida_por_periodo` (exige
 * frequência + prazo definidos, prazo não vencido e meta ainda não
 * concluída, seção 1.2 da análise). Nunca recalcula o valor, só formata. */
export function fraseContribuicaoSugerida(meta: MetaRead): string | null {
  if (meta.contribuicao_sugerida_por_periodo == null || meta.frequencia_contribuicao == null) return null;
  const sufixo = FREQUENCIA_CONTRIBUICAO_SUFIXO[meta.frequencia_contribuicao];
  return `Você precisa guardar aproximadamente ${formatMoney(meta.contribuicao_sugerida_por_periodo)} ${sufixo}.`;
}

// ---- Planejado x realizado (seção 2 do refinamento) ----

export const SITUACAO_PLANEJAMENTO_TONE: Record<SituacaoPlanejamentoMeta, BadgeTone> = {
  ADIANTADO: "positive",
  DENTRO_DO_PLANEJADO: "info",
  ATRASADO: "negative",
};

export const SITUACAO_PLANEJAMENTO_LABEL: Record<SituacaoPlanejamentoMeta, string> = {
  ADIANTADO: "Adiantado",
  DENTRO_DO_PLANEJADO: "Dentro do planejado",
  ATRASADO: "Atrasado",
};

/** "Você está R$350 acima do planejado." / "Você está R$180 abaixo do
 * planejado." — sinal de `diferenca_planejado_realizado` já vem pronto do
 * backend (positivo = acima, negativo = abaixo, seção 2.2); aqui só se
 * escolhe a palavra e formata o valor absoluto. `null` sem `data_alvo`
 * (mesma condição de `situacao_planejamento`). */
export function fraseDiferencaPlanejado(meta: MetaRead): string | null {
  if (meta.diferenca_planejado_realizado == null) return null;
  const diferenca = Number(meta.diferenca_planejado_realizado);
  const rotulo = diferenca >= 0 ? "acima" : "abaixo";
  return `Você está ${formatMoney(Math.abs(diferenca))} ${rotulo} do planejado.`;
}

// ---- Previsão de conclusão (seção 3 do refinamento) ----

/** "No ritmo atual você concluirá esta Meta aproximadamente em 18/09/2027."
 * — `null` quando o backend não tem dados suficientes para uma previsão
 * confiável (`data_prevista_conclusao` é `null`, seção 3.1); a ausência
 * deliberada da informação já é tratada pelo próprio componente (não exibe
 * nada), não por esta função. */
export function frasePrevisaoConclusao(meta: MetaRead): string | null {
  if (meta.data_prevista_conclusao == null) return null;
  return `No ritmo atual você concluirá esta Meta aproximadamente em ${formatDate(meta.data_prevista_conclusao)}.`;
}

// ---- Histórico (seção 5 do refinamento) ----

/** "N dias" / "N meses" entre `criado_em` e `concluida_em` — só chamada
 * quando a meta já foi concluída (`concluida_em` não-nulo), mesma aritmética
 * pura de calendário de `diferencaEmDias`. */
export function formatarTempoParaConcluir(meta: MetaRead): string | null {
  if (meta.concluida_em == null) return null;
  const criadoEm = new Date(meta.criado_em);
  const concluidaEm = new Date(meta.concluida_em);
  const dias = Math.max(0, Math.round((concluidaEm.getTime() - criadoEm.getTime()) / 86_400_000));
  if (dias < 60) return `${dias} dia${dias === 1 ? "" : "s"}`;
  const meses = Math.round(dias / DIAS_POR_MES);
  return `~${meses} ${meses === 1 ? "mês" : "meses"}`;
}

// ---- Ordenação (client-side, volume baixo — mesmo raciocínio de Cartão/Financiamento) ----

export type CriterioOrdenacaoMeta = "PROXIMA_CONCLUSAO" | "MAIS_DISTANTE" | "VENCIMENTO" | "MAIOR_VALOR" | "MENOR_VALOR";

export const CRITERIO_ORDENACAO_META_LABEL: Record<CriterioOrdenacaoMeta, string> = {
  PROXIMA_CONCLUSAO: "Mais próxima da conclusão",
  MAIS_DISTANTE: "Mais distante da conclusão",
  VENCIMENTO: "Vencimento mais próximo",
  MAIOR_VALOR: "Maior valor",
  MENOR_VALOR: "Menor valor",
};

export const CRITERIO_ORDENACAO_META_OPTIONS: CriterioOrdenacaoMeta[] = [
  "VENCIMENTO",
  "PROXIMA_CONCLUSAO",
  "MAIS_DISTANTE",
  "MAIOR_VALOR",
  "MENOR_VALOR",
];

/** Nunca muta a lista recebida (`[...metas]` antes de ordenar) — mesmo
 * cuidado de qualquer ordenação client-side do projeto (o array que vem do
 * React Query não deve ser mutado in-place). Metas sem `data_alvo` sempre
 * vão para o fim em `VENCIMENTO`, em qualquer direção. */
export function ordenarMetas(metas: MetaRead[], criterio: CriterioOrdenacaoMeta): MetaRead[] {
  const copia = [...metas];
  switch (criterio) {
    case "PROXIMA_CONCLUSAO":
      return copia.sort((a, b) => Number(b.percentual) - Number(a.percentual));
    case "MAIS_DISTANTE":
      return copia.sort((a, b) => Number(a.percentual) - Number(b.percentual));
    case "VENCIMENTO":
      return copia.sort((a, b) => {
        if (a.data_alvo == null && b.data_alvo == null) return 0;
        if (a.data_alvo == null) return 1;
        if (b.data_alvo == null) return -1;
        return a.data_alvo.localeCompare(b.data_alvo);
      });
    case "MAIOR_VALOR":
      return copia.sort((a, b) => Number(b.valor_alvo) - Number(a.valor_alvo));
    case "MENOR_VALOR":
      return copia.sort((a, b) => Number(a.valor_alvo) - Number(b.valor_alvo));
    default:
      return copia;
  }
}
