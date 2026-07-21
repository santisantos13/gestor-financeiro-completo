import { createContext, useCallback, useMemo, useState, type ReactNode } from "react";
import { NAV_ITEMS, type NavItem } from "../components/layout/navItems";

const STORAGE_KEY = "financas:ordem-navegacao";

export interface NavOrderContextValue {
  /** Itens de navegação (sem o Dashboard) já na ordem final a exibir —
   * `Sidebar`/`MobileNav` consomem isto, nunca `NAV_ITEMS` diretamente. */
  itensOrdenados: NavItem[];
  /** Ordem em uso hoje (persistida), como array de `to` — usado pelo modal
   * de organização para inicializar a lista em edição. */
  ordemAtual: string[];
  /** Persiste uma nova ordem (array de `to`, sem o Dashboard). */
  salvarOrdem: (ordem: string[]) => void;
  /** Volta à ordem natural de `NAV_ITEMS` (equivalente a nunca ter
   * personalizado nada) e persiste essa "ausência de preferência". */
  restaurarPadrao: () => void;
}

export const NavOrderContext = createContext<NavOrderContextValue | null>(null);

function lerOrdemSalva(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const bruto = window.localStorage.getItem(STORAGE_KEY);
    if (!bruto) return [];
    const parsed = JSON.parse(bruto);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}

function persistirOrdem(ordem: string[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ordem));
  } catch {
    // localStorage indisponível (modo privado restrito etc.) — a ordem
    // ainda funciona nesta sessão, só não persiste entre visitas (mesma
    // degradação silenciosa de ThemeContext/tokenStore).
  }
}

/**
 * Reconcilia a ordem salva com a lista real de páginas (`NAV_ITEMS`), sem
 * nunca incluir o Dashboard (tratado fora deste sistema, sempre fixo em
 * primeiro por `Sidebar`/`MobileNav`). Função pura, testável isolada:
 *
 * 1. Itens cuja rota aparece em `ordemSalva` entram nessa ordem relativa.
 * 2. Itens que não aparecem em `ordemSalva` (página nova, adicionada depois
 *    que o usuário salvou sua preferência) são anexados ao final, na ordem
 *    em que já aparecem em `NAV_ITEMS` — é isto que garante que nenhuma
 *    página futura precise de nenhuma mudança além de uma linha nova em
 *    `navItems.ts` para participar da organização.
 * 3. Entradas de `ordemSalva` que não correspondem a nenhuma rota atual
 *    (página removida) são descartadas silenciosamente.
 */
export function reconciliarOrdem(navItems: NavItem[], ordemSalva: string[]): NavItem[] {
  const reordenaveis = navItems.filter((item) => item.to !== "/");
  const porRota = new Map(reordenaveis.map((item) => [item.to, item]));

  const daOrdemSalva = ordemSalva
    .map((to) => porRota.get(to))
    .filter((item): item is NavItem => item !== undefined);

  const jaIncluidas = new Set(daOrdemSalva.map((item) => item.to));
  const restantes = reordenaveis.filter((item) => !jaIncluidas.has(item.to));

  return [...daOrdemSalva, ...restantes];
}

/**
 * Preferência de organização da Sidebar — mesma forma de `ThemeProvider`
 * (`contexts/ThemeContext.tsx`): estado React inicializado de forma
 * síncrona a partir do `localStorage`, sem servidor, sem React Query.
 * Existe como Context (não um hook solto por componente) porque o gatilho
 * de mudança (`OrganizarNavegacaoDialog`, aberto a partir de `UserMenu`) e
 * os consumidores (`Sidebar`, `MobileNav`) são ramos irmãos da árvore, sem
 * relação pai-filho — precisam do mesmo estado vivendo um nível acima dos
 * dois. Ver docs/analise-arquitetural-organizacao-sidebar.md, seção 3.
 */
export function NavOrderProvider({ children }: { children: ReactNode }) {
  const [ordemAtual, setOrdemAtual] = useState<string[]>(lerOrdemSalva);

  const itensOrdenados = useMemo(() => reconciliarOrdem(NAV_ITEMS, ordemAtual), [ordemAtual]);

  const salvarOrdem = useCallback((ordem: string[]) => {
    setOrdemAtual(ordem);
    persistirOrdem(ordem);
  }, []);

  const restaurarPadrao = useCallback(() => {
    setOrdemAtual([]);
    persistirOrdem([]);
  }, []);

  return (
    <NavOrderContext.Provider value={{ itensOrdenados, ordemAtual, salvarOrdem, restaurarPadrao }}>
      {children}
    </NavOrderContext.Provider>
  );
}
