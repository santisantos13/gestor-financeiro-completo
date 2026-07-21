import { AtivoBadge } from "../../ui/AtivoBadge";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { formatMoney } from "../../../utils/format";
import type { ColumnDef, FilterDef } from "../../../types/table";
import type { ContaRead } from "../../../types/conta";

export const LABEL_TIPO_CONTA: Record<string, string> = {
  CORRENTE: "Conta corrente",
  POUPANCA: "Poupança",
  CARTEIRA: "Carteira",
  INVESTIMENTO: "Investimento",
};

/** Colunas do `DataTable` da página `/contas` — puramente apresentação,
 * nenhuma regra de negócio (`saldo_atual` já vem calculado do backend).
 * Ver docs/analise-arquitetural-frontend.md, seção 13. Coluna
 * `instituicao` usa `InstitutionBadge` (registry único de branding) em vez
 * de texto solto — mesmo componente usado em `ContaFormDialog` e nos
 * cards do Dashboard. */
export const contaTableColumns: ColumnDef<ContaRead>[] = [
  {
    key: "nome",
    header: "Nome",
    accessor: (conta) => conta.nome,
    sortable: true,
  },
  {
    key: "tipo",
    header: "Tipo",
    accessor: (conta) => conta.tipo,
    sortable: true,
    render: (conta) => LABEL_TIPO_CONTA[conta.tipo] ?? conta.tipo,
  },
  {
    key: "instituicao",
    header: "Instituição",
    accessor: (conta) => conta.instituicao ?? "",
    sortable: true,
    hideOnMobile: true,
    render: (conta) => <InstitutionBadge nome={conta.instituicao} size="sm" showName />,
  },
  {
    key: "saldo_atual",
    header: "Saldo atual",
    accessor: (conta) => Number(conta.saldo_atual),
    sortable: true,
    align: "right",
    render: (conta) => <span className="tabular">{formatMoney(conta.saldo_atual)}</span>,
  },
  {
    key: "ativo",
    header: "Status",
    accessor: (conta) => (conta.ativo ? "Ativa" : "Inativa"),
    sortable: true,
    render: (conta) => (
      <AtivoBadge ativo={conta.ativo} labelAtivo="Ativa" labelInativo="Inativa" />
    ),
  },
];

/** Um filtro real hoje (`tipo`) + infraestrutura já pronta para crescer
 * (bastaria adicionar mais `FilterDef`s aqui) — "filtros futuros
 * preparados" pedido na Etapa F6, sem inventar filtro que não tem valor
 * ainda (ex. filtrar por instituição livre já é coberto pela busca). */
export const contaTableFilters: FilterDef<ContaRead>[] = [
  {
    key: "tipo",
    label: "Tipo",
    options: Object.entries(LABEL_TIPO_CONTA).map(([value, label]) => ({ value, label })),
    predicate: (conta, value) => conta.tipo === value,
  },
];
