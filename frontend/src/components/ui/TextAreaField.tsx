import { useId, type TextareaHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";
import { FormField } from "./FormField";
import { Textarea } from "./Textarea";
import { getFieldErrorMessage } from "../../utils/formPath";

export interface TextAreaFieldProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id" | "name"> {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
}

export function TextAreaField({ name, label, optional, description, className, ...props }: TextAreaFieldProps) {
  const { register, formState } = useFormContext();
  const id = useId();
  const error = getFieldErrorMessage(formState.errors, name);

  return (
    <FormField id={id} label={label} optional={optional} description={description} error={error}>
      <Textarea id={id} hasError={!!error} className={className} rows={4} {...props} {...register(name)} />
    </FormField>
  );
}
