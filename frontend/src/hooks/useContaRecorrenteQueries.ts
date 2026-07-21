/**
 * Wrappers de `useQuery`/`useMutation` para `/contas-recorrentes/*` —
 * mesmo molde de `useFaturaQueries.ts`.
 *
 * Invalidação: toda mutação invalida `recorrentes.all`; as que podem
 * GERAR `Transacao` (criar, sincronizar — geração lazy no backend) também
 * chamam `invalidarTransacoes` (a função mais ampla do projeto: cobre
 * transações, dashboard, calendário, agenda, contas, cartões e faturas).
 * Pausar/reativar/encerrar/atualizar nunca criam nem apagam Transacao
 * (invariantes do backend), mas mudam a projeção do calendário
 * (`previsto`) — por isso invalidam `["dashboard","calendario"]` também.
 */
import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { contaRecorrenteService } from "../services/contaRecorrenteService";
import { invalidarTransacoes } from "./useTransacaoQueries";
import type { ContaRecorrenteCreate, ContaRecorrenteUpdate } from "../types/contaRecorrente";

function useInvalidarRecorrentes() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.recorrentes.all });
    // A projeção de ocorrências futuras (`previsto=True`) muda junto com
    // qualquer alteração de template/status.
    queryClient.invalidateQueries({ queryKey: ["dashboard", "calendario"] });
  };
}

export function useContasRecorrentes() {
  return useQuery({
    queryKey: queryKeys.recorrentes.list(),
    queryFn: () => contaRecorrenteService.listar(),
  });
}

export function useCriarContaRecorrente() {
  const invalidar = useInvalidarRecorrentes();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dados: ContaRecorrenteCreate) => contaRecorrenteService.criar(dados),
    onSuccess: (criada) => {
      invalidar();
      // criar() pode ter gerado ocorrências vencidas imediatamente
      invalidarTransacoes(queryClient, criada.conta_id ?? undefined, criada.cartao_id ?? undefined);
    },
  });
}

export function useAtualizarContaRecorrente() {
  const invalidar = useInvalidarRecorrentes();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: ContaRecorrenteUpdate }) =>
      contaRecorrenteService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

export function usePausarContaRecorrente() {
  const invalidar = useInvalidarRecorrentes();
  return useMutation({
    mutationFn: (id: number) => contaRecorrenteService.pausar(id),
    onSuccess: invalidar,
  });
}

export function useReativarContaRecorrente() {
  const invalidar = useInvalidarRecorrentes();
  return useMutation({
    mutationFn: (id: number) => contaRecorrenteService.reativar(id),
    onSuccess: invalidar,
  });
}

export function useEncerrarContaRecorrente() {
  const invalidar = useInvalidarRecorrentes();
  return useMutation({
    mutationFn: (id: number) => contaRecorrenteService.encerrar(id),
    onSuccess: invalidar,
  });
}

/**
 * Sincronização global no mount do `AppLayout` — uma vez por sessão
 * (guard com `useRef`, sobrevive a re-renders; um novo login remonta o
 * layout e sincroniza de novo). Só invalida caches quando `geradas > 0`
 * (evita refetch em cascata a cada login sem novidade). É a UX de
 * "geração automática" sem nenhum scheduler — ver
 * docs/analise-arquitetural-conta-recorrente-expansao.md, seção 6.
 */
export function useSincronizarRecorrentesAoAbrir() {
  const queryClient = useQueryClient();
  const jaSincronizou = useRef(false);

  useEffect(() => {
    if (jaSincronizou.current) return;
    jaSincronizou.current = true;
    contaRecorrenteService
      .sincronizar()
      .then((resultado) => {
        if (resultado.geradas > 0 || resultado.encerradas > 0) {
          queryClient.invalidateQueries({ queryKey: queryKeys.recorrentes.all });
          invalidarTransacoes(queryClient);
        }
      })
      .catch(() => {
        // Silencioso de propósito: sincronizar é oportunista — a próxima
        // navegação/abertura tenta de novo; nenhum dado do usuário se
        // perde (geração é idempotente e lazy).
      });
  }, [queryClient]);
}
