import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, Sparkles, User } from "lucide-react";
import { Form } from "../../components/ui/Form";
import { TextField } from "../../components/ui/TextField";
import { EmailField } from "../../components/ui/EmailField";
import { PasswordField } from "../../components/ui/PasswordField";
import { SubmitButton } from "../../components/ui/SubmitButton";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { DateFormatToggle } from "../../components/ui/DateFormatToggle";
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
 * `/configuracoes` — módulo do roadmap "Configurações". Escopo até agora:
 * Perfil (editar nome/email + trocar senha) e Preferências (formato de
 * data + tema, este último reaproveitando 100% o `ThemeToggle` que já
 * existia no `UserMenu` - não duplicado, só também exposto aqui para quem
 * espera encontrar "Aparência" numa página de Configurações de verdade).
 * Notificações (depende do backend de Alertas) e mais opções de tema
 * chegam em etapas seguintes. Moeda ficou deliberadamente FORA das
 * Preferências: um seletor de símbolo (R$/US$/€) sem conversão real de
 * valores arriscaria dar a impressão de que o saldo virou outra moeda de
 * verdade - decisão do usuário, ver docs/analise-arquitetural-configuracoes.md.
 * Ainda sem `Tabs`: com poucos cards curtos, cada um seu próprio card
 * empilhado é mais simples que introduzir navegação por abas.
 *
 * Estrutura deliberada de cards/formulários independentes (não um
 * formulário gigante): trocar senha exige a senha ATUAL como confirmação
 * (ver `AuthService.trocar_senha`) e tem seu próprio ciclo de
 * sucesso/erro/limpeza — misturar com o de Perfil obrigaria a resetar
 * campos de senha toda vez que só o nome mudasse, e vice-versa. Preferências
 * nem usa `useForm`: cada opção já se aplica ao ser clicada (mesmo padrão
 * do `ThemeToggle` original), sem precisar de um botão "Salvar" separado.
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

      <div className="rounded-lg border border-border bg-surface-2 p-5">
        <div className="mb-4 flex items-center gap-2 text-text-primary">
          <Sparkles size={16} aria-hidden="true" />
          <h2 className="text-body font-semibold">Preferências</h2>
        </div>
        <div className="max-w-md space-y-4">
          <div>
            <p className="mb-1.5 text-sm font-medium text-text-secondary">Formato de data</p>
            <DateFormatToggle />
            <p className="mt-1.5 text-caption text-text-tertiary">A página recarrega ao trocar.</p>
          </div>
          <div>
            <p className="mb-1.5 text-sm font-medium text-text-secondary">Tema</p>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </div>
  );
}
