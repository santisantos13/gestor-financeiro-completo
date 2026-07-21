import { Button, type ButtonProps } from "./Button";

export interface CancelButtonProps extends Omit<ButtonProps, "type" | "variant"> {}

/** Botão secundário padrão de "Cancelar" — nunca a ação primária de um
 * formulário (design-system.md, seção 15: foco/destaque vai para o
 * submit, não para o cancelamento). `type="button"` explícito para nunca
 * disparar submit por engano dentro de um `<form>`. */
export function CancelButton({ children = "Cancelar", ...props }: CancelButtonProps) {
  return (
    <Button type="button" variant="secondary" {...props}>
      {children}
    </Button>
  );
}
