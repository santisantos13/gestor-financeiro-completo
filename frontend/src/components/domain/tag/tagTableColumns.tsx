import { AtivoBadge } from "../../ui/AtivoBadge";
import { TagBadge } from "./TagBadge";
import type { ColumnDef } from "../../../types/table";
import type { TagRead } from "../../../types/tag";

/**
 * Colunas do `DataTable` da página `/tags` — puramente apresentação, mesmo
 * princípio de `contaTableColumns.tsx`/`categoriaTableColumns.tsx`. Só
 * duas colunas: Tag não tem `tipo`, `categoria_pai` nem qualquer outro
 * campo além de `nome`/`cor`/`ativo` — a tabela mais enxuta do projeto até
 * agora, por decisão honesta (não uma coluna a mais para "preencher
 * espaço"). Nenhuma coluna precisa de `hideOnMobile`: com só duas colunas,
 * o card mobile já é naturalmente compacto. Ver
 * docs/analise-arquitetural-tag-frontend.md, seção 9.
 */
export const tagTableColumns: ColumnDef<TagRead>[] = [
  {
    key: "nome",
    header: "Nome",
    accessor: (tag) => tag.nome,
    sortable: true,
    render: (tag) => <TagBadge nome={tag.nome} cor={tag.cor} />,
  },
  {
    key: "ativo",
    header: "Status",
    accessor: (tag) => (tag.ativo ? "Ativa" : "Inativa"),
    sortable: true,
    render: (tag) => <AtivoBadge ativo={tag.ativo} labelAtivo="Ativa" labelInativo="Inativa" />,
  },
];

/** Sem `FilterDef`: não há campo enumerável em Tag que justifique um
 * filtro — o mesmo raciocínio que já conteve a tentação de inventar
 * filtro sem valor em `contaTableColumns.tsx`. */
