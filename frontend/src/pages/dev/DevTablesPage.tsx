import { useMemo, useState } from "react";
import { Archive, ArchiveRestore, Eye, Inbox, Pencil, Trash2 } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { Badge, type BadgeTone } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Table } from "../../components/ui/Table";
import { TableBody } from "../../components/ui/TableBody";
import { TableSkeleton } from "../../components/ui/TableSkeleton";
import { DataTable } from "../../components/ui/DataTable";
import type { BulkAction, ColumnDef, FilterDef, RowAction } from "../../types/table";
import { formatMoney } from "../../utils/format";
import { formatDate } from "../../utils/date";
import { gerarRegistrosDemo, type RegistroDemo, type StatusDemo } from "./fixtures/tableFixtures";

const STATUS_TONE: Record<StatusDemo, BadgeTone> = {
  ativo: "positive",
  pendente: "warning",
  arquivado: "neutral",
};

const STATUS_LABEL: Record<StatusDemo, string> = {
  ativo: "Ativo",
  pendente: "Pendente",
  arquivado: "Arquivado",
};

const COLUNAS: ColumnDef<RegistroDemo>[] = [
  { key: "nome", header: "Nome", accessor: (r) => r.nome, sortable: true },
  { key: "categoria", header: "Categoria", accessor: (r) => r.categoria, sortable: true, hideOnMobile: true },
  {
    key: "status",
    header: "Status",
    accessor: (r) => r.status,
    sortable: true,
    render: (r) => <Badge tone={STATUS_TONE[r.status]}>{STATUS_LABEL[r.status]}</Badge>,
  },
  {
    key: "valor",
    header: "Valor",
    accessor: (r) => r.valor,
    sortable: true,
    align: "right",
    render: (r) => <span className="tabular">{formatMoney(r.valor)}</span>,
  },
  {
    key: "atualizadoEm",
    header: "Atualizado em",
    accessor: (r) => r.atualizadoEm,
    sortable: true,
    align: "right",
    hideOnMobile: true,
    render: (r) => <span className="tabular">{formatDate(r.atualizadoEm)}</span>,
  },
];

const FILTROS: FilterDef<RegistroDemo>[] = [
  {
    key: "status",
    label: "Status",
    options: [
      { value: "ativo", label: "Ativo" },
      { value: "pendente", label: "Pendente" },
      { value: "arquivado", label: "Arquivado" },
    ],
    predicate: (row, value) => row.status === value,
  },
  {
    key: "categoria",
    label: "Categoria",
    options: ["Alpha", "Beta", "Gama", "Delta", "Épsilon"].map((c) => ({ value: c, label: c })),
    predicate: (row, value) => row.categoria === value,
  },
];

/**
 * Laboratório visual permanente da infraestrutura de tabelas — rota
 * `/dev/tables` (Etapa F4), protegida mas fora do `Sidebar`, mesmo espírito
 * de `/dev` (Etapa F3). Dado 100% sintético (`fixtures/tableFixtures.ts`) —
 * nenhuma chamada à API, nenhuma entidade real, conforme exigido. Cobre
 * vazio/carregando/milhares-de-linhas/filtros/ordenação/paginação/seleção/
 * ações-por-linha/ações-em-lote/skeletons num único lugar.
 */
export function DevTablesPage() {
  const registros = useMemo(() => gerarRegistrosDemo(4000), []);
  const [arquivados, setArquivados] = useState<Set<number>>(new Set());
  const [simularErro, setSimularErro] = useState(false);

  const dadosComEstado = useMemo(
    () =>
      registros.map((r): RegistroDemo =>
        arquivados.has(r.id) ? { ...r, status: "arquivado" } : r,
      ),
    [registros, arquivados],
  );

  const acoesPorLinha: RowAction<RegistroDemo>[] = [
    { label: "Ver", icon: Eye, onClick: () => {} },
    { label: "Editar", icon: Pencil, onClick: () => {} },
    {
      label: "Arquivar",
      icon: Archive,
      onClick: (row) => setArquivados((atual) => new Set(atual).add(row.id)),
      hidden: (row) => row.status === "arquivado",
    },
    {
      label: "Restaurar",
      icon: ArchiveRestore,
      onClick: (row) =>
        setArquivados((atual) => {
          const proximo = new Set(atual);
          proximo.delete(row.id);
          return proximo;
        }),
      hidden: (row) => row.status !== "arquivado",
    },
    { label: "Remover", icon: Trash2, tone: "danger", onClick: () => {} },
  ];

  const acoesEmLote: BulkAction<RegistroDemo>[] = [
    {
      label: "Arquivar selecionados",
      icon: Archive,
      onClick: (linhas) =>
        setArquivados((atual) => {
          const proximo = new Set(atual);
          linhas.forEach((r) => proximo.add(r.id));
          return proximo;
        }),
    },
    {
      label: "Remover selecionados",
      icon: Trash2,
      tone: "danger",
      confirmTitle: "Remover registros selecionados?",
      confirmDescription: "Ação apenas demonstrativa — nada é removido de verdade nesta página.",
      onClick: () => {},
    },
  ];

  return (
    <div className="space-y-10 pb-16">
      <div>
        <h1 className="text-h1 font-semibold text-text-primary">/dev/tables — laboratório de tabelas</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Infraestrutura genérica de <code className="font-mono text-text-tertiary">components/ui/</code>{" "}
          criada na Etapa F4 (<code className="font-mono text-text-tertiary">DataTable</code> e as 18 peças
          que a compõem), exercitada aqui com dado 100% sintético — sem chamada à API, sem entidade real. Ver
          docs/analise-arquitetural-frontend.md, seção 13.
        </p>
      </div>

      <section>
        <SectionTitle>Tabela vazia</SectionTitle>
        <DataTable
          data={[]}
          columns={COLUNAS}
          getRowId={(r) => r.id}
          searchable
          emptyTitle="Nenhum registro ainda"
          emptyDescription="Estado vazio genuíno — array de dado vazio, sem busca nem filtro ativo."
        />
      </section>

      <section>
        <SectionTitle>Tabela carregando</SectionTitle>
        <DataTable data={[]} columns={COLUNAS} getRowId={(r) => r.id} isLoading />
      </section>

      <section>
        <SectionTitle>Erro + retry</SectionTitle>
        <div className="mb-3">
          <Button size="sm" variant="secondary" onClick={() => setSimularErro((v) => !v)}>
            {simularErro ? "Desligar erro simulado" : "Simular erro"}
          </Button>
        </div>
        <DataTable
          data={simularErro ? [] : dadosComEstado.slice(0, 5)}
          columns={COLUNAS}
          getRowId={(r) => r.id}
          error={simularErro ? { status: 500, detail: "Falha simulada só para esta página." } : undefined}
          onRetry={() => setSimularErro(false)}
        />
      </section>

      <section>
        <SectionTitle action={<Badge tone="accent">{registros.length} registros</Badge>}>
          Tabela completa — busca, filtro, ordenação, paginação, seleção, ações
        </SectionTitle>
        <DataTable
          data={dadosComEstado}
          columns={COLUNAS}
          getRowId={(r) => r.id}
          searchable
          searchPlaceholder="Buscar por nome, categoria, status..."
          filters={FILTROS}
          selectable
          columnVisibility
          rowActions={acoesPorLinha}
          bulkActions={acoesEmLote}
          pageSize={20}
          pageSizeOptions={[10, 20, 50, 100]}
          emptyIcon={Inbox}
          aria-label="Registros de demonstração"
        />
      </section>

      <section>
        <SectionTitle>TableSkeleton (isolado)</SectionTitle>
        <Card>
          <Table>
            <TableBody>
              <TableSkeleton rows={5} columns={5} withSelection />
            </TableBody>
          </Table>
        </Card>
      </section>
    </div>
  );
}
