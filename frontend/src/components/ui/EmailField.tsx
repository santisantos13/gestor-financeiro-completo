import { useId, type InputHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";
import { Mail } from "lucide-react";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface EmailFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "name" | "type"> {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
}

/** `TextField` especializado (`type="email"`, ícone `Mail`) — a validação
 * de formato de e-mail em si é sempre responsabilidade do schema Zod
 * (`z.string().email()`), este componente só cuida da apresentação. */
export function EmailField({ name, label, optional, description, className = "", ...props }: EmailFieldProps) {
  const { register, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <FormField id={id} label={label} optional={optional} description={description} error={error}>
      <div className="relative">
        <Mail
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary"
          aria-hidden="true"
        />
        <Input
          id={id}
          type="email"
          autoComplete="email"
          hasError={!!error}
          className={`pl-9 ${className}`}
          {...props}
          {...register(name)}
        />
      </div>
    </FormField>
  );
}
