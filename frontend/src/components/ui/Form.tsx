import type { FormHTMLAttributes, ReactNode } from "react";
import { FormProvider, type FieldErrors, type FieldValues, type SubmitHandler, type UseFormReturn } from "react-hook-form";

export interface FormProps<TFieldValues extends FieldValues> extends Omit<FormHTMLAttributes<HTMLFormElement>, "onSubmit"> {
  form: UseFormReturn<TFieldValues>;
  onSubmit: SubmitHandler<TFieldValues>;
  children: ReactNode;
}

/**
 * Base de todo formulário do sistema — Etapa F5
 * (docs/analise-arquitetural-frontend.md, seção 12). Quem cria o
 * formulário chama `useForm({ resolver: zodResolver(schema), mode:
 * "onBlur" })` (validação no blur, não a cada tecla — design-system.md,
 * seção 17) e passa o resultado aqui; `Form` só cuida de três coisas
 * genéricas: (1) prover o `FormProvider` do RHF para que qualquer `*Field`
 * descendente use `useFormContext()` sem precisar receber `control`/
 * `register` manualmente; (2) `noValidate` no `<form>` nativo (a validação
 * é 100% Zod, nunca o popup nativo do navegador); (3) em caso de submit
 * inválido, focar automaticamente o primeiro campo com erro e rolar até
 * ele — UX pedida explicitamente nesta etapa. `onSubmit` só é chamado
 * quando o Zod já validou tudo; a submissão em si (chamar a mutation)
 * continua sendo responsabilidade de quem usa `Form`, nunca deste
 * componente.
 */
export function Form<TFieldValues extends FieldValues>({
  form,
  onSubmit,
  children,
  className = "",
  ...props
}: FormProps<TFieldValues>) {
  function onInvalid(errors: FieldErrors<TFieldValues>) {
    const firstFieldName = Object.keys(errors)[0];
    if (!firstFieldName) return;

    form.setFocus(firstFieldName as never);

    // `setFocus` já move o foco; o scroll roda no próximo frame para dar
    // tempo do elemento focado existir/estar posicionado (ex. dentro de um
    // FormDialog que acabou de abrir).
    requestAnimationFrame(() => {
      const escaped = typeof CSS !== "undefined" && CSS.escape ? CSS.escape(firstFieldName) : firstFieldName;
      const el = document.querySelector(`[name="${escaped}"]`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  return (
    <FormProvider {...form}>
      <form noValidate className={className} onSubmit={form.handleSubmit(onSubmit, onInvalid)} {...props}>
        {children}
      </form>
    </FormProvider>
  );
}
