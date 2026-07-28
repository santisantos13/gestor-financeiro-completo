/**
 * Funções finas e tipadas — um por endpoint de `/transacoes/*`, mesmo
 * padrão de `cartaoService.ts`. Zero decisão aqui; toda regra vive no
 * backend (`app/api/routes/transacao.py`). Consumido exclusivamente por
 * `hooks/useTransacaoQueries.ts`.
 *
 * Diferente de toda entidade anterior, `listar` repassa um objeto de
 * filtros inteiro como query params reais (`data_inicio`/`data_fim`/
 * `tipo`/`status`/`categoria_id`/`conta_id`/`cartao_id`/`skip`/`limit`) —
 * o backend filtra de verdade, não é um "listar tudo" seguido de filtro
 * client-side (ver docs/analise-arquitetural-transacao-frontend.md, seção
 * 2). `httpClient.get` já ignora chaves `undefined`, então passar o objeto
 * de filtros direto é seguro mesmo com campos não preenchidos.
 */
import { httpClient } from "../api/httpClient";
import type { TransacaoCreate, TransacaoFiltros, TransacaoRead, TransacaoUpdate } from "../types/transacao";
import type { EscopoOperacaoParcela } from "../types/enums";

export const transacaoService = {
  listar: (filtros: TransacaoFiltros = {}) =>
    httpClient.get<TransacaoRead[]>("/transacoes", { ...filtros }),

  obter: (id: number) => httpClient.get<TransacaoRead>(`/transacoes/${id}`),

  criar: (dados: TransacaoCreate) => httpClient.post<TransacaoRead>("/transacoes", dados),

  atualizar: (id: number, dados: TransacaoUpdate) =>
    httpClient.patch<TransacaoRead>(`/transacoes/${id}`, dados),

  /** `DELETE /transacoes/{id}` — sempre definitivo, sem soft delete
   * (Transação é lançamento de livro-razão real, não há `ativo`/
   * "/permanente" nesta entidade — seção 1 do documento).
   *
   * `escopo` só importa quando a transação pertence a um Parcelamento
   * (ignorado pelo backend em qualquer outro caso) - omitido, o backend
   * assume `TODO_PARCELAMENTO` (cancela a compra inteira, comportamento
   * de sempre). `ESTA_PARCELA` (2026-07-28) remove só esta parcela, ver
   * docs/analise-arquitetural-escopo-parcelamento.md, seção 7. */
  excluir: (id: number, escopo?: EscopoOperacaoParcela) =>
    httpClient.delete<void>(`/transacoes/${id}`, escopo ? { escopo } : undefined),
};
