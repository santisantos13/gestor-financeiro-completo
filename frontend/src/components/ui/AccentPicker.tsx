import { Check } from "lucide-react";
import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";
import { ACCENT_PRESETS } from "../../lib/accentThemes";
import { useAccent } from "../../hooks/useAccent";

/**
 * Seletor de "Cor de destaque" — swatches redondos em vez do segmented
 * control de `ThemeToggle`/`DateFormatToggle` (aqui a própria cor já é a
 * informação, não cabe num rótulo de texto). Mesmo `role="radiogroup"` e
 * indicador animado (`layoutId`) das outras duas preferências, para manter
 * a mesma linguagem de interação em toda a página de Configurações.
 */
export function AccentPicker({ className = "" }: { className?: string }) {
  const { accent, setAccent } = useAccent();

  return (
    <div role="radiogroup" aria-label="Cor de destaque" className={`inline-flex items-center gap-2 ${className}`}>
      {ACCENT_PRESETS.map((preset) => {
        const ativo = accent === preset.id;
        return (
          <button
            key={preset.id}
            type="button"
            role="radio"
            aria-checked={ativo}
            aria-label={preset.label}
            title={preset.label}
            onClick={() => setAccent(preset.id)}
            className="relative flex h-8 w-8 items-center justify-center rounded-full transition-transform duration-fast ease-out hover:scale-105"
          >
            <span className="h-6 w-6 rounded-full" style={{ backgroundColor: preset.cor }} aria-hidden="true" />
            {ativo && (
              <motion.span
                layoutId="accent-picker-active"
                transition={SPRING.snappy}
                className="absolute inset-0 rounded-full"
                style={{ boxShadow: `0 0 0 2px var(--color-surface-2), 0 0 0 4px ${preset.cor}` }}
              />
            )}
            {ativo && (
              <Check
                size={12}
                className="absolute"
                style={{ color: "#14141a" }}
                aria-hidden="true"
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
