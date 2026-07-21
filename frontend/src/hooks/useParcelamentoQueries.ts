/**
 * `useCriarParcelamento` — usado exclusivamente pelo fluxo "Parcelado" de
 * `TransacaoFormDialog`. `useParcelamento(id)` — leitura só (sem
 * mutations), usada pelo diálogo de confirmação de exclusão de compra
 * parcelada em `TransacoesPage` para mostrar `num_parcelas` real (ver
 * docs/analise-arquitetural-escopo-parcelamento.md, seção 4). Sem
 * `useParcelamentos`/listagem: não existe página própria de Parcelamentos
 * ainda (pedido do usuário era só a escolha à vista/parcelado na hora de
 * lançar a compra, não um CRUD completo da entidade).
 *
 * Invalidação de `useCriarParcelamento` reaproveita `invalidarTransacoes`
 * (`useTransacaoQueries.ts`) em vez de duplicar a mesma lista de
 * queryKeys — criar um Parcelamento GERA N `Transacao` reais no backend
 * (`ParcelamentoService._gerar_parcelas`), então o efeito sobre
 * saldo/limite/Dashboard é idêntico ao de criar uma transação normal na
 * mesma conta/cartão. Cancelamento de Parcelamento não tem hook próprio
 * aqui: hoje só acontece implicitamente via `useExcluirTransacao`
 * (excluir qualquer parcela cancela o parcelamento inteiro no backend,
 * ver `TransacaoService._aplicar_exclusao_de_parcela`) — `queryKeys.
 * parcelamentos.all` cobre `detail(id)` por prefixo, então nenhuma
 * invalidação extra precisou ser adicionada em `useTransacaoQueries.ts`
 * para isso.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { parcelamentoService } from "../services/parcelamentoService";
import { invalidarTransacoes } from "./useTransacaoQueries";
import type { ParcelamentoCreate, ParcelamentoRead } from "../types/parcelamento";

export function useParcelamento(id: number | null) {
  return useQuery({
    queryKey: queryKeys.parcelamentos.detail(id ?? 0),
    queryFn: () => parcelamentoService.obter(id as number),
    enabled: id != null,
  });
}

export function useCriarParcelamento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: ParcelamentoCreate) => parcelamentoService.criar(dados),
    onSuccess: (parcelamento: ParcelamentoRead) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.parcelamentos.all });
      invalidarTransacoes(queryClient, parcelamento.conta_id, parcelamento.cartao_id);
    },
  });
}
