import { useId, type InputHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "name"> {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
}

/** Campo de texto simples — usa `register` diretamente (sem `Controller`,
 * o `<input>` nativo já é o bastante para RHF rastrear). Base de
 * `EmailField`/parte de `PasswordField`. */
export function TextField({ name, label, optional, description, className, ...props }: TextFieldProps) {
  const { register, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <FormField id={id} label={label} optional={optional} description={description} error={error}>
      <Input id={id} hasError={!!error} className={className} {...props} {...register(name)} />
    </FormField>
  );
}
