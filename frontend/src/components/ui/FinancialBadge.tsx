import { Badge, type BadgeTone } from "./Badge";
import type { StatusContratoCredito, StatusFatura, StatusTransacao } from "../../types/enums";

type StatusConhecido = StatusFatura | StatusContratoCredito | StatusTransacao;

// Mapa único enum -> tone, evita 3 `switch` espalhados pelo código —
// docs/analise-arquitetural-dashboard.md, seção 9.1.
//
// `ABERTA`/`ATIVO` migraram de `neutral` para `info` na revisão de UX de
// Cartões (sistema semântico de status, docs/analise-arquitetural-revisao-ux-cartoes.md):
// são estados informativos/em-andamento, não "sem estado" — `neutral`
// (cinza) fica reservado para o que é de fato inativo/neutro (ex.
// `AtivoBadge` de um cadastro desativado).
const TONE_POR_STATUS: Record<StatusConhecido, BadgeTone> = {
  ABERTA: "info",
  FECHADA: "warning",
  PARCIALMENTE_PAGA: "warning",
  PAGA: "positive",
  ATRASADA: "negative",
  ATIVO: "info",
  QUITADO: "positive",
  INADIMPLENTE: "negative",
  PENDENTE: "warning",
  PAGO: "positive",
};

const LABEL_POR_STATUS: Record<StatusConhecido, string> = {
  ABERTA: "Aberta",
  FECHADA: "Fechada",
  PARCIALMENTE_PAGA: "Parcialmente paga",
  PAGA: "Paga",
  ATRASADA: "Atrasada",
  ATIVO: "Ativo",
  QUITADO: "Quitado",
  INADIMPLENTE: "Inadimplente",
  PENDENTE: "Pendente",
  PAGO: "Pago",
};

export interface FinancialBadgeProps {
  status: StatusConhecido;
  className?: string;
}

/** `Badge` especializado: resolve tone + label a partir de
 * `StatusFatura`/`StatusContratoCredito`/`StatusTransacao` automaticamente —
 * design-system.md, seção 14 ("o componente visual por trás de todo
 * StatusFatura/StatusTransacao/StatusContratoCredito"). Ver
 * docs/analise-arquitetural-dashboard.md, seção 9.1 para a tabela completa. */
export function FinancialBadge({ status, className }: FinancialBadgeProps) {
  return (
    <Badge tone={TONE_POR_STATUS[status]} className={className}>
      {LABEL_POR_STATUS[status]}
    </Badge>
  );
}
