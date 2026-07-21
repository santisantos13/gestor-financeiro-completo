import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { useAuth } from "../../hooks/useAuth";
import { loginSchema, type LoginFormValues } from "../../schemas/auth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<unknown>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginFormValues) {
    setFormError(null);
    try {
      await login(values);
      navigate("/", { replace: true });
    } catch (error) {
      setFormError(error);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <label htmlFor="email" className="mb-1 block text-sm font-medium text-text-secondary">
          Email
        </label>
        <Input id="email" type="email" autoComplete="email" hasError={!!errors.email} {...register("email")} />
        {errors.email && <p className="mt-1 text-sm text-negative">{errors.email.message}</p>}
      </div>

      <div>
        <label htmlFor="senha" className="mb-1 block text-sm font-medium text-text-secondary">
          Senha
        </label>
        <Input
          id="senha"
          type="password"
          autoComplete="current-password"
          hasError={!!errors.senha}
          {...register("senha")}
        />
        {errors.senha && <p className="mt-1 text-sm text-negative">{errors.senha.message}</p>}
      </div>

      {formError !== null && <ErrorMessage error={formError} />}

      <Button type="submit" className="w-full" loading={isSubmitting}>
        Entrar
      </Button>

      <p className="text-center text-sm text-text-secondary">
        Não tem conta?{" "}
        <Link to="/registrar" className="font-medium text-accent hover:text-accent-hover">
          Registre-se
        </Link>
      </p>
    </form>
  );
}
