/**
 * Wrappers de `useQuery`/`useMutation` para `/categorias/*` — mesmo
 * formato de `useContaQueries.ts`. Nenhuma página guarda `isLoading`/
 * `error` em `useState` manual.
 *
 * Invalidação: só `queryKeys.categorias.all` — diferente de Conta, nenhum
 * card/indicador do Dashboard depende de Categoria hoje (ver
 * docs/analise-arquitetural-categoria-frontend.md, seção 6).
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { categoriaService } from "../services/categoriaService";
import type { CategoriaCreate, CategoriaUpdate } from "../types/categoria";

function useInvalidateCategorias() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.categorias.all });
  };
}

export function useCategorias(apenasAtivas = true, incluirOcultas = false) {
  return useQuery({
    queryKey: queryKeys.categorias.list(apenasAtivas, incluirOcultas),
    queryFn: () => categoriaService.listar(apenasAtivas, incluirOcultas),
    // Mesma razão de `useContas`: "mostrar inativas" troca a queryKey —
    // manter a lista anterior visível durante o refetch evita o flash de
    // skeleton a cada toggle. Mesmo raciocínio vale para o toggle "mostrar
    // ocultas" (Sprint de Refinamento Premium, item 4).
    placeholderData: keepPreviousData,
  });
}

export function useCategoria(id: number | null) {
  return useQuery({
    queryKey: queryKeys.categorias.detail(id ?? 0),
    queryFn: () => categoriaService.obter(id as number),
    enabled: id != null,
  });
}

export function useCriarCategoria() {
  const invalidar = useInvalidateCategorias();
  return useMutation({
    mutationFn: (dados: CategoriaCreate) => categoriaService.criar(dados),
    onSuccess: invalidar,
  });
}

export function useAtualizarCategoria() {
  const invalidar = useInvalidateCategorias();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: CategoriaUpdate }) =>
      categoriaService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

export function useDesativarCategoria() {
  const invalidar = useInvalidateCategorias();
  return useMutation({
    mutationFn: (id: number) => categoriaService.desativar(id),
    onSuccess: invalidar,
  });
}

/** Exclusão DEFINITIVA (hard delete) — Etapa F10,
 * `docs/analise-arquitetural-exclusao.md`. */
export function useExcluirCategoria() {
  const invalidar = useInvalidateCategorias();
  return useMutation({
    mutationFn: (id: number) => categoriaService.excluirPermanente(id),
    onSuccess: invalidar,
  });
}

/** "Excluir" uma categoria de SISTEMA do ponto de vista do usuário logado
 * (Sprint de Refinamento Premium, item 4) — nunca afeta os demais
 * usuários. */
export function useOcultarCategoria() {
  const invalidar = useInvalidateCategorias();
  return useMutation({
    mutationFn: (id: number) => categoriaService.ocultarParaUsuario(id),
    onSuccess: invalidar,
  });
}

/** Reverte `useOcultarCategoria`. */
export function useReexibirCategoria() {
  const invalidar = useInvalidateCategorias();
  return useMutation({
    mutationFn: (id: number) => categoriaService.reexibirParaUsuario(id),
    onSuccess: invalidar,
  });
}
