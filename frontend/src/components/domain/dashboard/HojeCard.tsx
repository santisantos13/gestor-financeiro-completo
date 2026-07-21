import type { KeyboardEvent } from "react";
import { Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { formatMoney } from "../../../utils/format";
import { useCalendarioFinanceiroQuery } from "../../../hooks/useCentralFinanceiraQueries";
import { ICONE_POR_ORIGEM, ROTA_POR_ORIGEM } from "../../../lib/origemNavegacao";

function hojeIso(): string {
  const hoje = new Date();
  return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
}

/** Card "Hoje" (Sprint de Refinamento Premium, item 13) — pedido explícito
 * do usuário: "não quero lógica duplicada, apenas utilizar os dados
 * existentes". Reaproveita 100% `calendario_financeiro` (já implementado
 * na Etapa de Calendário Financeiro) filtrando client-side só os eventos
 * cuja `data` é hoje — nenhum endpoint novo, nenhum cálculo novo. Mesmo
 * mapa `ICONE_POR_ORIGEM`/`ROTA_POR_ORIGEM` de `AgendaFinanceiraCard`, para
 * as duas nunca divergirem no que é clicável.
 *
 * Gap conhecido (documentado em `docs/analise-arquitetural-sprint-refinamento-premium.md`,
 * seção 3/6-14): recorrências futuras ainda não geradas e "poupar para
 * meta" como evento recorrente não aparecem aqui — mesmo gap já existente
 * em `agenda_financeira`/`calendario_financeiro`, fora do escopo desta
 * etapa. O card mostra fielmente o que já existe, como pedido. */
export function HojeCard() {
  const navigate = useNavigate();
  const hoje = new Date();
  const { data, isLoading } = useCalendarioFinanceiroQuery(hoje.getFullYear(), hoje.getMonth() + 1);

  if (isLoading) return <LoadingCard lines={2} />;

  const isoHoje = hojeIso();
  const eventosDeHoje = (data?.eventos ?? []).filter((evento) => evento.data === isoHoje);

  if (eventosDeHoje.length === 0) return null;

  return (
    <Card>
      <SectionTitle>Hoje</SectionTitle>
      <ul className="space-y-2.5">
        {eventosDeHoje.map((evento, index) => {
          const Icon = ICONE_POR_ORIGEM[evento.origem_tipo];
          const construirRota = ROTA_POR_ORIGEM[evento.origem_tipo];
          const destino = construirRota ? construirRota(evento.origem_id) : null;

          function abrirDestino() {
            if (destino) navigate(destino);
          }

          function onKeyDown(event: KeyboardEvent<HTMLLIElement>) {
            if (!destino) return;
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              abrirDestino();
            }
          }

          return (
            <li
              key={`${evento.origem_tipo}-${evento.origem_id}-${index}`}
              {...(destino ? { role: "link" as const, tabIndex: 0, onClick: abrirDestino, onKeyDown } : {})}
              className={`flex items-center justify-between rounded-md border-b border-border-subtle pb-2.5 transition-colors last:border-0 last:pb-0 ${destino ? "cursor-pointer hover:bg-surface-3" : ""}`}
            >
              <span className="flex items-center gap-2 text-sm text-text-primary">
                <Icon size={14} className="text-text-tertiary" aria-hidden="true" />
                {evento.descricao}
              </span>
              <span className="tabular text-sm text-text-primary">{formatMoney(evento.valor)}</span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** Reexporta o ícone usado no header desta seção — evita mais um import
 * espalhado quando `DashboardPage` quiser um ícone de contexto. */
export const HOJE_ICON = Sparkles;
