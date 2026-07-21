import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { useAuth } from "../../hooks/useAuth";
import { registrarSchema, type RegistrarFormValues } from "../../schemas/auth";

export function RegistrarPage() {
  const { registrar } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<unknown>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegistrarFormValues>({ resolver: zodResolver(registrarSchema) });

  async function onSubmit(values: RegistrarFormValues) {
    setFormError(null);
    try {
      await registrar(values);
      navigate("/", { replace: true });
    } catch (error) {
      setFormError(error);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <label htmlFor="nome" className="mb-1 block text-sm font-medium text-text-secondary">
          Nome
        </label>
        <Input id="nome" autoComplete="name" hasError={!!errors.nome} {...register("nome")} />
        {errors.nome && <p className="mt-1 text-sm text-negative">{errors.nome.message}</p>}
      </div>

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
          autoComplete="new-password"
          hasError={!!errors.senha}
          {...register("senha")}
        />
        {errors.senha && <p className="mt-1 text-sm text-negative">{errors.senha.message}</p>}
      </div>

      {formError !== null && <ErrorMessage error={formError} />}

      <Button type="submit" className="w-full" loading={isSubmitting}>
        Criar conta
      </Button>

      <p className="text-center text-sm text-text-secondary">
        Já tem conta?{" "}
        <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
          Entrar
        </Link>
      </p>
    </form>
  );
}
