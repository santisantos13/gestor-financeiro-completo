import { motion } from "motion/react";
import { SPRING } from "../../lib/motion";
import { usePreferencias } from "../../hooks/usePreferencias";
import type { FormatoData } from "../../lib/preferencesStore";

const HOJE = new Date();

const OPCOES: { valor: FormatoData; label: string }[] = [
  { valor: "DD/MM/AAAA", label: formatarExemplo("DD/MM/AAAA") },
  { valor: "AAAA-MM-DD", label: formatarExemplo("AAAA-MM-DD") },
  { valor: "MM/DD/AAAA", label: formatarExemplo("MM/DD/AAAA") },
];

function formatarExemplo(formato: FormatoData): string {
  const d = String(HOJE.getDate()).padStart(2, "0");
  const m = String(HOJE.getMonth() + 1).padStart(2, "0");
  const a = String(HOJE.getFullYear());
  switch (formato) {
    case "AAAA-MM-DD":
      return `${a}-${m}-${d}`;
    case "MM/DD/AAAA":
      return `${m}/${d}/${a}`;
    case "DD/MM/AAAA":
    default:
      return `${d}/${m}/${a}`;
  }
}

/**
 * Segmented control de formato de data, mesma mecânica visual de
 * `ThemeToggle` (indicador que desliza via `layoutId`) — cada opção já
 * mostra a data de HOJE no formato real, em vez de um rótulo genérico tipo
 * "Brasileiro"/"Americano" (evita qualquer ambiguidade sobre o que cada
 * opção realmente produz). Selecionar uma opção recarrega a página (ver
 * `PreferenciasContext.setFormatoData`) — não há como evitar isso sem
 * refatorar todo consumidor de `formatDate`/`formatDateTime` para reagir a
 * contexto, fora do escopo desta etapa.
 */
export function DateFormatToggle({ className = "" }: { className?: string }) {
  const { formatoData, setFormatoData } = usePreferencias();

  return (
    <div
      role="radiogroup"
      aria-label="Formato de data"
      className={`inline-flex items-center gap-0.5 rounded-md border border-border bg-surface-2 p-0.5 ${className}`}
    >
      {OPCOES.map(({ valor, label }) => {
        const ativo = formatoData === valor;
        return (
          <button
            key={valor}
            type="button"
            role="radio"
            aria-checked={ativo}
            onClick={() => setFormatoData(valor)}
            className={`relative rounded-sm px-2.5 py-1 font-mono text-caption transition-colors duration-fast ease-out ${
              ativo ? "text-text-primary" : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            {ativo && (
              <motion.span
                layoutId="date-format-toggle-active"
                transition={SPRING.snappy}
                className="absolute inset-0 rounded-sm bg-surface-4 shadow-xs"
              />
            )}
            <span className="relative">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
