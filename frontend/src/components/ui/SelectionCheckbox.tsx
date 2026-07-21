import { Checkbox, type CheckboxProps } from "./Checkbox";

export interface SelectionCheckboxProps extends CheckboxProps {
  label: string;
}

/** `Checkbox` (Etapa F2) com `stopPropagation` no clique — evita que
 * marcar a linha também dispare uma futura ação de clique na linha (ex.
 * abrir detalhe). Usado tanto na célula de seleção de cada `TableRow`
 * quanto no cabeçalho ("selecionar todos desta página"). */
export function SelectionCheckbox({ label, onClick, ...props }: SelectionCheckboxProps) {
  return (
    <Checkbox
      aria-label={label}
      onClick={(event) => {
        event.stopPropagation();
        onClick?.(event);
      }}
      {...props}
    />
  );
}
