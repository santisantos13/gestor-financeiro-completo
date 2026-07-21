import type { MouseEvent } from "react";
import { Ban, Pencil, Receipt, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "../../ui/Button";

export interface CartaoActionBarProps {
  ativo: boolean;
  onEditar: () => void;
  /** Só aparece quando informado — atalho "Faturas" pedido na revisão de
   * UX (`docs/analise-arquitetural-revisao-ux-cartoes.md`, seção 5), usado
   * só no card do grid de `/cartoes` (navega para
   * `/cartoes/:id#faturas`). A página de detalhes já mostra as faturas
   * inline, então não repete essa ação. */
  onFaturas?: () => void;
  onDesativar: () => void;
  onReativar: () => void;
  onExcluir: () => void;
  className?: string;
}

/**
 * Action Bar compartilhada de Cartão — revisão de UX (seção 5 da análise):
 * substitui os botões pequenos de antes por ações maiores, sempre com
 * ícone + texto (nunca escondidas atrás de um menu "..."), reaproveitada
 * tanto no `CartaoResumoCard` (grid de `/cartoes`) quanto na página de
 * detalhes. Todo `onClick` chama `event.stopPropagation()` antes de
 * delegar — necessário quando a barra vive dentro de um card inteiro
 * clicável (seção 4), inofensivo quando não vive (não há nada para a
 * propagação afetar). Overflow horizontal em vez de cortar texto em telas
 * estreitas (seção 11 — mobile nunca esconde texto de uma ação frequente).
 */
export function CartaoActionBar({
  ativo,
  onEditar,
  onFaturas,
  onDesativar,
  onReativar,
  onExcluir,
  className = "",
}: CartaoActionBarProps) {
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
      {onFaturas && (
        <Button variant="secondary" size="sm" className="shrink-0" onClick={segurar(onFaturas)}>
          <Receipt size={14} aria-hidden="true" />
          Faturas
        </Button>
      )}
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
      <Button
        variant="ghost"
        size="sm"
        className="shrink-0 hover:text-negative"
        onClick={segurar(onExcluir)}
      >
        <Trash2 size={14} aria-hidden="true" />
        Excluir
      </Button>
    </div>
  );
}
