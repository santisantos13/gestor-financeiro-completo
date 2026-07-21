import { Button, type ButtonProps } from "./Button";

export interface SubmitButtonProps extends Omit<ButtonProps, "type"> {}

/** `LoadingButton` de docs/design-system.md (seção 15) aplicado ao
 * contexto de formulário: `type="submit"`, spinner substitui o label
 * enquanto `loading` (tipicamente `formState.isSubmitting` do RHF ou
 * `mutation.isPending`), desabilitado no mesmo estado — nunca duplo
 * submit. */
export function SubmitButton({ variant = "primary", children = "Salvar", ...props }: SubmitButtonProps) {
  return (
    <Button type="submit" variant={variant} {...props}>
      {children}
    </Button>
  );
}
