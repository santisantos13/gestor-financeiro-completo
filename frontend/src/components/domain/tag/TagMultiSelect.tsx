import { useMemo } from "react";
import { MultiSelectField } from "../../ui/MultiSelectField";
import { TagBadge } from "./TagBadge";
import { useTags } from "../../../hooks/useTagQueries";

export interface TagMultiSelectProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  apenasAtivas?: boolean;
}

/**
 * `tag_ids` para `TransacaoFormDialog` — camada "inteligente" de domínio
 * sobre o primitivo genérico `MultiSelectField` (mesmo papel que
 * `AccountSelect`/`CardSelect`/`CategorySelect` têm sobre `SearchSelect`).
 * Ver docs/analise-arquitetural-transacao-frontend.md, seção 6.
 *
 * Diferente do `Badge` `tone="accent"` que `MultiSelectField` usa por
 * padrão para cada chip selecionado, aqui cada chip é um `TagBadge` de
 * verdade — mesma cor que a tag tem em qualquer outro lugar do projeto
 * (tabela de Tags, etc.) — via a prop `renderChip`.
 */
export function TagMultiSelect({
  name,
  label,
  optional,
  description,
  placeholder = "Selecione as tags",
  disabled,
  apenasAtivas = true,
}: TagMultiSelectProps) {
  const { data: tags } = useTags(apenasAtivas);

  const options = useMemo(() => (tags ?? []).map((tag) => ({ value: String(tag.id), label: tag.nome })), [tags]);

  const corPorId = useMemo(() => new Map((tags ?? []).map((tag) => [String(tag.id), tag.cor])), [tags]);

  return (
    <MultiSelectField
      name={name}
      label={label}
      options={options}
      optional={optional}
      description={description}
      placeholder={placeholder}
      disabled={disabled}
      renderChip={(option) => <TagBadge nome={option.label} cor={corPorId.get(option.value) ?? null} />}
    />
  );
}
