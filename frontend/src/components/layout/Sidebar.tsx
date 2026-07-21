import { NavLink } from "react-router-dom";
import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";
import { NAV_ITEMS } from "./navItems";
import { useNavOrder } from "../../hooks/useNavOrder";

const ITEM_DASHBOARD = NAV_ITEMS.find((item) => item.to === "/")!;

/**
 * Navegação lateral, primeira peça real de `components/layout/` — só
 * existia como placeholder em `AppLayout` na F1. A lista cresce uma
 * entidade por vez a partir daqui, mesmo espírito incremental do restante
 * do projeto (ver `AppRoutes.tsx`). O indicador de item ativo usa
 * `layoutId` (shared element) — já correto para quando novos itens forem
 * adicionados, o indicador desliza entre eles em vez de teleportar
 * (motion-principles.md, seção 5.4). Lista "crua" de itens em
 * `./navItems.ts`, compartilhada com `MobileNav` (Etapa de Refinamento de
 * UI — abaixo de `md` esta `aside` inteira é `hidden`, então a navegação
 * real do app abaixo de `md` mora em `MobileNav`, não aqui).
 *
 * Ordem exibida (Etapa de Organização da Sidebar): Dashboard sempre
 * primeiro (fixo, nunca vem de `useNavOrder`), seguido de
 * `useNavOrder().itensOrdenados` — a ordem que o usuário personalizou em
 * "Organizar navegação" (`UserMenu`), com reconciliação automática de
 * páginas novas (ver `contexts/NavOrderContext.tsx`). Nenhuma outra lógica
 * de ordenação vive aqui — este componente só renderiza a ordem já
 * resolvida pelo Context.
 *
 * Microinterações (Etapa de Refinamento Visual): ícone ganha uma escala
 * sutil no hover do item inteiro (`group-hover`, CSS puro — mais confiável
 * aqui que um `whileHover` do Framer aninhado, que só dispararia com o
 * cursor exatamente sobre o ícone, não sobre a linha toda); o indicador do
 * item ativo ganha um glow discreto de acento (`shadow-glow-accent`,
 * mesmo token usado no `Button` primário) além do fundo já existente.
 */
export function Sidebar() {
  const { itensOrdenados } = useNavOrder();
  const itensExibidos = [ITEM_DASHBOARD, ...itensOrdenados];

  return (
    <aside className="hidden shrink-0 border-r border-border-subtle bg-surface-1 md:flex md:w-16 lg:w-56 md:flex-col">
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {itensExibidos.map((item) => (
          <NavLink key={item.to} to={item.to} end className="group relative">
            {({ isActive }) => (
              <span
                className={`relative flex items-center gap-3 rounded-sm px-3 py-2 text-sm font-medium transition-colors duration-fast ease-out ${
                  isActive ? "text-accent" : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-indicator"
                    transition={SPRING.smooth}
                    className="absolute inset-0 rounded-sm bg-accent-subtle shadow-glow-accent"
                  />
                )}
                <item.icon
                  size={18}
                  className="relative shrink-0 transition-transform duration-fast ease-out group-hover:scale-110"
                  aria-hidden="true"
                />
                <span className="relative hidden lg:inline">{item.label}</span>
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
