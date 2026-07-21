import { BANDEIRAS, corDeContraste } from "../../lib/bandeiras";
import { MastercardLogo, VisaLogo } from "./brandLogos";
import type { Bandeira } from "../../types/enums";

export interface BandeiraBadgeProps {
  bandeira: Bandeira;
  size?: "sm" | "md" | "lg";
  /** Mostra o label da bandeira ao lado do selo — mesmo padrão de
   * `InstitutionBadge`, usado em colunas de tabela e listas. */
  showName?: boolean;
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<BandeiraBadgeProps["size"]>, string> = {
  sm: "h-5 w-5 text-[10px]",
  md: "h-7 w-7 text-micro",
  lg: "h-9 w-9 text-caption",
};

/**
 * Única peça visual de identificação de bandeira do projeto — consome
 * `lib/bandeiras.ts` (o registry) e nunca decide cor/sigla sozinha. Mesmo
 * papel de `InstitutionBadge`, versão para um enum fechado em vez de texto
 * livre (nenhum fallback "não informado" é necessário: `Bandeira` é sempre
 * obrigatório em `CartaoRead`).
 */
export function BandeiraBadge({ bandeira, size = "md", showName = false, className = "" }: BandeiraBadgeProps) {
  const info = BANDEIRAS[bandeira];

  // Visa/Mastercard ganham o logo real (pedido do usuário, com imagens de
  // referência) sem fundo sólido atrás - só uma borda branca sutil pra dar
  // contorno (usuário achou o selo branco cheio "pesado" demais). VisaLogo
  // usa a variante branca do wordmark (ver brandLogos.tsx) exatamente por
  // não ter mais uma caixa clara atrás pra sustentar o azul-marinho de
  // marca. As demais 5 bandeiras continuam com o monograma de sempre.
  const selo =
    bandeira === "MASTERCARD" || bandeira === "VISA" ? (
      <span
        className={`inline-flex shrink-0 items-center justify-center rounded-md border border-white/25 p-0.5 ${SIZE_CLASSES[size]}`}
        title={info.label}
      >
        {bandeira === "MASTERCARD" ? (
          <MastercardLogo className="h-full w-full" />
        ) : (
          <VisaLogo className="h-full w-full" />
        )}
      </span>
    ) : (
      <span
        className={`inline-flex shrink-0 items-center justify-center rounded-md font-semibold leading-none ${SIZE_CLASSES[size]}`}
        style={{ backgroundColor: info.cor, color: corDeContraste(info.cor) }}
        title={info.label}
      >
        {info.sigla}
      </span>
    );

  if (!showName) return selo;

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {selo}
      <span className="truncate text-text-primary">{info.label}</span>
    </span>
  );
}
