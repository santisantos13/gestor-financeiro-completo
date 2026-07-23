import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, User } from "lucide-react";
import { Form } from "../../components/ui/Form";
import { TextField } from "../../components/ui/TextField";
import { EmailField } from "../../components/ui/EmailField";
import { PasswordField } from "../../components/ui/PasswordField";
import { SubmitButton } from "../../components/ui/SubmitButton";
import { useAuth } from "../../hooks/useAuth";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../utils/errors";
import {
  perfilFormSchema,
  trocarSenhaFormSchema,
  trocarSenhaFormValuesParaPayload,
  type PerfilFormValues,
  type TrocarSenhaFormValues,
} from "../../schemas/auth";

const SENHA_VAZIA: TrocarSenhaFormValues = { senha_atual: "", senha_nova: "", senha_confirmacao: "" };

/**
 * `/configuracoes` — primeira etapa do módulo (roadmap "Configurações",
 * pendente desde o início do projeto). Escopo desta entrega: aba Perfil
 * (editar nome/email + trocar senha). Preferências/Notificações/Temas
 * chegam em etapas seguintes, cada uma some seu próprio card aqui — quando
 * a segunda existir, esta página ganha `Tabs` (já em `ui/Tabs.tsx`, usado
 * pelo Dashboard) para navegar entre elas; com um card só, `Tabs` seria
 * over-engineering.
 *
 * Estrutura deliberada de dois cards/dois formulários independentes (não um
 * formulário só): trocar senha exige a senha ATUAL como confirmação (ver
 * `AuthService.trocar_senha`) e tem seu próprio ciclo de
 * sucesso/erro/limpeza — misturar os dois num único `useForm` obrigaria a
 * resetar campos de senha toda vez que só o nome mudasse, e vice-versa.
 *
 * Diferente do resto do app, isto não é um `FormDialog`: é a primeira tela
 * do projeto sobre o próprio usuário autenticado, não uma entidade
 * CRUD com lista - uma página cheia, sempre em modo de edição direta (sem
 * modo "somente leitura" prévio), condiz com o padrão já usado por
 * `UserMenu` (edição imediata, sem confirmação extra) para tudo que é
 * "sobre mim".
 */
export function ConfiguracoesPage() {
  const { usuario, atualizarPerfil, trocarSenha } = useAuth();
  const toast = useToast();

  const perfilForm = useForm<PerfilFormValues>({
    resolver: zodResolver(perfilFormSchema),
    mode: "onBlur",
    defaultValues: { nome: "", email: "" },
  });

  useEffect(() => {
    if (usuario) {
      perfilForm.reset({ nome: usuario.nome, email: usuario.email });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usuario]);

  const senhaForm = useForm<TrocarSenhaFormValues>({
    resolver: zodResolver(trocarSenhaFormSchema),
    mode: "onBlur",
    defaultValues: SENHA_VAZIA,
  });

  async function onSubmitPerfil(values: PerfilFormValues) {
    try {
      await atualizarPerfil(values);
      toast.success("Perfil atualizado.");
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          perfilForm.setError(campo as keyof PerfilFormValues, { type: "server", message: mensagem });
        }
      } else if (getErrorMessage(error).toLowerCase().includes("e-mail")) {
        // 409 (e-mail já usado por outro usuário) não vem como erro 422 de
        // campo (ver getFieldErrors) - mapeado manualmente para o campo
        // "email" em vez de só um toast, mesma UX de um erro de validação.
        perfilForm.setError("email", { type: "server", message: getErrorMessage(error) });
      }
      toast.error(getErrorMessage(error));
    }
  }

  async function onSubmitSenha(values: TrocarSenhaFormValues) {
    try {
      await trocarSenha(trocarSenhaFormValuesParaPayload(values));
      toast.success("Senha alterada.");
      senhaForm.reset(SENHA_VAZIA);
    } catch (error) {
      // 401 (senha atual incorreta) é o único erro de negócio deste
      // formulário - mapeado direto para o campo (melhor UX que só um
      // toast solto, já que o usuário sabe exatamente o que corrigir).
      perfilForm.clearErrors();
      senhaForm.setError("senha_atual", { type: "server", message: getErrorMessage(error) });
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 font-semibold text-text-primary">Configurações</h1>
        <p className="mt-1 text-sm text-text-secondary">Gerencie seus dados pessoais e sua senha.</p>
      </div>

      <div className="rounded-lg border border-border bg-surface-2 p-5">
        <div className="mb-4 flex items-center gap-2 text-text-primary">
          <User size={16} aria-hidden="true" />
          <h2 className="text-body font-semibold">Perfil</h2>
        </div>
        <Form id="perfil-form" form={perfilForm} onSubmit={onSubmitPerfil} className="max-w-md space-y-4">
          <TextField name="nome" label="Nome" autoComplete="name" />
          <EmailField name="email" label="Email" autoComplete="email" />
          <SubmitButton form="perfil-form" loading={perfilForm.formState.isSubmitting}>
            Salvar alterações
          </SubmitButton>
        </Form>
      </div>

      <div className="rounded-lg border border-border bg-surface-2 p-5">
        <div className="mb-4 flex items-center gap-2 text-text-primary">
          <KeyRound size={16} aria-hidden="true" />
          <h2 className="text-body font-semibold">Senha</h2>
        </div>
        <Form id="senha-form" form={senhaForm} onSubmit={onSubmitSenha} className="max-w-md space-y-4">
          <PasswordField name="senha_atual" label="Senha atual" autoComplete="current-password" />
          <PasswordField name="senha_nova" label="Senha nova" autoComplete="new-password" />
          <PasswordField name="senha_confirmacao" label="Confirmar senha nova" autoComplete="new-password" />
          <SubmitButton form="senha-form" loading={senhaForm.formState.isSubmitting}>
            Alterar senha
          </SubmitButton>
        </Form>
      </div>
    </div>
  );
}
