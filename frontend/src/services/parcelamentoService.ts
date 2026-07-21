/**
 * Funções finas e tipadas — um por endpoint de `/parcelamentos/*`, mesmo
 * padrão de `transferenciaService.ts`. Consumido exclusivamente por
 * `hooks/useParcelamentoQueries.ts` — usado só pelo fluxo "Parcelado" de
 * `TransacaoFormDialog` (pedido do usuário: comprar no cartão à vista ou
 * em N vezes), não existe uma página própria de Parcelamentos ainda.
 */
import { httpClient } from "../api/httpClient";
import type { ParcelamentoCreate, ParcelamentoRead } from "../types/parcelamento";

export const parcelamentoService = {
  criar: (dados: ParcelamentoCreate) => httpClient.post<ParcelamentoRead>("/parcelamentos", dados),

  /** Usado pelo diálogo de confirmação de exclusão de compra parcelada
   * (`TransacoesPage`) para mostrar `num_parcelas` real antes de excluir -
   * ver docs/analise-arquitetural-escopo-parcelamento.md, seção 4. */
  obter: (id: number) => httpClient.get<ParcelamentoRead>(`/parcelamentos/${id}`),

  cancelar: (id: number) => httpClient.post<ParcelamentoRead>(`/parcelamentos/${id}/cancelar`),
};
