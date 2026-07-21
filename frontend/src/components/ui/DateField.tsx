import { useId } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { DateInput } from "./DateInput";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface DateFieldProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/** Wrapper RHF do `DateInput` puro — valor é sempre ISO `"AAAA-MM-DD"`,
 * igual ao campo `date` do backend (docs/analise-arquitetural-frontend.md,
 * seção 12). */
export function DateField({ name, label, optional, description, placeholder, disabled, className }: DateFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <FormField id={id} label={label} optional={optional} description={description} error={error}>
          <DateInput
            id={id}
            name={name}
            value={field.value ?? ""}
            onValueChange={field.onChange}
            onBlur={field.onBlur}
            hasError={!!error}
            disabled={disabled}
            placeholder={placeholder}
            className={className}
          />
        </FormField>
      )}
    />
  );
}
