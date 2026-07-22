import { useState, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { Tabs } from "../../ui/Tabs";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { formatDate, formatDateTime } from "../../../utils/date";
import { formatMoney } from "../../../utils/format";
import { useAgendaFinanceiraQuery, useAtividadesRecentesQuery } from "../../../hooks/useCentralFinanceiraQueries";
import { ICONE_POR_ORIGEM, ROTA_POR_ORIGEM } from "../../../lib/origemNavegacao";

type AbaTransacoesRecentes = "TRANSACOES" | "AGENDA";

const QUANTIDADE_LINHAS = 3;

const ABAS = [
  { id: "TRANSACOES", label: "Transações" },
  { id: "AGENDA", label: "Agenda" },
];

/**
 * Substitui `AgendaFinanceiraCard` (Refinamento Visual, pedido explícito
 * do usuário: uma referência visual de outro app mostrava uma tabela
 * "Transações Recentes" com abas Transações/Agenda). Aba "Transações"
 * reaproveita `useAtividadesRecentesQuery` — a mesma fonte da Central de
 * Atividades, hoje só acessível via Drawer no Header
 * (`AtividadesRecentesDrawer`); aba "Agenda" é a mesma
 * `useAgendaFinanceiraQuery` que a antiga `AgendaFinanceiraCard` já usava.
 * Nenhum endpoint novo. Ver
 * docs/analise-arquitetural-dashboard-hero-redesign.md, decisão 5.
 *
 * Só retorna `null` quando AS DUAS abas estão vazias — diferente da regra
 * padrão de "esconder card vazio" de um card de fonte única, aqui esconder
 * assim que UMA aba estiver vazia impediria o usuário de ver a outra que
 * tem conteúdo.
 */
export function TransacoesRecentesCard() {
  const navigate = useNavigate();
  const [aba, setAba] = useState<AbaTransacoesRecentes>("TRANSACOES");

  const {
    data: dadosAtividades,
    isLoading: carregandoAtividades,
    error: erroAtividades,
    refetch: refetchAtividades,
  } = useAtividadesRecentesQuery(QUANTIDADE_LINHAS);
  const {
    data: dadosAgenda,
    isLoading: carregandoAgenda,
    error: erroAgenda,
    refetch: refetchAgenda,
  } = useAgendaFinanceiraQuery(30);

  const carregando = aba === "TRANSACOES" ? carregandoAtividades : carregandoAgenda;
  if (carregando) return <LoadingCard lines={5} />;

  const atividades = dadosAtividades?.atividades ?? [];
  const eventosAgenda = (dadosAgenda?.eventos ?? []).slice(0, QUANTIDADE_LINHAS);

  if (atividades.length === 0 && eventosAgenda.length === 0 && !erroAtividades && !erroAgenda) return null;

  const erro = aba === "TRANSACOES" ? erroAtividades : erroAgenda;
  const refazer = aba === "TRANSACOES" ? refetchAtividades : refetchAgenda;

  function abrirVerMais() {
    navigate(aba === "TRANSACOES" ? "/transacoes" : "/calendario");
  }

  function onKeyDownLinha(destino: string | null) {
    return (event: KeyboardEvent<HTMLLIElement>) => {
      if (!destino) return;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        navigate(destino);
      }
    };
  }

  return (
    <Card>
      <SectionTitle
        action={
          <Tabs
            tabs={ABAS}
            value={aba}
            onChange={(id) => setAba(id as AbaTransacoesRecentes)}
            aria-label="Alternar entre transações recentes e agenda financeira"
          />
        }
      >
        Transações recentes
      </SectionTitle>

      {erro ? (
        <>
          <ErrorMessage error={erro} />
          <Button size="sm" variant="secondary" onClick={() => refazer()} className="mt-3">
            Tentar novamente
          </Button>
        </>
      ) : aba === "TRANSACOES" ? (
        atividades.length === 0 ? (
          <p className="text-caption text-text-tertiary">Nenhuma atividade registrada ainda.</p>
        ) : (
          <ul className="space-y-2.5">
            {atividades.map((atividade, index) => {
              const Icon = ICONE_POR_ORIGEM[atividade.origem_tipo];
              const construirRota = ROTA_POR_ORIGEM[atividade.origem_tipo];
              const destino = construirRota ? construirRota(atividade.origem_id) : null;
              return (
                <li
                  key={`atividade-${atividade.origem_tipo}-${atividade.origem_id}-${index}`}
                  {...(destino
                    ? { role: "link" as const, tabIndex: 0, onClick: () => navigate(destino), onKeyDown: onKeyDownLinha(destino) }
                    : {})}
                  className={`flex items-center justify-between gap-2 rounded-md border-b border-border-subtle pb-2.5 last:border-0 last:pb-0 ${destino ? "cursor-pointer hover:bg-surface-3" : ""}`}
                >
                  <span className="flex min-w-0 items-center gap-2 text-sm text-text-primary">
                    <Icon size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                    <span className="min-w-0">
                      <span className="block truncate">{atividade.descricao}</span>
                      <span className="block text-caption text-text-tertiary">{formatDateTime(atividade.data_hora)}</span>
                    </span>
                  </span>
                  {atividade.valor != null && (
                    <span className="tabular shrink-0 text-sm text-text-primary">{formatMoney(atividade.valor)}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )
      ) : eventosAgenda.length === 0 ? (
        <p className="text-caption text-text-tertiary">Nenhum evento nos próximos 30 dias.</p>
      ) : (
        <ul className="space-y-2.5">
          {eventosAgenda.map((evento, index) => {
            const Icon = ICONE_POR_ORIGEM[evento.origem_tipo];
            const construirRota = ROTA_POR_ORIGEM[evento.origem_tipo];
            const destino = construirRota ? construirRota(evento.origem_id) : null;
            return (
              <li
                key={`agenda-${evento.origem_tipo}-${evento.origem_id}-${index}`}
                {...(destino
                  ? { role: "link" as const, tabIndex: 0, onClick: () => navigate(destino), onKeyDown: onKeyDownLinha(destino) }
                  : {})}
                className={`flex items-center justify-between gap-2 rounded-md border-b border-border-subtle pb-2.5 last:border-0 last:pb-0 ${destino ? "cursor-pointer hover:bg-surface-3" : ""}`}
              >
                <span className="flex min-w-0 items-center gap-2 text-sm text-text-primary">
                  <Icon size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                  <span className="min-w-0">
                    <span className="block truncate">{evento.descricao}</span>
                    <span className="block text-caption text-text-tertiary">{formatDate(evento.data)}</span>
                  </span>
                </span>
                <span className="tabular shrink-0 text-sm text-text-primary">{formatMoney(evento.valor)}</span>
              </li>
            );
          })}
        </ul>
      )}

      {!erro && (
        <button
          type="button"
          onClick={abrirVerMais}
          className="mt-3 border-t border-border-subtle pt-3 text-micro font-medium text-accent transition-colors duration-fast ease-out hover:text-accent-hover"
        >
          Ver mais →
        </button>
      )}
    </Card>
  );
}
