import { useId, useRef, useState } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { File as FileIcon, Upload, X } from "lucide-react";
import { FormField } from "./FormField";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface FileUploadProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  className?: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Área de arrastar-e-soltar + seleção por clique — valor RHF é `File[]`.
 * **Infraestrutura apenas**: não envia nada, não conhece `Anexo` (a
 * entidade real do backend) — só junta arquivos localmente e devolve a
 * lista. A integração real (upload via `AnexoService`, associação a uma
 * `Transacao`) é trabalho de uma etapa futura de CRUD; construir isso
 * agora seria antecipar contrato de API que ainda não foi decidido para
 * upload de arquivo.
 */
export function FileUpload({
  name,
  label,
  optional,
  description,
  accept,
  multiple = true,
  disabled = false,
  className = "",
}: FileUploadProps) {
  const { control, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [arrastando, setArrastando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const arquivos: File[] = field.value ?? [];

        function addFiles(lista: FileList | null) {
          if (!lista || lista.length === 0) return;
          const novos = Array.from(lista);
          field.onChange(multiple ? [...arquivos, ...novos] : novos.slice(0, 1));
        }

        function removeFile(index: number) {
          field.onChange(arquivos.filter((_, i) => i !== index));
        }

        return (
          <FormField id={id} label={label} optional={optional} description={description} error={error}>
            <div
              role="button"
              tabIndex={disabled ? -1 : 0}
              onClick={() => !disabled && inputRef.current?.click()}
              onKeyDown={(event) => {
                if (!disabled && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  inputRef.current?.click();
                }
              }}
              onDragOver={(event) => {
                event.preventDefault();
                if (!disabled) setArrastando(true);
              }}
              onDragLeave={() => setArrastando(false)}
              onDrop={(event) => {
                event.preventDefault();
                setArrastando(false);
                if (!disabled) addFiles(event.dataTransfer.files);
              }}
              className={`flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-6 text-center transition-colors duration-fast ease-out ${
                disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
              } ${
                arrastando ? "border-accent bg-accent-subtle" : error ? "border-negative" : "border-border-strong hover:border-border-strong hover:bg-surface-2"
              }`}
            >
              <Upload size={20} className="text-text-tertiary" aria-hidden="true" />
              <p className="text-sm text-text-secondary">
                Arraste arquivos aqui ou <span className="text-accent">clique para selecionar</span>
              </p>
              <input
                ref={inputRef}
                id={id}
                name={name}
                type="file"
                accept={accept}
                multiple={multiple}
                disabled={disabled}
                onChange={(event) => addFiles(event.target.files)}
                onBlur={field.onBlur}
                className="sr-only"
              />
            </div>

            {arquivos.length > 0 && (
              <ul className="mt-2 space-y-1.5">
                {arquivos.map((arquivo, index) => (
                  <li
                    key={`${arquivo.name}-${index}`}
                    className="flex items-center justify-between gap-2 rounded-sm border border-border-subtle bg-surface-2 px-2.5 py-1.5 text-sm"
                  >
                    <span className="flex min-w-0 items-center gap-2 text-text-primary">
                      <FileIcon size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                      <span className="truncate">{arquivo.name}</span>
                      <span className="shrink-0 text-text-tertiary">{formatBytes(arquivo.size)}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      aria-label={`Remover ${arquivo.name}`}
                      className="shrink-0 rounded-sm p-1 text-text-tertiary hover:bg-surface-3 hover:text-text-primary"
                    >
                      <X size={14} aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </FormField>
        );
      }}
    />
  );
}
