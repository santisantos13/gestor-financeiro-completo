/**
 * Drawer de Alertas — aberto a partir do sino no `Header` (mesmo padrão de
 * `AtividadesRecentesDrawer`). Lista TODOS os alertas do usuário (ativos e
 * pausados - `apenas_ativos=false`, precisa dos pausados para oferecer
 * "Reativar"), com pausar/reativar/editar/excluir, e um botão "Novo
 * alerta" que abre `AlertaFormDialog` em modo criação.
 *
 * Um alerta disparado (`disparado=true`) mostra `mensagem` (já pronta,
 * calculada pelo backend a cada leitura - nunca um histórico); um alerta
 * não disparado ou pausado mostra a REGRA em si via
 * `descreverCondicaoAlerta` (`lib/alertaDescricao.ts`), já que não há
 * `mensagem` nesse caso. Ver docs/analise-arquitetural-alertas.md, seção 8.
 *
 * Nomes de entidade (Cartão/Conta/Meta/Conta Recorrente) vêm das mesmas
 * listagens usadas pelo picker de `AlertaFormDialog` - `AlertaRead` só traz
 * `entidade_id`, nunca o nome (nenhuma duplicação de dado entre backend e
 * frontend). `apenasAtivas=false` nos hooks de Cartão/Conta - um alerta
 * pode apontar para uma entidade já desativada, e o nome ainda deve
 * aparecer (mensagem "Cartão não encontrado" só ocorreria se a entidade
 * fosse EXCLUÍDA de verdade, caso defensivo já tratado pelo backend
 * retornando `disparado=false`).
 */
import { useMemo, useState } from "react";
import { Bell, BellOff, Pencil, Plus, Trash2 } from "lucide-react";
import { Drawer } from "../../ui/Drawer";
import { Button } from "../../ui/Button";
import { ConfirmAction } from "../../ui/ConfirmAction";
import { AlertaFormDialog } from "./AlertaFormDialog";
import { iconePorTipoAlerta, TIPO_ALERTA_LABEL, descreverCondicaoAlerta } from "../../../lib/alertaDescricao";
import { useAlertas, useAtualizarAlerta, useExcluirAlerta } from "../../../hooks/useAlertaQueries";
import { useCartoes } from "../../../hooks/useCartaoQueries";
import { useContas } from "../../../hooks/useContaQueries";
import { useMetas } from "../../../hooks/useMetaQueries";
import { useContasRecorrentes } from "../../../hooks/useContaRecorrenteQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage } from "../../../utils/errors";
import type { AlertaRead } from "../../../types/alerta";

export interface AlertasDrawerProps {
  open: boolean;
  onClose: () => void;
}

function useNomesDeEntidade() {
  const { data: cartoes } = useCartoes(false);
  const { data: contas } = useContas(false);
  const { data: metas } = useMetas(false);
  const { data: recorrentes } = useContasRecorrentes();

  return useMemo(() => {
    const nomesCartao = new Map((cartoes ?? []).map((c) => [c.id, c.nome]));
    const nomesConta = new Map((contas ?? []).map((c) => [c.id, c.nome]));
    const nomesMeta = new Map((metas ?? []).map((m) => [m.id, m.descricao]));
    const nomesRecorrente = new Map((recorrentes ?? []).map((r) => [r.id, r.descricao]));

    return function nomeDaEntidade(alerta: AlertaRead): string {
      if (alerta.entidade_id == null) return "";
      switch (alerta.tipo) {
        case "LIMITE_CARTAO":
        case "VENCIMENTO_FATURA":
          return nomesCartao.get(alerta.entidade_id) ?? `Cartão #${alerta.entidade_id}`;
        case "VENCIMENTO_CONTA_RECORRENTE":
          return nomesRecorrente.get(alerta.entidade_id) ?? `Conta recorrente #${alerta.entidade_id}`;
        case "META_ATINGIDA":
          return nomesMeta.get(alerta.entidade_id) ?? `Meta #${alerta.entidade_id}`;
        case "SALDO_BAIXO":
          return nomesConta.get(alerta.entidade_id) ?? `Conta #${alerta.entidade_id}`;
        default:
          return "";
      }
    };
  }, [cartoes, contas, metas, recorrentes]);
}

function ItemAlerta({ alerta, nomeDaEntidade }: { alerta: AlertaRead; nomeDaEntidade: (a: AlertaRead) => string }) {
  const toast = useToast();
  const atualizarAlerta = useAtualizarAlerta();
  const excluirAlerta = useExcluirAlerta();
  const [editando, setEditando] = useState(false);
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);

  const Icon = iconePorTipoAlerta(alerta.tipo);
  const nome = nomeDaEntidade(alerta);

  async function alternarAtivo() {
    try {
      await atualizarAlerta.mutateAsync({ id: alerta.id, dados: { ativo: !alerta.ativo } });
      toast.success(alerta.ativo ? "Alerta pausado." : "Alerta reativado.");
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function excluir() {
    try {
      await excluirAlerta.mutateAsync(alerta.id);
      toast.success("Alerta excluído.");
      setConfirmandoExclusao(false);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <li
      className={`rounded-md border p-3 ${
        alerta.disparado ? "border-warning-subtle bg-warning-subtle/40" : "border-border-subtle bg-surface-2"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 shrink-0 rounded-sm bg-surface-3 p-1.5 text-text-tertiary">
          <Icon size={14} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="font-medium text-text-primary">
              {TIPO_ALERTA_LABEL[alerta.tipo]}
              {nome && ` — ${nome}`}
            </p>
            {!alerta.ativo && (
              <span className="shrink-0 rounded-full bg-surface-3 px-1.5 py-0.5 text-micro text-text-tertiary">
                Pausado
              </span>
            )}
          </div>
          <p className={`mt-0.5 text-sm ${alerta.disparado ? "text-text-primary" : "text-text-tertiary"}`}>
            {alerta.disparado && alerta.mensagem ? alerta.mensagem : descreverCondicaoAlerta(alerta.tipo, alerta.condicao)}
          </p>

          <div className="mt-2 flex items-center gap-1">
            <button
              type="button"
              onClick={alternarAtivo}
              className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-3 hover:text-text-primary"
              aria-label={alerta.ativo ? "Pausar alerta" : "Reativar alerta"}
              title={alerta.ativo ? "Pausar" : "Reativar"}
            >
              {alerta.ativo ? <BellOff size={14} aria-hidden="true" /> : <Bell size={14} aria-hidden="true" />}
            </button>
            <button
              type="button"
              onClick={() => setEditando(true)}
              className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-3 hover:text-text-primary"
              aria-label="Editar alerta"
              title="Editar"
            >
              <Pencil size={14} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setConfirmandoExclusao(true)}
              className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-negative-subtle hover:text-negative"
              aria-label="Excluir alerta"
              title="Excluir"
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <AlertaFormDialog open={editando} alerta={alerta} onClose={() => setEditando(false)} />
      <ConfirmAction
        open={confirmandoExclusao}
        title="Excluir alerta?"
        description="Esta ação é definitiva - o alerta será removido para sempre."
        confirmLabel="Excluir"
        tone="danger"
        loading={excluirAlerta.isPending}
        onConfirm={excluir}
        onCancel={() => setConfirmandoExclusao(false)}
      />
    </li>
  );
}

export function AlertasDrawer({ open, onClose }: AlertasDrawerProps) {
  const { data, isLoading } = useAlertas(false);
  const nomeDaEntidade = useNomesDeEntidade();
  const [criando, setCriando] = useState(false);
  const alertas = data ?? [];

  return (
    <Drawer
      open={open}
      title="Alertas"
      description="Avisos configurados de limite de cartão, vencimento, meta e saldo baixo"
      onClose={onClose}
      footer={
        <Button variant="secondary" className="w-full" onClick={() => setCriando(true)}>
          <Plus size={16} aria-hidden="true" />
          Novo alerta
        </Button>
      }
    >
      {isLoading ? (
        <p className="text-sm text-text-tertiary">Carregando...</p>
      ) : alertas.length === 0 ? (
        <p className="text-sm text-text-tertiary">Nenhum alerta configurado ainda.</p>
      ) : (
        <ul className="space-y-3">
          {alertas.map((alerta) => (
            <ItemAlerta key={alerta.id} alerta={alerta} nomeDaEntidade={nomeDaEntidade} />
          ))}
        </ul>
      )}

      <AlertaFormDialog open={criando} onClose={() => setCriando(false)} />
    </Drawer>
  );
}
