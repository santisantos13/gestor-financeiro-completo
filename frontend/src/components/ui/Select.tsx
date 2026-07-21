import { useId, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { DURATION, EASE } from "../../lib/motion";
import { useFloatingPanel } from "../../hooks/useFloatingPanel";

export interface SelectOption {
  value: string;
  label: string;
  /** Slot visual opcional (ícone, swatch de cor) — Etapa F10, Rich Pickers
   * (`docs/analise-arquitetural-rich-pickers.md`, seção 5). Renderizado à
   * esquerda do label, tanto no botão-gatilho quanto em cada linha da
   * lista. `undefined` mantém o comportamento de sempre (texto puro),
   * nenhum consumidor existente quebra. */
  render?: ReactNode;
}

export interface SelectProps {
  options: SelectOption[];
  value: string | null;
  onChange: (value: string) => void;
  /** Chamado quando o popover FECHA (seleção, Esc ou clique fora) — nunca
   * ligado ao `blur` nativo do botão-gatilho (mesmo padrão de
   * `RichPicker.onBlur`, ver docstring de `close()` abaixo: por que). */
  onBlur?: () => void;
  placeholder?: string;
  disabled?: boolean;
  hasError?: boolean;
  className?: string;
  "aria-label"?: string;
  /** Repassados para o `<button role="combobox">` de gatilho — usados por
   * `SelectField` (Etapa F5) para associar `<label htmlFor>` e para o
   * `Form` achar o campo com erro via `[name="..."]` no scroll-to-error. */
  id?: string;
  name?: string;
}

/**
 * Combobox base — mesmo visual do `Input`, painel `--color-surface-3` +
 * `--shadow-md`, item ativo com fundo `--color-accent-subtle` —
 * design-system.md, seção 14. É a base de `CategorySelect`/
 * `AccountSelect`/`CardSelect` — aqui só a mecânica genérica de
 * single-select, sem busca-enquanto-digita (isso é adicionado pelos
 * componentes compostos que usam este como base).
 *
 * Painel portado para `document.body` com `position: fixed`
 * (`useFloatingPanel`) desde o Refinamento de Pickers/Performance — mesma
 * correção de `RichPicker`/`SearchSelect`/`MultiSelectField`/
 * `ColumnVisibility`.
 */
export function Select({
  options,
  value,
  onChange,
  onBlur,
  placeholder = "Selecione",
  disabled = false,
  hasError = false,
  className = "",
  ...props
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const listboxId = useId();

  const selected = options.find((o) => o.value === value) ?? null;

  // `onBlur` é chamado só AQUI (fechamento), nunca ligado a um `blur` nativo
  // de botão — mesmo padrão de `RichPicker.close()`. Corrige o "preciso
  // selecionar duas vezes": um `blur` nativo dispararia validação (RHF
  // `mode: "onBlur"`) contra o valor ainda antigo/vazio ANTES do clique na
  // opção rodar `onChange`, e essa validação assíncrona (stale) podia
  // resolver DEPOIS da validação do `onChange`, deixando erro preso —
  // mesma causa raiz corrigida em `DateInput.tsx` (2026-07-20).
  function close() {
    setOpen(false);
    onBlur?.();
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLDivElement, HTMLUListElement>(open, close);

  function openPanel() {
    if (disabled) return;
    setActiveIndex(Math.max(0, options.findIndex((o) => o.value === value)));
    setOpen(true);
  }

  function selectOption(option: SelectOption) {
    onChange(option.value);
    close();
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (disabled) return;
    if (!open && (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      openPanel();
      return;
    }
    if (!open) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => Math.min(options.length - 1, i + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (options[activeIndex]) selectOption(options[activeIndex]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      close();
    }
  }

  return (
    <div ref={anchorRef} className={`relative ${className}`}>
      <button
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        disabled={disabled}
        onClick={() => (open ? close() : openPanel())}
        onKeyDown={onKeyDown}
        className={`flex h-9 w-full items-center justify-between rounded-sm border bg-surface-2 px-3 text-body transition-colors duration-fast ease-out disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
          hasError ? "border-negative" : "border-border focus-visible:border-accent"
        }`}
        {...props}
      >
        <span className={`flex min-w-0 items-center gap-2 ${selected ? "text-text-primary" : "text-text-tertiary"}`}>
          {selected?.render && <span className="shrink-0">{selected.render}</span>}
          <span className="truncate">{selected ? selected.label : placeholder}</span>
        </span>
        <ChevronDown
          size={16}
          className={`shrink-0 text-text-tertiary transition-transform duration-fast ease-out ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {createPortal(
        <AnimatePresence>
          {open && rect && (
            <motion.ul
              ref={panelRef}
              id={listboxId}
              role="listbox"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
              exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
              style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
              className="z-[var(--z-tier1)] max-h-[min(60vh,420px)] overflow-auto rounded-md border border-border bg-surface-3 p-1 shadow-md"
            >
              {options.length === 0 && (
                <li className="px-2 py-1.5 text-sm text-text-tertiary">Nenhuma opção</li>
              )}
              {options.map((option, index) => (
                <li
                  key={option.value}
                  role="option"
                  aria-selected={option.value === value}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectOption(option)}
                  className={`flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors duration-fast ease-out ${
                    index === activeIndex ? "bg-accent-subtle text-accent" : "text-text-primary"
                  }`}
                >
                  {option.render && <span className="shrink-0">{option.render}</span>}
                  <span className="truncate">{option.label}</span>
                </li>
              ))}
            </motion.ul>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
