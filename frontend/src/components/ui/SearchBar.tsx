import { Search, X } from "lucide-react";
import { Input } from "./Input";

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

/** Campo de busca client-side — filtra sobre as colunas já carregadas
 * (`hooks/useDataTable.ts`). Ícone de lupa fixo à esquerda, botão de
 * limpar quando há texto digitado. */
export function SearchBar({ value, onChange, placeholder = "Buscar...", className = "" }: SearchBarProps) {
  return (
    <div className={`relative ${className}`}>
      <Search
        size={15}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary"
        aria-hidden="true"
      />
      <Input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="pl-9 pr-8"
        aria-label={placeholder}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Limpar busca"
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary transition-colors duration-fast ease-out hover:text-text-primary"
        >
          <X size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
