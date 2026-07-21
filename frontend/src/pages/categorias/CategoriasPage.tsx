import { useMemo, useState } from "react";
import { Ban, Eye, EyeOff, Pencil, Plus, RotateCcw, Tag, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { DataTable } from "../../components/ui/DataTable";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { Switch } from "../../components/ui/Switch";
import { CategoriaFormDialog } from "../../components/domain/categoria/CategoriaFormDialog";
import {
  buildCategoriaTableColumns,
  categoriaTableFilters,
  filtrarCategoriasVisiveis,
  ordenarCategoriasPorHierarquia,
} from "../../components/domain/categoria/categoriaTableColumns";
import {
  useCategorias,
  useAtualizarCategoria,
  useDesativarCategoria,
  useExcluirCategoria,
  useOcultarCategoria,
  useReexibirCategoria,
} from "../../hooks/useCategoriaQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import type { CategoriaRead } from "../../types/categoria";
import type { RowAction } from "../../types/table";

interface EstadoDialogoCategoria {
  aberto: boolean;
  categoria: CategoriaRead | null;
  somenteLeitura: boolean;
}

const DIALOGO_FECHADO: EstadoDialogoCategoria = { aberto: false, categoria: null, somenteLeitura: false };

// Etapa de Refinamento UX/UI, item 4: "lembrar o último estado durante a
// sessão" - `sessionStorage` (não `localStorage`, que é a régua já usada
// pela ordem da Sidebar para uma preferência permanente) porque recolher um
// grupo é uma escolha exploratória de agora, não uma preferência estável do
// usuário - some sozinha quando a aba fecha, sem precisar de UI para
// "resetar". Guarda só os ids (não a árvore inteira), tolera JSON inválido
// (fallback silencioso para "nada recolhido").
const CHAVE_SESSAO_COLAPSADOS = "categorias:colapsadas";

function carregarColapsadosDaSessao(): Set<number> {
  try {
    const bruto = sessionStorage.getItem(CHAVE_SESSAO_COLAPSADOS);
    if (!bruto) return new Set();
    const ids = JSON.parse(bruto);
    return Array.isArray(ids) ? new Set(ids.filter((id): id is number => typeof id === "number")) : new Set();
  } catch {
    return new Set();
  }
}

function salvarColapsadosNaSessao(colapsados: Set<number>): void {
  try {
    sessionStorage.setItem(CHAVE_SESSAO_COLAPSADOS, JSON.stringify([...colapsados]));
  } catch {
    // sessionStorage indisponível (modo privado, quota etc.) - degrada
    // graciosamente para "nunca lembra entre remontagens", nunca quebra a
    // tela.
  }
}

/**
 * Página `/categorias` — Etapa F7. Mesma composição de `ContasPage.tsx`
 * (`DataTable` + `CategoriaFormDialog` + `ConfirmAction`).
 *
 * Tarefa #111 (edição livre de categoria de sistema): "Editar" agora
 * aparece também para `e_do_sistema` — o backend passou a aceitar PATCH em
 * nome/tipo/cor/icone/categoria_pai_id de categoria de sistema
 * (`CategoriaService.atualizar` usa `_buscar_visivel`, não mais
 * `_buscar_editavel`). "Desativar"/"Excluir" continuam escondidas: uma
 * categoria de sistema é uma única linha compartilhada por TODOS os
 * usuários — desativar/excluir ela tiraria de todo mundo, não só de quem
 * clicou, e isso nunca foi pedido (o backend ainda rejeita as duas com 403
 * via `_buscar_editavel`). "Ver" continua sempre visível.
 *
 * Sprint de Refinamento Premium, item 4: "Ocultar para mim" é uma AÇÃO NOVA,
 * exclusiva de categoria de sistema (`e_do_sistema && !oculta_para_mim`) -
 * nunca toca a linha compartilhada, só grava uma entrada por-usuário no
 * backend (`CategoriaOcultaUsuario`). Some da listagem padrão sem afetar
 * ninguém mais; "Mostrar categorias ocultas" (`incluir_ocultas`) é como o
 * usuário encontra e reexibe o que ocultou.
 */
export function CategoriasPage() {
  const toast = useToast();
  const [mostrarInativas, setMostrarInativas] = useState(false);
  const [mostrarOcultas, setMostrarOcultas] = useState(false);
  const { data: categorias, isLoading, error, refetch } = useCategorias(!mostrarInativas, mostrarOcultas);

  // Ordem hierárquica por padrão (pai imediatamente seguido de suas
  // subcategorias) — ver docs/revisao-tecnica-refinamento-ui.md. Ordenar
  // explicitamente por uma coluna (clique no cabeçalho) sobrepõe esta
  // ordem dentro de `useDataTable`, o que é o comportamento esperado.
  const categoriasOrdenadas = useMemo(() => ordenarCategoriasPorHierarquia(categorias ?? []), [categorias]);

  const [colapsados, setColapsados] = useState<Set<number>>(carregarColapsadosDaSessao);

  // Ids que têm ao menos uma subcategoria direta — usado tanto para decidir
  // se "Expandir tudo"/"Recolher tudo" faz sentido mostrar (nenhuma
  // categoria com filhos = nada pra recolher) quanto para o próprio
  // "Recolher tudo" (recolhe só quem TEM filho; um id sem filho no Set não
  // faz diferença nenhuma, mas manter o Set enxuto é mais fácil de
  // depurar).
  const idsComFilhos = useMemo(
    () => [...new Set(categoriasOrdenadas.map((c) => c.categoria_pai_id).filter((id): id is number => id != null))],
    [categoriasOrdenadas],
  );

  function alternarColapso(id: number) {
    setColapsados((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(id)) {
        proximo.delete(id);
      } else {
        proximo.add(id);
      }
      salvarColapsadosNaSessao(proximo);
      return proximo;
    });
  }

  function alternarTodos(recolher: boolean) {
    const proximo = recolher ? new Set(idsComFilhos) : new Set<number>();
    setColapsados(proximo);
    salvarColapsadosNaSessao(proximo);
  }

  const categoriasVisiveis = useMemo(
    () => filtrarCategoriasVisiveis(categoriasOrdenadas, colapsados),
    [categoriasOrdenadas, colapsados],
  );
  const columns = useMemo(
    () => buildCategoriaTableColumns(categoriasOrdenadas, colapsados, alternarColapso),
    [categoriasOrdenadas, colapsados],
  );

  const [dialogo, setDialogo] = useState<EstadoDialogoCategoria>(DIALOGO_FECHADO);
  const [categoriaParaDesativar, setCategoriaParaDesativar] = useState<CategoriaRead | null>(null);
  const [categoriaParaExcluir, setCategoriaParaExcluir] = useState<CategoriaRead | null>(null);

  const atualizarCategoria = useAtualizarCategoria();
  const desativarCategoria = useDesativarCategoria();
  const excluirCategoria = useExcluirCategoria();
  const ocultarCategoria = useOcultarCategoria();
  const reexibirCategoria = useReexibirCategoria();

  function abrirCriacao() {
    setDialogo({ aberto: true, categoria: null, somenteLeitura: false });
  }

  function abrirVisualizacao(categoria: CategoriaRead) {
    setDialogo({ aberto: true, categoria, somenteLeitura: true });
  }

  function abrirEdicao(categoria: CategoriaRead) {
    setDialogo({ aberto: true, categoria, somenteLeitura: false });
  }

  function fecharDialogo() {
    setDialogo((atual) => ({ ...atual, aberto: false }));
  }

  async function confirmarDesativacao() {
    if (!categoriaParaDesativar) return;
    try {
      await desativarCategoria.mutateAsync(categoriaParaDesativar.id);
      toast.success(`Categoria "${categoriaParaDesativar.nome}" desativada.`);
      setCategoriaParaDesativar(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusao() {
    if (!categoriaParaExcluir) return;
    try {
      await excluirCategoria.mutateAsync(categoriaParaExcluir.id);
      toast.success(`Categoria "${categoriaParaExcluir.nome}" excluída definitivamente.`);
      setCategoriaParaExcluir(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  function reativar(categoria: CategoriaRead) {
    atualizarCategoria.mutate(
      { id: categoria.id, dados: { ativo: true } },
      {
        onSuccess: () => toast.success(`Categoria "${categoria.nome}" reativada.`),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  function ocultarParaMim(categoria: CategoriaRead) {
    ocultarCategoria.mutate(categoria.id, {
      onSuccess: () => toast.success(`Categoria "${categoria.nome}" ocultada - só para você.`),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  function reexibir(categoria: CategoriaRead) {
    reexibirCategoria.mutate(categoria.id, {
      onSuccess: () => toast.success(`Categoria "${categoria.nome}" reexibida.`),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  const rowActions: RowAction<CategoriaRead>[] = [
    { label: "Ver", icon: Eye, onClick: abrirVisualizacao },
    {
      label: "Editar",
      icon: Pencil,
      onClick: abrirEdicao,
    },
    {
      label: "Desativar",
      icon: Ban,
      tone: "danger",
      onClick: (categoria) => setCategoriaParaDesativar(categoria),
      hidden: (categoria) => !categoria.ativo || categoria.e_do_sistema,
    },
    {
      label: "Reativar",
      icon: RotateCcw,
      onClick: reativar,
      hidden: (categoria) => categoria.ativo,
    },
    {
      // Exclusiva de categoria de sistema (Sprint de Refinamento Premium,
      // item 4) - categoria própria já tem Desativar/Excluir acima.
      label: "Ocultar para mim",
      icon: EyeOff,
      tone: "danger",
      onClick: ocultarParaMim,
      hidden: (categoria) => !categoria.e_do_sistema || categoria.oculta_para_mim,
    },
    {
      label: "Reexibir",
      icon: RotateCcw,
      onClick: reexibir,
      hidden: (categoria) => !categoria.oculta_para_mim,
    },
    {
      // Escondida para categoria de sistema (mesmo motivo de
      // Editar/Desativar — somente leitura, o backend rejeitaria com 403).
      // Fora isso, sempre visível: quem decide se bloqueia por vínculo é o
      // backend (docs/analise-arquitetural-exclusao.md, seção 3).
      label: "Excluir",
      icon: Trash2,
      tone: "danger",
      onClick: (categoria) => setCategoriaParaExcluir(categoria),
      hidden: (categoria) => categoria.e_do_sistema,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Categorias</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Organize receitas e despesas. Categorias do sistema aparecem para todos os usuários e podem ser
            editadas livremente, mas não desativadas nem excluídas (são compartilhadas por todos).
          </p>
        </div>
        <Button onClick={abrirCriacao}>
          <Plus size={16} aria-hidden="true" />
          Nova categoria
        </Button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Switch
            id="mostrar-inativas"
            checked={mostrarInativas}
            onCheckedChange={setMostrarInativas}
            aria-label="Mostrar categorias inativas"
          />
          <label htmlFor="mostrar-inativas" className="cursor-pointer text-sm text-text-secondary">
            Mostrar categorias inativas
          </label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="mostrar-ocultas"
            checked={mostrarOcultas}
            onCheckedChange={setMostrarOcultas}
            aria-label="Mostrar categorias que você ocultou"
          />
          <label htmlFor="mostrar-ocultas" className="cursor-pointer text-sm text-text-secondary">
            Mostrar categorias ocultas por você
          </label>
        </div>
        {idsComFilhos.length > 0 && (
          <div className="flex items-center gap-3 text-sm">
            <button
              type="button"
              onClick={() => alternarTodos(false)}
              className="text-text-secondary transition-colors hover:text-text-primary"
            >
              Expandir tudo
            </button>
            <span className="text-border" aria-hidden="true">
              |
            </span>
            <button
              type="button"
              onClick={() => alternarTodos(true)}
              className="text-text-secondary transition-colors hover:text-text-primary"
            >
              Recolher tudo
            </button>
          </div>
        )}
      </div>

      <DataTable
        data={categoriasVisiveis}
        columns={columns}
        getRowId={(categoria) => categoria.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        searchable
        searchPlaceholder="Buscar por nome..."
        filters={categoriaTableFilters}
        rowActions={rowActions}
        emptyIcon={Tag}
        emptyTitle="Nenhuma categoria ainda"
        emptyDescription="Crie sua primeira categoria para organizar receitas e despesas."
        emptyAction={
          !categorias || categorias.length === 0 ? (
            <Button size="sm" onClick={abrirCriacao}>
              <Plus size={14} aria-hidden="true" />
              Nova categoria
            </Button>
          ) : undefined
        }
        aria-label="Categorias"
      />

      <CategoriaFormDialog
        open={dialogo.aberto}
        categoria={dialogo.categoria}
        somenteLeitura={dialogo.somenteLeitura}
        onClose={fecharDialogo}
      />

      <ConfirmAction
        open={categoriaParaDesativar != null}
        title={categoriaParaDesativar ? `Desativar "${categoriaParaDesativar.nome}"?` : ""}
        description="A categoria deixa de aparecer nas listagens padrão. Transações antigas continuam com o histórico preservado. Você pode reativá-la a qualquer momento."
        confirmLabel="Desativar"
        tone="danger"
        loading={desativarCategoria.isPending}
        onConfirm={confirmarDesativacao}
        onCancel={() => setCategoriaParaDesativar(null)}
      />

      <ConfirmAction
        open={categoriaParaExcluir != null}
        title={categoriaParaExcluir ? `Excluir "${categoriaParaExcluir.nome}" definitivamente?` : ""}
        description="Esta ação é permanente e não pode ser desfeita. A categoria será excluída para sempre — só é possível excluir uma categoria sem transações vinculadas e sem subcategorias."
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirCategoria.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setCategoriaParaExcluir(null)}
      />
    </div>
  );
}
