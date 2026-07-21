import { useMemo } from "react";
import { SearchSelect } from "../../ui/SearchSelect";
import { useContas } from "../../../hooks/useContaQueries";

export interface AccountSelectProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  apenasAtivas?: boolean;
  /** Etapa de Transferências: `TransferenciaFormDialog` usa DOIS
   * `AccountSelect` no mesmo formulário (origem/destino) — `excluirId`
   * remove uma conta específica das opções, evitando que o usuário
   * selecione a mesma conta nos dois campos pela própria UI (a validação
   * real e definitiva continua sendo o `.refine` do schema + o backend). */
  excluirId?: number | null;
}

/**
 * Segundo select "inteligente" de domínio do projeto — infraestrutura já
 * prevista desde a Etapa F1 (`docs/analise-arquitetural-frontend.md`, seção
 * 12), só nascendo agora que Cartão (`conta_pagamento_id`) é a primeira
 * entidade a de fato precisar dela (ver
 * `docs/analise-arquitetural-cartao-frontend.md`, seções 0 e 7). Mesmo
 * molde de `CategorySelect.tsx`, mais simples: sem hierarquia, sem cadeia
 * de ancestrais, sem exclusão de descendentes — só o nome da conta como
 * label. `AccountSelect` só lista contas do próprio usuário (`useContas` já
 * é escopado por `usuario_atual`), reduzindo a chance de a UI oferecer um
 * `conta_pagamento_id` inválido — a validação de posse de verdade continua
 * 100% no backend (`_validar_conta_do_usuario`, 404 anti-enumeração).
 */
export function AccountSelect({
  name,
  label,
  optional,
  description,
  placeholder = "Selecione a conta",
  disabled,
  apenasAtivas = true,
  excluirId,
}: AccountSelectProps) {
  const { data: contas, isLoading } = useContas(apenasAtivas);

  const options = useMemo(
    () => (contas ?? []).filter((c) => c.id !== excluirId).map((c) => ({ value: String(c.id), label: c.nome })),
    [contas, excluirId],
  );

  return (
    <SearchSelect
      name={name}
      label={label}
      options={options}
      optional={optional}
      description={description}
      placeholder={placeholder}
      searchPlaceholder="Buscar conta..."
      disabled={disabled}
      loading={isLoading}
    />
  );
}
