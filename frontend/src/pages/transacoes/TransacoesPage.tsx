import { useMemo, useState } from "react";
import { Pencil, Plus, Receipt, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { DataTable } from "../../components/ui/DataTable";
import { Select } from "../../components/ui/Select";
import { PeriodoSeletor } from "../../components/domain/dashboard/PeriodoSeletor";
import { TransacaoResumoPeriodo } from "../../components/domain/transacao/TransacaoResumoPeriodo";
import { TransacaoFormDialog } from "../../components/domain/transacao/TransacaoFormDialog";
import {
  buildTransacaoTableColumns,
  FILTROS_STATUS_TRANSACAO,
  FILTROS_TIPO_TRANSACAO,
} from "../../components/domain/transacao/transacaoTableColumns";
import { useTransacoes, useExcluirTransacao } from "../../hooks/useTransacaoQueries";
import { useParcelamento } from "../../hooks/useParcelamentoQueries";
import { useContas } from "../../hooks/useContaQueries";
import { useCartoes } from "../../hooks/useCartaoQueries";
import { useCategorias } from "../../hooks/useCategoriaQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import { intervaloDoMes } from "../../utils/date";
import { formatMoney } from "../../utils/format";
import type { TransacaoRead, TransacaoFiltros } from "../../types/transacao";
import type { RowAction } from "../../types/table";

interface EstadoDialogoTransacao {
  aberto: boolean;
  transacao: TransacaoRead | null;
}

const DIALOGO_FECHADO: EstadoDialogoTransacao = { aberto: false, transacao: null };

/**
 * Página `/transacoes` — a tela mais usada do aplicativo
 * (docs/analise-arquitetural-transacao-frontend.md, seção 0). Diferente de
 * `/cartoes` (grid de mini-dashboards), usa `DataTable`: volume alto,
 * lançamento por lançamento é o modelo mental correto de um livro-razão.
 *
 * Filtragem híbrida (seção 2): `PeriodoSeletor` + os três `Select`s abaixo
 * dele viram parâmetros REAIS de `GET /transacoes` (o backend filtra de
 * verdade) — diferente de `FilterBar`/`contaTableFilters`, que filtram só
 * client-side sobre uma lista já carregada por inteiro. O `DataTable`
 * continua fazendo busca textual adicional, ordenação de coluna e
 * paginação de exibição sobre o resultado já filtrado pelo servidor.
 *
 * Pedido explícito do usuário (2026-07-20): esta lista NUNCA mostra compras
 * de cartão de crédito - só lançamentos de Conta (diretos ou pagamento de
 * fatura). `filtros.apenas_conta: true` (sempre, não é um toggle) faz o
 * backend filtrar `cartao_id IS NULL` de verdade (`TransacaoRepository.
 * listar_do_cartao`). Regra é só de EXIBIÇÃO nesta tela: compras de cartão
 * continuam existindo normalmente e entrando em todo cálculo (limite do
 * cartão, faturas, Central Financeira/Dashboard) - só não aparecem aqui.
 * Para ver/registrar compras de um cartão específico, a tela é
 * `/cartoes/:id` (ação "Nova compra").
 */
export function TransacoesPage() {
  const toast = useToast();
  const hoje = new Date();
  const [periodo, setPeriodo] = useState({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });
  const [tipoFiltro, setTipoFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState("");
  const [categoriaFiltro, setCategoriaFiltro] = useState("");

  const { data: categorias } = useCategorias(false);
  const { data: contas } = useContas(false);
  const { data: cartoes } = useCartoes(false);

  const filtros: TransacaoFiltros = useMemo(() => {
    const { inicio, fim } = intervaloDoMes(periodo.ano, periodo.mes);
    return {
      data_inicio: inicio,
      data_fim: fim,
      tipo: tipoFiltro ? (tipoFiltro as TransacaoFiltros["tipo"]) : undefined,
      status: statusFiltro ? (statusFiltro as TransacaoFiltros["status"]) : undefined,
      categoria_id: categoriaFiltro ? Number(categoriaFiltro) : undefined,
      // Compras de cartão não aparecem aqui - pedido explícito do usuário
      // (2026-07-20). Só compras/lançamentos de Conta e pagamentos de
      // fatura (que também são Transacao com conta_id, nunca cartao_id).
      apenas_conta: true,
      limit: 200,
    };
  }, [periodo, tipoFiltro, statusFiltro, categoriaFiltro]);

  const { data: transacoes, isLoading, error, refetch } = useTransacoes(filtros);

  const [dialogo, setDialogo] = useState<EstadoDialogoTransacao>(DIALOGO_FECHADO);
  const [transacaoParaExcluir, setTransacaoParaExcluir] = useState<TransacaoRead | null>(null);
  const excluirTransacao = useExcluirTransacao(transacaoParaExcluir?.conta_id, transacaoParaExcluir?.cartao_id);
  // Diálogo de confirmação (seção 3, docs/analise-arquitetural-escopo-parcelamento.md):
  // busca o Parcelamento só para saber `num_parcelas` de verdade (em vez de
  // uma mensagem genérica "algumas parcelas") - `enabled` evita a
  // requisição em toda exclusão, só dispara quando a transação selecionada
  // pertence a um parcelamento.
  const { data: parcelamentoParaExcluir } = useParcelamento(transacaoParaExcluir?.parcelamento_id ?? null);

  const categoriasPorId = useMemo(() => new Map((categorias ?? []).map((c) => [c.id, c])), [categorias]);
  const contasPorId = useMemo(() => new Map((contas ?? []).map((c) => [c.id, c])), [contas]);
  const cartoesPorId = useMemo(() => new Map((cartoes ?? []).map((c) => [c.id, c])), [cartoes]);

  const columns = useMemo(
    () => buildTransacaoTableColumns({ categoriasPorId, contasPorId, cartoesPorId }),
    [categoriasPorId, contasPorId, cartoesPorId],
  );

  const categoriaOptions = useMemo(
    () => (categorias ?? []).map((c) => ({ value: String(c.id), label: c.nome })),
    [categorias],
  );

  function abrirCriacao() {
    setDialogo({ aberto: true, transacao: null });
  }

  function abrirEdicao(transacao: TransacaoRead) {
    setDialogo({ aberto: true, transacao });
  }

  function fecharDialogo() {
    setDialogo((atual) => ({ ...atual, aberto: false }));
  }

  async function confirmarExclusao() {
    if (!transacaoParaExcluir) return;
    try {
      await excluirTransacao.mutateAsync(transacaoParaExcluir.id);
      toast.success(`Transação "${transacaoParaExcluir.descricao}" excluída.`);
      setTransacaoParaExcluir(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  const rowActions: RowAction<TransacaoRead>[] = [
    { label: "Editar", icon: Pencil, onClick: abrirEdicao },
    { label: "Excluir", icon: Trash2, tone: "danger", onClick: (transacao) => setTransacaoParaExcluir(transacao) },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Transações</h1>
          <p className="mt-1 text-sm text-text-secondary">Receitas, despesas e movimentações do período.</p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodoSeletor ano={periodo.ano} mes={periodo.mes} onChange={(ano, mes) => setPeriodo({ ano, mes })} />
          <Button onClick={abrirCriacao}>
            <Plus size={16} aria-hidden="true" />
            Nova transação
          </Button>
        </div>
      </div>

      <TransacaoResumoPeriodo ano={periodo.ano} mes={periodo.mes} />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          className="w-40"
          value={tipoFiltro}
          onChange={setTipoFiltro}
          options={[{ value: "", label: "Tipo: todos" }, ...FILTROS_TIPO_TRANSACAO]}
          aria-label="Filtrar por tipo"
        />
        <Select
          className="w-40"
          value={statusFiltro}
          onChange={setStatusFiltro}
          options={[{ value: "", label: "Status: todos" }, ...FILTROS_STATUS_TRANSACAO]}
          aria-label="Filtrar por status"
        />
        <Select
          className="w-52"
          value={categoriaFiltro}
          onChange={setCategoriaFiltro}
          options={[{ value: "", label: "Categoria: todas" }, ...categoriaOptions]}
          aria-label="Filtrar por categoria"
        />
      </div>

      <DataTable
        data={transacoes ?? []}
        columns={columns}
        getRowId={(transacao) => transacao.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        searchable
        searchPlaceholder="Buscar por descrição..."
        rowActions={rowActions}
        emptyIcon={Receipt}
        emptyTitle="Nenhuma transação neste período"
        emptyAction={
          <Button size="sm" onClick={abrirCriacao}>
            <Plus size={14} aria-hidden="true" />
            Nova transação
          </Button>
        }
        emptyDescription="Registre sua primeira receita ou despesa do mês."
        aria-label="Transações"
      />

      <TransacaoFormDialog open={dialogo.aberto} transacao={dialogo.transacao} onClose={fecharDialogo} />

      <ConfirmAction
        open={transacaoParaExcluir != null}
        title={transacaoParaExcluir ? `Excluir "${transacaoParaExcluir.descricao}"?` : ""}
        description={
          transacaoParaExcluir
            ? transacaoParaExcluir.parcelamento_id != null
              ? `Esta compra possui ${parcelamentoParaExcluir?.num_parcelas ?? "várias"} parcelas. Ao excluí-la, todas as parcelas serão removidas permanentemente (as que já estiverem em faturas fechadas são preservadas como histórico). Esta ação não pode ser desfeita.`
              : `Esta ação é permanente e não pode ser desfeita. O valor de ${formatMoney(transacaoParaExcluir.valor)} deixa de contar no saldo/limite da origem.`
            : ""
        }
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirTransacao.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setTransacaoParaExcluir(null)}
      />
    </div>
  );
}
