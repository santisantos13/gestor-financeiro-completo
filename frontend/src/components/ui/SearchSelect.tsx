import { useDeferredValue, useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useController, useFormContext } from "react-hook-form";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, Search } from "lucide-react";
import { DURATION, EASE } from "../../lib/motion";
import { FormField } from "./FormField";
import { useFloatingPanel } from "../../hooks/useFloatingPanel";
import { destacarTrecho } from "../../utils/highlight";
import { getFieldErrorMessage } from "../../utils/formPath";
import type { SelectOption } from "./Select";

export interface SearchSelectProps {
  name: string;
  label: string;
  options: SelectOption[];
  optional?: boolean;
  description?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  /** Reservado para uma versão futura assíncrona (ex. buscar categoria no
   * servidor) — hoje o filtro é sempre client-side sobre `options`
   * (docs/analise-arquitetural-frontend.md, seção 13, já decidido para
   * todo o projeto). */
  loading?: boolean;
  className?: string;
}

/**
 * Base genérica dos selects "inteligentes" de domínio
 * (`CategorySelect`/`AccountSelect`/`CardSelect`, docs/analise-arquitetural-frontend.md,
 * seção 12): combobox com busca-enquanto-digita client-side.
 *
 * Painel portado para `document.body` com `position: fixed`
 * (`useFloatingPanel`) desde o Refinamento de Pickers/Performance
 * (`docs/analise-arquitetural-refinamento-pickers-performance.md`, seção
 * 2) — escapa do clipping de um `FormDialog` ancestral, mesma correção
 * aplicada a `RichPicker`/`MultiSelectField`/`Select`/`ColumnVisibility`.
 */
export function SearchSelect({
  name,
  label,
  options,
  optional,
  description,
  placeholder = "Selecione",
  searchPlaceholder = "Buscar...",
  disabled = false,
  loading = false,
  className = "",
}: SearchSelectProps) {
  const { control, formState } = useFormContext();
  const { field } = useController({ control, name });
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const searchRef = useRef<HTMLInputElement>(null);

  // Fechamento é o ÚNICO lugar que chama `field.onBlur()` — nunca ligado
  // ao `blur` nativo do botão-gatilho. Antes, `onBlur={field.onBlur}` no
  // botão disparava validação (RHF `mode: "onBlur"`) assim que o
  // `useEffect` abaixo movia o foco para o campo de busca ao ABRIR o
  // popover — ou seja, a validação rodava contra o valor ainda vazio ANTES
  // de qualquer seleção, e podia resolver (assíncrona, zodResolver) depois
  // da validação do `onChange`, deixando "Selecione a conta" preso mesmo
  // após escolher — precisava selecionar de novo para sumir. Mesma causa
  // raiz de `DateInput.tsx`/`Select.tsx` (2026-07-20).
  function close() {
    setOpen(false);
    field.onBlur();
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLDivElement>(open, close);

  const filtradas = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, deferredQuery]);

  useEffect(() => {
    if (!open) return;
    // `setTimeout(0)`: o campo de busca só existe no DOM depois que o
    // painel portado monta — focar no mesmo tick perderia o foco.
    const t = setTimeout(() => searchRef.current?.focus(), 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const selecionado = options.find((o) => o.value === field.value) ?? null;

  return (
    <FormField id={id} label={label} optional={optional} description={description} error={error}>
      <div ref={anchorRef} className="relative">
        <button
          type="button"
          id={id}
          name={name}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          onClick={() => {
            setQuery("");
            setOpen((v) => !v);
          }}
          className={`flex h-9 w-full items-center justify-between rounded-sm border bg-surface-2 px-3 text-body transition-colors duration-fast ease-out disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
            error ? "border-negative" : "border-border focus-visible:border-accent"
          }`}
        >
          <span className={`flex min-w-0 items-center gap-2 ${selecionado ? "text-text-primary" : "text-text-tertiary"}`}>
            {selecionado?.render && <span className="shrink-0">{selecionado.render}</span>}
            <span className="truncate">
              {loading ? "Carregando..." : selecionado ? selecionado.label : placeholder}
            </span>
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
              <motion.div
                ref={panelRef}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
                exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
                style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
                className="z-[var(--z-tier1)] flex max-h-[min(60vh,420px)] flex-col overflow-hidden rounded-md border border-border bg-surface-3 shadow-md"
              >
                <div className="relative shrink-0 border-b border-border-subtle p-1.5">
                  <Search
                    size={14}
                    className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-text-tertiary"
                    aria-hidden="true"
                  />
                  <input
                    ref={searchRef}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={searchPlaceholder}
                    className="h-7 w-full rounded-sm bg-transparent pl-6 pr-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none"
                  />
                </div>
                <ul role="listbox" className="min-h-0 flex-1 overflow-y-auto p-1">
                  {filtradas.length === 0 && (
                    <li className="px-2 py-1.5 text-sm text-text-tertiary">Nenhum resultado</li>
                  )}
                  {filtradas.map((option) => (
                    <li
                      key={option.value}
                      role="option"
                      aria-selected={option.value === field.value}
                      onClick={() => {
                        field.onChange(option.value);
                        close();
                      }}
                      className={`flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors duration-fast ease-out ${
                        option.value === field.value ? "bg-accent-subtle text-accent" : "text-text-primary hover:bg-surface-4"
                      }`}
                    >
                      {option.render && <span className="shrink-0">{option.render}</span>}
                      <span className="truncate">{destacarTrecho(option.label, deferredQuery)}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>,
          document.body,
        )}
      </div>
    </FormField>
  );
}
