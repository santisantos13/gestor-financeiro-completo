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

export const perfilFormSchema = z.object({
  nome: z.string().min(1, "Informe o nome.").max(120, "Nome muito longo."),
  email: z.string().min(1, "Informe o email.").email("Email inválido."),
});

export type PerfilFormValues = z.infer<typeof perfilFormSchema>;

/** `senha_confirmacao` é só validação de UX (garantir que o usuário não
 * digitou a senha nova errada duas vezes) - nunca é enviada ao backend, que
 * só recebe `senha_atual`/`senha_nova` (ver `trocarSenhaFormValuesParaPayload`). */
export const trocarSenhaFormSchema = z
  .object({
    senha_atual: z.string().min(1, "Informe a senha atual."),
    senha_nova: z
      .string()
      .min(8, "A senha precisa de pelo menos 8 caracteres.")
      .max(72, "A senha pode ter no máximo 72 caracteres."),
    senha_confirmacao: z.string().min(1, "Confirme a senha nova."),
  })
  .refine((valores) => valores.senha_nova === valores.senha_confirmacao, {
    message: "As senhas não coincidem.",
    path: ["senha_confirmacao"],
  });

export type TrocarSenhaFormValues = z.infer<typeof trocarSenhaFormSchema>;

export function trocarSenhaFormValuesParaPayload(
  valores: TrocarSenhaFormValues,
): { senha_atual: string; senha_nova: string } {
  return { senha_atual: valores.senha_atual, senha_nova: valores.senha_nova };
}
