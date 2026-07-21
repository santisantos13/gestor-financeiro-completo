/**
 * Wrappers de `useQuery`/`useMutation` para `/financiamentos/*` — mesmo
 * molde de `useFaturaQueries.ts`. `useFinanciamentos(apenasAtivos)` usa o
 * endpoint próprio (não `dashboard.financiamentos`, que hardcoda
 * `apenas_ativos=True` no backend e nunca mostraria um contrato QUITADO —
 * ver `queryKeys.ts`).
 *
 * Criar um Financiamento gera Transacao reais (entrada opcional + N
 * parcelas), e pagar uma parcela também marca uma Transacao como PAGO e
 * decrementa `saldo_devedor` — por isso as duas mutations reaproveitam
 * `invalidarTransacoes` (mesmo raciocínio de `useCriarParcelamento`/
 * `useRegistrarPagamento`), além de invalidar `financiamentos.list`/
 * `.detail` (prefixo comum) e `dashboard.financiamentos` (o card do
 * Dashboard).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { financiamentoService } from "../services/financiamentoService";
import { transacaoService } from "../services/transacaoService";
import { invalidarTransacoes } from "./useTransacaoQueries";
import type { FinanciamentoCreate, FinanciamentoRead } from "../types/financiamento";

function invalidarFinanciamentos(queryClient: ReturnType<typeof useQueryClient>) {
  // Prefixo ["financiamentos"] casa `list(apenasAtivos)` e qualquer
  // `detail(id)` aberto no momento (mesma técnica de `useFaturaQueries.ts`)
  // — criar ou pagar uma parcela pode mudar status/saldo_devedor de um
  // contrato já visível na lista.
  queryClient.invalidateQueries({ queryKey: ["financiamentos"] });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.financiamentos });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
}

export function useFinanciamentos(apenasAtivos: boolean) {
  return useQuery({
    queryKey: queryKeys.financiamentos.list(apenasAtivos),
    queryFn: () => financiamentoService.listar(apenasAtivos),
  });
}

export function useFinanciamento(id: number | null) {
  return useQuery({
    queryKey: queryKeys.financiamentos.detail(id ?? 0),
    queryFn: () => financiamentoService.obter(id as number),
    enabled: id != null,
  });
}

/** Cronograma de parcelas do Drawer — reaproveita `GET /transacoes?
 * financiamento_id=` (já usado pelo backend/testes) em vez de inventar um
 * endpoint novo só para listar parcelas. `queryKeys.transacoes.list` já
 * aceita qualquer objeto de filtros, então a mesma chave que
 * `invalidarTransacoes` já invalida (prefixo `["transacoes"]`) cobre esta
 * query automaticamente — nenhuma invalidação extra necessária aqui. */
export function useParcelasFinanciamento(financiamentoId: number | null) {
  const filtros = { financiamento_id: financiamentoId ?? undefined, limit: 500 };
  return useQuery({
    queryKey: queryKeys.transacoes.list(filtros),
    queryFn: () => transacaoService.listar(filtros),
    enabled: financiamentoId != null,
  });
}

export function useCriarFinanciamento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: FinanciamentoCreate) => financiamentoService.criar(dados),
    onSuccess: (financiamento: FinanciamentoRead) => {
      invalidarFinanciamentos(queryClient);
      invalidarTransacoes(queryClient, financiamento.conta_id, null);
    },
  });
}

export function usePagarParcelaFinanciamento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, numeroParcela }: { id: number; numeroParcela: number }) =>
      financiamentoService.pagarParcela(id, numeroParcela),
    onSuccess: (financiamento: FinanciamentoRead) => {
      invalidarFinanciamentos(queryClient);
      invalidarTransacoes(queryClient, financiamento.conta_id, null);
    },
  });
}

/** Sempre permitida (mesmo com parcelas pagas) - ver
 * `FinanciamentoService.excluir` (backend). `contaId` é passado pelo
 * chamador (capturado do `FinanciamentoRead` já carregado, antes do 204
 * sem corpo) só para invalidar `contas.detail` daquela conta específica -
 * `invalidarTransacoes` já invalida o prefixo `["transacoes"]` inteiro de
 * qualquer forma. */
export function useExcluirFinanciamento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: number; contaId: number | null }) => financiamentoService.excluir(id),
    onSuccess: (_dados, variaveis) => {
      invalidarFinanciamentos(queryClient);
      invalidarTransacoes(queryClient, variaveis.contaId, null);
    },
  });
}
