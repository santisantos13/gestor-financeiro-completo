/**
 * Onze hooks `useQuery`, um por endpoint de `/central-financeira/*` — mesmo
 * formato já documentado em `analise-arquitetural-frontend.md` (seção 9):
 * nenhum componente guarda `isLoading`/`error` em `useState` manual. Central
 * Financeira é 100% leitura, então não há `useMutation` aqui. Ver
 * docs/analise-arquitetural-dashboard.md, seção 6.4 e 16.1 — cada componente
 * de `components/domain/dashboard/` chama exatamente um destes hooks e é,
 * por construção, puro de apresentação.
 */
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { centralFinanceiraService } from "../services/centralFinanceiraService";

export function useResumoFinanceiroQuery(ano?: number, mes?: number) {
  return useQuery({
    queryKey: queryKeys.dashboard.resumo(ano, mes),
    queryFn: () => centralFinanceiraService.resumo(ano, mes),
  });
}

export function useSaldoConsolidadoQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.saldoConsolidado,
    queryFn: centralFinanceiraService.saldoConsolidado,
  });
}

export function useContasQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.contas,
    queryFn: centralFinanceiraService.contas,
  });
}

export function useCartoesQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.cartoes,
    queryFn: centralFinanceiraService.cartoes,
  });
}

/** "Dashboard de Cartões" (Sprint de Refinamento Premium, item 3) — irmão
 * de `useCartoesQuery` acima, não substitui. */
export function useCartoesAgregadoQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.cartoesAgregado,
    queryFn: centralFinanceiraService.cartoesAgregado,
  });
}

export function useFaturasQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.faturas,
    queryFn: centralFinanceiraService.faturas,
  });
}

export function useFinanciamentosQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.financiamentos,
    queryFn: centralFinanceiraService.financiamentos,
  });
}

export function useEmprestimosQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.emprestimos,
    queryFn: centralFinanceiraService.emprestimos,
  });
}

export function useMetasQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.metas,
    queryFn: centralFinanceiraService.metas,
  });
}

export function useAgendaFinanceiraQuery(dias = 30) {
  return useQuery({
    queryKey: queryKeys.dashboard.agenda(dias),
    queryFn: () => centralFinanceiraService.agenda(dias),
  });
}

/** Etapa de Calendário Financeiro — irmão de `useAgendaFinanceiraQuery`
 * acima, não substitui. `ano`/`mes` sempre explícitos (o calendário sempre
 * mostra UM mês navegável, nunca "o mês atual implícito"), diferente de
 * `resumo`/`visaoMensal` (onde ambos são opcionais). */
export function useCalendarioFinanceiroQuery(ano: number, mes: number) {
  return useQuery({
    queryKey: queryKeys.dashboard.calendario(ano, mes),
    queryFn: () => centralFinanceiraService.calendario(ano, mes),
    // Mantém o mês anterior visível durante a navegação entre meses
    // (evita "piscar" para um esqueleto vazio a cada clique de
    // anterior/próximo) — mesmo padrão de `useTransacoes`/`useVisaoMensalQuery`.
    placeholderData: keepPreviousData,
  });
}

/** Central de Atividades (Sprint de Refinamento Premium, item 17) - feed
 * cronológico combinando Transação/Transferência/Meta concluída, aberto a
 * partir de um botão no `Header` (ver `AtividadesRecentesDrawer`). */
export function useAtividadesRecentesQuery(limit = 30) {
  return useQuery({
    queryKey: queryKeys.dashboard.atividades(limit),
    queryFn: () => centralFinanceiraService.atividades(limit),
  });
}

export function useVisaoMensalQuery(ano?: number, mes?: number) {
  return useQuery({
    queryKey: queryKeys.dashboard.visaoMensal(ano, mes),
    queryFn: () => centralFinanceiraService.visaoMensal(ano, mes),
  });
}

export function useIndicadoresGeraisQuery() {
  return useQuery({
    queryKey: queryKeys.dashboard.indicadores,
    queryFn: centralFinanceiraService.indicadores,
  });
}

/** Etapa de Gráficos (docs/analise-arquitetural-graficos.md) — "Evolução do
 * saldo" + "Entradas x Saídas por mês", consumido tanto pelo mini-card do
 * Dashboard quanto pela página `/graficos` (mesmo hook, `meses` diferente
 * em cada lugar). */
export function useGraficosTendenciasQuery(meses = 12) {
  return useQuery({
    queryKey: queryKeys.dashboard.graficosTendencias(meses),
    queryFn: () => centralFinanceiraService.graficosTendencias(meses),
  });
}

/** "Gastos por categoria" + "Gastos por cartão" — irmão do hook acima, não
 * substitui. `keepPreviousData` pelo mesmo motivo de `useCalendarioFinanceiroQuery`
 * (navegação de mês na página `/graficos` não deve "piscar" para um
 * esqueleto vazio). */
export function useGraficosPeriodoQuery(ano?: number, mes?: number) {
  return useQuery({
    queryKey: queryKeys.dashboard.graficosPeriodo(ano, mes),
    queryFn: () => centralFinanceiraService.graficosPeriodo(ano, mes),
    placeholderData: keepPreviousData,
  });
}
