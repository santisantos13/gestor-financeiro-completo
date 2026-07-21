/**
 * Funções finas e tipadas — um por endpoint de `/faturas/*`, mesmo padrão
 * de `cartaoService.ts`. Zero decisão aqui; toda regra vive no backend
 * (`app/api/routes/fatura.py`). Consumido exclusivamente por
 * `hooks/useFaturaQueries.ts`.
 *
 * Diferente das demais entidades, `listar` é sempre escopada a um
 * `cartao_id` (o backend exige — não existe "listar todas as faturas do
 * usuário" nesta rota, ver docs/analise-arquitetural-fatura-frontend.md,
 * seção 0), e não existe `atualizar` (sem PATCH genérico).
 */
import { httpClient } from "../api/httpClient";
import type {
  FaturaAjusteManualUpdate,
  FaturaAjustePosFechamentoCreate,
  FaturaCreate,
  FaturaImportarCreate,
  FaturaPagamentoCreate,
  FaturaPagamentoEmLoteCreate,
  FaturaPagamentoEmLoteResult,
  FaturaRead,
} from "../types/fatura";

export const faturaService = {
  listar: (cartaoId: number) => httpClient.get<FaturaRead[]>("/faturas", { cartao_id: cartaoId }),

  obter: (id: number) => httpClient.get<FaturaRead>(`/faturas/${id}`),

  criar: (dados: FaturaCreate) => httpClient.post<FaturaRead>("/faturas", dados),

  /** `POST /faturas/importar` — Etapa de Onboarding: cria uma fatura já
   * FECHADA com `valor_total` informado diretamente (histórico de antes
   * do usuário usar o app), sem recriar cada compra. Ver
   * `FaturaImportarCreate` no backend. */
  importar: (dados: FaturaImportarCreate) => httpClient.post<FaturaRead>("/faturas/importar", dados),

  /** `POST /faturas/{id}/fechar` — sem payload. ABERTA → FECHADA, congela
   * `valor_total`. */
  fechar: (id: number) => httpClient.post<FaturaRead>(`/faturas/${id}/fechar`),

  /** `POST /faturas/{id}/pagamentos` — pagamento parcial ou total, pode
   * ser chamado várias vezes; só permitido se a fatura não estiver
   * ABERTA. */
  registrarPagamento: (id: number, dados: FaturaPagamentoCreate) =>
    httpClient.post<FaturaRead>(`/faturas/${id}/pagamentos`, dados),

  /** `PATCH /faturas/{id}/ajuste-manual` — declara o saldo já usado do
   * ciclo ABERTO diretamente, SEM nenhuma Transacao por trás. Pedido
   * explícito do usuário: "poder informar o saldo já utilizado do cartão
   * independentemente de transações". Editar sempre define o total
   * (nunca soma em cima do que já estava salvo). */
  ajustarSaldoInicial: (id: number, dados: FaturaAjusteManualUpdate) =>
    httpClient.patch<FaturaRead>(`/faturas/${id}/ajuste-manual`, dados),

  /** `PATCH /faturas/{id}/ajuste-pos-fechamento` — soma um valor esquecido
   * ao total de uma fatura JÁ FECHADA (ou paga/atrasada/parcial), sem
   * criar nenhuma Transacao. Pedido explícito do usuário (2026-07-20):
   * "quero adicionar uma transação em uma fatura que já foi fechada e
   * paga, porém tinha esquecido dela antes". Diferente de
   * `ajustarSaldoInicial` (define o total), cada chamada aqui SOMA — pode
   * ser chamado de novo mais tarde se o usuário lembrar de outra compra. */
  ajustarValorPosFechamento: (id: number, dados: FaturaAjustePosFechamentoCreate) =>
    httpClient.patch<FaturaRead>(`/faturas/${id}/ajuste-pos-fechamento`, dados),

  /** `DELETE /faturas/{id}` — hard delete REAL (Fatura nunca teve soft
   * delete, diferente de Conta/Categoria/Tag/Cartão) — sempre permitido,
   * em qualquer status e com ou sem transação vinculada (compra e/ou
   * pagamento); a transação só perde o vínculo com a fatura, nunca é
   * apagada (regra relaxada em 2026-07-24, pedido explícito do usuário). */
  excluir: (id: number) => httpClient.delete<void>(`/faturas/${id}`),

  /** `POST /faturas/excluir-em-lote` — pedido explícito do usuário:
   * "quero poder selecionar várias faturas para excluir". Mesma regra de
   * `excluir` (sempre permitido, desvincula em vez de apagar transação),
   * só que para N faturas de uma vez — tudo ou nada (se qualquer id não
   * existir/não for do usuário, a requisição inteira falha e nenhuma
   * fatura é apagada, ver `FaturaService.excluir_em_lote` no backend). */
  excluirEmLote: (ids: number[]) => httpClient.post<void>("/faturas/excluir-em-lote", { fatura_ids: ids }),

  /** `POST /faturas/pagar-em-lote` — pedido explícito do usuário: "seria
   * interessante poder pagar todas selecionadas". Cada fatura é paga pelo
   * seu próprio restante (o backend calcula, não o cliente); faturas
   * ABERTAS ou já quitadas são puladas em vez de derrubar o lote inteiro
   * (`pagas` na resposta pode ser menor que `dados.fatura_ids.length`, ver
   * `FaturaService.pagar_em_lote` no backend). */
  pagarEmLote: (dados: FaturaPagamentoEmLoteCreate) =>
    httpClient.post<FaturaPagamentoEmLoteResult>("/faturas/pagar-em-lote", dados),
};
