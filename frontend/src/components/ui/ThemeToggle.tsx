import { Moon, Sun } from "lucide-react";
import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";
import { useTheme, type Theme } from "../../hooks/useTheme";

const OPCOES: { valor: Theme; label: string; Icon: typeof Sun }[] = [
  { valor: "dark", label: "Escuro", Icon: Moon },
  { valor: "light", label: "Claro", Icon: Sun },
];

/**
 * Alternância claro/escuro — segmented control de dois ícones com um
 * indicador que desliza entre eles (`layoutId`, mesmo padrão do item
 * ativo da `Sidebar`, `motion-principles.md`, seção 5.4, spring `snappy`
 * por ser uma microinteração de toggle, seção 4.3). Componente genérico de
 * `ui/` (não específico do `UserMenu`) para poder aparecer também em
 * `/dev` sem duplicar a mecânica.
 */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Tema da interface"
      className={`inline-flex items-center gap-0.5 rounded-md border border-border bg-surface-2 p-0.5 ${className}`}
    >
      {OPCOES.map(({ valor, label, Icon }) => {
        const ativo = theme === valor;
        return (
          <button
            key={valor}
            type="button"
            role="radio"
            aria-checked={ativo}
            aria-label={label}
            onClick={() => setTheme(valor)}
            className={`relative flex h-7 w-8 items-center justify-center rounded-sm transition-colors duration-fast ease-out ${
              ativo ? "text-text-primary" : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            {ativo && (
              <motion.span
                layoutId="theme-toggle-active"
                transition={SPRING.snappy}
                className="absolute inset-0 rounded-sm bg-surface-4 shadow-xs"
              />
            )}
            <Icon size={14} className="relative" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
