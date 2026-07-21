import { useId, useState } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { DateInput } from "./DateInput";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";
import { digitsToTimeDisplay, joinIsoDateTime, onlyDigits, splitIsoDateTime, timeDigitsToValue } from "../../utils/mask";

export interface DateTimeFieldProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  disabled?: boolean;
  className?: string;
}

/** Combina `DateInput` (data) + um campo de hora mascarado `HH:MM` num só
 * valor RHF: datetime local ISO `"AAAA-MM-DDTHH:MM"` (string vazia se
 * qualquer uma das duas partes estiver incompleta — nunca um valor
 * parcial). O campo de hora não vira um componente próprio (`TimeInput`)
 * porque não há um segundo consumidor além deste nesta etapa — mascarar
 * 4 dígitos é simples o bastante para ficar inline sem perder clareza. */
export function DateTimeField({ name, label, optional, description, disabled, className }: DateTimeFieldProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [horaDigitos, setHoraDigitos] = useState("");

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const { date: dataAtual, time: horaAtual } = splitIsoDateTime(field.value ?? "");
        const horaExibida = horaDigitos || onlyDigits(horaAtual);

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <div className="flex gap-2">
              <DateInput
                id={id}
                name={name}
                value={dataAtual}
                onValueChange={(novaData) => field.onChange(joinIsoDateTime(novaData, horaAtual))}
                onBlur={field.onBlur}
                hasError={!!error}
                disabled={disabled}
                className={`flex-[2] ${className ?? ""}`}
              />
              <Input
                inputMode="numeric"
                autoComplete="off"
                placeholder="HH:MM"
                value={digitsToTimeDisplay(horaExibida)}
                onChange={(event) => {
                  const novosDigitos = onlyDigits(event.target.value).slice(0, 4);
                  setHoraDigitos(novosDigitos);
                  const horaValida = timeDigitsToValue(novosDigitos);
                  field.onChange(joinIsoDateTime(dataAtual, horaValida));
                }}
                onBlur={field.onBlur}
                disabled={disabled}
                hasError={!!error}
                className="flex-1 font-mono tabular"
              />
            </div>
          </FormField>
        );
      }}
    />
  );
}
