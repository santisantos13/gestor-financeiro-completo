/**
 * Wrappers de `useQuery`/`useMutation` para `/cartoes/*` — mesmo molde de
 * `useContaQueries.ts`. Invalidação: `queryKeys.cartoes.all` invalida
 * list+detail; toda mutation também invalida `dashboard.cartoes` e
 * `dashboard.indicadores` (`/central-financeira/cartoes` e
 * `/central-financeira/indicadores`, ambos dependem de Cartão — ver
 * docs/analise-arquitetural-cartao-frontend.md, seção 6). Diferente de
 * Conta, Cartão não tem um "saldo consolidado" equivalente no Dashboard,
 * então `dashboard.saldoConsolidado` nunca é invalidado aqui.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { cartaoService } from "../services/cartaoService";
import type { CartaoCreate, CartaoUpdate } from "../types/cartao";

function useInvalidateCartoes() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.cartoes.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoes });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoesAgregado });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
  };
}

export function useCartoes(apenasAtivas = true) {
  return useQuery({
    queryKey: queryKeys.cartoes.list(apenasAtivas),
    queryFn: () => cartaoService.listar(apenasAtivas),
    // Mesmo tratamento de `useContas`/`useTags` desde o primeiro commit —
    // alternar "mostrar inativos" mantém a lista anterior visível até a
    // nova chegar, em vez de piscar um skeleton cheio.
    placeholderData: keepPreviousData,
  });
}

export function useCartao(id: number | null) {
  return useQuery({
    queryKey: queryKeys.cartoes.detail(id ?? 0),
    queryFn: () => cartaoService.obter(id as number),
    enabled: id != null,
  });
}

export function useCriarCartao() {
  const invalidar = useInvalidateCartoes();
  return useMutation({
    mutationFn: (dados: CartaoCreate) => cartaoService.criar(dados),
    onSuccess: invalidar,
  });
}

export function useAtualizarCartao() {
  const invalidar = useInvalidateCartoes();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: CartaoUpdate }) => cartaoService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

export function useDesativarCartao() {
  const invalidar = useInvalidateCartoes();
  return useMutation({
    mutationFn: (id: number) => cartaoService.desativar(id),
    onSuccess: invalidar,
  });
}

/** Exclusão DEFINITIVA (hard delete) — Etapa F10,
 * `docs/analise-arquitetural-exclusao.md`. `apagarTransacoes` (pedido
 * explícito do usuário, ver
 * docs/analise-arquitetural-exclusao-cartao-com-historico.md): quando
 * `true`, apaga faturas e transações do cartão junto com ele em vez de
 * bloquear com 422 — usado pela segunda confirmação em
 * `CartaoDetalhePage`.
 *
 * Invalidação mais ampla que `useInvalidateCartoes` (bug real encontrado
 * em 2026-07, mesma causa do achado em `useFaturaQueries.ts`): com
 * `apagarTransacoes=true` esta mutation pode apagar faturas e transações
 * inteiras, não só o cartão - sem invalidar `dashboard.calendario`/
 * `dashboard.agenda`/`dashboard.faturas`/`transacoes.all` também, o
 * vencimento de uma fatura já excluída ficava "preso" no Calendário/Agenda
 * até um F5 manual, mesmo a exclusão tendo funcionado de verdade no
 * banco. */
export function useExcluirCartao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, apagarTransacoes = false }: { id: number; apagarTransacoes?: boolean }) =>
      cartaoService.excluirPermanente(id, apagarTransacoes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.cartoes.all });
      queryClient.invalidateQueries({ queryKey: ["faturas"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.transacoes.all });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
