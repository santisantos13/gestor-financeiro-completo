/**
 * Personalização do Dashboard (Sprint de Refinamento Premium, item 15,
 * `docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 15):
 * ordem e visibilidade dos cards do Bento Grid, persistidas em
 * `localStorage` — mesmo padrão de `lib/cardThemes.ts` (preferência
 * puramente visual, sem necessidade de backend). Formato já desenhado
 * para migrar a um endpoint de preferências de usuário no futuro (chave
 * estável por card, não um índice posicional), mas essa migração NÃO é
 * implementada agora.
 */
/** Correção pedida pelo usuário (2026-07-22): "Contas e Cartões"/
 * "Transações Recentes" (fixados desde o Refinamento Visual, decisão 7) e
 * "Evolução do saldo" (Etapa de Gráficos) voltam a fazer parte da
 * personalização — o usuário reportou que a lista estava incompleta (só
 * mostrava Faturas/Financiamentos/Empréstimos/Metas). Ficam PRIMEIRO na
 * ordem padrão para preservar o arranjo visual atual de quem ainda não
 * personalizou nada. `carregarLayoutDashboard` abaixo já tolera ids
 * desconhecidos/ausentes por construção — um layout salvo ANTES desta
 * mudança (só com os 4 ids antigos) trata os 3 novos como "faltantes" e os
 * acrescenta ao final automaticamente, sem precisar de migração manual. */
export type DashboardCardId =
  | "contas-cartoes"
  | "transacoes-recentes"
  | "evolucao-saldo"
  | "faturas"
  | "financiamentos"
  | "emprestimos"
  | "metas";

export interface DashboardCardMeta {
  id: DashboardCardId;
  label: string;
}

/** Ordem e conjunto de ids válidos — única fonte de verdade. Adicionar um
 * card novo no futuro é só adicionar uma entrada aqui + no mapa de
 * componentes em `DashboardPage.tsx`. */
export const CARDS_PERSONALIZAVEIS: DashboardCardMeta[] = [
  { id: "contas-cartoes", label: "Contas e Cartões" },
  { id: "transacoes-recentes", label: "Transações Recentes" },
  { id: "evolucao-saldo", label: "Evolução do saldo" },
  { id: "faturas", label: "Faturas" },
  { id: "financiamentos", label: "Financiamentos" },
  { id: "emprestimos", label: "Empréstimos" },
  { id: "metas", label: "Metas" },
];

const IDS_VALIDOS = new Set<string>(CARDS_PERSONALIZAVEIS.map((c) => c.id));
const ORDEM_PADRAO: DashboardCardId[] = CARDS_PERSONALIZAVEIS.map((c) => c.id);

export interface LayoutDashboard {
  ordem: DashboardCardId[];
  ocultos: DashboardCardId[];
}

const CHAVE_LOCALSTORAGE = "dashboard:layout";

export function layoutPadrao(): LayoutDashboard {
  return { ordem: [...ORDEM_PADRAO], ocultos: [] };
}

/** Tolerante a qualquer coisa que não seja o formato esperado - JSON
 * inválido, ids desconhecidos (versão antiga do app, campo corrompido),
 * card removido do catálogo etc. Nunca lança, sempre cai de volta pro
 * padrão nesses casos (preferência cosmética, não vale a pena arriscar
 * quebrar o Dashboard inteiro por causa dela). */
export function carregarLayoutDashboard(): LayoutDashboard {
  try {
    const bruto = localStorage.getItem(CHAVE_LOCALSTORAGE);
    if (!bruto) return layoutPadrao();
    const dados = JSON.parse(bruto);
    if (!dados || !Array.isArray(dados.ordem) || !Array.isArray(dados.ocultos)) return layoutPadrao();

    const ordemValida = dados.ordem.filter((id: unknown): id is DashboardCardId => typeof id === "string" && IDS_VALIDOS.has(id));
    // Ids válidos ausentes da ordem salva (card novo lançado depois que o
    // usuário personalizou) entram no final, na ordem padrão - nunca
    // somem silenciosamente do Dashboard.
    const faltantes = ORDEM_PADRAO.filter((id) => !ordemValida.includes(id));
    const ocultosValidos = dados.ocultos.filter((id: unknown): id is DashboardCardId => typeof id === "string" && IDS_VALIDOS.has(id));

    return { ordem: [...ordemValida, ...faltantes], ocultos: ocultosValidos };
  } catch {
    return layoutPadrao();
  }
}

export function salvarLayoutDashboard(layout: LayoutDashboard): void {
  try {
    localStorage.setItem(CHAVE_LOCALSTORAGE, JSON.stringify(layout));
  } catch {
    // localStorage indisponível (modo privado, quota etc.) - degrada
    // graciosamente para "nunca lembra entre sessões", nunca quebra a tela.
  }
}
