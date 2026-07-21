import { useState } from "react";
import { Button } from "./Button";
import { ConfirmAction } from "./ConfirmAction";
import type { BulkAction } from "../../types/table";

export interface BulkActionsProps<T> {
  selectedCount: number;
  selectedRows: T[];
  actions: BulkAction<T>[];
  onClearSelection: () => void;
  className?: string;
}

/** Barra que aparece quando há seleção ativa — "N selecionado(s)" +
 * botões de ação. Infraestrutura pronta desde já (pedido explícito),
 * mesmo sem nenhuma entidade a usar ainda; ações com `tone: "danger"`
 * pedem confirmação via `ConfirmAction` por padrão. */
export function BulkActions<T>({
  selectedCount,
  selectedRows,
  actions,
  onClearSelection,
  className = "",
}: BulkActionsProps<T>) {
  const [pendingAction, setPendingAction] = useState<BulkAction<T> | null>(null);

  if (selectedCount === 0) return null;

  function executar(action: BulkAction<T>) {
    const precisaConfirmar = action.requireConfirmation ?? action.tone === "danger";
    if (precisaConfirmar) {
      setPendingAction(action);
    } else {
      action.onClick(selectedRows);
    }
  }

  return (
    <div className={`flex items-center gap-3 rounded-md border border-border bg-surface-3 px-3 py-2 ${className}`}>
      <span className="tabular text-sm text-text-secondary">{selectedCount} selecionado(s)</span>
      <div className="flex items-center gap-2">
        {actions.map((action) => (
          <Button
            key={action.label}
            variant={action.tone === "danger" ? "danger" : "secondary"}
            size="sm"
            onClick={() => executar(action)}
          >
            {action.icon && <action.icon size={14} aria-hidden="true" />}
            {action.label}
          </Button>
        ))}
        <Button variant="ghost" size="sm" onClick={onClearSelection}>
          Limpar seleção
        </Button>
      </div>

      <ConfirmAction
        open={pendingAction !== null}
        title={pendingAction?.confirmTitle ?? `${pendingAction?.label}?`}
        description={
          pendingAction?.confirmDescription ?? `Essa ação afeta ${selectedCount} item(ns) selecionado(s).`
        }
        tone={pendingAction?.tone === "danger" ? "danger" : "default"}
        onConfirm={() => {
          pendingAction?.onClick(selectedRows);
          setPendingAction(null);
        }}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  );
}
