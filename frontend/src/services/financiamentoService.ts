/**
 * Funções finas e tipadas — um por endpoint de `/financiamentos/*`, mesmo
 * padrão de `faturaService.ts`. Sem `atualizar` (sem PATCH genérico —
 * `FinanciamentoRead` é imutável após a criação, exceto pela ação dedicada
 * `pagarParcela`). `excluir` é sempre permitida (mesmo com parcelas já
 * pagas) — as transações de parcela só perdem o vínculo no backend
 * (`ondelete=SET NULL`), nunca são apagadas.
 */
import { httpClient } from "../api/httpClient";
import type { FinanciamentoCreate, FinanciamentoRead } from "../types/financiamento";

export const financiamentoService = {
  listar: (apenasAtivos: boolean) =>
    httpClient.get<FinanciamentoRead[]>("/financiamentos", { apenas_ativos: apenasAtivos, limit: 200 }),

  criar: (dados: FinanciamentoCreate) => httpClient.post<FinanciamentoRead>("/financiamentos", dados),

  obter: (id: number) => httpClient.get<FinanciamentoRead>(`/financiamentos/${id}`),

  /** `POST /financiamentos/{id}/parcelas/{numero}/pagar` — sem payload;
   * decrementa `saldo_devedor` pela amortização daquela parcela e
   * transiciona o contrato para QUITADO na última. */
  pagarParcela: (id: number, numeroParcela: number) =>
    httpClient.post<FinanciamentoRead>(`/financiamentos/${id}/parcelas/${numeroParcela}/pagar`),

  excluir: (id: number) => httpClient.delete<void>(`/financiamentos/${id}`),
};
