/**
 * Funções finas e tipadas, uma por endpoint de `/central-financeira/*` —
 * mesmo padrão de `authService.ts` (analise-arquitetural-frontend.md,
 * seção 5): zero decisão, só chamam `httpClient`. Consumidas exclusivamente
 * pelos hooks de `hooks/useCentralFinanceiraQueries.ts`, nunca direto de um
 * componente. Ver docs/analise-arquitetural-dashboard.md, seção 6.2.
 */
import { httpClient } from "../api/httpClient";
import type {
  AgendaFinanceiraRead,
  CalendarioFinanceiroRead,
  CentralAtividadesRead,
  GraficosPeriodoRead,
  GraficosTendenciasRead,
  IndicadoresGeraisRead,
  ProgressoMetasRead,
  ResumoCartoesAgregadoRead,
  ResumoCartoesRead,
  ResumoContasRead,
  ResumoEmprestimosRead,
  ResumoFaturasRead,
  ResumoFinanceiroRead,
  ResumoFinanciamentosRead,
  SaldoConsolidadoRead,
  VisaoMensalRead,
} from "../types/centralFinanceira";

export const centralFinanceiraService = {
  resumo: (ano?: number, mes?: number) =>
    httpClient.get<ResumoFinanceiroRead>("/central-financeira/resumo", { ano, mes }),

  saldoConsolidado: () =>
    httpClient.get<SaldoConsolidadoRead>("/central-financeira/saldo-consolidado"),

  contas: () => httpClient.get<ResumoContasRead>("/central-financeira/contas"),

  cartoes: () => httpClient.get<ResumoCartoesRead>("/central-financeira/cartoes"),

  /** "Dashboard de Cartões" (Sprint de Refinamento Premium, item 3) —
   * irmão de `cartoes` acima, não substitui (aquele continua a lista
   * crua usada por `FaturasCard`/etc. para montar o mapa de nomes). */
  cartoesAgregado: () =>
    httpClient.get<ResumoCartoesAgregadoRead>("/central-financeira/cartoes/agregado"),

  faturas: () => httpClient.get<ResumoFaturasRead>("/central-financeira/faturas"),

  financiamentos: () =>
    httpClient.get<ResumoFinanciamentosRead>("/central-financeira/financiamentos"),

  emprestimos: () =>
    httpClient.get<ResumoEmprestimosRead>("/central-financeira/emprestimos"),

  metas: () => httpClient.get<ProgressoMetasRead>("/central-financeira/metas"),

  agenda: (dias = 30) =>
    httpClient.get<AgendaFinanceiraRead>("/central-financeira/agenda", { dias }),

  /** Etapa de Calendário Financeiro — irmão de `agenda` acima, não
   * substitui (ver docs/analise-arquitetural-transferencias-frontend.md). */
  calendario: (ano?: number, mes?: number) =>
    httpClient.get<CalendarioFinanceiroRead>("/central-financeira/calendario", { ano, mes }),

  /** Central de Atividades (Sprint de Refinamento Premium, item 17) —
   * feed cronológico combinando Transação/Transferência/Meta concluída. */
  atividades: (limit = 30) =>
    httpClient.get<CentralAtividadesRead>("/central-financeira/atividades", { limit }),

  visaoMensal: (ano?: number, mes?: number) =>
    httpClient.get<VisaoMensalRead>("/central-financeira/visao-mensal", { ano, mes }),

  indicadores: () =>
    httpClient.get<IndicadoresGeraisRead>("/central-financeira/indicadores"),

  /** Etapa de Gráficos (docs/analise-arquitetural-graficos.md) — "Evolução
   * do saldo" + "Entradas x Saídas por mês" (janela dos últimos `meses`
   * meses, padrão 12). */
  graficosTendencias: (meses = 12) =>
    httpClient.get<GraficosTendenciasRead>("/central-financeira/graficos/tendencias", { meses }),

  /** "Gastos por categoria" + "Gastos por cartão" (escopo de um único mês,
   * padrão mês atual) — irmão de `graficosTendencias` acima, não substitui. */
  graficosPeriodo: (ano?: number, mes?: number) =>
    httpClient.get<GraficosPeriodoRead>("/central-financeira/graficos/periodo", { ano, mes }),
};
