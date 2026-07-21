import { useId, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useController, useFormContext } from "react-hook-form";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { DURATION, EASE } from "../../lib/motion";
import { FormField } from "./FormField";
import { Checkbox } from "./Checkbox";
import { Badge } from "./Badge";
import { useFloatingPanel } from "../../hooks/useFloatingPanel";
import { getFieldErrorMessage } from "../../utils/formPath";
import type { SelectOption } from "./Select";

export interface MultiSelectFieldProps {
  name: string;
  label: string;
  options: SelectOption[];
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  /** Personaliza o chip de cada opção selecionada — usado por
   * `TagMultiSelect` para mostrar a cor real da tag (`TagBadge`) em vez do
   * `Badge` genérico `tone="accent"`. Omitido mantém o comportamento
   * padrão (texto puro em um `Badge`). */
  renderChip?: (option: SelectOption) => ReactNode;
}

/**
 * Seleção múltipla — valor RHF é `string[]`. Um `Checkbox` por opção. O
 * gatilho mostra as opções escolhidas como `Badge`s truncados (nunca uma
 * lista longa de texto solta) — quando não cabe, resume para "N
 * selecionados".
 *
 * Painel portado para `document.body` com `position: fixed`
 * (`useFloatingPanel`) desde o Refinamento de Pickers/Performance —
 * mesma correção de `RichPicker`/`SearchSelect`/`Select`/`ColumnVisibility`
 * (antes, cada um duplicava seu próprio `useEffect` de clique-fora/`Esc`,
 * dívida técnica já registrada em `docs/analise-arquitetural-overlays.md`,
 * seção 7).
 */
export function MultiSelectField({
  name,
  label,
  options,
  optional,
  description,
  placeholder = "Selecione",
  disabled = false,
  className = "",
  renderChip,
}: MultiSelectFieldProps) {
  const { control, formState } = useFormContext();
  const { field } = useController({ control, name });
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [open, setOpen] = useState(false);

  // `field.onBlur()` só roda ao FECHAR o popover (clique fora, Esc, ou
  // reabrir/clicar de novo no gatilho) — nunca ligado ao `blur` nativo do
  // botão. Como cada `Checkbox` interno é um `<input>` nativamente
  // focável, um clique numa opção reproduziria a mesma corrida de
  // `DateInput.tsx` (mousedown tira o foco do gatilho, disparando
  // validação contra o valor ainda antigo, antes do `toggle()` rodar) se
  // `onBlur` estivesse ligado ao gatilho. Aqui isso é ainda mais
  // apropriado: seleção múltipla fica aberta para vários cliques, então
  // validar só quando a interação inteira termina (fechamento) é o
  // comportamento correto, não só uma correção de bug.
  function close() {
    setOpen(false);
    field.onBlur();
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLDivElement>(open, close);

  const selecionados: string[] = field.value ?? [];

  function toggle(value: string) {
    const proximo = selecionados.includes(value)
      ? selecionados.filter((v) => v !== value)
      : [...selecionados, value];
    field.onChange(proximo);
  }

  return (
    <FormField id={id} label={label} optional={optional} description={description} error={error}>
      <div ref={anchorRef} className={`relative ${className}`}>
        <button
          type="button"
          id={id}
          name={name}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          onClick={() => (open ? close() : setOpen(true))}
          className={`flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-sm border bg-surface-2 px-3 py-1.5 text-body transition-colors duration-fast ease-out disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
            error ? "border-negative" : "border-border focus-visible:border-accent"
          }`}
        >
          {selecionados.length === 0 ? (
            <span className="text-text-tertiary">{placeholder}</span>
          ) : selecionados.length <= 3 ? (
            selecionados.map((value) => {
              const option = options.find((o) => o.value === value);
              if (renderChip && option) return <span key={value}>{renderChip(option)}</span>;
              return (
                <Badge key={value} tone="accent">
                  {option?.label ?? value}
                </Badge>
              );
            })
          ) : (
            <Badge tone="accent">{selecionados.length} selecionados</Badge>
          )}
          <ChevronDown
            size={16}
            className={`ml-auto shrink-0 text-text-tertiary transition-transform duration-fast ease-out ${open ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </button>

        {createPortal(
          <AnimatePresence>
            {open && rect && (
              <motion.div
                ref={panelRef}
                role="listbox"
                aria-multiselectable="true"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
                exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
                style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
                className="z-[var(--z-tier1)] max-h-[min(60vh,420px)] overflow-auto rounded-md border border-border bg-surface-3 p-1 shadow-md"
              >
                {options.length === 0 && (
                  <p className="px-2 py-1.5 text-sm text-text-tertiary">Nenhuma opção</p>
                )}
                {options.map((option) => (
                  <label
                    key={option.value}
                    role="option"
                    aria-selected={selecionados.includes(option.value)}
                    className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-text-primary hover:bg-surface-4"
                  >
                    <Checkbox checked={selecionados.includes(option.value)} onChange={() => toggle(option.value)} />
                    {option.label}
                  </label>
                ))}
              </motion.div>
            )}
          </AnimatePresence>,
          document.body,
        )}
      </div>
    </FormField>
  );
}
