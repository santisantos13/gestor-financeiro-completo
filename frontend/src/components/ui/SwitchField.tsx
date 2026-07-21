import { useId } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { Switch } from "./Switch";
import { FormError } from "./FormError";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface SwitchFieldProps {
  name: string;
  label: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

/** `Switch` não é um `<input>` nativo (é um `<button role="switch">`),
 * então precisa de `Controller` em vez de `register` — mesmo padrão de
 * qualquer campo "composto" desta etapa. */
export function SwitchField({ name, label, description, disabled, className = "" }: SwitchFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between gap-4">
        <label htmlFor={id} className="text-sm text-text-primary">
          {label}
          {description && <span className="mt-0.5 block text-sm text-text-tertiary">{description}</span>}
        </label>
        <Controller
          control={control}
          name={name}
          render={({ field }) => (
            <Switch
              id={id}
              checked={!!field.value}
              onCheckedChange={field.onChange}
              disabled={disabled}
              aria-label={label}
            />
          )}
        />
      </div>
      <FormError message={error} />
    </div>
  );
}
