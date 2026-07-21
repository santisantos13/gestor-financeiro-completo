/**
 * Utilitários de cor puros, sem conhecimento de nenhuma entidade específica
 * — extraído de `lib/institutions.ts` durante a Etapa F7 (Categoria), que
 * precisava exatamente da mesma lógica ("cor definida em runtime precisa de
 * um texto/ícone legível em cima dela") para `CategoryBadge`. Antes vivia
 * só em `institutions.ts`; agora é a base compartilhada por qualquer badge
 * de cor livre do projeto (Instituição, Categoria, e futuramente Tag).
 */

/** Componente sRGB (0-255) para linear (correção de gama), passo exigido
 * pela fórmula de luminância relativa do WCAG 2.1 — sem isso, o resultado é
 * só uma aproximação (é exatamente o bug corrigido abaixo). */
function paraLinear(canal255: number): number {
  const c = canal255 / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminanciaRelativa(hex: string): number {
  const limpo = hex.replace("#", "");
  const r = paraLinear(parseInt(limpo.slice(0, 2), 16));
  const g = paraLinear(parseInt(limpo.slice(2, 4), 16));
  const b = paraLinear(parseInt(limpo.slice(4, 6), 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razão de contraste WCAG 2.1 entre duas cores (1:1 a 21:1). */
function razaoDeContraste(hexA: string, hexB: string): number {
  const la = luminanciaRelativa(hexA);
  const lb = luminanciaRelativa(hexB);
  const maior = Math.max(la, lb);
  const menor = Math.min(la, lb);
  return (maior + 0.05) / (menor + 0.05);
}

/** Preto ou branco (tons quase-puros do Design System, nunca extremos
 * absolutos — `#0B0B0D`/`#FFFFFF` já são os tons de superfície/texto mais
 * extremos usados em `index.css`), o que der MAIS CONTRASTE REAL sobre
 * `corFundoHex` — calcula a razão de contraste WCAG 2.1 completa para as
 * duas opções e escolhe a maior, em vez de decidir por um limiar fixo de
 * luminância sem gama corrigida (revisão de UX de Cartões, seção "cores
 * adaptativas": achado de auditoria real — a fórmula antiga (limiar de
 * luminância sem correção de gama) recomendava branco para 11 das 43 cores
 * de `PALETA_SUGESTAO`, em TODOS os 11 casos um contraste pior do que preto
 * teria dado, vários abaixo do mínimo AA de 4.5:1 mesmo quando preto
 * passaria com folga — ex. `#fb7185` (negative): branco dá 2.69:1 (reprova
 * AA), preto dá 7.31:1. A troca é retrocompatível (mesma assinatura, mesmos
 * dois valores possíveis de retorno) e beneficia automaticamente todo
 * consumidor existente (`InstitutionBadge`, `BandeiraBadge`,
 * `CategoryBadge`, preview do `ColorPicker`) sem nenhuma mudança de API. */
export function corDeContraste(corFundoHex: string): "#0B0B0D" | "#FFFFFF" {
  const contrastePreto = razaoDeContraste(corFundoHex, "#0B0B0D");
  const contrasteBranco = razaoDeContraste(corFundoHex, "#FFFFFF");
  return contrastePreto >= contrasteBranco ? "#0B0B0D" : "#FFFFFF";
}

export interface CorSugestao {
  cor: string;
  /** Grupo de exibição no `ColorPicker` (Etapa F10, Rich Pickers) — antes
   * existia só como comentário separando as faixas abaixo; formalizado em
   * dado para o `ColorPicker` agrupar de verdade, sem mudar nenhum valor
   * de cor existente. */
  grupo: string;
}

/** Paleta de sugestão para `ColorPicker` — usada por qualquer entidade com
 * campo `cor` hex livre (Categoria e Tag hoje, `CategoriaFormDialog`/
 * `TagFormDialog`). Curada a partir dos tons já usados no Design System
 * (`--color-chart-*`/`--color-accent` de `index.css`) mais o restante do
 * espectro na mesma família de saturação/luminância (equivalente à escala
 * Tailwind 300-600), ordenada em ARCO-IRIS LINEAR de verdade (ROYGBIV).
 * Historico: 10 -> 19 -> 29 -> 43 tons, mesmo criterio de sempre. */
export const PALETA_SUGESTAO: readonly CorSugestao[] = [
  // --- Vermelho ---
  { cor: "#fca5a5", grupo: "Vermelho" },
  { cor: "#f87171", grupo: "Vermelho" },
  { cor: "#dc2626", grupo: "Vermelho" },
  { cor: "#991b1b", grupo: "Vermelho" },
  // --- Laranja ---
  { cor: "#fdba74", grupo: "Laranja" },
  { cor: "#fb923c", grupo: "Laranja" },
  { cor: "#ea580c", grupo: "Laranja" },
  // --- Amarelo ---
  { cor: "#fbbf24", grupo: "Amarelo" },
  { cor: "#fde047", grupo: "Amarelo" },
  { cor: "#facc15", grupo: "Amarelo" },
  { cor: "#ca8a04", grupo: "Amarelo" },
  // --- Verde ---
  { cor: "#a3e635", grupo: "Verde" },
  { cor: "#4ade80", grupo: "Verde" },
  { cor: "#16a34a", grupo: "Verde" },
  { cor: "#34d399", grupo: "Verde" },
  { cor: "#059669", grupo: "Verde" },
  // --- Ciano/Turquesa ---
  { cor: "#2dd4bf", grupo: "Ciano" },
  { cor: "#0d9488", grupo: "Ciano" },
  { cor: "#22d3ee", grupo: "Ciano" },
  { cor: "#0891b2", grupo: "Ciano" },
  // --- Azul ---
  { cor: "#38bdf8", grupo: "Azul" },
  { cor: "#93c5fd", grupo: "Azul" },
  { cor: "#60a5fa", grupo: "Azul" },
  { cor: "#2563eb", grupo: "Azul" },
  { cor: "#1e40af", grupo: "Azul" },
  // --- Indigo / Violeta / Roxo ---
  { cor: "#818cf8", grupo: "Roxo" },
  { cor: "#4f46e5", grupo: "Roxo" },
  { cor: "#a78bfa", grupo: "Roxo" },
  { cor: "#7c3aed", grupo: "Roxo" },
  { cor: "#c084fc", grupo: "Roxo" },
  { cor: "#9333ea", grupo: "Roxo" },
  // --- Magenta / Rosa ---
  { cor: "#e879f9", grupo: "Rosa" },
  { cor: "#c026d3", grupo: "Rosa" },
  { cor: "#f472b6", grupo: "Rosa" },
  { cor: "#db2777", grupo: "Rosa" },
  { cor: "#fb7185", grupo: "Rosa" },
  { cor: "#e11d48", grupo: "Rosa" },
  // --- Neutros ---
  { cor: "#ffffff", grupo: "Neutros" },
  { cor: "#e2e8f0", grupo: "Neutros" },
  { cor: "#94a3b8", grupo: "Neutros" },
  { cor: "#475569", grupo: "Neutros" },
  { cor: "#000000", grupo: "Neutros" },
  // --- Marca ---
  { cor: "#b0c4de", grupo: "Marca" },
];

const PADRAO_COR_HEX = /^#[0-9A-Fa-f]{6}$/;

/** Mesmo padrão `^#[0-9A-Fa-f]{6}$` validado pelo backend
 * (`app/schemas/categoria.py`, `_PADRAO_COR_HEX`) — usado pelo schema Zod
 * do formulário para dar feedback de formato antes do submit, nunca como
 * substituto da validação real do backend. */
export function eCorHexValida(valor: string): boolean {
  return PADRAO_COR_HEX.test(valor);
}
