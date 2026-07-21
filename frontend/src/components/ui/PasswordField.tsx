import { useId, useState, type InputHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";
import { Eye, EyeOff } from "lucide-react";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "name" | "type"> {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
}

/** `TextField` especializado com alternância mostrar/ocultar (`Eye`/
 * `EyeOff`) — o botão é `type="button"` para nunca disparar submit. */
export function PasswordField({ name, label, optional, description, className = "", ...props }: PasswordFieldProps) {
  const { register, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);
  const [visivel, setVisivel] = useState(false);

  return (
    <FormField id={id} label={label} optional={optional} description={description} error={error}>
      <div className="relative">
        <Input
          id={id}
          type={visivel ? "text" : "password"}
          autoComplete="current-password"
          hasError={!!error}
          className={`pr-10 ${className}`}
          {...props}
          {...register(name)}
        />
        <button
          type="button"
          onClick={() => setVisivel((v) => !v)}
          aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary transition-colors duration-fast ease-out hover:text-text-primary"
        >
          {visivel ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
        </button>
      </div>
    </FormField>
  );
}
