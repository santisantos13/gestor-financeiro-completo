import type { KeyboardEvent } from "react";
import { Receipt } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { formatMoney } from "../../../utils/format";
import { formatDate, diferencaEmDias } from "../../../utils/date";
import { useCartoesQuery, useFaturasQuery } from "../../../hooks/useCentralFinanceiraQueries";
import type { FaturaRead } from "../../../types/centralFinanceira";

const DIAS_A_VENCER_EM_BREVE = 10;

/** `/central-financeira/faturas` — resumo (Sprint de Refinamento Premium,
 * item 9): mostra só faturas ATRASADAS ou vencendo em breve (próximos
 * `DIAS_A_VENCER_EM_BREVE` dias), não a lista inteira de todo cartão em
 * qualquer status - o que sobra some do Dashboard (é o que menos precisa
 * de atenção imediata) e continua disponível em `/cartoes/:id`. Filtro é
 * só uma leitura de `data_vencimento`/`status` já calculados por
 * `FaturaService`, nenhuma regra nova. */
export function FaturasCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useFaturasQuery();
  const { data: dadosCartoes } = useCartoesQuery();

  if (isLoading) return <LoadingCard lines={3} />;

  if (error) {
    return (
      <Card>
        <SectionTitle>Faturas</SectionTitle>
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  if (!data || data.faturas.length === 0) return null;

  const relevantes = data.faturas
    .filter((fatura: FaturaRead) => {
      if (fatura.status === "ATRASADA") return true;
      if (fatura.status === "ABERTA" || fatura.status === "FECHADA" || fatura.status === "PARCIALMENTE_PAGA") {
        const dias = diferencaEmDias(fatura.data_vencimento);
        return dias >= 0 && dias <= DIAS_A_VENCER_EM_BREVE;
      }
      return false;
    })
    .sort((a, b) => a.data_vencimento.localeCompare(b.data_vencimento));

  if (relevantes.length === 0) return null;

  const cartaoPorId = new Map((dadosCartoes?.cartoes ?? []).map((cartao) => [cartao.id, cartao]));

  return (
    <Card>
      <SectionTitle>Faturas</SectionTitle>
      <p className="text-caption text-text-tertiary">Vencidas ou vencendo em breve</p>
      <ul className="mt-3 space-y-3">
        {relevantes.map((fatura) => {
          const cartao = cartaoPorId.get(fatura.cartao_id);

          function abrirCartao() {
            navigate(`/cartoes/${fatura.cartao_id}`);
          }

          function onKeyDown(event: KeyboardEvent<HTMLLIElement>) {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              abrirCartao();
            }
          }

          return (
            <li
              key={fatura.id}
              role="link"
              tabIndex={0}
              onClick={abrirCartao}
              onKeyDown={onKeyDown}
              aria-label={`Ver cartão da fatura de ${cartao ? cartao.nome : "vencimento " + fatura.data_vencimento}`}
              className="flex cursor-pointer items-center justify-between rounded-md border-b border-border-subtle pb-2.5 transition-colors last:border-0 last:pb-0 hover:bg-surface-3"
            >
              <span className="flex min-w-0 items-center gap-2 text-sm text-text-primary">
                {cartao ? (
                  <InstitutionBadge nome={cartao.instituicao} size="sm" />
                ) : (
                  <Receipt size={14} className="text-text-tertiary" aria-hidden="true" />
                )}
                <span className="truncate">
                  {cartao ? `${cartao.nome} · ` : ""}Vence {formatDate(fatura.data_vencimento)}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="tabular text-sm text-text-primary">{formatMoney(fatura.valor_total)}</span>
                <FinancialBadge status={fatura.status} />
              </span>
            </li>
          );
        })}
      </ul>
      <Button size="sm" variant="ghost" onClick={() => navigate("/cartoes")} className="mt-3">
        Ver cartões
      </Button>
    </Card>
  );
}
