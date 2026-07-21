import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { CalendarioMensal } from "../../components/domain/calendario/CalendarioMensal";
import { LegendaCalendario } from "../../components/domain/calendario/LegendaCalendario";
import { ResumoMesCalendario } from "../../components/domain/calendario/ResumoMesCalendario";
import { EventoDiaDrawer } from "../../components/domain/calendario/EventoDiaDrawer";
import { MesAnoSeletor } from "../../components/domain/calendario/MesAnoSeletor";
import { useCalendarioFinanceiroQuery } from "../../hooks/useCentralFinanceiraQueries";

/**
 * Página `/calendario` — Etapa de Calendário Financeiro. Substitui a
 * proposta original de "lista de eventos" por um calendário mensal
 * navegável, com indicadores por dia e um Drawer de detalhes ao clicar.
 * Ver docs/analise-arquitetural-transferencias-frontend.md.
 *
 * Estado local mínimo (ano/mes/direção de navegação/dia selecionado) — todo
 * dado financeiro vem de `useCalendarioFinanceiroQuery`, mesmo princípio de
 * toda página do projeto (nenhum `useState` guarda dado de servidor).
 */
export function CalendarioPage() {
  const hoje = new Date();
  const [periodo, setPeriodo] = useState({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });
  const [direcao, setDirecao] = useState(0);
  const [diaSelecionado, setDiaSelecionado] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useCalendarioFinanceiroQuery(periodo.ano, periodo.mes);

  function irParaMes(deltaMeses: number) {
    setDirecao(deltaMeses > 0 ? 1 : -1);
    setPeriodo(({ ano, mes }) => {
      const dataBase = new Date(ano, mes - 1 + deltaMeses, 1);
      return { ano: dataBase.getFullYear(), mes: dataBase.getMonth() + 1 };
    });
  }

  function selecionarMesAno(anoEscolhido: number, mesEscolhido: number) {
    setDirecao(
      anoEscolhido === periodo.ano
        ? mesEscolhido > periodo.mes
          ? 1
          : mesEscolhido < periodo.mes
            ? -1
            : 0
        : anoEscolhido > periodo.ano
          ? 1
          : -1,
    );
    setPeriodo({ ano: anoEscolhido, mes: mesEscolhido });
  }

  function irParaHoje() {
    setDirecao(0);
    setPeriodo({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });
  }

  const eventos = data?.eventos ?? [];
  const eventosDoDiaSelecionado = diaSelecionado ? eventos.filter((e) => e.data === diaSelecionado) : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Calendário financeiro</h1>
          <p className="mt-1 text-sm text-text-secondary">Seu mês inteiro, num só lugar.</p>
        </div>
        <div className="flex items-center gap-1.5">
          <Button variant="secondary" size="sm" onClick={irParaHoje}>
            Hoje
          </Button>
          <Button variant="ghost" size="sm" onClick={() => irParaMes(-1)} aria-label="Mês anterior">
            <ChevronLeft size={16} aria-hidden="true" />
          </Button>
          <MesAnoSeletor
            ano={periodo.ano}
            mes={periodo.mes}
            onSelecionar={selecionarMesAno}
            className="min-w-[9rem] justify-center"
          />
          <Button variant="ghost" size="sm" onClick={() => irParaMes(1)} aria-label="Próximo mês">
            <ChevronRight size={16} aria-hidden="true" />
          </Button>
        </div>
      </div>

      {isLoading && !data ? (
        <LoadingCard lines={8} />
      ) : error ? (
        <div className="space-y-3">
          <ErrorMessage error={error} />
          <Button size="sm" variant="secondary" onClick={() => refetch()}>
            Tentar novamente
          </Button>
        </div>
      ) : (
        <>
          <ResumoMesCalendario eventos={eventos} />

          <div className="rounded-lg border border-border bg-surface-2 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <LegendaCalendario />
            </div>
            <CalendarioMensal
              ano={periodo.ano}
              mes={periodo.mes}
              eventos={eventos}
              onSelecionarDia={setDiaSelecionado}
              direcao={direcao}
            />
          </div>
        </>
      )}

      <EventoDiaDrawer iso={diaSelecionado} eventos={eventosDoDiaSelecionado} onClose={() => setDiaSelecionado(null)} />
    </div>
  );
}
