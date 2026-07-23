import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, ListOrdered, LogOut, Settings, Settings2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { DURATION, EASE } from "../../lib/motion";
import { Avatar } from "../ui/Avatar";
import { Divider } from "../ui/Divider";
import { ThemeToggle } from "../ui/ThemeToggle";
import { OrganizarNavegacaoDialog } from "./OrganizarNavegacaoDialog";
import { useAuth } from "../../hooks/useAuth";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";

/**
 * Menu do usuário — abre ao clicar no nome/avatar no `Header` (pedido
 * explícito do usuário nesta etapa). Substitui o botão de logout solto que
 * existia antes: "Sair" agora mora aqui dentro, junto de "Aparência"
 * (tema claro/escuro). Mesma mecânica de popover de `Select.tsx`
 * (clique-fora fecha, `Esc` fecha, fade+slide de 4px em `--duration-base`)
 * — nenhum padrão de menu novo inventado.
 *
 * Âncora deliberada para crescimento futuro: o usuário pediu explicitamente
 * para registrar aqui que mais opções de personalização (densidade de
 * tabela, cor de acento, fonte, etc.) devem ganhar espaço NESTE menu no
 * futuro, não espalhadas pela aplicação. Qualquer nova preferência de UI
 * deve primeiro considerar um lugar aqui dentro antes de um componente novo
 * em outro canto do app.
 */
export function UserMenu() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [organizarAberto, setOrganizarAberto] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;

    function onClickOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function handleLogout() {
    setOpen(false);
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  if (!usuario) return null;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-sm px-1.5 py-1 transition-colors duration-fast ease-out hover:bg-surface-2"
      >
        <Avatar nome={usuario.nome} size="sm" />
        <span className="hidden text-sm text-text-secondary sm:inline">{usuario.nome}</span>
        <ChevronDown
          size={14}
          className={`hidden shrink-0 text-text-tertiary transition-transform duration-fast ease-out sm:block ${
            open ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            id={menuId}
            role="menu"
            aria-label="Menu do usuário"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
            exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
            className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-border bg-surface-3 p-1.5 shadow-md"
          >
            <div className="flex items-center gap-2.5 px-2 py-2">
              <Avatar nome={usuario.nome} size="md" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">{usuario.nome}</p>
                <p className="truncate text-caption text-text-tertiary">{usuario.email}</p>
              </div>
            </div>

            <Divider className="my-1.5" />

            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/configuracoes");
              }}
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm text-text-secondary transition-colors duration-fast ease-out hover:bg-surface-2 hover:text-text-primary"
            >
              <Settings size={14} aria-hidden="true" />
              Configurações
            </button>

            <Divider className="my-1.5" />

            <div className="px-2 py-1.5">
              <div className="mb-2 flex items-center gap-1.5 text-caption font-medium text-text-tertiary">
                <Settings2 size={12} aria-hidden="true" />
                <span>Aparência</span>
              </div>
              <ThemeToggle />
              {/* Âncora para futuras opções de personalização (densidade de
                  tabela, cor de acento, fonte, etc.) — crescem aqui dentro,
                  não espalhadas pelo app. "Organizar navegação" (Etapa de
                  Organização da Sidebar) é a primeira a ocupar esse
                  espaço. */}
            </div>

            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                setOrganizarAberto(true);
              }}
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm text-text-secondary transition-colors duration-fast ease-out hover:bg-surface-2 hover:text-text-primary"
            >
              <ListOrdered size={14} aria-hidden="true" />
              Organizar navegação
            </button>

            <Divider className="my-1.5" />

            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm text-text-secondary transition-colors duration-fast ease-out hover:bg-negative-subtle hover:text-negative"
            >
              <LogOut size={14} aria-hidden="true" />
              Sair
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <OrganizarNavegacaoDialog open={organizarAberto} onClose={() => setOrganizarAberto(false)} />
    </div>
  );
}
