/**
 * Funções finas e tipadas — um por endpoint de `/categorias/*`, mesmo
 * padrão de `contaService.ts`. Zero decisão aqui; toda regra vive no
 * backend (`app/api/routes/categoria.py`). Consumido exclusivamente por
 * `hooks/useCategoriaQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { CategoriaCreate, CategoriaRead, CategoriaUpdate } from "../types/categoria";

export const categoriaService = {
  listar: (apenasAtivas = true, incluirOcultas = false) =>
    httpClient.get<CategoriaRead[]>("/categorias", {
      apenas_ativas: apenasAtivas,
      incluir_ocultas: incluirOcultas,
    }),

  obter: (id: number) => httpClient.get<CategoriaRead>(`/categorias/${id}`),

  criar: (dados: CategoriaCreate) => httpClient.post<CategoriaRead>("/categorias", dados),

  atualizar: (id: number, dados: CategoriaUpdate) =>
    httpClient.patch<CategoriaRead>(`/categorias/${id}`, dados),

  /** `DELETE /categorias/{id}` — soft delete no backend (`ativo = false`),
   * nunca remove a linha. 204 sem corpo. Rejeitada com 422 se a categoria
   * tiver subcategoria ativa, ou com 403 se for uma categoria de sistema. */
  desativar: (id: number) => httpClient.delete<void>(`/categorias/${id}`),

  /** `DELETE /categorias/{id}/permanente` — exclusão DEFINITIVA (hard
   * delete), Etapa F10 (`docs/analise-arquitetural-exclusao.md`). Rejeitada
   * com 422 se houver transação vinculada ou qualquer subcategoria (ativa
   * ou inativa), ou com 403 se for uma categoria de sistema. */
  excluirPermanente: (id: number) => httpClient.delete<void>(`/categorias/${id}/permanente`),

  /** `DELETE /categorias/{id}/ocultar` - Sprint de Refinamento Premium,
   * item 4: "exclui" uma categoria de SISTEMA do ponto de vista do usuário
   * logado, sem afetar os demais (nunca toca a linha compartilhada). 204
   * sem corpo. Rejeitada com 422 se a categoria for própria (use
   * `desativar`/`excluirPermanente`) ou se o usuário tiver transação
   * vinculada a ela, ou com 404 se for privada de outro usuário. */
  ocultarParaUsuario: (id: number) => httpClient.delete<void>(`/categorias/${id}/ocultar`),

  /** `POST /categorias/{id}/reexibir` - reverte `ocultarParaUsuario`,
   * sempre idempotente. */
  reexibirParaUsuario: (id: number) => httpClient.post<void>(`/categorias/${id}/reexibir`),
};
