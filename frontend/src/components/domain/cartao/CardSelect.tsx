import { useMemo } from "react";
import { SearchSelect } from "../../ui/SearchSelect";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { BandeiraBadge } from "../../ui/BandeiraBadge";
import { useCartoes } from "../../../hooks/useCartaoQueries";

export interface CardSelectProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  apenasAtivas?: boolean;
}

/**
 * `cartao_id` para `TransacaoFormDialog` — espelha `AccountSelect.tsx`
 * quase literalmente (mesmo hook de listagem por baixo, mesmo
 * `SearchSelect`), ver docs/analise-arquitetural-transacao-frontend.md,
 * seção 4. Único acréscimo real: cada opção mostra `InstitutionBadge`+
 * `BandeiraBadge` como slot visual (mesmo padrão de `CategorySelect`, que
 * já mostra ícone+cor por opção) — reconhecer o cartão certo pela
 * bandeira/instituição é mais rápido que ler só o nome.
 */
export function CardSelect({
  name,
  label,
  optional,
  description,
  placeholder = "Selecione o cartão",
  disabled,
  apenasAtivas = true,
}: CardSelectProps) {
  const { data: cartoes, isLoading } = useCartoes(apenasAtivas);

  const options = useMemo(
    () =>
      (cartoes ?? []).map((cartao) => ({
        value: String(cartao.id),
        label: `${cartao.nome} •••• ${cartao.ultimos_quatro_digitos}`,
        render: (
          <span className="flex items-center gap-1.5">
            <InstitutionBadge nome={cartao.instituicao} size="sm" />
            <BandeiraBadge bandeira={cartao.bandeira} size="sm" />
          </span>
        ),
      })),
    [cartoes],
  );

  return (
    <SearchSelect
      name={name}
      label={label}
      options={options}
      optional={optional}
      description={description}
      placeholder={placeholder}
      searchPlaceholder="Buscar cartão..."
      disabled={disabled}
      loading={isLoading}
    />
  );
}
