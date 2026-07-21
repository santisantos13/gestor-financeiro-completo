import type { LucideIcon } from "lucide-react";
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../ui/Card";

export interface ProximoPassoCardProps {
  icon: LucideIcon;
  titulo: string;
  descricao: string;
  rota: string;
}

/** Sugestão leve de "próximo passo" — Etapa de Refinamento de UX/Dashboard/
 * Cartões, seção 9 ("primeira experiência de uso"). Diferente de
 * `DashboardOnboarding` (tela cheia, só quando `contas_ativas === 0`), este
 * banner é compacto e aparece DENTRO do Bento Grid normal, para o estado
 * intermediário em que o usuário já tem uma Conta mas ainda não deu o
 * próximo passo óbvio (ex. cadastrar o primeiro Cartão) — evita ele voltar
 * ao Dashboard e só ver cards vazios sem saber o que fazer a seguir.
 * Mesmo padrão `role="link"` + teclado dos demais cards clicáveis (seção
 * 1) — mas com um `ArrowRight` explícito, já que aqui o texto É um convite
 * de ação (não um dado que também pode ser navegado). */
export function ProximoPassoCard({ icon: Icon, titulo, descricao, rota }: ProximoPassoCardProps) {
  const navigate = useNavigate();

  function abrir() {
    navigate(rota);
  }

  return (
    <Card
      role="link"
      tabIndex={0}
      onClick={abrir}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          abrir();
        }
      }}
      aria-label={titulo}
      className="flex cursor-pointer items-center gap-4 border-dashed bg-surface-1"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-info-subtle text-info">
        <Icon size={18} aria-hidden="true" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-text-primary">{titulo}</p>
        <p className="text-caption text-text-tertiary">{descricao}</p>
      </div>
      <ArrowRight size={16} className="shrink-0 text-text-tertiary" aria-hidden="true" />
    </Card>
  );
}
