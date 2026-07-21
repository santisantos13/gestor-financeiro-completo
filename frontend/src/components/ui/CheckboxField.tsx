import { useId, type InputHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";
import { Checkbox } from "./Checkbox";
import { FormError } from "./FormError";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface CheckboxFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "name" | "type"> {
  name: string;
  label: string;
  description?: string;
}

/** Layout diferente dos demais campos: o `Checkbox` fica ao lado do label
 * (não acima), então usa seu próprio chrome em vez de `FormField`
 * (que assume label-acima-do-input). `register` funciona nativamente com
 * `type="checkbox"` — RHF já lê `checked` sozinho, sem `Controller`. */
export function CheckboxField({ name, label, description, className = "", ...props }: CheckboxFieldProps) {
  const { register, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <div className={`space-y-1.5 ${className}`}>
      <label htmlFor={id} className="flex cursor-pointer items-start gap-2">
        <Checkbox id={id} className="mt-0.5" {...props} {...register(name)} />
        <span className="text-sm text-text-primary">
          {label}
          {description && <span className="mt-0.5 block text-sm text-text-tertiary">{description}</span>}
        </span>
      </label>
      <FormError message={error} />
    </div>
  );
}
