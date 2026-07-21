/**
 * Wrappers de `useQuery`/`useMutation` para `/transferencias/*` - mesmo
 * molde de `useTransacaoQueries.ts`. Ver
 * docs/analise-arquitetural-transferencias-frontend.md, seção 4.
 *
 * Diferença chave em relação a Transação: uma transferência afeta DUAS
 * contas (origem e destino), não uma - `invalidarTransferencias` recebe os
 * dois ids e invalida ambos os `queryKeys.contas.detail`. `contas.all` já
 * casaria os dois por prefixo sozinho, mas os dois `detail` explícitos são
 * mantidos por legibilidade (mesmo raciocínio já registrado em
 * `useTransacaoQueries.ts`).
 *
 * Também invalida `dashboard.calendario` por PREFIXO (`["dashboard",
 * "calendario"]`, sem `ano`/`mes`) - mesmo raciocínio de `resumo`/
 * `visao-mensal`: a chave real sempre tem os dois parâmetros
 * (`["dashboard","calendario",2026,7]`), então invalidar sem eles casa
 * qualquer mês já em cache.
 *
 * Refatoramento de Metas/Transferências (ver
 * docs/analise-arquitetural-metas-transferencias.md, seção 4): aporte/
 * resgate de Meta agora É uma Transferencia comum, então toda mutation
 * aqui também invalida `metas.all`/`dashboard.metas` - não há como saber de
 * antemão se uma das duas contas envolvidas é o "cofrinho" de alguma Meta
 * sem olhar o payload, e o custo de invalidar sempre é desprezível (mesmo
 * raciocínio já usado em `useTransacaoQueries.ts` para `dashboard.indicadores`).
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { transferenciaService } from "../services/transferenciaService";
import type { TransferenciaCreate, TransferenciaFiltros, TransferenciaRead } from "../types/transferencia";

export function invalidarTransferencias(
  queryClient: QueryClient,
  contaOrigemId?: number | null,
  contaDestinoId?: number | null,
) {
  queryClient.invalidateQueries({ queryKey: queryKeys.transferencias.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.contas.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.saldoConsolidado });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.contas });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.metas });
  queryClient.invalidateQueries({ queryKey: queryKeys.metas.all });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "resumo"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "visao-mensal"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "agenda"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "calendario"] });
  if (contaOrigemId != null) {
    queryClient.invalidateQueries({ queryKey: queryKeys.contas.detail(contaOrigemId) });
  }
  if (contaDestinoId != null) {
    queryClient.invalidateQueries({ queryKey: queryKeys.contas.detail(contaDestinoId) });
  }
}

export function useTransferencias(apenasAtivas = true) {
  const filtros: TransferenciaFiltros = { apenas_ativas: apenasAtivas, limit: 200 };
  return useQuery({
    queryKey: queryKeys.transferencias.list(apenasAtivas),
    queryFn: () => transferenciaService.listar(filtros),
    placeholderData: keepPreviousData,
  });
}

export function useCriarTransferencia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: TransferenciaCreate) => transferenciaService.criar(dados),
    onSuccess: (transferencia: TransferenciaRead) => {
      invalidarTransferencias(queryClient, transferencia.conta_origem_id, transferencia.conta_destino_id);
    },
  });
}

/** `contaOrigemId`/`contaDestinoId` vêm de quem chama (a `TransferenciaRead`
 * sendo cancelada já é conhecida antes da mutation) - evita esperar a
 * resposta do cancelamento para saber quais `detail` invalidar. */
export function useCancelarTransferencia(contaOrigemId?: number | null, contaDestinoId?: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => transferenciaService.cancelar(id),
    onSuccess: () => invalidarTransferencias(queryClient, contaOrigemId, contaDestinoId),
  });
}
