import { Landmark } from "lucide-react";
import { corDeContraste, resolveInstitution } from "../../lib/institutions";

export interface InstitutionBadgeProps {
  /** Valor livre de `instituicao` (Conta/Cartão) — `null`/vazio mostra o
   * ícone neutro de fallback, nunca um monograma vazio. */
  nome: string | null | undefined;
  size?: "sm" | "md" | "lg";
  /** Mostra o nome da instituição ao lado do selo — usado em colunas de
   * tabela e listas; omitido em contextos mais compactos (ex. dentro de
   * um `FormField`). */
  showName?: boolean;
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<InstitutionBadgeProps["size"]>, string> = {
  sm: "h-5 w-5 text-[10px]",
  md: "h-7 w-7 text-micro",
  lg: "h-9 w-9 text-caption",
};

const ICON_SIZE: Record<NonNullable<InstitutionBadgeProps["size"]>, number> = {
  sm: 11,
  md: 14,
  lg: 18,
};

/**
 * Única peça visual de branding de instituição financeira do projeto —
 * consome `lib/institutions.ts` (o registry) e nunca decide cor/nome
 * sozinho. Usado por Conta (colunas de tabela, formulário), Cartão e os
 * cards do Dashboard que exibem `instituicao` — qualquer entidade futura
 * com o mesmo campo reaproveita este componente sem alteração.
 */
export function InstitutionBadge({ nome, size = "md", showName = false, className = "" }: InstitutionBadgeProps) {
  const info = resolveInstitution(nome);

  const selo = info ? (
    info.logoUrl ? (
      // Logo oficial real (ver lib/institutions.ts), sem selo/fundo sólido
      // atrás - só uma borda branca sutil pra dar contorno em qualquer cor
      // de fundo (correção de UX, usuário achou o quadrado branco cheio
      // "pesado" demais).
      <span
        className={`inline-flex shrink-0 items-center justify-center rounded-md border border-white/25 p-0.5 ${SIZE_CLASSES[size]}`}
        title={info.nome}
      >
        <img src={info.logoUrl} alt="" className="h-full w-full object-contain" aria-hidden="true" />
      </span>
    ) : (
      <span
        className={`inline-flex shrink-0 items-center justify-center rounded-md font-semibold leading-none ${SIZE_CLASSES[size]}`}
        style={{ backgroundColor: info.cor, color: corDeContraste(info.cor) }}
        title={info.nome}
      >
        {info.iniciais}
      </span>
    )
  ) : (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-md bg-surface-3 text-text-tertiary ${SIZE_CLASSES[size]}`}
      title="Instituição não informada"
    >
      <Landmark size={ICON_SIZE[size]} aria-hidden="true" />
    </span>
  );

  if (!showName) return selo;

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {selo}
      <span className="truncate text-text-primary">{info ? info.nome : "Sem instituição"}</span>
    </span>
  );
}
