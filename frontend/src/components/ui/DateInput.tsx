import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";
import { DURATION, EASE } from "../../lib/motion";
import { useFloatingPanel } from "../../hooks/useFloatingPanel";
import { Input } from "./Input";
import { dateDigitsToIso, digitsToDateDisplay, isoToDateDigits, onlyDigits } from "../../utils/mask";

export interface DateInputProps {
  id?: string;
  name?: string;
  /** ISO "AAAA-MM-DD", ou "" quando vazio — nunca `Date` (mesma convenção
   * do backend, que serializa `date` como string ISO). */
  value: string;
  onValueChange: (value: string) => void;
  onBlur?: () => void;
  hasError?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

const NOMES_MES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];
const DIAS_SEMANA = ["D", "S", "T", "Q", "Q", "S", "S"];

/**
 * `DateInput` puro de docs/design-system.md (seção 15): input mascarado
 * `DD/MM/AAAA` + ícone `Calendar` que abre um popover de calendário custom
 * — nunca `<input type=date>` nativo, cujo visual não é controlável
 * (mesma seção). Base compartilhada de `DateField`/`DateTimeField` (Etapa
 * F5) — o usuário pode digitar a data OU escolher no calendário,
 * mantendo os dois sincronizados a partir da mesma fonte de verdade
 * (`value`, sempre ISO).
 *
 * Painel portado para `document.body` com `position: fixed`
 * (`useFloatingPanel`) desde a Estabilização de Overlays — este era o
 * único popover do projeto ainda com `position: absolute` e um
 * `useEffect` próprio de clique-fora/`Esc`, esquecido na migração anterior
 * (Refinamento de Pickers/Performance). Mesmo bug de "scroll dentro de
 * scroll"/clipping que afetava `RichPicker`/`SearchSelect` antes daquela
 * correção também afetava este calendário (usado por `DateField`, campo
 * "Data" de Transação e "Data do pagamento" de Fatura) — agora
 * consistente com todo o resto da família.
 */
export function DateInput({
  id,
  name,
  value,
  onValueChange,
  onBlur,
  hasError,
  disabled,
  placeholder = "DD/MM/AAAA",
  className = "",
}: DateInputProps) {
  const [digitos, setDigitos] = useState(() => isoToDateDigits(value));
  const [open, setOpen] = useState(false);
  const [mesVisivel, setMesVisivel] = useState(() => {
    const [anoStr, mesStr] = (value || new Date().toISOString().slice(0, 10)).split("-");
    return { ano: Number(anoStr), mes: Number(mesStr) - 1 };
  });

  function close() {
    setOpen(false);
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLDivElement>(open, close, {
    panelWidth: () => 256,
  });

  useEffect(() => {
    setDigitos(isoToDateDigits(value));
  }, [value]);

  function handleTextChange(event: React.ChangeEvent<HTMLInputElement>) {
    const novosDigitos = onlyDigits(event.target.value).slice(0, 8);
    setDigitos(novosDigitos);
    if (novosDigitos.length === 0) {
      onValueChange("");
      return;
    }
    const iso = dateDigitsToIso(novosDigitos);
    if (iso) onValueChange(iso);
  }

  function selectDay(dia: number) {
    const iso = `${String(mesVisivel.ano).padStart(4, "0")}-${String(mesVisivel.mes + 1).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
    onValueChange(iso);
    setOpen(false);
  }

  const diasNoMes = new Date(mesVisivel.ano, mesVisivel.mes + 1, 0).getDate();
  const primeiroDiaSemana = new Date(mesVisivel.ano, mesVisivel.mes, 1).getDay();

  return (
    <div ref={anchorRef} className={`relative ${className}`}>
      <Input
        id={id}
        name={name}
        inputMode="numeric"
        autoComplete="off"
        value={digitsToDateDisplay(digitos)}
        onChange={handleTextChange}
        onFocus={() => setOpen(true)}
        onBlur={onBlur}
        disabled={disabled}
        hasError={hasError}
        placeholder={placeholder}
        className="pr-9 font-mono tabular"
      />
      <button
        type="button"
        tabIndex={-1}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-label="Abrir calendário"
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary transition-colors duration-fast ease-out hover:text-text-primary disabled:cursor-not-allowed"
      >
        <CalendarIcon size={16} aria-hidden="true" />
      </button>

      {createPortal(
        <AnimatePresence>
          {open && rect && (
            <motion.div
              ref={panelRef}
              // Impede o mousedown padrão de tirar o foco do input ANTES do
              // clique no dia terminar de rodar - causa raiz real do "preciso
              // selecionar duas vezes" (2026-07-20). Sequência sem isto:
              // mousedown num botão do calendário já dispara blur no input
              // (RHF valida o valor ainda vazio/antigo, mode "onBlur") antes
              // do click chamar selectDay/onValueChange; a validação do blur
              // (stale) podia resolver DEPOIS da validação do onChange
              // (zodResolver é assíncrono), sobrescrevendo o campo válido de
              // volta para "erro". Com o foco nunca saindo do input durante
              // a seleção, só existe uma validação (a do valor final certo).
              onMouseDown={(event) => event.preventDefault()}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
              exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
              style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
              className="z-[var(--z-tier1)] rounded-lg border border-border bg-surface-3 p-3 shadow-md"
            >
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() =>
                  setMesVisivel((m) => (m.mes === 0 ? { ano: m.ano - 1, mes: 11 } : { ano: m.ano, mes: m.mes - 1 }))
                }
                aria-label="Mês anterior"
                className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary"
              >
                <ChevronLeft size={16} aria-hidden="true" />
              </button>
              <span className="text-sm font-medium text-text-primary">
                {NOMES_MES[mesVisivel.mes]} {mesVisivel.ano}
              </span>
              <button
                type="button"
                onClick={() =>
                  setMesVisivel((m) => (m.mes === 11 ? { ano: m.ano + 1, mes: 0 } : { ano: m.ano, mes: m.mes + 1 }))
                }
                aria-label="Próximo mês"
                className="rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary"
              >
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            </div>
            <div className="mt-2 grid grid-cols-7 gap-1 text-center text-micro text-text-tertiary">
              {DIAS_SEMANA.map((dia, index) => (
                <span key={index}>{dia}</span>
              ))}
            </div>
            <div className="mt-1 grid grid-cols-7 gap-1">
              {Array.from({ length: primeiroDiaSemana }).map((_, index) => (
                <span key={`vazio-${index}`} />
              ))}
              {Array.from({ length: diasNoMes }).map((_, index) => {
                const dia = index + 1;
                const iso = `${String(mesVisivel.ano).padStart(4, "0")}-${String(mesVisivel.mes + 1).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
                const selecionado = iso === value;
                return (
                  <button
                    key={dia}
                    type="button"
                    onClick={() => selectDay(dia)}
                    className={`rounded-sm py-1 text-sm transition-colors duration-fast ease-out ${
                      selecionado ? "bg-accent text-text-onAccent" : "text-text-primary hover:bg-surface-4"
                    }`}
                  >
                    {dia}
                  </button>
                );
              })}
            </div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
