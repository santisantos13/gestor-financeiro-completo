import { ChevronDown, ChevronRight, CornerDownRight } from "lucide-react";
import { Badge } from "../../ui/Badge";
import { AtivoBadge } from "../../ui/AtivoBadge";
import { CategoryBadge } from "./CategoryBadge";
import type { ColumnDef, FilterDef } from "../../../types/table";
import type { CategoriaRead } from "../../../types/categoria";

export const LABEL_TIPO_CATEGORIA: Record<string, string> = {
  RECEITA: "Receita",
  DESPESA: "Despesa",
  AMBOS: "Receita e despesa",
};

/**
 * Reordena a lista para que cada categoria pai apareca imediatamente
 * seguida de suas subcategorias (profundidade indefinida, mas na pratica
 * o backend so permite um nivel, mesmo assim a funcao e recursiva, nao
 * assume isso). Refinamento de UI: antes pai e filha apareciam em
 * qualquer ordem (a do backend), sem nenhum agrupamento visual, e o
 * usuario nao conseguia identificar a hierarquia sem precisar pensar.
 * Ordem entre irmaos preserva a ordem original recebida. Categorias
 * orfas (cujo categoria_pai_id aponta para um id fora da lista atual,
 * ex. filtro "apenas ativas" escondendo o pai) viram raiz, nunca somem da
 * listagem. So reordena o array; nao muda nenhum dado da entidade.
 */
export function ordenarCategoriasPorHierarquia(categorias: CategoriaRead[]): CategoriaRead[] {
  const idsExistentes = new Set(categorias.map((c) => c.id));
  const filhosPorPai = new Map<number, CategoriaRead[]>();
  const raizes: CategoriaRead[] = [];

  for (const categoria of categorias) {
    const paiId = categoria.categoria_pai_id;
    if (paiId != null && idsExistentes.has(paiId)) {
      const filhos = filhosPorPai.get(paiId) ?? [];
      filhos.push(categoria);
      filhosPorPai.set(paiId, filhos);
    } else {
      raizes.push(categoria);
    }
  }

  const resultado: CategoriaRead[] = [];
  function visitar(categoria: CategoriaRead) {
    resultado.push(categoria);
    for (const filho of filhosPorPai.get(categoria.id) ?? []) visitar(filho);
  }
  raizes.forEach(visitar);
  return resultado;
}

/**
 * Remove da lista qualquer categoria com um ancestral recolhido — Etapa de
 * Refinamento UX/UI, item 4 ("categorias pai/filha como grupos
 * recolhíveis"). Recebe a lista JÁ ordenada por `ordenarCategoriasPorHierarquia`
 * (pai sempre antes dos filhos) e um `Set` de ids recolhidos; percorre uma
 * vez só, empilhando "estou dentro de um ramo recolhido" enquanto a
 * profundidade dos itens seguintes for maior que a do pai que disparou o
 * recolhimento. Só filtra a lista visível do `DataTable` - `buildCategoriaTableColumns`
 * continua recebendo a lista completa (precisa saber quantos filhos cada
 * pai tem e a profundidade real, mesmo dos que estão escondidos agora).
 *
 * Efeito colateral aceito: como a busca embutida do `DataTable`
 * (`useDataTable`) filtra só sobre o array `data` recebido, uma
 * subcategoria escondida por um pai recolhido também some da busca -
 * mesmo comportamento de qualquer árvore recolhível comum (Explorer, VS
 * Code) onde um nó fechado não aparece até ser reaberto.
 */
export function filtrarCategoriasVisiveis(
  categoriasOrdenadas: CategoriaRead[],
  colapsados: ReadonlySet<number>,
): CategoriaRead[] {
  if (colapsados.size === 0) return categoriasOrdenadas;

  const visiveis: CategoriaRead[] = [];
  // pilha de ids cujo ramo está recolhido - um item só é escondido se
  // algum ancestral (não necessariamente o pai imediato) estiver aqui.
  const ramosRecolhidos = new Set<number>();

  for (const categoria of categoriasOrdenadas) {
    const paiId = categoria.categoria_pai_id;
    const paiEscondido = paiId != null && (colapsados.has(paiId) || ramosRecolhidos.has(paiId));
    if (paiEscondido) {
      ramosRecolhidos.add(categoria.id);
      continue;
    }
    visiveis.push(categoria);
  }
  return visiveis;
}

/**
 * Colunas do DataTable da pagina /categorias, puramente apresentacao,
 * mesmo principio de contaTableColumns.tsx.
 *
 * Hierarquia visual (Refinamento de UI): a coluna "Nome" indenta cada
 * subcategoria (20px por nivel) com um conector sutil (CornerDownRight,
 * text-text-tertiary, nunca um badge escrito "Pai"/"Filha") e mostra a
 * contagem de subcategorias diretas ao lado do nome de quem tem filhas.
 * Funciona junto de ordenarCategoriasPorHierarquia: esta funcao so
 * decide COMO desenhar cada linha; a ordem de quem aparece perto de quem
 * e responsabilidade de quem monta data (CategoriasPage).
 *
 * Etapa de Refinamento UX/UI, item 4 (ajustado a pedido do usuário depois
 * da 1ª versão): `colapsados`/`onAlternarColapso` são opcionais
 * (retrocompatível com qualquer outro uso futuro desta função sem grupos
 * recolhíveis) - quando uma categoria tem `totalFilhos > 0`, a linha
 * INTEIRA do nome (chevron + badge + texto, não só um ícone pequeno) vira
 * clicável e recolhe/expande os filhos - clicar em "Alimentação" já
 * recolhe "Delivery"/"Mercado"/"Padaria"/"Restaurantes" para dentro dela,
 * sem precisar acertar um alvo minúsculo. `stopPropagation` só por
 * disciplina, caso um clique de linha genérico venha a existir no futuro
 * no `DataTable`. Coluna "Categoria pai" removida a pedido do usuário
 * ("inútil") - a indentação + conector visual já comunica a hierarquia.
 */
export function buildCategoriaTableColumns(
  categorias: CategoriaRead[],
  colapsados?: ReadonlySet<number>,
  onAlternarColapso?: (id: number) => void,
): ColumnDef<CategoriaRead>[] {
  const porId = new Map(categorias.map((c) => [c.id, c]));

  const totalFilhosPorId = new Map<number, number>();
  for (const categoria of categorias) {
    if (categoria.categoria_pai_id != null) {
      totalFilhosPorId.set(categoria.categoria_pai_id, (totalFilhosPorId.get(categoria.categoria_pai_id) ?? 0) + 1);
    }
  }

  function calcularProfundidade(categoria: CategoriaRead): number {
    let profundidade = 0;
    let atual = categoria;
    const visitados = new Set<number>([categoria.id]);
    while (atual.categoria_pai_id != null) {
      const pai = porId.get(atual.categoria_pai_id);
      if (!pai || visitados.has(pai.id)) break;
      profundidade += 1;
      visitados.add(pai.id);
      atual = pai;
    }
    return profundidade;
  }

  return [
    {
      key: "nome",
      header: "Nome",
      accessor: (categoria) => categoria.nome,
      sortable: true,
      render: (categoria) => {
        const profundidade = calcularProfundidade(categoria);
        const totalFilhos = totalFilhosPorId.get(categoria.id) ?? 0;
        const recolhido = colapsados?.has(categoria.id) ?? false;
        const recolhivel = totalFilhos > 0 && !!onAlternarColapso;

        const conteudo = (
          <>
            {profundidade > 0 && (
              <CornerDownRight size={13} className="shrink-0 text-text-tertiary" aria-hidden="true" />
            )}
            {totalFilhos > 0 ? (
              recolhido ? (
                <ChevronRight size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
              ) : (
                <ChevronDown size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
              )
            ) : (
              <span className="w-3.5 shrink-0" aria-hidden="true" />
            )}
            <CategoryBadge nome={categoria.nome} cor={categoria.cor} icone={categoria.icone} size="sm" showName />
            {categoria.e_do_sistema && (
              // Auditoria de Identidade Visual: tone `accent` é reservado
              // para interação (design-system.md, seção 6.3) — "Sistema" é
              // uma classificação neutra, não uma ação. Com o seed de
              // categorias padrão (13+ categorias de sistema), esse badge
              // passou a aparecer em toda a tabela — `neutral` (cinza)
              // é o tone correto para essa densidade, sem competir com
              // `CategoryBadge` (cor real da categoria) ao lado.
              <Badge tone="neutral" className="shrink-0">
                Sistema
              </Badge>
            )}
            {categoria.oculta_para_mim && (
              // Sprint de Refinamento Premium, item 4: só aparece com
              // "Mostrar categorias ocultas" ligado (senão a linha nem
              // entra na listagem) - sinaliza que só ESTE usuário não vê
              // mais esta categoria de sistema.
              <Badge tone="warning" className="shrink-0">
                Oculta para você
              </Badge>
            )}
            {totalFilhos > 0 && (
              <span className="shrink-0 text-micro text-text-tertiary">
                {totalFilhos} subcategoria{totalFilhos > 1 ? "s" : ""}
              </span>
            )}
          </>
        );

        if (recolhivel) {
          return (
            <button
              type="button"
              onClick={(evento) => {
                evento.stopPropagation();
                onAlternarColapso!(categoria.id);
              }}
              className="-my-1 flex w-full items-center gap-2 rounded py-1 text-left transition-colors hover:bg-surface-3"
              style={profundidade > 0 ? { paddingLeft: `${profundidade * 20}px` } : undefined}
              aria-label={recolhido ? `Expandir ${categoria.nome}` : `Recolher ${categoria.nome}`}
              aria-expanded={!recolhido}
            >
              {conteudo}
            </button>
          );
        }

        return (
          <span
            className="flex items-center gap-2"
            style={profundidade > 0 ? { paddingLeft: `${profundidade * 20}px` } : undefined}
          >
            {conteudo}
          </span>
        );
      },
    },
    {
      key: "tipo",
      header: "Tipo",
      accessor: (categoria) => categoria.tipo,
      sortable: true,
      render: (categoria) => LABEL_TIPO_CATEGORIA[categoria.tipo] ?? categoria.tipo,
    },
    {
      key: "ativo",
      header: "Status",
      accessor: (categoria) => (categoria.ativo ? "Ativa" : "Inativa"),
      sortable: true,
      render: (categoria) => (
        <AtivoBadge ativo={categoria.ativo} labelAtivo="Ativa" labelInativo="Inativa" />
      ),
    },
  ];
}

export const categoriaTableFilters: FilterDef<CategoriaRead>[] = [
  {
    key: "tipo",
    label: "Tipo",
    options: Object.entries(LABEL_TIPO_CATEGORIA).map(([value, label]) => ({ value, label })),
    predicate: (categoria, value) => categoria.tipo === value,
  },
];
