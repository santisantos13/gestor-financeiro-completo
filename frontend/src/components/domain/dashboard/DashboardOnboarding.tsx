import { Wallet } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { EmptyState } from "../../ui/EmptyState";
import { Button } from "../../ui/Button";

/** Tela cheia exibida no lugar do Bento Grid quando o usuário não tem
 * nenhuma conta cadastrada ainda (`indicadores.contas_ativas === 0`) — evita
 * a "parede de zeros" (central-financeira-especificacao.md, seção 2).
 * docs/analise-arquitetural-dashboard.md, seção 9.3.
 *
 * Achado da revisão geral de UX/UI (ponto 6): o botão "Criar conta" estava
 * desabilitado com tooltip "Disponível em breve" desde a especificação
 * original do Dashboard (quando a Etapa F6/CRUD de Conta ainda não
 * existia). A página `/contas` já existe desde a F6 — o botão estava
 * silenciosamente obsoleto, mandando o usuário recém-cadastrado para lugar
 * nenhum bem no primeiro contato com o app. Agora navega de verdade. */
export function DashboardOnboarding() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={Wallet}
        title="Comece cadastrando sua primeira conta"
        description="Assim que você tiver uma conta, o Dashboard mostra seu saldo, cartões, faturas, metas e agenda financeira em um só lugar."
        action={
          <Button variant="primary" onClick={() => navigate("/contas")}>
            Criar conta
          </Button>
        }
      />
    </div>
  );
}
