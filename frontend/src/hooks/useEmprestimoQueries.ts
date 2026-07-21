/**
 * Wrappers de `useQuery`/`useMutation` para `/emprestimos/*` — mesmo
 * raciocínio de `useFinanciamentoQueries.ts` (`useEmprestimos(apenasAtivos)`
 * usa o endpoint próprio, não `dashboard.emprestimos`; mutations
 * reaproveitam `invalidarTransacoes`).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { emprestimoService } from "../services/emprestimoService";
import { transacaoService } from "../services/transacaoService";
import { invalidarTransacoes } from "./useTransacaoQueries";
import type { EmprestimoCreate, EmprestimoRead } from "../types/emprestimo";

function invalidarEmprestimos(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["emprestimos"] });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.emprestimos });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
}

export function useEmprestimos(apenasAtivos: boolean) {
  return useQuery({
    queryKey: queryKeys.emprestimos.list(apenasAtivos),
    queryFn: () => emprestimoService.listar(apenasAtivos),
  });
}

export function useEmprestimo(id: number | null) {
  return useQuery({
    queryKey: queryKeys.emprestimos.detail(id ?? 0),
    queryFn: () => emprestimoService.obter(id as number),
    enabled: id != null,
  });
}

/** Mesmo raciocínio de `useParcelasFinanciamento` — reaproveita `GET
 * /transacoes?emprestimo_id=` em vez de um endpoint novo. */
export function useParcelasEmprestimo(emprestimoId: number | null) {
  const filtros = { emprestimo_id: emprestimoId ?? undefined, limit: 500 };
  return useQuery({
    queryKey: queryKeys.transacoes.list(filtros),
    queryFn: () => transacaoService.listar(filtros),
    enabled: emprestimoId != null,
  });
}

export function useCriarEmprestimo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: EmprestimoCreate) => emprestimoService.criar(dados),
    onSuccess: (emprestimo: EmprestimoRead) => {
      invalidarEmprestimos(queryClient);
      invalidarTransacoes(queryClient, emprestimo.conta_id, null);
    },
  });
}

export function usePagarParcelaEmprestimo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, numeroParcela }: { id: number; numeroParcela: number }) =>
      emprestimoService.pagarParcela(id, numeroParcela),
    onSuccess: (emprestimo: EmprestimoRead) => {
      invalidarEmprestimos(queryClient);
      invalidarTransacoes(queryClient, emprestimo.conta_id, null);
    },
  });
}

/** Espelha `useExcluirFinanciamento` - sempre permitida, mesmo com
 * parcelas já pagas (ver `EmprestimoService.excluir`, backend). */
export function useExcluirEmprestimo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: number; contaId: number | null }) => emprestimoService.excluir(id),
    onSuccess: (_dados, variaveis) => {
      invalidarEmprestimos(queryClient);
      invalidarTransacoes(queryClient, variaveis.contaId, null);
    },
  });
}
