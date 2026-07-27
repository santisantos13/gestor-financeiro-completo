/**
 * Registro de "Cor de destaque" (Configurações → Temas personalizáveis) —
 * predefinições curadas, nunca um seletor de cor livre: todas na mesma
 * família "acinzentado/pastel" do azul original (`--color-accent` em
 * `index.css`, seção 6.3), escolhida deliberadamente para não ser um tom
 * puro/saturado (mesma filosofia "nunca extremo puro" do design-system.md,
 * seção 2). Isso permite reaproveitar o MESMO `--color-text-on-accent`
 * escuro (#14141a) para todas as opções, sem precisar calcular/validar
 * contraste WCAG por predefinição.
 *
 * Cada preset é aplicado via `[data-accent="<id>"]` em `index.css` — mesmo
 * mecanismo de atributo de `[data-theme]` (`ThemeContext`), só que num
 * atributo independente: a cor de destaque não depende de claro/escuro
 * (o token `--color-accent` já é idêntico nos dois blocos de tema hoje).
 * Este arquivo só existe para alimentar a UI do seletor (`AccentPicker`) e
 * o tipo `AccentId` — os valores de CSS de verdade vivem em `index.css`,
 * nunca duplicados aqui (ver `AccentContext`, que só grava o atributo).
 */
export type AccentId = "azul" | "verde" | "rosa" | "lilas" | "ambar";

export const ACCENT_PADRAO: AccentId = "azul";

export interface AccentPreset {
  id: AccentId;
  label: string;
  /** Cor base (mesmo valor do `--color-accent` do preset em `index.css`) —
   * usada só para desenhar o swatch do seletor, nunca aplicada via inline
   * style (a aplicação de verdade é o atributo `data-accent` + CSS). */
  cor: string;
}

export const ACCENT_PRESETS: AccentPreset[] = [
  { id: "azul", label: "Azul", cor: "#b0c4de" },
  { id: "verde", label: "Verde", cor: "#a8c9b0" },
  { id: "rosa", label: "Rosa", cor: "#d9aebb" },
  { id: "lilas", label: "Lilás", cor: "#c2aed9" },
  { id: "ambar", label: "Âmbar", cor: "#d9c299" },
];

function ehAccentIdValido(valor: string | null): valor is AccentId {
  return ACCENT_PRESETS.some((p) => p.id === valor);
}

const STORAGE_KEY = "financas:accent";

export function lerAccentSalvo(): AccentId {
  if (typeof window === "undefined") return ACCENT_PADRAO;
  try {
    const salvo = window.localStorage.getItem(STORAGE_KEY);
    return ehAccentIdValido(salvo) ? salvo : ACCENT_PADRAO;
  } catch {
    return ACCENT_PADRAO;
  }
}

export function gravarAccent(id: AccentId): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // localStorage indisponível - a cor ainda vale para esta sessão (mesma
    // degradação silenciosa de ThemeContext/PreferenciasContext).
  }
}
