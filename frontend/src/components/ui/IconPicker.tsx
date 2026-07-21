import { useId, useMemo } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { RichPicker, type RichPickerItem } from "./RichPicker";
import { TODOS_ICONES } from "../../lib/icons";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface IconPickerProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Evolução de `IconField` (Etapa F10, Rich Pickers —
 * `docs/analise-arquitetural-rich-pickers.md`, seção 3): mesmo contrato de
 * fora (`name`/`label`/`optional`/`description`/`disabled`, wrapper de
 * `Controller`/`FormField` idêntico), mas por dentro compõe `RichPicker`
 * em vez de reimplementar popover/grid do zero — painel maior, busca
 * instantânea, agrupado por `IconInfo.grupo`, navegação por teclado
 * completa. Convenção de dado salvo inalterada: o valor continua sendo o
 * `id` de um ícone do registry curado (`lib/icons.ts`).
 */
export function IconPicker({ name, label, optional, description, disabled = false, className = "" }: IconPickerProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  const items = useMemo<RichPickerItem<string>[]>(
    () =>
      TODOS_ICONES.map((icone) => ({
        value: icone.id,
        label: icone.label,
        group: icone.grupo,
        render: <icone.Icon size={16} aria-hidden="true" />,
      })),
    [],
  );

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <FormField id={id} label={label} optional={optional} description={description} error={error}>
          <RichPicker
            id={id}
            name={name}
            layout="grid"
            items={items}
            value={field.value ?? null}
            onChange={field.onChange}
            onBlur={field.onBlur}
            disabled={disabled}
            hasError={!!error}
            placeholder="Selecionar ícone"
            searchPlaceholder="Buscar ícone..."
            aria-label={label}
            className={className}
          />
        </FormField>
      )}
    />
  );
}
