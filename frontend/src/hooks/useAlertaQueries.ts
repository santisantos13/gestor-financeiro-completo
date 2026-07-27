/**
 * Wrappers de `useQuery`/`useMutation` para `/alertas/*` — mesmo formato de
 * `useTagQueries.ts`. Nenhuma página/componente guarda `isLoading`/`error`
 * em `useState` manual.
 *
 * Invalidação: só `queryKeys.alertas.all` — nenhum card/indicador do
 * Dashboard depende de Alerta hoje (o sino/contador vive no `Header`,
 * fora da árvore do Dashboard).
 *
 * Diferente de outras entidades, não há um `useDesativarAlerta`/
 * `useReativarAlerta` dedicado: pausar/reativar é só
 * `useAtualizarAlerta({ id, dados: { ativo } })`, mesmo `PATCH` usado para
 * editar `condicao` (não existe rota separada — ver docstring de
 * `alertaService.atualizar`).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { alertaService } from "../services/alertaService";
import type { AlertaCreate, AlertaUpdate } from "../types/alerta";

function useInvalidateAlertas() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.alertas.all });
  };
}

export function useAlertas(apenasAtivos = false) {
  return useQuery({
    queryKey: queryKeys.alertas.list(apenasAtivos),
    queryFn: () => alertaService.listar(apenasAtivos),
  });
}

export function useCriarAlerta() {
  const invalidar = useInvalidateAlertas();
  return useMutation({
    mutationFn: (dados: AlertaCreate) => alertaService.criar(dados),
    onSuccess: invalidar,
  });
}

export function useAtualizarAlerta() {
  const invalidar = useInvalidateAlertas();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: AlertaUpdate }) => alertaService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

export function useExcluirAlerta() {
  const invalidar = useInvalidateAlertas();
  return useMutation({
    mutationFn: (id: number) => alertaService.excluir(id),
    onSuccess: invalidar,
  });
}
