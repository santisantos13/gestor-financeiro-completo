/**
 * Wrappers de `useQuery`/`useMutation` para `/contas/*` — mesmo formato de
 * `docs/analise-arquitetural-frontend.md`, seção 9. Nenhuma página guarda
 * `isLoading`/`error` em `useState` manual.
 *
 * Invalidação: `queryKeys.contas.all` (`["contas"]`) invalida list+detail
 * de uma vez só (o React Query casa por prefixo) — é o único jeito de uma
 * mutation de Conta afetar a própria listagem. Além disso, toda mutation
 * que muda dado de Conta também invalida as três chaves do Dashboard que
 * de fato dependem de Conta: `dashboard.contas` (lista detalhada, endpoint
 * separado `/central-financeira/contas`), `dashboard.saldoConsolidado`
 * (soma os saldos) e `dashboard.indicadores` (`contas_ativas`, usado pelo
 * gate de onboarding). Nada mais do Dashboard é invalidado — `resumo`,
 * `visaoMensal`, `agenda`, `cartoes` etc. não dependem de metadado de
 * Conta, então invalidá-los seria refetch sem necessidade.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { contaService } from "../services/contaService";
import type { ContaCreate, ContaUpdate } from "../types/conta";

function useInvalidateContas() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.contas.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.contas });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.saldoConsolidado });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
  };
}

export function useContas(apenasAtivas = true) {
  return useQuery({
    queryKey: queryKeys.contas.list(apenasAtivas),
    queryFn: () => contaService.listar(apenasAtivas),
    // Alternar "mostrar inativas" troca a queryKey (apenasAtivas muda) —
    // sem isso, a tabela pisca um skeleton cheio a cada troca em vez de
    // manter a lista anterior visível até a nova chegar (performance
    // percebida, não uma requisição a menos: o refetch ainda acontece).
    placeholderData: keepPreviousData,
  });
}

export function useConta(id: number | null) {
  return useQuery({
    queryKey: queryKeys.contas.detail(id ?? 0),
    queryFn: () => contaService.obter(id as number),
    enabled: id != null,
  });
}

/** Extrato (histórico expansível) de uma Conta - pedido explícito do
 * usuário, ver docs/analise-arquitetural-extrato-conta.md. `enabled`
 * (mesmo padrão de `useAportesLegadosDaMeta`/`useTransferenciasDoCofrinho`
 * em `useMetaQueries.ts`) existe para `ContaResumoCard` só buscar o
 * extrato quando o card é de fato expandido - a lista de Contas nunca
 * dispara N requisições extras ao carregar. `ano`/`mes` omitidos = mês
 * atual (mesmo default do backend). */
export function useContaExtrato(contaId: number, ano: number | undefined, mes: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.contas.extrato(contaId, ano, mes),
    queryFn: () => contaService.obterExtrato(contaId, ano, mes),
    enabled,
  });
}

export function useCriarConta() {
  const invalidar = useInvalidateContas();
  return useMutation({
    mutationFn: (dados: ContaCreate) => contaService.criar(dados),
    onSuccess: invalidar,
  });
}

export function useAtualizarConta() {
  const invalidar = useInvalidateContas();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: ContaUpdate }) => contaService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

export function useDesativarConta() {
  const invalidar = useInvalidateContas();
  return useMutation({
    mutationFn: (id: number) => contaService.desativar(id),
    onSuccess: invalidar,
  });
}

/** Exclusão DEFINITIVA (hard delete) — Etapa F10,
 * `docs/analise-arquitetural-exclusao.md`. `apagarVinculos` (pedido
 * explícito do usuário, ver
 * docs/analise-arquitetural-exclusao-conta-com-historico.md): quando
 * `true`, apaga tudo vinculado à conta (transações, transferências,
 * cartões — com faturas e transações deles junto —, financiamentos,
 * empréstimos) em vez de bloquear com 422 — usado pela segunda
 * confirmação em `ContaDetalhePage`/`ContasPage`.
 *
 * Invalidação mais ampla que as outras mutations deste arquivo: como a
 * cascata pode apagar Cartão/Fatura/Financiamento/Empréstimo/Transação/
 * Transferência inteiros (não só a própria Conta), invalida também as
 * queryKeys dessas entidades e todo o Dashboard - não só as 3 chaves que
 * `useInvalidateContas` cobre. `invalidateQueries` casa por PREFIXO, então
 * `["financiamentos"]` já invalida `list`/`detail` de qualquer parâmetro,
 * mesmo raciocínio para as demais. */
export function useExcluirConta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, apagarVinculos = false }: { id: number; apagarVinculos?: boolean }) =>
      contaService.excluirPermanente(id, apagarVinculos),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.contas.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.cartoes.all });
      queryClient.invalidateQueries({ queryKey: ["faturas"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.transacoes.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transferencias.all });
      queryClient.invalidateQueries({ queryKey: ["financiamentos"] });
      queryClient.invalidateQueries({ queryKey: ["emprestimos"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
