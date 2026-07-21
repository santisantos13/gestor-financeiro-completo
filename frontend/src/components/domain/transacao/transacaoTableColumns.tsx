import { ArrowDownCircle, ArrowUpCircle } from "lucide-react";
import { CategoryBadge } from "../categoria/CategoryBadge";
import { TagBadge } from "../tag/TagBadge";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { BandeiraBadge } from "../../ui/BandeiraBadge";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { formatDate } from "../../../utils/date";
import { formatMoney } from "../../../utils/format";
import type { ColumnDef } from "../../../types/table";
import type { CategoriaRead } from "../../../types/categoria";
import type { ContaRead } from "../../../types/conta";
import type { CartaoRead } from "../../../types/cartao";
import type { TransacaoRead } from "../../../types/transacao";

export const LABEL_TIPO_TRANSACAO: Record<string, string> = {
  RECEITA: "Receita",
  DESPESA: "Despesa",
};

export const LABEL_STATUS_TRANSACAO: Record<string, string> = {
  PENDENTE: "Pendente",
  PAGO: "Pago",
};

interface BuildColumnsOptions {
  categoriasPorId: Map<number, CategoriaRead>;
  contasPorId: Map<number, ContaRead>;
  cartoesPorId: Map<number, CartaoRead>;
}

/**
 * Diferente de toda `*TableColumns.tsx` anterior (`ColumnDef[]` como
 * constante — `ContaRead`/`CategoriaRead`/etc. já trazem tudo que a linha
 * precisa mostrar), `TransacaoRead` só guarda `categoria_id`/`conta_id`/
 * `cartao_id` crus (ver docs/analise-arquitetural-transacao-frontend.md,
 * seção 1) — o nome/cor/ícone da categoria e o nome/instituição da conta
 * ou cartão de origem vêm de listas carregadas à parte (`useCategorias`/
 * `useContas`/`useCartoes`) na própria `TransacoesPage`. Por isso as
 * colunas são construídas por uma função, recebendo os três mapas de
 * consulta já prontos, em vez de uma constante exportada direto.
 */
export function buildTransacaoTableColumns({
  categoriasPorId,
  contasPorId,
  cartoesPorId,
}: BuildColumnsOptions): ColumnDef<TransacaoRead>[] {
  return [
    {
      key: "data",
      header: "Data",
      accessor: (transacao) => transacao.data,
      sortable: true,
      width: "w-28",
      render: (transacao) => <span className="tabular">{formatDate(transacao.data)}</span>,
    },
    {
      key: "descricao",
      header: "Descrição",
      accessor: (transacao) => transacao.descricao,
      sortable: true,
    },
    {
      key: "categoria",
      header: "Categoria",
      accessor: (transacao) => (transacao.categoria_id ? categoriasPorId.get(transacao.categoria_id)?.nome ?? "" : ""),
      hideOnMobile: true,
      render: (transacao) => {
        const categoria = transacao.categoria_id ? categoriasPorId.get(transacao.categoria_id) : undefined;
        if (!categoria) return <span className="text-text-tertiary">Sem categoria</span>;
        return <CategoryBadge nome={categoria.nome} cor={categoria.cor} icone={categoria.icone} size="sm" showName />;
      },
    },
    {
      key: "origem",
      header: "Origem",
      accessor: (transacao) =>
        transacao.conta_id
          ? contasPorId.get(transacao.conta_id)?.nome ?? ""
          : transacao.cartao_id
            ? cartoesPorId.get(transacao.cartao_id)?.nome ?? ""
            : "",
      hideOnMobile: true,
      render: (transacao) => {
        // mesma correção de `transferenciaTableColumns.tsx` (responsividade,
        // 2026-07-21): `truncate` no container flex não faz nada sozinho -
        // o span de texto precisa do próprio `min-w-0` para poder encolher
        // abaixo do conteúdo antes do `truncate` ter efeito.
        if (transacao.conta_id != null) {
          const conta = contasPorId.get(transacao.conta_id);
          return (
            <span className="flex min-w-0 items-center gap-1.5">
              <InstitutionBadge nome={conta?.instituicao} size="sm" />
              <span className="min-w-0 truncate">{conta?.nome ?? "Conta"}</span>
            </span>
          );
        }
        if (transacao.cartao_id != null) {
          const cartao = cartoesPorId.get(transacao.cartao_id);
          return (
            <span className="flex min-w-0 items-center gap-1.5">
              {cartao && <BandeiraBadge bandeira={cartao.bandeira} size="sm" />}
              <span className="min-w-0 truncate">{cartao?.nome ?? "Cartão"}</span>
            </span>
          );
        }
        return "—";
      },
    },
    {
      key: "tipo",
      header: "Tipo",
      accessor: (transacao) => transacao.tipo,
      sortable: true,
      width: "w-28",
      // Nunca só texto (design-system.md, sistema semântico de status): a
      // seta + cor comunica entrada/saída antes mesmo de ler o rótulo.
      render: (transacao) =>
        transacao.tipo === "RECEITA" ? (
          <span className="flex items-center gap-1.5 text-positive">
            <ArrowUpCircle size={14} aria-hidden="true" />
            Receita
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-negative">
            <ArrowDownCircle size={14} aria-hidden="true" />
            Despesa
          </span>
        ),
    },
    {
      key: "valor",
      header: "Valor",
      accessor: (transacao) => Number(transacao.valor),
      sortable: true,
      align: "right",
      render: (transacao) => (
        <span className={`tabular font-medium ${transacao.tipo === "RECEITA" ? "text-positive" : "text-negative"}`}>
          {transacao.tipo === "RECEITA" ? "+" : "-"} {formatMoney(transacao.valor)}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      accessor: (transacao) => transacao.status,
      sortable: true,
      width: "w-28",
      render: (transacao) => <FinancialBadge status={transacao.status} />,
    },
    {
      key: "tags",
      header: "Tags",
      accessor: () => "",
      hideOnMobile: true,
      render: (transacao) =>
        transacao.tags.length === 0 ? (
          <span className="text-text-tertiary">—</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {transacao.tags.slice(0, 2).map((tag) => (
              <TagBadge key={tag.id} nome={tag.nome} cor={tag.cor} />
            ))}
            {transacao.tags.length > 2 && (
              <span className="text-micro text-text-tertiary">+{transacao.tags.length - 2}</span>
            )}
          </div>
        ),
    },
  ];
}

/** Filtros server-side de fato (seção 2 do documento) — repassados direto
 * como parâmetro de `GET /transacoes`, não um `FilterDef` client-side como
 * `contaTableFilters`. Mantidos aqui só para reaproveitar os mesmos rótulos
 * das colunas. */
export const FILTROS_TIPO_TRANSACAO = Object.entries(LABEL_TIPO_TRANSACAO).map(([value, label]) => ({
  value,
  label,
}));

export const FILTROS_STATUS_TRANSACAO = Object.entries(LABEL_STATUS_TRANSACAO).map(([value, label]) => ({
  value,
  label,
}));
