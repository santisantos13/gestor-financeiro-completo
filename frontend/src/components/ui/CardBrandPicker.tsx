import { useId, useMemo } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { RichPicker, type RichPickerItem } from "./RichPicker";
import { BANDEIRAS, corDeContraste } from "../../lib/bandeiras";
import { MastercardLogo, VisaLogo } from "./brandLogos";
import type { Bandeira } from "../../types/enums";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface CardBrandPickerProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  disabled?: boolean;
  className?: string;
}

/** Visa/Mastercard mostram o logo real (mesmo critério de `BandeiraBadge`),
 * sem fundo sólido - só uma borda sutil; as demais bandeiras seguem com o
 * monograma. */
function Monograma({ bandeira, cor, sigla }: { bandeira: Bandeira; cor: string; sigla: string }) {
  if (bandeira === "MASTERCARD" || bandeira === "VISA") {
    const Logo = bandeira === "MASTERCARD" ? MastercardLogo : VisaLogo;
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/25 p-0.5">
        <Logo className="h-full w-full" />
      </span>
    );
  }
  return (
    <span
      className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold"
      style={{ backgroundColor: cor, color: corDeContraste(cor) }}
    >
      {sigla}
    </span>
  );
}

/**
 * Rich Picker novo — Etapa F10 (`docs/analise-arquitetural-rich-pickers.md`,
 * seção 4). `Bandeira` é um enum FECHADO no backend (7 valores) — diferente
 * de `BankPicker`, uma lista fechada é o comportamento correto aqui, já era
 * o que `SelectField`/`BANDEIRA_OPTIONS` fazia, só sem riqueza visual.
 * `layout="list"`, sem busca (7 itens, abaixo do `searchThreshold` padrão),
 * cada linha com o monograma sobre a cor de marca real.
 */
export function CardBrandPicker({ name, label, optional, description, disabled = false, className = "" }: CardBrandPickerProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  const items = useMemo<RichPickerItem<Bandeira>[]>(
    () =>
      (Object.entries(BANDEIRAS) as [Bandeira, (typeof BANDEIRAS)[Bandeira]][]).map(([valor, info]) => ({
        value: valor,
        label: info.label,
        render: <Monograma bandeira={valor} cor={info.cor} sigla={info.sigla} />,
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
            layout="list"
            items={items}
            value={field.value ?? null}
            onChange={field.onChange}
            onBlur={field.onBlur}
            disabled={disabled}
            hasError={!!error}
            placeholder="Selecionar bandeira"
            aria-label={label}
            className={className}
          />
        </FormField>
      )}
    />
  );
}
