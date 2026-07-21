import { useMemo, useState } from "react";
import { CircleStop, Pause, Pencil, Play, Plus, Repeat } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { DataTable } from "../../components/ui/DataTable";
import { Switch } from "../../components/ui/Switch";
import { RecorrenteFormDialog } from "../../components/domain/contaRecorrente/RecorrenteFormDialog";
import {
  useContasRecorrentes,
  usePausarContaRecorrente,
  useReativarContaRecorrente,
  useEncerrarContaRecorrente,
} from "../../hooks/useContaRecorrenteQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import { formatDate } from "../../utils/date";
import { formatMoney } from "../../utils/format";
import { LABEL_FREQUENCIA } from "../../schemas/contaRecorrente";
import type { ContaRecorrenteRead, FrequenciaRecorrencia } from "../../types/contaRecorrente";
import type { ColumnDef, RowAction } from "../../types/table";

interface EstadoDialogoRecorrente {
  aberto: boolean;
  recorrente: ContaRecorrenteRead | null;
}

const DIALOGO_FECHADO: EstadoDialogoRecorrente = { aberto: false, recorrente: null };

type AcaoCicloDeVida = "pausar" | "reativar" | "encerrar";

/** Ocorrências por mês (aproximado) — só para o resumo do topo, nunca
 * para cálculo financeiro real (que é sempre do backend). */
const OCORRENCIAS_POR_MES: Record<FrequenciaRecorrencia, number> = {
  DIARIA: 30,
  SEMANAL: 52 / 12,
  QUINZENAL: 26 / 12,
  MENSAL: 1,
  BIMESTRAL: 1 / 2,
  TRIMESTRAL: 1 / 3,
  SEMESTRAL: 1 / 6,
  ANUAL: 1 / 12,
};

const COLUNAS: ColumnDef<ContaRecorrenteRead>[] = [
  {
    key: "descricao",
    header: "Descrição",
    accessor: (r) => r.descricao,
    sortable: true,
    render: (r) => (
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate font-medium text-text-primary">{r.descricao}</span>
        {r.tipo === "RECEITA" ? (
          <Badge tone="positive">Receita</Badge>
        ) : (
          <Badge tone="negative">Despesa</Badge>
        )}
      </div>
    ),
  },
  {
    key: "valor",
    header: "Valor",
    accessor: (r) => Number(r.valor),
    sortable: true,
    align: "right",
    width: "w-32",
    render: (r) => (
      <span className={`font-mono tabular ${r.tipo === "RECEITA" ? "text-positive" : "text-text-primary"}`}>
        {formatMoney(r.valor)}
      </span>
    ),
  },
  {
    key: "frequencia",
    header: "Frequência",
    accessor: (r) => r.frequencia,
    sortable: true,
    width: "w-32",
    hideOnMobile: true,
    render: (r) => <span className="text-text-secondary">{LABEL_FREQUENCIA[r.frequencia]}</span>,
  },
  {
    key: "proxima",
    header: "Próxima ocorrência",
    accessor: (r) => r.proxima_execucao,
    sortable: true,
    width: "w-40",
    render: (r) =>
      r.status === "ATIVA" ? (
        <span className="tabular">{formatDate(r.proxima_execucao)}</span>
      ) : (
        <span className="text-text-tertiary">—</span>
      ),
  },
  {
    key: "status",
    header: "Status",
    accessor: (r) => r.status,
    sortable: true,
    width: "w-28",
    render: (r) =>
      r.status === "ATIVA" ? (
        <Badge tone="positive">Ativa</Badge>
      ) : r.status === "PAUSADA" ? (
        <Badge tone="warning">Pausada</Badge>
      ) : (
        <Badge tone="neutral">Encerrada</Badge>
      ),
  },
];

/**
 * Página `/recorrentes` — módulo de Contas Recorrentes (expansão
 * 2026-07-20, docs/analise-arquitetural-conta-recorrente-expansao.md,
 * seção 8). Lista com `DataTable` (mesma infraestrutura de
 * `/transferencias`), resumo mensal estimado no topo (só apresentação —
 * normaliza cada frequência para o mês, nunca um cálculo do backend), e
 * ciclo de vida com vocabulário explícito: Pausar / Reativar / Encerrar
 * (nunca "Excluir" — o backend preserva histórico sempre, DELETE também
 * encerra).
 *
 * "Mostrar encerradas" espelha o "Mostrar canceladas" de Transferências —
 * encerradas são histórico, escondidas por padrão, nunca apagadas.
 */
export function RecorrentesPage() {
  const toast = useToast();
  const { data: recorrentes, isLoading, error, refetch } = useContasRecorrentes();
  const [mostrarEncerradas, setMostrarEncerradas] = useState(false);
  const [dialogo, setDialogo] = useState<EstadoDialogoRecorrente>(DIALOGO_FECHADO);
  const [acaoPendente, setAcaoPendente] = useState<{
    acao: AcaoCicloDeVida;
    recorrente: ContaRecorrenteRead;
  } | null>(null);

  const pausar = usePausarContaRecorrente();
  const reativar = useReativarContaRecorrente();
  const encerrar = useEncerrarContaRecorrente();

  const visiveis = useMemo(
    () => (recorrentes ?? []).filter((r) => mostrarEncerradas || r.status !== "ENCERRADA"),
    [recorrentes, mostrarEncerradas],
  );

  const resumoMensal = useMemo(() => {
    let receitas = 0;
    let despesas = 0;
    for (const r of recorrentes ?? []) {
      if (r.status !== "ATIVA") continue;
      const mensal = Number(r.valor) * OCORRENCIAS_POR_MES[r.frequencia];
      if (r.tipo === "RECEITA") receitas += mensal;
      else despesas += mensal;
    }
    return { receitas, despesas };
  }, [recorrentes]);

  async function confirmarAcao() {
    if (!acaoPendente) return;
    const { acao, recorrente } = acaoPendente;
    try {
      if (acao === "pausar") {
        await pausar.mutateAsync(recorrente.id);
        toast.success(`"${recorrente.descricao}" pausada — nenhuma ocorrência nova até reativar.`);
      } else if (acao === "reativar") {
        const reativada = await reativar.mutateAsync(recorrente.id);
        toast.success(
          reativada.status === "ENCERRADA"
            ? `"${recorrente.descricao}" chegou ao fim do período — foi encerrada.`
            : `"${recorrente.descricao}" reativada — próxima ocorrência em ${formatDate(reativada.proxima_execucao)}.`,
        );
      } else {
        await encerrar.mutateAsync(recorrente.id);
        toast.success(`"${recorrente.descricao}" encerrada — o histórico foi preservado.`);
      }
      setAcaoPendente(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  const rowActions: RowAction<ContaRecorrenteRead>[] = [
    {
      label: "Editar",
      icon: Pencil,
      onClick: (r) => setDialogo({ aberto: true, recorrente: r }),
      hidden: (r) => r.status === "ENCERRADA",
    },
    {
      label: "Pausar",
      icon: Pause,
      onClick: (r) => setAcaoPendente({ acao: "pausar", recorrente: r }),
      hidden: (r) => r.status !== "ATIVA",
    },
    {
      label: "Reativar",
      icon: Play,
      onClick: (r) => setAcaoPendente({ acao: "reativar", recorrente: r }),
      hidden: (r) => r.status !== "PAUSADA",
    },
    {
      label: "Encerrar",
      icon: CircleStop,
      tone: "danger",
      onClick: (r) => setAcaoPendente({ acao: "encerrar", recorrente: r }),
      hidden: (r) => r.status === "ENCERRADA",
    },
  ];

  const descricaoConfirmacao =
    acaoPendente?.acao === "pausar"
      ? "Nenhuma ocorrência nova será gerada enquanto estiver pausada. Você pode reativar quando quiser — o período pausado não gera lançamentos retroativos."
      : acaoPendente?.acao === "reativar"
        ? "A recorrência volta a gerar ocorrências a partir da próxima data válida. O período em que ficou pausada NÃO é lançado retroativamente."
        : "Encerrar é definitivo: a recorrência para de gerar ocorrências para sempre, mas o registro e todas as transações já geradas são preservados como histórico.";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Recorrentes</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Receitas e despesas que se repetem sozinhas — salário, aluguel, assinaturas.
          </p>
        </div>
        <Button onClick={() => setDialogo({ aberto: true, recorrente: null })}>
          <Plus size={16} aria-hidden="true" />
          Nova recorrência
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:max-w-md">
        <Card className="p-4">
          <p className="text-caption text-text-tertiary">Receitas recorrentes / mês</p>
          <p className="mt-1 font-mono tabular text-h3 font-semibold text-positive">
            {formatMoney(resumoMensal.receitas)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-caption text-text-tertiary">Despesas recorrentes / mês</p>
          <p className="mt-1 font-mono tabular text-h3 font-semibold text-negative">
            {formatMoney(resumoMensal.despesas)}
          </p>
        </Card>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="mostrar-encerradas"
          checked={mostrarEncerradas}
          onCheckedChange={setMostrarEncerradas}
          aria-label="Mostrar recorrências encerradas"
        />
        <label htmlFor="mostrar-encerradas" className="cursor-pointer text-sm text-text-secondary">
          Mostrar encerradas
        </label>
      </div>

      <DataTable
        data={visiveis}
        columns={COLUNAS}
        getRowId={(r) => r.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        searchable
        searchPlaceholder="Buscar por descrição..."
        rowActions={rowActions}
        emptyIcon={Repeat}
        emptyTitle="Nenhuma recorrência ainda"
        emptyAction={
          <Button size="sm" onClick={() => setDialogo({ aberto: true, recorrente: null })}>
            <Plus size={14} aria-hidden="true" />
            Nova recorrência
          </Button>
        }
        emptyDescription="Cadastre seu salário, aluguel ou assinaturas e deixe os lançamentos acontecerem sozinhos."
        aria-label="Contas recorrentes"
      />

      <RecorrenteFormDialog
        open={dialogo.aberto}
        recorrente={dialogo.recorrente}
        onClose={() => setDialogo((atual) => ({ ...atual, aberto: false }))}
      />

      <ConfirmAction
        open={acaoPendente != null}
        title={
          acaoPendente
            ? acaoPendente.acao === "pausar"
              ? `Pausar "${acaoPendente.recorrente.descricao}"?`
              : acaoPendente.acao === "reativar"
                ? `Reativar "${acaoPendente.recorrente.descricao}"?`
                : `Encerrar "${acaoPendente.recorrente.descricao}"?`
            : ""
        }
        description={descricaoConfirmacao}
        confirmLabel={
          acaoPendente?.acao === "pausar"
            ? "Pausar"
            : acaoPendente?.acao === "reativar"
              ? "Reativar"
              : "Encerrar"
        }
        tone={acaoPendente?.acao === "encerrar" ? "danger" : "default"}
        loading={pausar.isPending || reativar.isPending || encerrar.isPending}
        onConfirm={confirmarAcao}
        onCancel={() => setAcaoPendente(null)}
      />
    </div>
  );
}
