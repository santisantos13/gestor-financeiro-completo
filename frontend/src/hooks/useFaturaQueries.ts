/**
 * Wrappers de `useQuery`/`useMutation` para `/faturas/*` — mesmo molde de
 * `useCartaoQueries.ts`. Diferente das demais entidades, toda listagem é
 * escopada a um `cartaoId` (`useFaturas(cartaoId)`), e não existe
 * `useAtualizarFatura` — as únicas mutações são as ações de negócio
 * (criar, fechar, registrar pagamento, excluir), cada uma com seu próprio
 * hook. Invalidação toca `faturas.list(cartaoId)` **e**
 * `dashboard.faturas`/`dashboard.cartoes` (a Central Financeira agrega os
 * mesmos dados — mesmo cuidado de invalidação cruzada de
 * `useCartaoQueries.ts`).
 *
 * `useRegistrarPagamento` também invalida tudo que `invalidarTransacoes`
 * (`useTransacaoQueries.ts`) já cobre — achado real do Refinamento de
 * Fatura/Pagamento (`docs/analise-arquitetural-refinamento-fatura-pagamento.md`,
 * seção 2): `FaturaService.registrar_pagamento` cria uma `Transacao` de
 * verdade (despesa na conta de pagamento do cartão), então sem isso
 * `/transacoes`, o saldo da Conta e a maior parte do Dashboard não
 * refletiam o pagamento sem um F5 manual.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { faturaService } from "../services/faturaService";
import { invalidarTransacoes } from "./useTransacaoQueries";
import type {
  FaturaAjusteManualUpdate,
  FaturaAjustePosFechamentoCreate,
  FaturaCreate,
  FaturaImportarCreate,
  FaturaPagamentoCreate,
  FaturaPagamentoEmLoteCreate,
} from "../types/fatura";

function useInvalidateFaturas(cartaoId: number) {
  const queryClient = useQueryClient();
  return () => {
    // Prefixo ["faturas"] casa tanto `list(cartaoId)` quanto qualquer
    // `detail(id)` aberto no momento (ex. o `FaturaDrawer` de uma fatura
    // específica) — mais simples e mais seguro do que invalidar só a
    // lista e esquecer o detail de uma fatura que acabou de mudar de
    // status por uma ação feita a partir da própria lista.
    queryClient.invalidateQueries({ queryKey: ["faturas"] });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.faturas });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoes });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoesAgregado });
    // `cartoes.all` (nunca só `cartoes.detail(cartaoId)`) — bug crítico real
    // encontrado (2026-07, ver docs/analise-arquitetural-limite-cartao-invalidacao.md):
    // `list`/`detail` são ramos IRMÃOS da chave de Cartão (`list` não é
    // descendente de `detail`), então invalidar só `detail(cartaoId)` nunca
    // re-buscava `/cartoes` (`CartoesPage`) nem o `CardSelect` de
    // `/transacoes` — os dois continuavam mostrando `limite_disponivel`
    // desatualizado depois de pagar/fechar/excluir uma fatura, mesmo o
    // backend já recalculando corretamente a cada leitura. `all` é prefixo
    // dos dois ramos, mesmo padrão que `useCartaoQueries.ts` já usava para
    // as mutations do próprio Cartão.
    queryClient.invalidateQueries({ queryKey: queryKeys.cartoes.all });
    // Bug real encontrado (2026-07): faturas têm data de vencimento, que
    // aparece tanto na Agenda ("próximos N dias") quanto no Calendário
    // (mês inteiro) - criar/fechar/excluir uma fatura sem invalidar essas
    // duas chaves deixava vencimento de fatura já excluída (ou de uma
    // criada agora) "preso" no cache até um F5 manual. Mesmo raciocínio de
    // `invalidarTransacoes` (`useTransacaoQueries.ts`), que já cobria isso
    // do lado de Transação mas não do lado de Fatura. `resumo`/
    // `visao-mensal` também dependem do total de faturas do mês.
    queryClient.invalidateQueries({ queryKey: ["dashboard", "calendario"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "agenda"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "resumo"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "visao-mensal"] });
  };
}

export function useFaturas(cartaoId: number | null) {
  return useQuery({
    queryKey: queryKeys.faturas.list(cartaoId ?? 0),
    queryFn: () => faturaService.listar(cartaoId as number),
    enabled: cartaoId != null,
  });
}

export function useFatura(id: number | null) {
  return useQuery({
    queryKey: queryKeys.faturas.detail(id ?? 0),
    queryFn: () => faturaService.obter(id as number),
    enabled: id != null,
  });
}

export function useCriarFatura(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: (dados: FaturaCreate) => faturaService.criar(dados),
    onSuccess: invalidar,
  });
}

/** Etapa de Onboarding: mesma invalidação de `useCriarFatura` — a fatura
 * importada é só uma variação de criação (nasce FECHADA em vez de
 * ABERTA), o efeito sobre Dashboard/Central Financeira é idêntico. */
export function useImportarFatura(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: (dados: FaturaImportarCreate) => faturaService.importar(dados),
    onSuccess: invalidar,
  });
}

export function useFecharFatura(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: (id: number) => faturaService.fechar(id),
    onSuccess: invalidar,
  });
}

/** `contaId` = `Cartao.conta_pagamento_id` — quem chama já tem esse dado
 * (a página/drawer já carregou o `CartaoRead` para chegar até aqui), então
 * é passado explicitamente em vez de o hook precisar buscá-lo de novo. */
export function useRegistrarPagamento(cartaoId: number, contaId?: number | null) {
  const invalidar = useInvalidateFaturas(cartaoId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: FaturaPagamentoCreate }) =>
      faturaService.registrarPagamento(id, dados),
    onSuccess: () => {
      invalidar();
      invalidarTransacoes(queryClient, contaId, cartaoId);
    },
  });
}

/** Declara o saldo já usado do ciclo ABERTO diretamente, sem nenhuma
 * Transacao — pedido explícito do usuário. Mesma invalidação das demais
 * mutações de Fatura: `limite_disponivel` do Cartão muda junto (ver
 * `CartaoRepository.somar_gastos_nao_pagos` no backend), por isso
 * `queryKeys.cartoes.all` também é invalidado aqui. */
export function useAjustarSaldoInicialFatura(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: FaturaAjusteManualUpdate }) =>
      faturaService.ajustarSaldoInicial(id, dados),
    onSuccess: invalidar,
  });
}

/** Soma um valor esquecido ao total de uma fatura JÁ FECHADA (ou paga/
 * atrasada/parcial), sem criar nenhuma Transacao — pedido explícito do
 * usuário (2026-07-20): "quero adicionar uma transação em uma fatura que
 * já foi fechada e paga, porém tinha esquecido dela antes". Mesma
 * invalidação de `useAjustarSaldoInicialFatura` (`limite_disponivel` muda
 * junto, mesmo raciocínio). */
export function useAjustarValorPosFechamento(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: FaturaAjustePosFechamentoCreate }) =>
      faturaService.ajustarValorPosFechamento(id, dados),
    onSuccess: invalidar,
  });
}

export function useExcluirFatura(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: (id: number) => faturaService.excluir(id),
    onSuccess: invalidar,
  });
}

/** Pedido explícito do usuário: "quero poder selecionar várias faturas
 * para excluir" — usado pela seleção múltipla em `CartaoDetalhePage`
 * (`BulkActions`/`SelectionCheckbox`, mesma infraestrutura genérica já
 * usada por `DataTable`). Mesma invalidação de `useExcluirFatura` (a
 * função é a mesma, só a mutation muda). */
export function useExcluirFaturasEmLote(cartaoId: number) {
  const invalidar = useInvalidateFaturas(cartaoId);
  return useMutation({
    mutationFn: (ids: number[]) => faturaService.excluirEmLote(ids),
    onSuccess: invalidar,
  });
}

/** Pedido explícito do usuário: "seria interessante poder pagar todas
 * selecionadas" — mesma seleção múltipla de `useExcluirFaturasEmLote`,
 * agora para registrar pagamento. Mesma invalidação de
 * `useRegistrarPagamento` (o pagamento em lote também cria `Transacao`
 * reais na conta de pagamento do cartão — precisa do mesmo `contaId` para
 * `invalidarTransacoes`). */
export function usePagarFaturasEmLote(cartaoId: number, contaId?: number | null) {
  const invalidar = useInvalidateFaturas(cartaoId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: FaturaPagamentoEmLoteCreate) => faturaService.pagarEmLote(dados),
    onSuccess: () => {
      invalidar();
      invalidarTransacoes(queryClient, contaId, cartaoId);
    },
  });
}
