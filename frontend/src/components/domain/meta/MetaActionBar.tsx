import type { MouseEvent } from "react";
import { ArrowDownCircle, ArrowUpCircle, Ban, Pencil, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "../../ui/Button";

export interface MetaActionBarProps {
  ativo: boolean;
  onEditar: () => void;
  onAportar: () => void;
  onResgatar: () => void;
  onDesativar: () => void;
  onReativar: () => void;
  onExcluir: () => void;
  className?: string;
}

/**
 * Action Bar de Meta — mesmo molde de `CartaoActionBar` (ícone + texto,
 * nunca escondido atrás de um menu "..."). "Excluir" (hard delete, pedido
 * explícito do usuário) além de "Desativar"/"Reativar" (soft delete) —
 * mesma dupla de ações de Cartão: `desativar()` continua sendo o caminho
 * reversível padrão, `excluir()` é uma ação nova e separada, nunca
 * bloqueada por aportes vinculados (a transação legada em si nunca é
 * apagada, só perde o vínculo com a meta — ver `MetaService.excluir` no
 * backend). Todo `onClick` chama `stopPropagation` — a barra vive dentro
 * de um card inteiro clicável/expansível (`MetaResumoCard`).
 *
 * "Aportar"/"Resgatar" (Refatoramento de Metas/Transferências, ver
 * docs/analise-arquitetural-metas-transferencias.md, seção 7) só aparecem
 * em metas ATIVAS — só fazem sentido enquanto a meta aceita movimentação.
 * Abrem `MetaAporteDialog` com `direcao` fixa, cada um criando uma
 * Transferência real para/do cofrinho da meta.
 */
export function MetaActionBar({
  ativo,
  onEditar,
  onAportar,
  onResgatar,
  onDesativar,
  onReativar,
  onExcluir,
  className = "",
}: MetaActionBarProps) {
  function segurar(handler: () => void) {
    return (event: MouseEvent<HTMLButtonElement>) => {
      event.stopPropagation();
      handler();
    };
  }

  return (
    <div className={`flex items-center gap-2 overflow-x-auto ${className}`}>
      {ativo && (
        <>
          <Button variant="primary" size="sm" className="shrink-0" onClick={segurar(onAportar)}>
            <ArrowDownCircle size={14} aria-hidden="true" />
            Aportar
          </Button>
          <Button variant="secondary" size="sm" className="shrink-0" onClick={segurar(onResgatar)}>
            <ArrowUpCircle size={14} aria-hidden="true" />
            Resgatar
          </Button>
        </>
      )}
      <Button variant="secondary" size="sm" className="shrink-0" onClick={segurar(onEditar)}>
        <Pencil size={14} aria-hidden="true" />
        Editar
      </Button>
      {ativo ? (
        <Button variant="secondary" size="sm" className="shrink-0" onClick={segurar(onDesativar)}>
          <Ban size={14} aria-hidden="true" />
          Desativar
        </Button>
      ) : (
        <Button variant="secondary" size="sm" className="shrink-0" onClick={segurar(onReativar)}>
          <RotateCcw size={14} aria-hidden="true" />
          Reativar
        </Button>
      )}
      <Button variant="ghost" size="sm" className="shrink-0 hover:text-negative" onClick={segurar(onExcluir)}>
        <Trash2 size={14} aria-hidden="true" />
        Excluir
      </Button>
    </div>
  );
}
