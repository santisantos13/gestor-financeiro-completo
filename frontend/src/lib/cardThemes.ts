/**
 * Registry de temas visuais de Cartão — Ajustes de UX/UI antes da Etapa F9.
 * Não é regra de negócio: `Cartão.instituicao` já existe como string livre
 * no backend (mesmo campo de Conta, `lib/institutions.ts`); este arquivo só
 * decora visualmente um valor que o backend já entrega, nunca valida nem
 * transforma o dado salvo — mesmo princípio de `institutions.ts`/
 * `bandeiras.ts`.
 *
 * Resolve a instituição real via `resolveInstitution` (mesmo `id` usado por
 * `InstitutionBadge`) e devolve as variantes de tema conhecidas para ela —
 * cada uma com um gradiente de marca real (fato público) e uma cor de texto
 * legível sobre esse gradiente. Instituição sem tema específico (ou não
 * reconhecida) cai no tema "Padrão" do Design System (tokens de superfície,
 * nunca uma cor inventada).
 *
 * Sobre a "variante Platinum/Gold/Black" pedida nos ajustes de UX/UI: como
 * `Bandeira` é um enum fechado sem conceito de tier (ver nota em
 * `lib/bandeiras.ts`), essa riqueza visual vive AQUI, como uma segunda
 * variante de tema por instituição (ex. "Nubank Ultra", "Inter Black") —
 * nunca um campo novo no backend. A preferência de variante é por cartão,
 * puramente visual, e persiste em `localStorage` (nunca enviada à API) —
 * mesmo padrão já usado por `ThemeContext`/`NavOrderContext` para qualquer
 * preferência de UI que não é dado de domínio.
 */
import { resolveInstitution } from "./institutions";

export interface CardThemeVariant {
  id: string;
  label: string;
  /** Gradiente linear (2 stops) usado como fundo do `CartaoVisual`. Cores
   * fixas (não `var(--...)`) nas variantes de instituição real — são a cor
   * de marca, o mesmo raciocínio de `lib/institutions.ts`/`lib/bandeiras.ts`
   * (fato público, não decorativo arbitrário). Só a variante "Padrão" usa
   * tokens do Design System. */
  gradiente: [string, string];
  corTexto: string;
}

interface CardThemeGroup {
  /** Casa com `InstitutionInfo.id` de `lib/institutions.ts`. */
  instituicaoId: string;
  variantes: CardThemeVariant[];
}

const TEMA_PADRAO: CardThemeVariant = {
  id: "padrao",
  label: "Padrão",
  gradiente: ["var(--color-surface-3)", "var(--color-surface-4)"],
  corTexto: "var(--color-text-primary)",
};

/** Curadoria pequena e deliberada — só instituições citadas nos ajustes de
 * UX/UI ganham uma segunda variante "premium"; as demais têm só a variante
 * de marca padrão. Instituições fora desta lista (ou texto livre não
 * reconhecido por `resolveInstitution`) caem em `TEMA_PADRAO`. */
const GRUPOS: CardThemeGroup[] = [
  {
    instituicaoId: "nubank",
    variantes: [
      { id: "padrao", label: "Nubank", gradiente: ["#9013E0", "#5F0A9C"], corTexto: "#FFFFFF" },
      { id: "ultra", label: "Nubank Ultra", gradiente: ["#3D0F5C", "#160523"], corTexto: "#E9D9FF" },
    ],
  },
  {
    instituicaoId: "inter",
    variantes: [
      { id: "padrao", label: "Banco Inter", gradiente: ["#FF7A00", "#C75E00"], corTexto: "#FFFFFF" },
      { id: "black", label: "Inter Black", gradiente: ["#1C1C1C", "#000000"], corTexto: "#F5A623" },
    ],
  },
  {
    instituicaoId: "santander",
    variantes: [
      { id: "padrao", label: "Santander", gradiente: ["#EC0000", "#8C0000"], corTexto: "#FFFFFF" },
      { id: "black", label: "Santander Black", gradiente: ["#1A1A1A", "#000000"], corTexto: "#EC0000" },
    ],
  },
  {
    instituicaoId: "itau",
    variantes: [
      { id: "padrao", label: "Itaú", gradiente: ["#EC7000", "#004A8D"], corTexto: "#FFFFFF" },
      { id: "black", label: "Itaú Black", gradiente: ["#151515", "#000000"], corTexto: "#EC7000" },
    ],
  },
  {
    instituicaoId: "bradesco",
    variantes: [{ id: "padrao", label: "Bradesco", gradiente: ["#CC092F", "#7A0619"], corTexto: "#FFFFFF" }],
  },
  {
    instituicaoId: "caixa",
    variantes: [{ id: "padrao", label: "Caixa", gradiente: ["#0070AE", "#004161"], corTexto: "#FFFFFF" }],
  },
  {
    instituicaoId: "bb",
    variantes: [{ id: "padrao", label: "Banco do Brasil", gradiente: ["#FADB00", "#0033A0"], corTexto: "#14141A" }],
  },
  {
    instituicaoId: "c6",
    variantes: [{ id: "padrao", label: "C6 Bank", gradiente: ["#3B3B3B", "#0A0A0A"], corTexto: "#FFD700" }],
  },
  {
    instituicaoId: "picpay",
    variantes: [{ id: "padrao", label: "PicPay", gradiente: ["#21C25E", "#0E6B33"], corTexto: "#FFFFFF" }],
  },
  {
    instituicaoId: "neon",
    variantes: [{ id: "padrao", label: "Neon", gradiente: ["#00E28A", "#00915A"], corTexto: "#0B0B0D" }],
  },
  {
    instituicaoId: "mercadopago",
    variantes: [
      { id: "padrao", label: "Mercado Pago", gradiente: ["#00B1EA", "#00688A"], corTexto: "#FFFFFF" },
      { id: "premium", label: "Mercado Pago Premium Black", gradiente: ["#1E1E1E", "#000000"], corTexto: "#00B1EA" },
    ],
  },
  {
    instituicaoId: "xp",
    variantes: [{ id: "padrao", label: "XP Investimentos", gradiente: ["#1C1C1C", "#000000"], corTexto: "#FFC800" }],
  },
  {
    instituicaoId: "btg",
    variantes: [{ id: "padrao", label: "BTG Pactual", gradiente: ["#003DA5", "#001A45"], corTexto: "#FFFFFF" }],
  },
  {
    instituicaoId: "sicredi",
    variantes: [{ id: "padrao", label: "Sicredi", gradiente: ["#7AB51D", "#425F0F"], corTexto: "#FFFFFF" }],
  },
  {
    instituicaoId: "sicoob",
    variantes: [{ id: "padrao", label: "Sicoob", gradiente: ["#00A65E", "#00552F"], corTexto: "#FFFFFF" }],
  },
];

/** Todas as variantes de tema disponíveis para o texto livre de
 * `instituicao` — sempre pelo menos `[TEMA_PADRAO]` (nunca lista vazia). */
export function getCardThemeVariants(instituicao: string | null | undefined): CardThemeVariant[] {
  const info = resolveInstitution(instituicao);
  if (!info) return [TEMA_PADRAO];
  const grupo = GRUPOS.find((g) => g.instituicaoId === info.id);
  if (!grupo) return [TEMA_PADRAO];
  return grupo.variantes;
}

/** Resolve a variante efetiva a exibir — `variantId` desconhecido ou
 * ausente cai na primeira variante do grupo (a "de marca padrão", sempre a
 * primeira da lista por convenção acima). Nunca lança erro. */
export function resolveCardTheme(
  instituicao: string | null | undefined,
  variantId: string | null | undefined,
): CardThemeVariant {
  const variantes = getCardThemeVariants(instituicao);
  return variantes.find((v) => v.id === variantId) ?? variantes[0];
}

// ---- Preferência de variante por cartão (localStorage, nunca backend) ----

const STORAGE_KEY = "financas:variante-tema-cartao";

/** Cache em memória do módulo — evita reler/parsear `localStorage` a cada
 * chamada. `lerVariantePreferida` é chamada uma vez por LINHA do
 * `DataTable` a cada render da tabela (busca client-side re-renderiza a
 * lista inteira a cada tecla digitada, `deferredQuery` de `SearchBar`) —
 * sem cache, isso seria um `JSON.parse` completo do objeto de preferências
 * por linha por render (análise de desempenho pós-implementação da Etapa
 * F9). O cache só é invalidado por uma escrita nesta própria sessão
 * (`salvarVariantePreferida` atualiza `cache` e `localStorage` juntos) —
 * nunca fica desatualizado dentro de uma mesma aba, e uma aba nova sempre
 * começa com `cache === null` (lê do zero). */
let cache: Record<string, string> | null = null;

function lerPreferencias(): Record<string, string> {
  if (cache) return cache;
  if (typeof window === "undefined") return {};
  try {
    const bruto = window.localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = bruto ? JSON.parse(bruto) : {};
    cache = parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
  } catch {
    cache = {};
  }
  return cache;
}

/** Chave usada para um cartão ainda não salvo (criação) — a preferência
 * escolhida no formulário de criação não tem `id` real até o `POST`
 * responder, então fica só em memória do formulário (RHF), nunca gravada
 * aqui com uma chave "novo" genérica (evitaria colisão entre criações
 * concorrentes/sequenciais). Só cartões com `id` real persistem. */
export function lerVariantePreferida(cartaoId: number): string | null {
  return lerPreferencias()[String(cartaoId)] ?? null;
}

export function salvarVariantePreferida(cartaoId: number, variantId: string): void {
  const atual = { ...lerPreferencias(), [String(cartaoId)]: variantId };
  cache = atual;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(atual));
  } catch {
    // localStorage indisponível (modo privado restrito etc.) — a variante
    // ainda funciona nesta sessão (o cache em memória continua valendo),
    // só não persiste entre visitas (mesma degradação silenciosa de
    // ThemeContext/NavOrderContext).
  }
}
