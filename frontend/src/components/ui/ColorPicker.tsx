import { useId, useMemo } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { RichPicker, type RichPickerItem } from "./RichPicker";
import { PALETA_SUGESTAO, eCorHexValida } from "../../lib/color";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface ColorPickerProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Evolução de `ColorField` (Etapa F10, Rich Pickers —
 * `docs/analise-arquitetural-rich-pickers.md`, seção 3): mesmo contrato de
 * fora, agora sobre `RichPicker` — painel maior, agrupado por família de
 * matiz (`PALETA_SUGESTAO[].grupo`). **Mantém o input de hex livre ao lado
 * do gatilho** (não é substituído pelo picker — quem já sabe o hex exato
 * continua podendo digitá-lo direto, mesmo comportamento de sempre). A
 * busca do `RichPicker` filtra por `grupo` (ex. digitar "verde" restringe
 * à família verde) via `keywords`, já que o "label" de cada item é só o
 * próprio hex (sem nome natural por swatch individual).
 */
export function ColorPicker({ name, label, optional, description, disabled = false, className = "" }: ColorPickerProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  const items = useMemo<RichPickerItem<string>[]>(
    () =>
      PALETA_SUGESTAO.map((sugestao) => ({
        value: sugestao.cor,
        label: sugestao.cor,
        group: sugestao.grupo,
        keywords: [sugestao.grupo],
        render: <span className="block h-6 w-6 rounded-full border border-border-subtle" style={{ backgroundColor: sugestao.cor }} />,
      })),
    [],
  );

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const valorValido = eCorHexValida(field.value ?? "");

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <div className="flex items-center gap-2">
              <RichPicker
                id={id}
                name={name}
                layout="grid"
                items={items}
                value={valorValido ? field.value : null}
                onChange={field.onChange}
                onBlur={field.onBlur}
                disabled={disabled}
                hasError={!!error}
                placeholder="Paleta"
                searchPlaceholder="Buscar cor (ex. verde)..."
                searchThreshold={0}
                aria-label={`${label} — paleta de sugestões`}
                className="w-28 shrink-0"
                renderPreview={() => (
                  <div className="flex items-center gap-2 text-text-primary">
                    <span
                      className="block h-6 w-6 shrink-0 rounded-full border border-border-subtle"
                      style={{ backgroundColor: valorValido ? field.value : "var(--color-surface-2)" }}
                    />
                    <span className="font-mono text-sm">{valorValido ? field.value : "Nenhuma cor selecionada"}</span>
                  </div>
                )}
              />
              <input
                value={field.value ?? ""}
                onChange={(event) => field.onChange(event.target.value)}
                onBlur={field.onBlur}
                disabled={disabled}
                placeholder="#34D399"
                maxLength={7}
                aria-label={`${label} — hex livre`}
                aria-invalid={!!error || undefined}
                className={`h-9 w-full rounded-sm border bg-surface-2 px-3 font-mono text-body text-text-primary placeholder:text-text-tertiary transition-colors duration-fast ease-out focus-visible:border-accent disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
                  error ? "border-negative" : "border-border"
                }`}
              />
              {field.value && (
                <button
                  type="button"
                  onClick={() => field.onChange("")}
                  disabled={disabled}
                  className="shrink-0 text-caption text-text-tertiary underline-offset-2 transition-colors duration-fast ease-out hover:text-text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Limpar
                </button>
              )}
            </div>
          </FormField>
        );
      }}
    />
  );
}
