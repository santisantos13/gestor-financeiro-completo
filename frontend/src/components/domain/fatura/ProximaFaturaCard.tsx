import { Lock, Receipt } from "lucide-react";
import { Card } from "../../ui/Card";
import { Button } from "../../ui/Button";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { ProgressBar } from "../../ui/ProgressBar";
import { Skeleton } from "../../ui/Skeleton";
import { formatMoney } from "../../../utils/format";
import { formatDate, nomeMes, diferencaEmDias } from "../../../utils/date";
import { selecionarProximaFatura } from "../../../utils/fatura";
import type { FaturaRead } from "../../../types/fatura";

export interface ProximaFaturaCardProps {
  faturas: FaturaRead[] | undefined;
  carregando: boolean;
  /** Abre o `FaturaDrawer` já escopado nesta fatura — a ação contextual
   * (fechar ciclo / registrar pagamento) acontece ali, sem duplicar a
   * mutation/formulário que o Drawer já tem (revisão de UX de Cartões,
   * seção 7, item 4: "atalho que evita abrir o FaturaDrawer para a ação
   * mais comum" — o atalho é chegar direto nela, não reimplementar a
   * ação em dois lugares). */
  onAbrirFatura: (faturaId: number) => void;
}

/**
 * Card de destaque "Próxima fatura" — página de detalhes do Cartão,
 * quarta pergunta da ordem de leitura pedida na revisão de UX ("qual será
 * minha próxima fatura?"). Isolado da lista completa de faturas (que
 * continua abaixo, seção "Faturas") porque merece protagonismo próprio,
 * não misturado com o histórico inteiro. `selecionarProximaFatura`
 * (função pura) decide qual fatura é "a" fatura a destacar a partir da
 * mesma lista que a página já carrega — nenhuma query nova.
 */
export function ProximaFaturaCard({ faturas, carregando, onAbrirFatura }: ProximaFaturaCardProps) {
  if (carregando) {
    return (
      <Card>
        <Skeleton className="h-4 w-24" />
        <Skeleton className="mt-3 h-8 w-40" />
        <Skeleton className="mt-3 h-9 w-full" />
      </Card>
    );
  }

  const fatura = selecionarProximaFatura(faturas ?? []);

  if (!fatura) {
    return (
      <Card className="flex items-center gap-3">
        <Receipt size={18} className="text-text-tertiary" aria-hidden="true" />
        <p className="text-sm text-text-secondary">Nenhuma fatura criada ainda para este cartão.</p>
      </Card>
    );
  }

  const [ano, mes] = fatura.mes_referencia.split("-").map(Number);
  const diferenca = diferencaEmDias(fatura.data_vencimento);
  const vencimentoTexto =
    fatura.status === "ATRASADA"
      ? `Atrasada há ${Math.abs(diferenca)} dia(s)`
      : diferenca <= 0
        ? "Vence hoje"
        : `Vence em ${diferenca} dia(s)`;

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-caption text-text-tertiary">Próxima fatura</p>
          <p className="mt-0.5 text-h3 font-semibold text-text-primary">
            {nomeMes(mes)}/{ano}
          </p>
        </div>
        <FinancialBadge status={fatura.status} />
      </div>

      <div className="mt-3 flex items-baseline justify-between gap-3">
        <span className="font-mono tabular text-h2 font-semibold text-text-primary">
          {formatMoney(fatura.valor_total)}
        </span>
        <span className={`text-sm ${fatura.status === "ATRASADA" ? "text-negative" : "text-text-secondary"}`}>
          {vencimentoTexto}
        </span>
      </div>
      <p className="mt-1 text-caption text-text-tertiary">Vencimento em {formatDate(fatura.data_vencimento)}</p>

      {/* Progresso de pagamento — só depois de fechada (valor_total ainda
          "corrente"/em formação numa fatura ABERTA, comparar com valor_pago
          não diria nada útil). Densidade proposital (valor pago + restante
          sempre visíveis, não escondidos atrás de um clique) — prioriza
          quem usa o sistema todo dia e quer ver o número direto. */}
      {fatura.status !== "ABERTA" && (
        <div className="mt-3 space-y-1">
          <div className="flex items-center justify-between text-caption text-text-tertiary">
            <span>Pago: {formatMoney(fatura.valor_pago)}</span>
            <span>Restante: {formatMoney(Math.max(0, Number(fatura.valor_total) - Number(fatura.valor_pago)))}</span>
          </div>
          <ProgressBar
            value={Number(fatura.valor_total) > 0 ? (Number(fatura.valor_pago) / Number(fatura.valor_total)) * 100 : 0}
            tone={fatura.status === "PAGA" ? "positive" : "info"}
            aria-label="Progresso de pagamento da fatura"
          />
        </div>
      )}

      {fatura.status !== "PAGA" && (
        <Button
          variant="secondary"
          size="sm"
          className="mt-4 w-full"
          onClick={() => onAbrirFatura(fatura.id)}
        >
          {fatura.status === "ABERTA" ? (
            <>
              <Lock size={14} aria-hidden="true" />
              Fechar ciclo
            </>
          ) : (
            "Registrar pagamento"
          )}
        </Button>
      )}
    </Card>
  );
}
