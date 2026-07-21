import { useMemo, useState } from "react";
import { Plus, Target } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { SearchBar } from "../../components/ui/SearchBar";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { MetaFormDialog } from "../../components/domain/meta/MetaFormDialog";
import { MetaResumoCard } from "../../components/domain/meta/MetaResumoCard";
import { useDesativarMeta, useExcluirMeta, useMetas, useReativarMeta } from "../../hooks/useMetaQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import {
  situacaoDaMeta,
  SITUACAO_META_LABEL,
  ordenarMetas,
  CRITERIO_ORDENACAO_META_LABEL,
  CRITERIO_ORDENACAO_META_OPTIONS,
  type SituacaoMeta,
  type CriterioOrdenacaoMeta,
} from "../../utils/meta";
import type { MetaRead } from "../../types/meta";

type FiltroRapido = "TODAS" | SituacaoMeta;

const FILTROS_RAPIDOS: FiltroRapido[] = ["TODAS", "EM_ANDAMENTO", "CONCLUIDA", "ATRASADA", "DESATIVADA"];

const LABEL_FILTRO_RAPIDO: Record<FiltroRapido, string> = {
  TODAS: "Todas",
  ...SITUACAO_META_LABEL,
};

const CRITERIO_PADRAO: CriterioOrdenacaoMeta = "VENCIMENTO";

/**
 * Página `/metas` — Etapa F12. Grid de `MetaResumoCard` (nunca `DataTable`
 * — pedido explícito do usuário: "não quero uma tabela como tela inicial"),
 * mesmo raciocínio de volume baixo já usado em Cartão/Financiamento/
 * Empréstimo. Busca a lista INTEIRA uma vez (`useMetas(false)`) — filtros
 * rápidos, busca textual e ordenação são 100% client-side sobre essa
 * lista (docs/analise-arquitetural-metas-frontend.md, seção 2.4/2.5),
 * nenhum refetch a cada troca de filtro/ordenação.
 */
export function MetasPage() {
  const toast = useToast();
  const { data: metas, isLoading, error, refetch } = useMetas(false);

  const [filtroRapido, setFiltroRapido] = useState<FiltroRapido>("TODAS");
  const [busca, setBusca] = useState("");
  const [criterio, setCriterio] = useState<CriterioOrdenacaoMeta>(CRITERIO_PADRAO);

  const [formularioAberto, setFormularioAberto] = useState(false);
  const [metaEmEdicao, setMetaEmEdicao] = useState<MetaRead | null>(null);
  const [metaParaDesativar, setMetaParaDesativar] = useState<MetaRead | null>(null);
  const [metaParaExcluir, setMetaParaExcluir] = useState<MetaRead | null>(null);

  const desativarMeta = useDesativarMeta();
  const reativarMeta = useReativarMeta();
  const excluirMeta = useExcluirMeta();

  const contagemPorSituacao = useMemo(() => {
    const contagem: Record<FiltroRapido, number> = {
      TODAS: metas?.length ?? 0,
      EM_ANDAMENTO: 0,
      CONCLUIDA: 0,
      ATRASADA: 0,
      DESATIVADA: 0,
    };
    for (const meta of metas ?? []) {
      contagem[situacaoDaMeta(meta)] += 1;
    }
    return contagem;
  }, [metas]);

  const metasFiltradas = useMemo(() => {
    let lista = metas ?? [];
    if (filtroRapido !== "TODAS") {
      lista = lista.filter((meta) => situacaoDaMeta(meta) === filtroRapido);
    }
    if (busca.trim()) {
      const termo = busca.trim().toLowerCase();
      lista = lista.filter((meta) => meta.descricao.toLowerCase().includes(termo));
    }
    return ordenarMetas(lista, criterio);
  }, [metas, filtroRapido, busca, criterio]);

  function abrirCriacao() {
    setMetaEmEdicao(null);
    setFormularioAberto(true);
  }

  function abrirEdicao(meta: MetaRead) {
    setMetaEmEdicao(meta);
    setFormularioAberto(true);
  }

  function fecharFormulario() {
    setFormularioAberto(false);
  }

  async function confirmarDesativacao() {
    if (!metaParaDesativar) return;
    try {
      await desativarMeta.mutateAsync(metaParaDesativar.id);
      toast.success(`Meta "${metaParaDesativar.descricao}" desativada.`);
      setMetaParaDesativar(null);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  function reativar(meta: MetaRead) {
    reativarMeta.mutate(meta.id, {
      onSuccess: () => toast.success(`Meta "${meta.descricao}" reativada.`),
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  }

  async function confirmarExclusao() {
    if (!metaParaExcluir) return;
    try {
      await excluirMeta.mutateAsync(metaParaExcluir.id);
      toast.success(`Meta "${metaParaExcluir.descricao}" excluída definitivamente.`);
      setMetaParaExcluir(null);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  const criterioOptions = CRITERIO_ORDENACAO_META_OPTIONS.map((valor) => ({
    value: valor,
    label: CRITERIO_ORDENACAO_META_LABEL[valor],
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Metas</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Seus objetivos de economia — o progresso vem dos lançamentos que você marcar como aporte.
          </p>
        </div>
        <Button onClick={abrirCriacao}>
          <Plus size={16} aria-hidden="true" />
          Nova meta
        </Button>
      </div>

      {!isLoading && metas && metas.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {FILTROS_RAPIDOS.map((filtro) => (
              <button
                key={filtro}
                type="button"
                onClick={() => setFiltroRapido(filtro)}
                className={`rounded-full px-3 py-1 text-caption font-medium transition-colors duration-fast ease-out ${
                  filtroRapido === filtro
                    ? "bg-accent text-text-onAccent"
                    : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                }`}
              >
                {LABEL_FILTRO_RAPIDO[filtro]} ({contagemPorSituacao[filtro]})
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <SearchBar
              value={busca}
              onChange={setBusca}
              placeholder="Buscar meta..."
              className="w-48"
            />
            <Select
              options={criterioOptions}
              value={criterio}
              onChange={(valor) => setCriterio(valor as CriterioOrdenacaoMeta)}
              aria-label="Ordenar metas"
              className="w-56"
            />
          </div>
        </div>
      )}

      {error ? (
        <Card>
          <ErrorMessage error={error} />
          <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
            Tentar novamente
          </Button>
        </Card>
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="space-y-3">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-2 w-full" />
            </Card>
          ))}
        </div>
      ) : !metas || metas.length === 0 ? (
        <Card>
          <EmptyState
            icon={Target}
            title="Nenhuma meta ainda"
            description="Crie um objetivo de economia — uma viagem, uma reserva de emergência, o que fizer sentido para você."
            action={
              <Button size="sm" onClick={abrirCriacao}>
                <Plus size={14} aria-hidden="true" />
                Criar meta
              </Button>
            }
          />
        </Card>
      ) : metasFiltradas.length === 0 ? (
        <Card>
          <EmptyState icon={Target} title="Nenhuma meta encontrada" description="Ajuste o filtro ou a busca para ver outras metas." />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {metasFiltradas.map((meta) => (
            <MetaResumoCard
              key={meta.id}
              meta={meta}
              onEditar={abrirEdicao}
              onDesativar={(m) => setMetaParaDesativar(m)}
              onReativar={reativar}
              onExcluir={(m) => setMetaParaExcluir(m)}
            />
          ))}
        </div>
      )}

      <MetaFormDialog open={formularioAberto} meta={metaEmEdicao} onClose={fecharFormulario} />

      <ConfirmAction
        open={metaParaDesativar != null}
        title={metaParaDesativar ? `Desativar "${metaParaDesativar.descricao}"?` : ""}
        description="A meta deixa de aparecer nas listagens padrão e não aceita novos aportes, mas todo o histórico de lançamentos já vinculados a ela é preservado. Você pode reativá-la a qualquer momento."
        confirmLabel="Desativar"
        tone="danger"
        loading={desativarMeta.isPending}
        onConfirm={confirmarDesativacao}
        onCancel={() => setMetaParaDesativar(null)}
      />

      <ConfirmAction
        open={metaParaExcluir != null}
        title={metaParaExcluir ? `Excluir "${metaParaExcluir.descricao}" definitivamente?` : ""}
        description="Esta ação é permanente e não pode ser desfeita. Os lançamentos já marcados como aporte desta meta não são apagados — eles continuam existindo em Transações, só deixam de ficar vinculados a esta meta."
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirMeta.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setMetaParaExcluir(null)}
      />
    </div>
  );
}
