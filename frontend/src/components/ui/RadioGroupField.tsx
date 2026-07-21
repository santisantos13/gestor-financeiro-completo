import { useId } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { Radio } from "./Radio";
import { FormError } from "./FormError";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface RadioGroupOption {
  value: string;
  label: string;
  description?: string;
}

export interface RadioGroupFieldProps {
  name: string;
  label: string;
  options: RadioGroupOption[];
  optional?: boolean;
  /** Empilha as opções lado a lado em vez de uma por linha — só faz
   * sentido com poucas opções curtas (ex. Sim/Não). */
  inline?: boolean;
  className?: string;
}

/** `fieldset`/`legend` semânticos (acessibilidade de grupo de rádio —
 * leitor de tela anuncia o grupo inteiro, não cada opção isolada). */
export function RadioGroupField({
  name,
  label,
  options,
  optional,
  inline = false,
  className = "",
}: RadioGroupFieldProps) {
  const { control, formState } = useFormContext();
  const groupId = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <fieldset className={`space-y-2 ${className}`}>
          <legend className="text-sm font-medium text-text-secondary">
            {label}
            {optional && <span className="ml-1 font-normal text-text-tertiary">(opcional)</span>}
          </legend>
          <div className={inline ? "flex flex-wrap gap-4" : "space-y-2"}>
            {options.map((option, index) => {
              const optionId = `${groupId}-${index}`;
              return (
                <label key={option.value} htmlFor={optionId} className="flex cursor-pointer items-start gap-2">
                  <Radio
                    id={optionId}
                    name={name}
                    value={option.value}
                    checked={field.value === option.value}
                    onChange={() => field.onChange(option.value)}
                    onBlur={field.onBlur}
                    className="mt-0.5"
                  />
                  <span className="text-sm text-text-primary">
                    {option.label}
                    {option.description && (
                      <span className="mt-0.5 block text-sm text-text-tertiary">{option.description}</span>
                    )}
                  </span>
                </label>
              );
            })}
          </div>
          <FormError message={error} />
        </fieldset>
      )}
    />
  );
}
