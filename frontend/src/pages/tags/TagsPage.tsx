import { useState } from "react";
import { Ban, Eye, Pencil, Plus, RotateCcw, Tags, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { DataTable } from "../../components/ui/DataTable";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { Switch } from "../../components/ui/Switch";
import { TagFormDialog } from "../../components/domain/tag/TagFormDialog";
import { tagTableColumns } from "../../components/domain/tag/tagTableColumns";
import {
  useTags,
  useAtualizarTag,
  useDesativarTag,
  useExcluirTag,
  useUsoTag,
} from "../../hooks/useTagQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import type { TagRead } from "../../types/tag";
import type { RowAction } from "../../types/table";

interface EstadoDialogoTag {
  aberto: boolean;
  tag: TagRead | null;
  somenteLeitura: boolean;
}

const DIALOGO_FECHADO: EstadoDialogoTag = { aberto: false, tag: null, somenteLeitura: false };

/**
 * Página `/tags` — Etapa F8. Mesma composição de `ContasPage.tsx`/
 * `CategoriasPage.tsx` (`DataTable` + `*FormDialog` + `ConfirmAction`),
 * versão mais enxuta: sem regra de "escondido para categoria de sistema"
 * (Tag não tem essa dimensão) e sem `filters` (nenhum campo enumerável).
 * Ver docs/analise-arquitetural-tag-frontend.md, seção 9.
 */
export function TagsPage() {
  const toast = useToast();
  const [mostrarInativas, setMostrarInativas] = useState(false);
  const { data: tags, isLoading, error, refetch } = useTags(!mostrarInativas);

  const [dialogo, setDialogo] = useState<EstadoDialogoTag>(DIALOGO_FECHADO);
  const [tagParaDesativar, setTagParaDesativar] = useState<TagRead | null>(null);
  const [tagParaExcluir, setTagParaExcluir] = useState<TagRead | null>(null);

  const atualizarTag = useAtualizarTag();
  const desativarTag = useDesativarTag();
  const excluirTag = useExcluirTag();
  // Só informativo — nunca bloqueia a exclusão (seção 2.3 da análise de
  // exclusão), consultado assim que a confirmação abre.
  const { data: uso } = useUsoTag(tagParaExcluir?.id ?? null);

  function abrirCriacao() {
    setDialogo({ aberto: true, tag: null, somenteLeitura: false });
  }

  function abrirVisualizacao(tag: TagRead) {
    setDialogo({ aberto: true, tag, somenteLeitura: true });
  }

  function abrirEdicao(tag: TagRead) {
    setDialogo({ aberto: true, tag, somenteLeitura: false });
  }

  function fecharDialogo() {
    setDialogo((atual) => ({ ...atual, aberto: false }));
  }

  async function confirmarDesativacao() {
    if (!tagParaDesativar) return;
    try {
      await desativarTag.mutateAsync(tagParaDesativar.id);
      toast.success(`Tag "${tagParaDesativar.nome}" desativada.`);
      setTagParaDesativar(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusao() {
    if (!tagParaExcluir) return;
    try {
      await excluirTag.mutateAsync(tagParaExcluir.id);
      toast.success(`Tag "${tagParaExcluir.nome}" excluída definitivamente.`);
      setTagParaExcluir(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  function reativar(tag: TagRead) {
    atualizarTag.mutate(
      { id: tag.id, dados: { ativo: true } },
      {
        onSuccess: () => toast.success(`Tag "${tag.nome}" reativada.`),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  const rowActions: RowAction<TagRead>[] = [
    { label: "Ver", icon: Eye, onClick: abrirVisualizacao },
    { label: "Editar", icon: Pencil, onClick: abrirEdicao },
    {
      label: "Desativar",
      icon: Ban,
      tone: "danger",
      onClick: (tag) => setTagParaDesativar(tag),
      hidden: (tag) => !tag.ativo,
    },
    {
      label: "Reativar",
      icon: RotateCcw,
      onClick: reativar,
      hidden: (tag) => tag.ativo,
    },
    {
      // Sempre visível — Tag nunca bloqueia por uso (seção 2.3), a
      // confirmação só avisa quantas transações perdem o rótulo.
      label: "Excluir",
      icon: Trash2,
      tone: "danger",
      onClick: (tag) => setTagParaExcluir(tag),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Tags</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Classifique receitas e despesas livremente, além da categoria.
          </p>
        </div>
        <Button onClick={abrirCriacao}>
          <Plus size={16} aria-hidden="true" />
          Nova tag
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="mostrar-inativas"
          checked={mostrarInativas}
          onCheckedChange={setMostrarInativas}
          aria-label="Mostrar tags inativas"
        />
        <label htmlFor="mostrar-inativas" className="cursor-pointer text-sm text-text-secondary">
          Mostrar tags inativas
        </label>
      </div>

      <DataTable
        data={tags ?? []}
        columns={tagTableColumns}
        getRowId={(tag) => tag.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        searchable
        searchPlaceholder="Buscar por nome..."
        rowActions={rowActions}
        emptyIcon={Tags}
        emptyTitle="Nenhuma tag ainda"
        emptyAction={
          !tags || tags.length === 0 ? (
            <Button size="sm" onClick={abrirCriacao}>
              <Plus size={14} aria-hidden="true" />
              Nova tag
            </Button>
          ) : undefined
        }
        emptyDescription="Crie sua primeira tag para classificar receitas e despesas."
        aria-label="Tags"
      />

      <TagFormDialog
        open={dialogo.aberto}
        tag={dialogo.tag}
        somenteLeitura={dialogo.somenteLeitura}
        onClose={fecharDialogo}
      />

      <ConfirmAction
        open={tagParaDesativar != null}
        title={tagParaDesativar ? `Desativar "${tagParaDesativar.nome}"?` : ""}
        description="A tag deixa de aparecer nas listagens padrão. Transações antigas continuam com o histórico preservado. Você pode reativá-la a qualquer momento."
        confirmLabel="Desativar"
        tone="danger"
        loading={desativarTag.isPending}
        onConfirm={confirmarDesativacao}
        onCancel={() => setTagParaDesativar(null)}
      />

      <ConfirmAction
        open={tagParaExcluir != null}
        title={tagParaExcluir ? `Excluir "${tagParaExcluir.nome}" definitivamente?` : ""}
        description={
          tagParaExcluir
            ? `Esta ação é permanente. "${tagParaExcluir.nome}" será removida de` +
              (uso && uso.transacoes_vinculadas > 0
                ? ` ${uso.transacoes_vinculadas} transação(ões) que a usam.`
                : " todas as transações que a usam (nenhuma no momento).")
            : ""
        }
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirTag.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setTagParaExcluir(null)}
      />
    </div>
  );
}
