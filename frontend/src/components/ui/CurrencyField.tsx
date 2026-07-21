import { useId, useState } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";
import { decimalStringToDigits, digitsToDecimalString, formatDigitsAsFixedDecimal, onlyDigits } from "../../utils/mask";

export interface CurrencyFieldProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * `MoneyInput` de docs/design-system.md (seção 15) / `CurrencyField` no
 * vocabulário pedido nesta etapa: valor RHF é sempre a string decimal que
 * o backend espera (`"1234.56"`, nunca `number` — arquitetura-frontend.md,
 * seção 12), a máscara opera sobre dígitos puros ("digitação de
 * calculadora": os últimos 2 dígitos são sempre centavos). Alinhamento
 * flip left/right em foco/blur, design-system.md, seção 15.
 */
export function CurrencyField({
  name,
  label,
  optional,
  description,
  placeholder = "0,00",
  disabled,
  className = "",
}: CurrencyFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [focado, setFocado] = useState(false);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const digitos = decimalStringToDigits(field.value ?? "", 2);
        const display = digitos ? formatDigitsAsFixedDecimal(digitos, 2) : "";

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-body text-text-tertiary">
                R$
              </span>
              <Input
                id={id}
                name={name}
                ref={field.ref}
                inputMode="decimal"
                value={display}
                onChange={(event) => {
                  const digitosNovos = onlyDigits(event.target.value).slice(0, 13);
                  field.onChange(digitsToDecimalString(digitosNovos, 2));
                }}
                onFocus={() => setFocado(true)}
                onBlur={() => {
                  setFocado(false);
                  field.onBlur();
                }}
                disabled={disabled}
                hasError={!!error}
                placeholder={placeholder}
                className={`pl-9 font-mono tabular ${focado ? "text-left" : "text-right"} ${className}`}
              />
            </div>
          </FormField>
        );
      }}
    />
  );
}
