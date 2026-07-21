/**
 * Funções finas e tipadas — um por endpoint de `/emprestimos/*`, mesmo
 * padrão de `financiamentoService.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { EmprestimoCreate, EmprestimoRead } from "../types/emprestimo";

export const emprestimoService = {
  listar: (apenasAtivos: boolean) =>
    httpClient.get<EmprestimoRead[]>("/emprestimos", { apenas_ativos: apenasAtivos, limit: 200 }),

  criar: (dados: EmprestimoCreate) => httpClient.post<EmprestimoRead>("/emprestimos", dados),

  obter: (id: number) => httpClient.get<EmprestimoRead>(`/emprestimos/${id}`),

  pagarParcela: (id: number, numeroParcela: number) =>
    httpClient.post<EmprestimoRead>(`/emprestimos/${id}/parcelas/${numeroParcela}/pagar`),

  /** Sempre permitida (mesmo com parcelas já pagas) - ver
   * `EmprestimoService.excluir` (backend). */
  excluir: (id: number) => httpClient.delete<void>(`/emprestimos/${id}`),
};
