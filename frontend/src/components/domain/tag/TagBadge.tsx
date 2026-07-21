import { corDeContraste } from "../../../lib/color";

export interface TagBadgeProps {
  nome: string;
  cor: string | null;
  className?: string;
}

/**
 * Peça visual de Tag — análoga a `CategoryBadge`, mas mais simples: Tag
 * não tem `icone` (o model do backend não tem essa coluna), então não há
 * resolvedor de ícone a chamar. Onde `CategoryBadge` é um quadrado
 * (`rounded-md`) com um ícone dentro, `TagBadge` é um "pill"
 * (`rounded-full`) com o nome dentro — coerente com a entrada "Badge/Tag"
 * do Design System (`docs/design-system.md`, seção 14: "`--radius-full`,
 * `--text-micro`"). `cor` nula usa fundo neutro (`--color-surface-3`) com
 * texto em `--color-text-secondary`, mesmo fallback visual de
 * `CategoryBadge`/`InstitutionBadge` para entidade sem cor/marca definida.
 */
export function TagBadge({ nome, cor, className = "" }: TagBadgeProps) {
  if (!cor) {
    return (
      <span
        className={`inline-flex max-w-full items-center truncate rounded-full bg-surface-3 px-2.5 py-0.5 text-micro font-medium text-text-secondary ${className}`}
      >
        {nome}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex max-w-full items-center truncate rounded-full px-2.5 py-0.5 text-micro font-medium ${className}`}
      style={{ backgroundColor: cor, color: corDeContraste(cor) }}
    >
      {nome}
    </span>
  );
}
