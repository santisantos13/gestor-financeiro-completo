import { ArrowRight } from "lucide-react";
import { AtivoBadge } from "../../ui/AtivoBadge";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { formatDate } from "../../../utils/date";
import { formatMoney } from "../../../utils/format";
import type { ColumnDef } from "../../../types/table";
import type { ContaRead } from "../../../types/conta";
import type { TransferenciaRead } from "../../../types/transferencia";

interface BuildColumnsOptions {
  contasPorId: Map<number, ContaRead>;
}

/**
 * Colunas do DataTable de `/transferencias` — mesmo princípio de
 * `transacaoTableColumns.tsx` (função, não constante, porque o nome/
 * instituição da conta vem de uma lista carregada à parte na própria
 * página). Ver docs/analise-arquitetural-transferencias-frontend.md,
 * seção 7.4.
 *
 * Diferente de Transação (colunas separadas "Origem"/coluna nenhuma de
 * destino), aqui existe UMA única coluna "Movimentação" com a mesma seta
 * (estática, sem animação — motion-principles.md: listas densas não
 * recebem efeito "hero" por linha) usada no formulário, para leitura
 * instantânea da direção do dinheiro.
 */
export function buildTransferenciaTableColumns({ contasPorId }: BuildColumnsOptions): ColumnDef<TransferenciaRead>[] {
  return [
    {
      key: "data",
      header: "Data",
      accessor: (transferencia) => transferencia.data,
      sortable: true,
      width: "w-28",
      render: (transferencia) => <span className="tabular">{formatDate(transferencia.data)}</span>,
    },
    {
      key: "movimentacao",
      header: "Movimentação",
      accessor: (transferencia) =>
        `${contasPorId.get(transferencia.conta_origem_id)?.nome ?? ""} ${contasPorId.get(transferencia.conta_destino_id)?.nome ?? ""}`,
      render: (transferencia) => {
        const origem = contasPorId.get(transferencia.conta_origem_id);
        const destino = contasPorId.get(transferencia.conta_destino_id);
        // Bug real corrigido (responsividade mobile, 2026-07-21): os dois
        // spans "origem"/"destino" tinham `truncate` no container flex
        // (não faz nada ali - `truncate` só afeta texto de verdade, e o
        // container só tem elementos filhos) e NENHUM `min-w-0` no span de
        // texto que de fato precisa truncar - sem isso, o item flex nunca
        // encolhe abaixo do próprio conteúdo (min-width:auto é o default
        // do navegador), e o nome era cortado sem reticências em vez de
        // truncar graciosamente. `flex-1` em cada lado faz origem/destino
        // dividirem o espaço disponível igualmente, em vez de um lado
        // "roubar" espaço do outro.
        return (
          <div className="flex min-w-0 items-center gap-1.5">
            <span className="flex min-w-0 flex-1 items-center gap-1.5">
              <InstitutionBadge nome={origem?.instituicao} size="sm" />
              <span className="min-w-0 truncate">{origem?.nome ?? "Conta"}</span>
            </span>
            <ArrowRight size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
            <span className="flex min-w-0 flex-1 items-center gap-1.5">
              <InstitutionBadge nome={destino?.instituicao} size="sm" />
              <span className="min-w-0 truncate">{destino?.nome ?? "Conta"}</span>
            </span>
          </div>
        );
      },
    },
    {
      key: "descricao",
      header: "Descrição",
      accessor: (transferencia) => transferencia.descricao ?? "",
      hideOnMobile: true,
      render: (transferencia) => (
        <span className={transferencia.descricao ? "" : "text-text-tertiary"}>
          {transferencia.descricao || "—"}
        </span>
      ),
    },
    {
      key: "valor",
      header: "Valor",
      accessor: (transferencia) => Number(transferencia.valor),
      sortable: true,
      align: "right",
      render: (transferencia) => (
        <span className="tabular font-medium text-text-primary">{formatMoney(transferencia.valor)}</span>
      ),
    },
    {
      key: "ativo",
      header: "Status",
      accessor: (transferencia) => (transferencia.ativo ? "Ativa" : "Cancelada"),
      sortable: true,
      width: "w-28",
      render: (transferencia) => (
        <AtivoBadge ativo={transferencia.ativo} labelAtivo="Ativa" labelInativo="Cancelada" />
      ),
    },
  ];
}
