/**
 * Funções finas e tipadas — uma por endpoint de `/metas/*`, mesmo padrão de
 * `cartaoService.ts`. Zero decisão aqui; toda regra vive no backend
 * (`app/api/routes/meta.py`). Consumido exclusivamente por
 * `hooks/useMetaQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { MetaCreate, MetaRead, MetaUpdate } from "../types/meta";

export const metaService = {
  listar: (apenasAtivas = true) => httpClient.get<MetaRead[]>("/metas", { apenas_ativas: apenasAtivas }),

  obter: (id: number) => httpClient.get<MetaRead>(`/metas/${id}`),

  criar: (dados: MetaCreate) => httpClient.post<MetaRead>("/metas", dados),

  atualizar: (id: number, dados: MetaUpdate) => httpClient.patch<MetaRead>(`/metas/${id}`, dados),

  /** `DELETE /metas/{id}` — soft delete no backend (`ativo = false`), nunca
   * remove a linha. 204 sem corpo. */
  desativar: (id: number) => httpClient.delete<void>(`/metas/${id}`),

  /** `DELETE /metas/{id}/permanente` — exclusão DEFINITIVA (hard delete),
   * pedido explícito do usuário: uma ação nova, separada de `desativar`,
   * mesmo padrão de `cartaoService.excluirPermanente`. Nunca bloqueada por
   * aportes vinculados — a transação em si nunca é apagada, só perde o
   * vínculo com a meta (ver `MetaService.excluir` no backend). 204 sem
   * corpo. */
  excluirPermanente: (id: number) => httpClient.delete<void>(`/metas/${id}/permanente`),
};
