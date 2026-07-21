import { useId } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { Select, type SelectOption } from "./Select";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface SelectFieldProps {
  name: string;
  label: string;
  options: SelectOption[];
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/** Wrapper RHF (`Controller`) do `Select` genérico já existente (Etapa
 * F2) — base para os selects "inteligentes" de domínio
 * (`CategorySelect`/`AccountSelect`/etc., a partir da F6) que vão compor
 * este mesmo padrão com sua própria busca via React Query por cima. */
export function SelectField({
  name,
  label,
  options,
  optional,
  description,
  placeholder,
  disabled,
  className,
}: SelectFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <FormField id={id} label={label} optional={optional} description={description} error={error}>
          <Select
            options={options}
            value={field.value ?? null}
            onChange={field.onChange}
            onBlur={field.onBlur}
            placeholder={placeholder}
            disabled={disabled}
            hasError={!!error}
            className={className}
            aria-label={label}
            id={id}
            name={name}
          />
        </FormField>
      )}
    />
  );
}
