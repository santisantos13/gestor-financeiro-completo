/**
 * Funções finas e tipadas — uma por endpoint de `/contas-recorrentes/*`,
 * mesmo padrão de `faturaService.ts`. Zero decisão aqui; toda regra vive
 * no backend (`app/api/routes/conta_recorrente.py`). Consumido
 * exclusivamente por `hooks/useContaRecorrenteQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type {
  ContaRecorrenteCreate,
  ContaRecorrenteRead,
  ContaRecorrenteUpdate,
  SincronizacaoRecorrentesResult,
} from "../types/contaRecorrente";

export const contaRecorrenteService = {
  /** Sem filtro de status — a lista traz TUDO (encerradas são histórico);
   * filtros são client-side (ver queryKeys.recorrentes). */
  listar: () => httpClient.get<ContaRecorrenteRead[]>("/contas-recorrentes"),

  obter: (id: number) => httpClient.get<ContaRecorrenteRead>(`/contas-recorrentes/${id}`),

  criar: (dados: ContaRecorrenteCreate) =>
    httpClient.post<ContaRecorrenteRead>("/contas-recorrentes", dados),

  atualizar: (id: number, dados: ContaRecorrenteUpdate) =>
    httpClient.patch<ContaRecorrenteRead>(`/contas-recorrentes/${id}`, dados),

  pausar: (id: number) => httpClient.post<ContaRecorrenteRead>(`/contas-recorrentes/${id}/pausar`),

  /** Nunca gera retroativos — o cursor pula para a próxima data futura
   * (decisão do usuário, 2026-07-20). */
  reativar: (id: number) => httpClient.post<ContaRecorrenteRead>(`/contas-recorrentes/${id}/reativar`),

  /** ENCERRADA é terminal; preserva template e transações já geradas. O
   * `DELETE` do backend também encerra (nunca apaga) — usamos a rota
   * explícita para o vocabulário ficar claro. */
  encerrar: (id: number) => httpClient.post<ContaRecorrenteRead>(`/contas-recorrentes/${id}/encerrar`),

  /** Catch-up global de todos os templates ativos — chamado uma vez por
   * sessão no mount do AppLayout (UX de geração automática sem scheduler). */
  sincronizar: () => httpClient.post<SincronizacaoRecorrentesResult>("/contas-recorrentes/sincronizar"),
};
