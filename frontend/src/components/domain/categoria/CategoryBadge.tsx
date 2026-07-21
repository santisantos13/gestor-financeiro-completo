import { corDeContraste } from "../../../lib/color";
import { resolveIconInfo } from "../../../lib/icons";

export interface CategoryBadgeProps {
  nome: string;
  cor: string | null;
  icone: string | null;
  size?: "sm" | "md" | "lg";
  showName?: boolean;
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<CategoryBadgeProps["size"]>, string> = {
  sm: "h-5 w-5",
  md: "h-7 w-7",
  lg: "h-9 w-9",
};

const ICON_SIZE: Record<NonNullable<CategoryBadgeProps["size"]>, number> = {
  sm: 11,
  md: 14,
  lg: 18,
};

/**
 * Peça visual de Categoria — mesma estrutura de `InstitutionBadge`, mas
 * `cor`/`icone` já são campos estruturados da própria entidade (não um
 * texto livre a normalizar), então não existe resolvedor "adivinhando" a
 * categoria a partir de um nome: o componente só lê os dois campos e
 * decora. `cor` nula usa fundo neutro (`--color-surface-3`) com o ícone
 * em `--color-text-tertiary`, mesmo fallback visual de instituição sem
 * marca reconhecida.
 */
export function CategoryBadge({ nome, cor, icone, size = "md", showName = false, className = "" }: CategoryBadgeProps) {
  const { Icon } = resolveIconInfo(icone);

  const selo = cor ? (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-md ${SIZE_CLASSES[size]}`}
      style={{ backgroundColor: cor, color: corDeContraste(cor) }}
      title={nome}
    >
      <Icon size={ICON_SIZE[size]} aria-hidden="true" />
    </span>
  ) : (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-md bg-surface-3 text-text-tertiary ${SIZE_CLASSES[size]}`}
      title={nome}
    >
      <Icon size={ICON_SIZE[size]} aria-hidden="true" />
    </span>
  );

  if (!showName) return selo;

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {selo}
      <span className="truncate text-text-primary">{nome}</span>
    </span>
  );
}
