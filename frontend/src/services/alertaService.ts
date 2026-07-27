/**
 * Funções finas e tipadas — um por endpoint de `/alertas/*`, mesmo padrão
 * de `tagService.ts`. Zero decisão aqui; toda regra (validação de
 * `condicao` por tipo, avaliação em tempo real) vive no backend
 * (`AlertaService`). Consumido exclusivamente por `hooks/useAlertaQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { AlertaCreate, AlertaRead, AlertaUpdate } from "../types/alerta";

export const alertaService = {
  /** `apenas_ativos=false` (padrão) traz também os pausados — a
   * `AlertasDrawer` precisa deles para oferecer "Reativar". */
  listar: (apenasAtivos = false) => httpClient.get<AlertaRead[]>("/alertas", { apenas_ativos: apenasAtivos }),

  obter: (id: number) => httpClient.get<AlertaRead>(`/alertas/${id}`),

  criar: (dados: AlertaCreate) => httpClient.post<AlertaRead>("/alertas", dados),

  /** Também usado para pausar/reativar — `PATCH { ativo: false/true }`,
   * mesmo endpoint de editar `condicao` (não existe rota separada de
   * pausar, ver docstring de `api/routes/alerta.py`). */
  atualizar: (id: number, dados: AlertaUpdate) => httpClient.patch<AlertaRead>(`/alertas/${id}`, dados),

  /** `DELETE /alertas/{id}` — sempre exclusão DEFINITIVA (sem soft delete
   * separado: `ativo` já cobre o estado "pausado"). */
  excluir: (id: number) => httpClient.delete<void>(`/alertas/${id}`),
};
