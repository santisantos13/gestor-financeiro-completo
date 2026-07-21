import { useMemo } from "react";
import { SearchSelect } from "../../ui/SearchSelect";
import { useCategorias } from "../../../hooks/useCategoriaQueries";
import { resolveIconInfo } from "../../../lib/icons";
import { corDeContraste } from "../../../lib/color";
import type { CategoriaRead } from "../../../types/categoria";
import type { TipoTransacao } from "../../../types/enums";

export interface CategorySelectProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  /** Categoria sendo editada — ela mesma e todos os seus descendentes são
   * excluídos das opções (não pode virar filha da própria filha). Filtro
   * de UX apenas: o backend recalcula e rejeita qualquer ciclo de verdade
   * (`BusinessRuleError`, 422) independentemente do que a UI ofereceu. */
  excludeId?: number;
  apenasAtivas?: boolean;
  /** Usado por `TransacaoFormDialog` (docs/analise-arquitetural-transacao-frontend.md,
   * seção 5): quando definido, restringe as opções a categorias compatíveis
   * com o tipo da transação (`categoria.tipo === tipoTransacao ||
   * categoria.tipo === "AMBOS"`). Filtro de UX apenas — a compatibilidade
   * real continua validada pelo backend. */
  tipoTransacao?: TipoTransacao;
}

function construirCadeia(categoria: CategoriaRead, porId: Map<number, CategoriaRead>): string {
  const partes: string[] = [categoria.nome];
  let atual = categoria;
  while (atual.categoria_pai_id != null) {
    const pai = porId.get(atual.categoria_pai_id);
    if (!pai) break;
    partes.unshift(pai.nome);
    atual = pai;
  }
  return partes.join(" > ");
}

function eDescendente(categoria: CategoriaRead, ancestralId: number, porId: Map<number, CategoriaRead>): boolean {
  let atual: CategoriaRead | undefined = categoria;
  while (atual?.categoria_pai_id != null) {
    if (atual.categoria_pai_id === ancestralId) return true;
    atual = porId.get(atual.categoria_pai_id);
  }
  return false;
}

/**
 * Primeiro select "inteligente" de domínio do projeto (previsto desde a
 * Etapa F1, `docs/analise-arquitetural-frontend.md`, seção 12) — busca sua
 * própria lista via `useCategorias` e se comporta como um `SearchSelect`
 * comum por fora. Usado tanto para `categoria_pai_id` no formulário de
 * Categoria quanto, futuramente, para `categoria_id` em Transação. Label
 * de cada opção é a cadeia de ancestrais (`"Moradia > Aluguel"`) — nenhum
 * componente de árvore visual é criado (ver
 * docs/analise-arquitetural-categoria-frontend.md, seção 7).
 */
export function CategorySelect({
  name,
  label,
  optional,
  description,
  placeholder = "Sem categoria pai",
  disabled,
  excludeId,
  apenasAtivas = true,
  tipoTransacao,
}: CategorySelectProps) {
  const { data: categorias, isLoading } = useCategorias(apenasAtivas);

  const options = useMemo(() => {
    if (!categorias) return [];
    const porId = new Map(categorias.map((c) => [c.id, c]));
    return categorias
      .filter((c) => excludeId == null || (c.id !== excludeId && !eDescendente(c, excludeId, porId)))
      .filter((c) => tipoTransacao == null || c.tipo === tipoTransacao || c.tipo === "AMBOS")
      .map((c) => {
        const { Icon } = resolveIconInfo(c.icone);
        return {
          value: String(c.id),
          label: construirCadeia(c, porId),
          // Mesmo par ícone+cor que `CategoryBadge` já usa na tabela — Etapa
          // F10 (Rich Pickers, `docs/analise-arquitetural-rich-pickers.md`,
          // seção 5): zero mudança de busca/seleção, só a linha fica
          // visualmente idêntica à de `CategoryBadge`.
          render: (
            <span
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md"
              style={{
                backgroundColor: c.cor ?? "var(--color-surface-3)",
                color: c.cor ? corDeContraste(c.cor) : "var(--color-text-tertiary)",
              }}
            >
              <Icon size={11} aria-hidden="true" />
            </span>
          ),
        };
      });
  }, [categorias, excludeId, tipoTransacao]);

  return (
    <SearchSelect
      name={name}
      label={label}
      options={options}
      optional={optional}
      description={description}
      placeholder={placeholder}
      searchPlaceholder="Buscar categoria..."
      disabled={disabled}
      loading={isLoading}
    />
  );
}
