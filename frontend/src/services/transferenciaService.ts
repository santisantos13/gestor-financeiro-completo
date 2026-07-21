/**
 * Funções finas e tipadas - um por endpoint de `/transferencias/*`, mesmo
 * padrão de `transacaoService.ts`/`cartaoService.ts`. Zero decisão aqui;
 * toda regra vive no backend (`app/api/routes/transferencia.py`).
 * Consumido exclusivamente por `hooks/useTransferenciaQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { TransferenciaCreate, TransferenciaFiltros, TransferenciaRead } from "../types/transferencia";

export const transferenciaService = {
  listar: (filtros: TransferenciaFiltros = {}) =>
    httpClient.get<TransferenciaRead[]>("/transferencias", { ...filtros }),

  obter: (id: number) => httpClient.get<TransferenciaRead>(`/transferencias/${id}`),

  criar: (dados: TransferenciaCreate) => httpClient.post<TransferenciaRead>("/transferencias", dados),

  /** `POST /transferencias/{id}/cancelar` - soft delete (mesmo padrão de
   * Conta/Cartão/Tag/Categoria): a linha nunca é apagada, só marca
   * `ativo=false`. Nunca chamado de "excluir" na UI - ver
   * docs/analise-arquitetural-transferencias-frontend.md, seção 8, ponto 4. */
  cancelar: (id: number) => httpClient.post<TransferenciaRead>(`/transferencias/${id}/cancelar`),
};
