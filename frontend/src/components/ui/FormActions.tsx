import type { ReactNode } from "react";

export interface FormActionsProps {
  children: ReactNode;
  className?: string;
}

/** Rodapé de ações do formulário — design-system.md, seção 17: "botão de
 * submit fica fixo no rodapé do `FormDialog`, não rola junto com o
 * conteúdo". Este componente só cuida do layout (alinhado à direita,
 * espaçado); `FormDialog` é quem fixa a posição visualmente. Fora de um
 * `FormDialog` (ex. formulário de página cheia), funciona como um rodapé
 * comum. */
export function FormActions({ children, className = "" }: FormActionsProps) {
  return <div className={`flex items-center justify-end gap-2 ${className}`}>{children}</div>;
}
