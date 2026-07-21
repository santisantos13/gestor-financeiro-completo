import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { DURATION, EASE } from "../../../lib/motion";
import { useFloatingPanel } from "../../../hooks/useFloatingPanel";
import { nomeMes } from "../../../utils/date";

export interface MesAnoSeletorProps {
  ano: number;
  mes: number;
  onSelecionar: (ano: number, mes: number) => void;
  className?: string;
}

const MESES_ABREVIADOS = Array.from({ length: 12 }, (_, indice) => nomeMes(indice + 1).slice(0, 3));

/**
 * Etapa de Refinamento UX/UI, item 6 ("navegação entre datas"): antes só
 * dava para trocar de mês uma seta de cada vez — navegar para uma data
 * distante (ex. "ver dezembro do ano passado") exigia dezenas de cliques.
 * Este seletor substitui o rótulo estático "Julho de 2026" por um botão que
 * abre um painel com stepper de ANO + grid dos 12 meses — escolher
 * diretamente o mês desejado do ano já visível é sempre 1 clique
 * (`selecionar` fecha o painel imediatamente, mesmo padrão de
 * `RichPicker`/`DateInput`/`Select` - nunca um passo extra de confirmação).
 * Trocar de ano é sempre 1 clique nas setas do stepper, sem fechar o
 * painel (o usuário normalmente troca de ano e já escolhe um mês em
 * seguida).
 *
 * Mesma mecânica de posicionamento (`useFloatingPanel`, Tier 1, sem
 * backdrop) já usada por todo o resto da família de pickers do projeto -
 * nenhuma técnica nova inventada aqui.
 */
export function MesAnoSeletor({ ano, mes, onSelecionar, className = "" }: MesAnoSeletorProps) {
  const [open, setOpen] = useState(false);
  const [anoVisivel, setAnoVisivel] = useState(ano);

  function close() {
    setOpen(false);
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLButtonElement>(open, close, {
    panelWidth: () => 280,
    estimatedHeight: 220,
  });

  useEffect(() => {
    if (open) setAnoVisivel(ano);
  }, [open, ano]);

  function selecionarMes(mesEscolhido: number) {
    onSelecionar(anoVisivel, mesEscolhido);
    close();
  }

  return (
    <>
      <button
        ref={anchorRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={`flex items-center gap-1.5 rounded-sm px-2 py-1 text-h3 font-semibold text-text-primary transition-colors duration-fast ease-out hover:bg-surface-3 ${className}`}
      >
        {nomeMes(mes)} {ano}
        <ChevronDown
          size={14}
          className={`text-text-tertiary transition-transform duration-fast ease-out ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {createPortal(
        <AnimatePresence>
          {open && rect && (
            <motion.div
              ref={panelRef}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
              exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
              style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
              className="z-[var(--z-tier1)] rounded-lg border border-border bg-surface-3 p-3 shadow-md"
            >
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setAnoVisivel((a) => a - 1)}
                  aria-label="Ano anterior"
                  className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary"
                >
                  <ChevronLeft size={16} aria-hidden="true" />
                </button>
                <span className="tabular text-sm font-medium text-text-primary">{anoVisivel}</span>
                <button
                  type="button"
                  onClick={() => setAnoVisivel((a) => a + 1)}
                  aria-label="Próximo ano"
                  className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary"
                >
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-1.5">
                {MESES_ABREVIADOS.map((label, indice) => {
                  const numeroMes = indice + 1;
                  const selecionado = anoVisivel === ano && numeroMes === mes;
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => selecionarMes(numeroMes)}
                      className={`rounded-sm py-2 text-sm capitalize transition-colors duration-fast ease-out ${
                        selecionado
                          ? "bg-accent text-text-onAccent"
                          : "text-text-primary hover:bg-surface-4"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}
