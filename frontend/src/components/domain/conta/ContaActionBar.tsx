import type { MouseEvent } from "react";
import { Ban, Pencil, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "../../ui/Button";

export interface ContaActionBarProps {
  ativo: boolean;
  onEditar: () => void;
  onDesativar: () => void;
  onReativar: () => void;
  onExcluir: () => void;
  className?: string;
}

/**
 * Action Bar de Conta — mesmo molde de `MetaActionBar`/`CartaoActionBar`
 * (ícone + texto, nunca escondido atrás de um menu "..."). Vive dentro de
 * `ContaResumoCard`, um card inteiro clicável/expansível — todo `onClick`
 * chama `stopPropagation` para não expandir/recolher o card ao clicar numa
 * ação. Ver docs/analise-arquitetural-extrato-conta.md.
 */
export function ContaActionBar({
  ativo,
  onEditar,
  onDesativar,
  onReativar,
  onExcluir,
  className = "",
}: ContaActionBarProps) {
  function segurar(handler: () => void) {
    return (event: MouseEvent<HTMLButtonElement>) => {
      event.stopPropagation();
      handler();
    };
  }

  return (
    <div className={`flex items-center gap-2 overflow-x-auto ${className}`}>
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
