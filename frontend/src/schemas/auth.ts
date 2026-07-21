/**
 * Validação de FORMATO/obrigatoriedade só para UX - a regra de negócio real
 * (email já cadastrado, credenciais inválidas, etc.) continua exclusiva do
 * backend e chega como 422/401 tratado por `getErrorMessage`. Ver
 * docs/analise-arquitetural-frontend.md, seção 5.
 */
import { z } from "zod";
import type { LoginRequest, UsuarioCreate } from "../types/auth";

export const loginSchema = z.object({
  email: z.string().min(1, "Informe o email.").email("Email inválido."),
  senha: z.string().min(1, "Informe a senha."),
}) satisfies z.ZodType<LoginRequest>;

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registrarSchema = z.object({
  nome: z.string().min(1, "Informe o nome.").max(120, "Nome muito longo."),
  email: z.string().min(1, "Informe o email.").email("Email inválido."),
  // min/max espelham UsuarioCreate.senha no backend (max_length=72 é limite
  // de bytes do bcrypt) - ver backend/app/schemas/auth.py.
  senha: z
    .string()
    .min(8, "A senha precisa de pelo menos 8 caracteres.")
    .max(72, "A senha pode ter no máximo 72 caracteres."),
}) satisfies z.ZodType<UsuarioCreate>;

export type RegistrarFormValues = z.infer<typeof registrarSchema>;
