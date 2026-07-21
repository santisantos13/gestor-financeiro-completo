import { useId, useMemo, useState } from "react";
import { Controller, useFormContext, type ControllerRenderProps, type FieldValues } from "react-hook-form";
import { Landmark } from "lucide-react";
import { FormField } from "./FormField";
import { RichPicker, type RichPickerItem } from "./RichPicker";
import { TODAS_INSTITUICOES_CONHECIDAS, corDeContraste } from "../../lib/institutions";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface BankPickerProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  disabled?: boolean;
  className?: string;
}

const OUTRA = "__outra__";

function Monograma({ cor, iniciais, logoUrl }: { cor: string; iniciais: string; logoUrl?: string }) {
  if (logoUrl) {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/25 p-0.5">
        <img src={logoUrl} alt="" className="h-full w-full object-contain" aria-hidden="true" />
      </span>
    );
  }
  return (
    <span
      className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold"
      style={{ backgroundColor: cor, color: corDeContraste(cor) }}
    >
      {iniciais}
    </span>
  );
}

/** Componente interno separado da `Controller` só para poder usar `useState`
 * sem violar as regras de hooks (a render prop do `Controller` é chamada
 * durante o render de `BankPicker`, então o estado de "modo texto livre"
 * precisa viver num componente próprio). */
function BankPickerField({
  field,
  id,
  name,
  label,
  error,
  disabled,
  className,
}: {
  field: ControllerRenderProps<FieldValues, string>;
  id: string;
  name: string;
  label: string;
  error?: string;
  disabled: boolean;
  className: string;
}) {
  const conhecida = TODAS_INSTITUICOES_CONHECIDAS.find((inst) => inst.nome === field.value);
  const [modoCustom, setModoCustom] = useState(() => !!field.value && !conhecida);

  const items = useMemo<RichPickerItem<string>[]>(
    () => [
      ...TODAS_INSTITUICOES_CONHECIDAS.map((inst) => ({
        value: inst.nome,
        label: inst.nome,
        keywords: inst.aliases,
        render: <Monograma cor={inst.cor} iniciais={inst.iniciais} logoUrl={inst.logoUrl} />,
      })),
      {
        value: OUTRA,
        label: "Outra instituição",
        render: <Landmark size={16} className="text-text-tertiary" aria-hidden="true" />,
      },
    ],
    [],
  );

  if (modoCustom) {
    return (
      <div className="flex items-center gap-2">
        <input
          id={id}
          name={name}
          value={field.value ?? ""}
          onChange={(event) => field.onChange(event.target.value)}
          onBlur={field.onBlur}
          disabled={disabled}
          placeholder="Digite o nome da instituição"
          aria-invalid={!!error || undefined}
          className={`h-9 w-full rounded-sm border bg-surface-2 px-3 text-body text-text-primary placeholder:text-text-tertiary transition-colors duration-fast ease-out focus-visible:border-accent disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
            error ? "border-negative" : "border-border"
          }`}
        />
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            setModoCustom(false);
            field.onChange("");
          }}
          className="shrink-0 whitespace-nowrap text-caption text-text-tertiary underline-offset-2 transition-colors duration-fast ease-out hover:text-text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50"
        >
          Ver lista
        </button>
      </div>
    );
  }

  return (
    <RichPicker
      id={id}
      name={name}
      layout="list"
      items={items}
      value={field.value || null}
      onChange={(valor) => {
        if (valor === OUTRA) {
          setModoCustom(true);
          field.onChange("");
          return;
        }
        field.onChange(valor);
      }}
      onBlur={field.onBlur}
      disabled={disabled}
      hasError={!!error}
      placeholder="Selecionar instituição"
      searchPlaceholder="Buscar instituição..."
      aria-label={label}
      className={className}
    />
  );
}

/**
 * Rich Picker novo — Etapa F10 (`docs/analise-arquitetural-rich-pickers.md`,
 * seção 4). Diferente de `IconPicker`/`ColorPicker`, não evolui um campo
 * existente: `instituicao` era `TextField` livre em `ContaFormDialog`/
 * `CartaoFormDialog`, sem seleção visual nenhuma. Consome
 * `lib/institutions.ts` — **preserva a liberdade de texto livre** via a
 * opção "Outra instituição", que revela um campo de texto (o backend
 * aceita qualquer string em `instituicao`, então o picker nunca pode virar
 * uma lista fechada).
 */
export function BankPicker({ name, label, optional, description, disabled = false, className = "" }: BankPickerProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <FormField id={id} label={label} optional={optional} description={description} error={error}>
          <BankPickerField
            field={field}
            id={id}
            name={name}
            label={label}
            error={error}
            disabled={disabled}
            className={className}
          />
        </FormField>
      )}
    />
  );
}
