import { useId } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";
import { decimalStringToDigits, digitsToDecimalString, formatDigitsAsFixedDecimal, onlyDigits } from "../../utils/mask";

export interface PercentageFieldProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/** Mesma mecânica de `CurrencyField` (dígitos → decimal de 2 casas), sem
 * separador de milhar (percentuais deste sistema nunca passam de 3 dígitos
 * inteiros) e com sufixo "%" em vez de prefixo "R$". Valor RHF é a string
 * decimal ("42.50"), nunca dividida por 100 aqui — cada consumidor decide
 * a escala esperada pelo backend (ver `utils/format.ts`,
 * `formatPercent`). */
export function PercentageField({
  name,
  label,
  optional,
  description,
  placeholder = "0,00",
  disabled,
  className = "",
}: PercentageFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const digitos = decimalStringToDigits(field.value ?? "", 2);
        const display = digitos ? formatDigitsAsFixedDecimal(digitos, 2, false) : "";

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <div className="relative">
              <Input
                id={id}
                name={name}
                ref={field.ref}
                inputMode="decimal"
                value={display}
                onChange={(event) => {
                  const digitosNovos = onlyDigits(event.target.value).slice(0, 5);
                  field.onChange(digitsToDecimalString(digitosNovos, 2));
                }}
                onBlur={field.onBlur}
                disabled={disabled}
                hasError={!!error}
                placeholder={placeholder}
                className={`pr-8 text-right font-mono tabular ${className}`}
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-body text-text-tertiary">
                %
              </span>
            </div>
          </FormField>
        );
      }}
    />
  );
}
