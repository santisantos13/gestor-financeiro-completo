/**
 * Funções finas e tipadas — um por endpoint de `/anexos/*`, mesmo padrão de
 * `tagService.ts`. Zero decisão aqui; toda regra vive no backend
 * (`app/api/routes/anexo.py`). Consumido exclusivamente por
 * `hooks/useAnexoQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { AnexoCreate, AnexoRead } from "../types/anexo";

export const anexoService = {
  /** `GET /anexos?transacao_id=` — sempre escopado a uma transação (o
   * backend não expõe listagem global, ver
   * docs/analise-arquitetural-anexo-frontend.md). */
  listarPorTransacao: (transacaoId: number, apenasAtivos = true) =>
    httpClient.get<AnexoRead[]>("/anexos", { transacao_id: transacaoId, apenas_ativos: apenasAtivos }),

  criar: (dados: AnexoCreate) => httpClient.post<AnexoRead>("/anexos", dados),

  /** `DELETE /anexos/{id}` — soft delete no backend (`ativo = false`), 204
   * sem corpo. Sem `AnexoUpdate`/PATCH — decisão já confirmada no backend. */
  desativar: (id: number) => httpClient.delete<void>(`/anexos/${id}`),
};
