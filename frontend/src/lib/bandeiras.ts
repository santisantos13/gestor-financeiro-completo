/**
 * Registry único de bandeiras de cartão — Etapa F9 (Cartão), espelha
 * exatamente o espírito de `lib/institutions.ts`, mas mais simples: `Bandeira`
 * já é um enum FECHADO no backend (`app/models/enums.py`, 7 valores, ver
 * `types/enums.ts`), então não precisa de `normalizar()`/aliases/fallback
 * "desconhecida" — é só um mapa direto `Bandeira -> BandeiraInfo`.
 *
 * Mesma decisão de direitos de marca já tomada para `institutions.ts`
 * (`docs/revisao-tecnica-branding-e-microinteracoes.md`, seção 2): nenhum
 * SVG de logo real é embutido. Monograma sobre a cor de marca pública real
 * (fato público, não protegido por direito autoral).
 *
 * Sobre "Visa Platinum/Gold", "Mastercard Platinum/Gold" etc. (pedido nos
 * ajustes de UX/UI): `Bandeira` no backend não tem conceito de nível/tier —
 * são só os 7 valores abaixo, sem coluna extra. Inventar um campo de tier
 * aqui seria decorar um dado que não existe. A riqueza visual "Platinum/
 * Gold/Black" pedida é resolvida em `lib/cardThemes.ts` (variante de TEMA do
 * cartão, por instituição, nunca por bandeira) — é lá que nomes como "Nubank
 * Ultra"/"Inter Black" vivem, sempre como preferência visual local
 * (localStorage), nunca um campo novo no backend nem uma reinterpretação do
 * enum fechado de `Bandeira`.
 */
import { corDeContraste } from "./color";
import type { Bandeira as BandeiraEnum } from "../types/enums";

export interface BandeiraInfo {
  label: string;
  /** Cor de marca real (hex) — fato público. */
  cor: string;
  /** Monograma de 2 caracteres exibido quando não há logo real. */
  sigla: string;
}

export const BANDEIRAS: Record<BandeiraEnum, BandeiraInfo> = {
  VISA: { label: "Visa", cor: "#1A1F71", sigla: "VI" },
  MASTERCARD: { label: "Mastercard", cor: "#EB001B", sigla: "MC" },
  ELO: { label: "Elo", cor: "#000000", sigla: "EL" },
  AMERICAN_EXPRESS: { label: "American Express", cor: "#2E77BC", sigla: "AE" },
  HIPERCARD: { label: "Hipercard", cor: "#B3131B", sigla: "HC" },
  DINERS_CLUB: { label: "Diners Club", cor: "#004A97", sigla: "DC" },
  OUTRA: { label: "Outra", cor: "#3F3F46", sigla: "—" },
};

/** Resolve `BandeiraInfo` para um valor de `Bandeira` — nunca `undefined`
 * porque o tipo já é um enum fechado (diferente de `resolveInstitution`,
 * que lida com texto livre e pode não achar nada). */
export function resolveBandeira(bandeira: BandeiraEnum): BandeiraInfo {
  return BANDEIRAS[bandeira];
}

/** Reexportado por conveniência — mesma função de `lib/color.ts`, usada por
 * `BandeiraBadge` para o texto do monograma sobre a cor de marca. */
export { corDeContraste };

/** Lista completa — usada só pelo filtro de bandeira da página `/cartoes` e
 * pela galeria de demonstração em `/dev/forms`. */
export const TODAS_BANDEIRAS: readonly BandeiraEnum[] = Object.keys(BANDEIRAS) as BandeiraEnum[];
