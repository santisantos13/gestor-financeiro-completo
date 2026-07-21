import { NAV_ITEMS } from "../components/layout/navItems";

/**
 * Índice de resultados do Command Palette (Sprint de Refinamento Premium,
 * item 16, `docs/analise-arquitetural-sprint-refinamento-premium.md`,
 * seção 16). `tipo` é um discriminador deliberado — hoje só existe
 * `"navegacao"`, mas o formato já aceita tipos novos no futuro (ex.:
 * `"acao"` para atalhos tipo "Nova transação", `"entidade"` para pular
 * direto pra uma Conta/Cartão específico) sem precisar refatorar nada
 * disso, só adicionar ao array de resultados.
 */
export interface ResultadoComando {
  tipo: "navegacao";
  id: string;
  label: string;
  rota: string;
  icon: (typeof NAV_ITEMS)[number]["icon"];
}

/** Reaproveita `NAV_ITEMS` (já compartilhado por Sidebar/MobileNav) - nenhuma
 * lista de rotas nova/duplicada. */
export const RESULTADOS_NAVEGACAO: ResultadoComando[] = NAV_ITEMS.map((item) => ({
  tipo: "navegacao",
  id: `nav-${item.to}`,
  label: item.label,
  rota: item.to,
  icon: item.icon,
}));

export function buscarComandos(query: string): ResultadoComando[] {
  const termo = query.trim().toLowerCase();
  if (!termo) return RESULTADOS_NAVEGACAO;
  return RESULTADOS_NAVEGACAO.filter((resultado) => resultado.label.toLowerCase().includes(termo));
}
