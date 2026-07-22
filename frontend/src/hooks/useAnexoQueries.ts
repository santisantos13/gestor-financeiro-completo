/**
 * Wrappers de `useQuery`/`useMutation` para `/anexos/*` — mesmo molde de
 * `useTagQueries.ts`. Diferente de toda entidade anterior, não invalida
 * nenhuma chave fora de `["anexos", "list", transacaoId]`: criar/excluir um
 * Anexo é só metadado de arquivo, não afeta saldo, limite nem qualquer
 * agregado do Dashboard/Central Financeira (ver
 * docs/analise-arquitetural-anexo-frontend.md, seção "Invalidação de
 * cache").
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { anexoService } from "../services/anexoService";
import type { AnexoCreate } from "../types/anexo";

export function useAnexosPorTransacao(transacaoId: number | null) {
  return useQuery({
    queryKey: queryKeys.anexos.list(transacaoId ?? 0),
    queryFn: () => anexoService.listarPorTransacao(transacaoId as number),
    enabled: transacaoId != null,
  });
}

export function useCriarAnexo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: AnexoCreate) => anexoService.criar(dados),
    onSuccess: (anexo) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.anexos.list(anexo.transacao_id) });
    },
  });
}

export function useExcluirAnexo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: number; transacaoId: number }) => anexoService.desativar(id),
    onSuccess: (_dados, variaveis) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.anexos.list(variaveis.transacaoId) });
    },
  });
}
