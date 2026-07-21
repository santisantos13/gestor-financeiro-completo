import { useId } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";
import { decimalStringToDigits, digitsToDecimalString, formatDigitsAsFixedDecimal, onlyDigits } from "../../utils/mask";

export interface NumberFieldProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  /** Casas decimais aceitas — 0 (padrão) para contagens inteiras (ex.
   * número de parcelas), >0 para números fracionários genéricos que não
   * são nem moeda nem percentual. */
  decimalPlaces?: number;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/** Número genérico com separador de milhar — mesma família de máscara de
 * `CurrencyField`/`PercentageField`, mas sem prefixo/sufixo e com valor
 * RHF já como `number` (não string decimal), por ser o formato mais
 * natural para contagens/quantidades. */
export function NumberField({
  name,
  label,
  optional,
  description,
  decimalPlaces = 0,
  placeholder,
  disabled,
  className = "",
}: NumberFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const valorAtual = field.value === undefined || field.value === null ? "" : String(field.value);
        const digitos = decimalStringToDigits(valorAtual, decimalPlaces);
        const display = digitos ? formatDigitsAsFixedDecimal(digitos, decimalPlaces) : "";

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <Input
              id={id}
              name={name}
              ref={field.ref}
              inputMode={decimalPlaces > 0 ? "decimal" : "numeric"}
              value={display}
              onChange={(event) => {
                const digitosNovos = onlyDigits(event.target.value).slice(0, 15);
                const decimal = digitsToDecimalString(digitosNovos, decimalPlaces);
                field.onChange(decimal === "" ? undefined : Number(decimal));
              }}
              onBlur={field.onBlur}
              disabled={disabled}
              hasError={!!error}
              placeholder={placeholder}
              className={`text-right font-mono tabular ${className}`}
            />
          </FormField>
        );
      }}
    />
  );
}
