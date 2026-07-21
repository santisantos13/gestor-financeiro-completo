/**
 * Wrappers de `useQuery`/`useMutation` para `/metas/*` — mesmo molde de
 * `useCartaoQueries.ts`. Invalidação: `queryKeys.metas.all` invalida
 * list+detail; toda mutation também invalida `dashboard.metas` e
 * `dashboard.indicadores` (`/central-financeira/metas` e
 * `/central-financeira/indicadores`, ambos dependem de Meta) e
 * `dashboard.calendario` por PREFIXO (mesmo raciocínio de
 * `useTransferenciaQueries.ts` — `data_alvo` pode entrar/sair/mudar de mês
 * no Calendário Financeiro, e a chave real sempre carrega `ano`/`mes`, que
 * a invalidação sem esses parâmetros casa de qualquer forma). Ver
 * docs/analise-arquitetural-metas-frontend.md, seção 2.8/2.10.
 *
 * Refatoramento de Metas/Transferências
 * (docs/analise-arquitetural-metas-transferencias.md): o histórico de
 * aportes/resgates de uma Meta agora combina DUAS fontes -
 * `useAportesLegadosDaMeta` (legado, `Transacao.meta_id`, congelado) e
 * `useTransferenciasDoCofrinho` (novo, `Transferencia` real do cofrinho) -
 * mescladas no componente (`MetaResumoCard`), nunca aqui.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { metaService } from "../services/metaService";
import { transacaoService } from "../services/transacaoService";
import { transferenciaService } from "../services/transferenciaService";
import type { MetaCreate, MetaUpdate } from "../types/meta";

function useInvalidarMetas() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.metas.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.metas });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "calendario"] });
  };
}

/** Sempre busca TODAS as metas (`apenasAtivas=false` no backend) — os
 * filtros rápidos (seção 2.4 da análise) e a busca/ordenação são 100%
 * client-side sobre essa lista única, evitando refetch a cada troca de
 * filtro (volume baixo por natureza). O parâmetro `apenasAtivas` existe só
 * para espelhar o contrato do endpoint e permitir um `useMetas(true)` mais
 * barato em consumidores que realmente só precisam das ativas (ex.
 * `MetaSelect`, seção 2.9). */
export function useMetas(apenasAtivas = false) {
  return useQuery({
    queryKey: queryKeys.metas.list(apenasAtivas),
    queryFn: () => metaService.listar(apenasAtivas),
  });
}

/** Histórico LEGADO de uma meta — `GET /transacoes?meta_id=`, reusa a mesma
 * `queryKey`/cache de `useTransacoes` (`queryKeys.transacoes.list`), então
 * já é invalidado de graça por `invalidarTransacoes`. Desde o Refatoramento
 * de Metas/Transferências (docs/analise-arquitetural-metas-transferencias.md,
 * seção 5) essa lista só cresce com dado ANTIGO (`Transacao.meta_id`
 * congelado) — nenhuma Transação nova entra mais aqui, só aportes/resgates
 * novos (`useTransferenciasDoCofrinho` abaixo). `enabled` existe para só
 * buscar quando `MetaResumoCard` está expandido (seção 4.1/6 da análise:
 * "expandir em vez de navegar") — evitar N requisições (uma por card)
 * quando a página `/metas` carrega. */
export function useAportesLegadosDaMeta(metaId: number, enabled: boolean) {
  const filtros = { meta_id: metaId, limit: 10 };
  return useQuery({
    queryKey: queryKeys.transacoes.list(filtros),
    queryFn: () => transacaoService.listar(filtros),
    enabled,
  });
}

/** Histórico NOVO de aportes/resgates de uma meta — `GET
 * /transferencias?conta_id=`, onde `contaId` é o "cofrinho" da própria
 * Meta (`meta.conta_id`). Toda mutation de Transferência já invalida
 * `queryKeys.transferencias.all` (casa por prefixo com `porConta`, ver
 * `api/queryKeys.ts`), então nenhuma invalidação extra é necessária aqui.
 * Ver docs/analise-arquitetural-metas-transferencias.md, seção 5. */
export function useTransferenciasDoCofrinho(contaId: number, enabled: boolean) {
  const filtros = { conta_id: contaId, limit: 10 };
  return useQuery({
    queryKey: queryKeys.transferencias.porConta(contaId),
    queryFn: () => transferenciaService.listar(filtros),
    enabled,
  });
}

export function useMeta(id: number | null) {
  return useQuery({
    queryKey: queryKeys.metas.detail(id ?? 0),
    queryFn: () => metaService.obter(id as number),
    enabled: id != null,
  });
}

export function useCriarMeta() {
  const invalidar = useInvalidarMetas();
  return useMutation({
    mutationFn: (dados: MetaCreate) => metaService.criar(dados),
    onSuccess: invalidar,
  });
}

export function useAtualizarMeta() {
  const invalidar = useInvalidarMetas();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: MetaUpdate }) => metaService.atualizar(id, dados),
    onSuccess: invalidar,
  });
}

/** `DELETE /metas/{id}` — soft delete (seção 2.3). */
export function useDesativarMeta() {
  const invalidar = useInvalidarMetas();
  return useMutation({
    mutationFn: (id: number) => metaService.desativar(id),
    onSuccess: invalidar,
  });
}

/** Exclusão DEFINITIVA (hard delete) — pedido explícito do usuário, mesmo
 * padrão de `useExcluirCartao`. Nunca bloqueada por aportes vinculados. */
export function useExcluirMeta() {
  const invalidar = useInvalidarMetas();
  return useMutation({
    mutationFn: (id: number) => metaService.excluirPermanente(id),
    onSuccess: invalidar,
  });
}

/** Reativar é `PATCH { ativo: true }` no mesmo endpoint de edição — mesma
 * forma de `TagUpdate`/`CartaoUpdate` (seção 2.2). Wrapper dedicado só para
 * a Action Bar não precisar montar `{ ativo: true }` manualmente toda vez,
 * mesmo padrão explícito de reativação que outras entidades expõem via um
 * botão próprio. */
export function useReativarMeta() {
  const invalidar = useInvalidarMetas();
  return useMutation({
    mutationFn: (id: number) => metaService.atualizar(id, { ativo: true }),
    onSuccess: invalidar,
  });
}
