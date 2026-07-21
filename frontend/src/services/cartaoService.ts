/**
 * Funções finas e tipadas — um por endpoint de `/cartoes/*`, mesmo padrão de
 * `contaService.ts`. Zero decisão aqui; toda regra vive no backend
 * (`app/api/routes/cartao.py`). Consumido exclusivamente por
 * `hooks/useCartaoQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { CartaoCreate, CartaoRead, CartaoUpdate } from "../types/cartao";

export const cartaoService = {
  listar: (apenasAtivas = true) =>
    httpClient.get<CartaoRead[]>("/cartoes", { apenas_ativos: apenasAtivas }),

  obter: (id: number) => httpClient.get<CartaoRead>(`/cartoes/${id}`),

  criar: (dados: CartaoCreate) => httpClient.post<CartaoRead>("/cartoes", dados),

  atualizar: (id: number, dados: CartaoUpdate) => httpClient.patch<CartaoRead>(`/cartoes/${id}`, dados),

  /** `DELETE /cartoes/{id}` — soft delete no backend (`ativo = false`),
   * nunca remove a linha. 204 sem corpo. */
  desativar: (id: number) => httpClient.delete<void>(`/cartoes/${id}`),

  /** `DELETE /cartoes/{id}/permanente` — exclusão DEFINITIVA (hard delete),
   * Etapa F10 (`docs/analise-arquitetural-exclusao.md`). Rejeitada com 422
   * se houver qualquer fatura vinculada, em qualquer status — a menos que
   * `apagarTransacoes` seja `true` (pedido explícito do usuário, ver
   * docs/analise-arquitetural-exclusao-cartao-com-historico.md): nesse
   * caso o backend apaga as faturas e as transações do cartão junto com
   * ele, em vez de bloquear. */
  excluirPermanente: (id: number, apagarTransacoes = false) =>
    httpClient.delete<void>(`/cartoes/${id}/permanente`, { apagar_transacoes: apagarTransacoes }),
};
