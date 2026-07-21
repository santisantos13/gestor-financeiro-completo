import { useId, useState } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { X } from "lucide-react";
import { FormField } from "./FormField";
import { Badge } from "./Badge";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface TagsInputProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  /** Impede duplicatas (comparação case-insensitive) — padrão `true`. */
  preventDuplicates?: boolean;
  className?: string;
}

/** Entrada de tags livres — `Enter`/`,` adiciona a tag digitada,
 * `Backspace` num campo vazio remove a última. Valor RHF é `string[]`.
 * Infraestrutura genérica (nenhuma entidade) — a versão "inteligente"
 * (`TagSelect`, que busca tags existentes do usuário via React Query) é
 * uma composição futura da F6 sobre este mesmo componente ou sobre
 * `SearchSelect`. */
export function TagsInput({
  name,
  label,
  optional,
  description,
  placeholder = "Digite e pressione Enter",
  disabled = false,
  preventDuplicates = true,
  className = "",
}: TagsInputProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [rascunho, setRascunho] = useState("");

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const tags: string[] = field.value ?? [];

        function commitDraft() {
          const valor = rascunho.trim();
          setRascunho("");
          if (!valor) return;
          if (preventDuplicates && tags.some((t) => t.toLowerCase() === valor.toLowerCase())) return;
          field.onChange([...tags, valor]);
        }

        function removeTag(index: number) {
          field.onChange(tags.filter((_, i) => i !== index));
        }

        function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
          if (event.key === "Enter" || event.key === ",") {
            event.preventDefault();
            commitDraft();
          } else if (event.key === "Backspace" && rascunho === "" && tags.length > 0) {
            removeTag(tags.length - 1);
          }
        }

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <div
              className={`flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-sm border bg-surface-2 px-2 py-1.5 transition-colors duration-fast ease-out focus-within:border-accent ${
                error ? "border-negative" : "border-border"
              } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
            >
              {tags.map((tag, index) => (
                <Badge key={`${tag}-${index}`} tone="neutral" className="gap-1 pr-1">
                  {tag}
                  {!disabled && (
                    <button
                      type="button"
                      onClick={() => removeTag(index)}
                      aria-label={`Remover ${tag}`}
                      className="rounded-full p-0.5 hover:bg-surface-4"
                    >
                      <X size={10} aria-hidden="true" />
                    </button>
                  )}
                </Badge>
              ))}
              <input
                id={id}
                name={name}
                value={rascunho}
                onChange={(event) => setRascunho(event.target.value)}
                onKeyDown={onKeyDown}
                onBlur={() => {
                  commitDraft();
                  field.onBlur();
                }}
                disabled={disabled}
                placeholder={tags.length === 0 ? placeholder : ""}
                className="min-w-[8ch] flex-1 bg-transparent py-0.5 text-body text-text-primary placeholder:text-text-tertiary focus:outline-none disabled:cursor-not-allowed"
              />
            </div>
          </FormField>
        );
      }}
    />
  );
}
