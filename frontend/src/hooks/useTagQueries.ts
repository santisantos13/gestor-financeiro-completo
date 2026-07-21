/**
 * Wrappers de `useQuery`/`useMutation` para `/tags/*` — mesmo formato de
 * `useCategoriaQueries.ts`. Nenhuma página guarda `isLoading`/`error` em
 * `useState` manual.
 *
 * Invalidação: só `queryKeys.tags.all` — nenhum card/indicador do
 * Dashboard depende de Tag hoje.
 *
 * `placeholderData: keepPreviousData` já entra desde o primeiro commit
 * (diferente de Categoria/Conta, que só ganharam isso numa etapa de
 * correção posterior) — evita o flash de skeleton ao alternar "mostrar
 * inativas", identificado como problema real na etapa de Refinamento de
 * UI (ver docs/revisao-tecnica-refinamento-ui.md).
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { tagService } from "../services/tagService";
import type { TagCreate, TagUpdate } from "../types/tag";

function useInvalidateTags() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.tags.all });
  };
}

export function useTags(apenasAtivas = true) {
  return useQuery({
    queryKey: queryKeys.tags.list(apenasAtivas),
    queryFn: () => tagService.listar(apenasAtivas),
    placeholderData: keepPreviousData,
  });
}

export function useTag(id: number | null) {
  return useQuery({
    queryKey: queryKeys.tags.detail(id ?? 0),
    queryFn: () => tagService.obter(id as number),
    enabled: id != null,
  });
}

export function useCriarTag() {
  const invalidar = useInvalidateTags();
  return useMutation({
    mutationFn: (dados: TagCreate) => tagService.criar(dados),
    onSuccess: invalidar,
  });
}

export function useAtualizarTag() {
  const invalidar = useInvalidateTags();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: TagUpdate }) => tagService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

export function useDesativarTag() {
  const invalidar = useInvalidateTags();
  return useMutation({
    mutationFn: (id: number) => tagService.desativar(id),
    onSuccess: invalidar,
  });
}

/** Só informativo — Etapa F10 (Exclusão definitiva, seção 2.3): consultado
 * ao abrir a confirmação de excluir, para avisar quantas transações
 * perdem o rótulo. Nunca bloqueia a ação em si. */
export function useUsoTag(id: number | null) {
  return useQuery({
    queryKey: queryKeys.tags.uso(id ?? 0),
    queryFn: () => tagService.obterUso(id as number),
    enabled: id != null,
  });
}

/** Exclusão DEFINITIVA (hard delete) — Etapa F10,
 * `docs/analise-arquitetural-exclusao.md`. Diferente das outras entidades,
 * nunca é rejeitada por uso (seção 2.3). */
export function useExcluirTag() {
  const invalidar = useInvalidateTags();
  return useMutation({
    mutationFn: (id: number) => tagService.excluirPermanente(id),
    onSuccess: invalidar,
  });
}
