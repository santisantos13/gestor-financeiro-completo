import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { NavLink } from "react-router-dom";
import { X } from "lucide-react";
import { DURATION, EASE } from "../../lib/motion";
import { NAV_ITEMS } from "./navItems";
import { useNavOrder } from "../../hooks/useNavOrder";

const ITEM_DASHBOARD = NAV_ITEMS.find((item) => item.to === "/")!;

export interface MobileNavProps {
  open: boolean;
  onClose: () => void;
}

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Navegacao abaixo de md - Sidebar e hidden nessa faixa (so existe a
 * partir de md), e ate esta etapa nao havia NENHUM substituto: o app
 * ficava sem forma de navegar entre /, /contas e /categorias no
 * celular a nao ser digitando a URL. Achado central da revisao de UI (ver
 * docs/revisao-tecnica-refinamento-ui.md).
 *
 * Painel desliza da esquerda (x: -100% -> 0), mesmo par
 * fundo-desfocado + spring smooth de entrada / fade rapido de saida ja
 * usado por FormDialog (lib/motion.ts, modalBackdrop) - nenhum
 * timing novo inventado. Fecha com Esc, clique no backdrop ou ao
 * selecionar um item (navegacao real, nao um menu que fica no caminho).
 * Foco preso dentro do painel enquanto aberto, devolvido ao botao que
 * abriu ao fechar - mesma mecanica de acessibilidade de FormDialog.
 *
 * Ordem dos itens (Etapa de Organizacao da Sidebar): Dashboard fixo
 * primeiro, resto vem de `useNavOrder().itensOrdenados` - mesma fonte que
 * `Sidebar` usa, os dois nunca divergem.
 */
export function MobileNav({ open, onClose }: MobileNavProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const { itensOrdenados } = useNavOrder();
  const itensExibidos = [ITEM_DASHBOARD, ...itensOrdenados];

  useEffect(() => {
    if (!open) return;

    const previamenteFocado = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const focaveis = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    focaveis?.[0]?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const nodes = panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeyDown);
      previamenteFocado?.focus();
    };
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { duration: DURATION.moderate, ease: EASE.out } }}
          exit={{ opacity: 0, transition: { duration: DURATION.fast, ease: EASE.in } }}
          className="fixed inset-0 z-50 bg-bg/60 backdrop-blur-lg md:hidden"
          onClick={onClose}
        >
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Navegacao"
            initial={{ x: "-100%" }}
            animate={{ x: 0, transition: { type: "spring", stiffness: 300, damping: 30 } }}
            exit={{ x: "-100%", transition: { duration: DURATION.fast, ease: EASE.in } }}
            onClick={(event) => event.stopPropagation()}
            className="flex h-full w-64 max-w-[80vw] flex-col border-r border-border-subtle bg-surface-1 p-3"
          >
            <div className="mb-2 flex items-center justify-between px-1 py-1">
              <span className="text-h3 font-semibold text-text-primary">Financas Pessoais</span>
              <button
                type="button"
                onClick={onClose}
                aria-label="Fechar navegacao"
                className="rounded-sm p-1.5 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-2 hover:text-text-primary"
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            <nav className="flex flex-1 flex-col gap-1">
              {itensExibidos.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm font-medium transition-colors duration-fast ease-out ${
                      isActive ? "bg-accent-subtle text-accent" : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                    }`
                  }
                >
                  <item.icon size={18} className="shrink-0" aria-hidden="true" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
