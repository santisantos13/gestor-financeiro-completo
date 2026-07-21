/**
 * Funções finas e tipadas — um por endpoint de `/tags/*`, mesmo padrão de
 * `categoriaService.ts`. Zero decisão aqui; toda regra vive no backend
 * (`app/api/routes/tag.py`). Consumido exclusivamente por
 * `hooks/useTagQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { TagCreate, TagRead, TagUpdate, TagUso } from "../types/tag";

export const tagService = {
  listar: (apenasAtivas = true) => httpClient.get<TagRead[]>("/tags", { apenas_ativas: apenasAtivas }),

  obter: (id: number) => httpClient.get<TagRead>(`/tags/${id}`),

  /** `POST /tags` — se o nome colidir com uma tag desativada do mesmo
   * usuário, o backend REATIVA a existente em vez de rejeitar (e
   * sobrescreve `cor` com o valor enviado). Se colidir com uma tag ativa,
   * 409. Nenhuma distinção é feita aqui — os dois casos chegam da mesma
   * forma (201 ou erro), tratados via `getErrorMessage`/toast. */
  criar: (dados: TagCreate) => httpClient.post<TagRead>("/tags", dados),

  atualizar: (id: number, dados: TagUpdate) => httpClient.patch<TagRead>(`/tags/${id}`, dados),

  /** `DELETE /tags/{id}` — soft delete no backend (`ativo = false`), nunca
   * remove a linha. 204 sem corpo. Sem checagem de "em uso": o vínculo N-N
   * com Transação não é afetado por soft delete. */
  desativar: (id: number) => httpClient.delete<void>(`/tags/${id}`),

  /** `GET /tags/{id}/uso` — Etapa F10, só informativo (quantas transações
   * perdem o rótulo se a tag for excluída definitivamente). */
  obterUso: (id: number) => httpClient.get<TagUso>(`/tags/${id}/uso`),

  /** `DELETE /tags/{id}/permanente` — exclusão DEFINITIVA (hard delete),
   * Etapa F10. Diferente das outras entidades, NUNCA bloqueia por uso
   * (`docs/analise-arquitetural-exclusao.md`, seção 2.3). */
  excluirPermanente: (id: number) => httpClient.delete<void>(`/tags/${id}/permanente`),
};
