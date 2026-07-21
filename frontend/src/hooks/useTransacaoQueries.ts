/**
 * Wrappers de `useQuery`/`useMutation` para `/transacoes/*` — mesmo molde
 * de `useCartaoQueries.ts`. Ver
 * docs/analise-arquitetural-transacao-frontend.md, seção 9.
 *
 * Invalidação é a mais ampla do projeto até agora: uma transação nova,
 * editada ou excluída pode mudar saldo de Conta, limite de Cartão e/ou
 * Fatura, então toda mutation invalida praticamente todo o Dashboard, além
 * de `contas.all`/`cartoes.all` (nunca só `.detail` — ver
 * docs/analise-arquitetural-escopo-parcelamento.md, seção 3: `list`/
 * `detail` são ramos IRMÃOS da chave de Conta/Cartão, não pai/filho, então
 * `/contas`, `/cartoes` e o `CardSelect` de `/transacoes` — todos
 * baseados em `list` — ficavam com dado desatualizado mesmo depois de
 * `.detail` já ter sido invalidado corretamente) e `["faturas"]` (mesmo
 * raciocínio, para o total derivado da Fatura do ciclo da compra).
 *
 * `dashboard.metas`/`dashboard.calendario` também são invalidados aqui —
 * histórico legado: uma Transação antiga pode ainda carregar `meta_id`
 * (congelado, nunca mais escrito por um formulário novo desde o
 * Refatoramento de Metas/Transferências, ver
 * docs/analise-arquitetural-metas-transferencias.md, seção 6), então
 * qualquer edição numa Transação existente pode mudar o
 * `valor_acumulado`/`percentual` de uma Meta. Invalidar sempre (mesmo custo
 * desprezível de `dashboard.indicadores`, que já era invalidado
 * incondicionalmente) é mais simples do que checar `meta_id` em cada
 * mutation antes de decidir.
 *
 * `invalidarTransacoes` é uma função comum (não um hook) que recebe o
 * `queryClient` já resolvido — evita violar a regra dos hooks: precisa ser
 * chamada dentro de `onSuccess` (fora do render), e só `useQueryClient()`
 * em si é um hook, não a invalidação que vem depois dele.
 *
 * Exportada (não mais privada do módulo) desde o Refinamento de
 * Fatura/Pagamento (`docs/analise-arquitetural-refinamento-fatura-pagamento.md`,
 * seção 2): `FaturaService.registrar_pagamento` também cria uma `Transacao`
 * de verdade (despesa na conta de pagamento do cartão) — `useFaturaQueries.ts`
 * reaproveita esta mesma função em vez de duplicar a lista de invalidações.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { transacaoService } from "../services/transacaoService";
import type { TransacaoCreate, TransacaoFiltros, TransacaoRead, TransacaoUpdate } from "../types/transacao";

export function invalidarTransacoes(
  queryClient: QueryClient,
  contaId?: number | null,
  cartaoId?: number | null,
) {
  queryClient.invalidateQueries({ queryKey: queryKeys.transacoes.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.saldoConsolidado });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.contas });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoes });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoesAgregado });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.faturas });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.metas });
  queryClient.invalidateQueries({ queryKey: queryKeys.metas.all });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "calendario"] });
  // `resumo`/`visaoMensal`/`agenda` dependem de parâmetro (`ano`/`mes`/
  // `dias`) — invalidados pelo PREFIXO (`["dashboard", "resumo"]`, sem os
  // parâmetros), nunca chamando a função da chave sem argumento (isso
  // geraria `[..., undefined, undefined]`, que só bateria por igualdade
  // exata e nunca casaria com uma chave real como `[..., 2026, 7]`). Mesmo
  // raciocínio de `queryKeys.contas.all` casando `list`+`detail` de uma
  // vez só por prefixo comum.
  queryClient.invalidateQueries({ queryKey: ["dashboard", "resumo"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "visao-mensal"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "agenda"] });
  // `contas.all` (nunca só `contas.detail(contaId)`) — mesma classe de bug
  // já corrigida do lado de Cartão logo abaixo: `list`/`detail` são ramos
  // IRMÃOS da chave de Conta também, então uma transação criada/editada/
  // excluída numa conta deixava `/contas` (`ContasPage`, que usa
  // `contas.list`) com `saldo_atual` desatualizado, mesmo a página de
  // detalhe (`contas.detail`) já se atualizando corretamente. `all` é
  // prefixo dos dois ramos - mesmo padrão que `useContaQueries.ts` e
  // `invalidarTransferencias` (`useTransferenciaQueries.ts`) já usavam;
  // só esta função ainda usava a chave estreita.
  if (contaId != null) {
    queryClient.invalidateQueries({ queryKey: queryKeys.contas.all });
  }
  if (cartaoId != null) {
    // `cartoes.all` (nunca só `cartoes.detail(cartaoId)`) — bug crítico real
    // encontrado (2026-07, ver docs/analise-arquitetural-limite-cartao-invalidacao.md):
    // `list`/`detail` são ramos IRMÃOS da chave de Cartão, então invalidar só
    // `detail(cartaoId)` nunca re-buscava `/cartoes` (`CartoesPage`) nem o
    // `CardSelect` de `/transacoes` — uma compra criada/editada/excluída no
    // cartão continuava mostrando `limite_disponivel` desatualizado nessas
    // duas telas, mesmo o backend recalculando corretamente a cada leitura
    // (não há campo `limite_utilizado` persistido nem aqui nem lá). `all` é
    // prefixo dos dois ramos, sempre invalidado independente de `cartaoId` ser
    // conhecido de imediato — mesma robustez de `dashboard.cartoes` acima.
    queryClient.invalidateQueries({ queryKey: queryKeys.cartoes.all });
    // `["faturas"]` (prefixo cru, mesma chave que `useInvalidateFaturas` já
    // usa) — segunda inconsistência real encontrada na mesma auditoria: uma
    // compra de cartão tem `fatura_id`, então criar/editar/excluir uma
    // compra muda o `valor_total_calculado`/`status_calculado` DERIVADO da
    // fatura correspondente (`FaturaService._com_valores_calculados`), mas
    // até aqui só `dashboard.faturas` (o agregado da Central Financeira) era
    // invalidado - a lista de faturas de UM cartão (`useFaturas(cartaoId)`,
    // usada em `CartaoDetalhePage`) ficava com o total antigo até um F5,
    // mesmo o `limite_disponivel` do cartão (acima) já corrigido. Não dá pra
    // saber de antemão qual fatura foi afetada sem uma consulta extra - o
    // prefixo cobre `list(cartaoId)` e qualquer `detail(id)` aberto, mesmo
    // custo desprezível já aceito em `useInvalidateFaturas`.
    queryClient.invalidateQueries({ queryKey: ["faturas"] });
  }
}

export function useTransacoes(filtros: TransacaoFiltros = {}) {
  return useQuery({
    queryKey: queryKeys.transacoes.list(filtros),
    queryFn: () => transacaoService.listar(filtros),
    placeholderData: keepPreviousData,
  });
}

export function useTransacao(id: number | null) {
  return useQuery({
    queryKey: queryKeys.transacoes.detail(id ?? 0),
    queryFn: () => transacaoService.obter(id as number),
    enabled: id != null,
  });
}

/** Histórico de compras de UMA fatura (`FaturaDrawer`, expansível — pedido
 * do usuário, 2026-07-20). `enabled` segue o mesmo padrão de
 * `useAportesLegadosDaMeta`/`useContaExtrato`: só busca quando a seção é
 * de fato expandida, evitando N requisições extras ao só abrir a lista de
 * faturas do cartão. `fatura_id` filtra as compras lançadas naquele
 * ciclo — nunca o pagamento da fatura (`fatura_paga_id`, Transacao
 * separada, ver TransacaoRepository.listar_do_usuario). */
export function useComprasDaFatura(faturaId: number, enabled: boolean) {
  const filtros = { fatura_id: faturaId, limit: 200 };
  return useQuery({
    queryKey: queryKeys.transacoes.list(filtros),
    queryFn: () => transacaoService.listar(filtros),
    enabled,
  });
}

/** Origem só é conhecida depois da resposta (o formulário de criação não
 * tem `contaId`/`cartaoId` "atual" antes de o backend confirmar), por isso
 * a invalidação lê `transacao.conta_id`/`transacao.cartao_id` da própria
 * resposta em vez de receber parâmetro. */
export function useCriarTransacao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: TransacaoCreate) => transacaoService.criar(dados),
    onSuccess: (transacao: TransacaoRead) => {
      invalidarTransacoes(queryClient, transacao.conta_id, transacao.cartao_id);
    },
  });
}

/** `contaId`/`cartaoId` vêm de quem chama (a `TransacaoRead` sendo editada
 * já é conhecida antes da mutation) — evita esperar a resposta do PATCH
 * para saber qual `detail` invalidar. */
export function useAtualizarTransacao(contaId?: number | null, cartaoId?: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: TransacaoUpdate }) => transacaoService.atualizar(id, dados),
    onSuccess: () => invalidarTransacoes(queryClient, contaId, cartaoId),
  });
}

export function useExcluirTransacao(contaId?: number | null, cartaoId?: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => transacaoService.excluir(id),
    onSuccess: () => invalidarTransacoes(queryClient, contaId, cartaoId),
  });
}
