import { useMemo } from "react";
import { motion } from "motion/react";
import { construirGradeMensal } from "../../../utils/date";
import { COR_DOT_POR_CATEGORIA } from "../../../lib/calendarioCategorias";
import { DURATION, EASE } from "../../../lib/motion";
import type { EventoCalendario } from "../../../types/centralFinanceira";

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const MAX_DOTS_POR_DIA = 4;

export interface CalendarioMensalProps {
  ano: number;
  mes: number;
  eventos: EventoCalendario[];
  onSelecionarDia: (iso: string) => void;
  /** Direção da última navegação (`1` = avançou, `-1` = voltou, `0` = sem
   * transição/"ir para hoje") — decide de que lado a grade nova desliza,
   * motion-principles.md, seção 5.4 (mudança de contexto direcional). */
  direcao: number;
}

/**
 * Grade mensal do Calendário Financeiro — indicadores em formato de pontos
 * (nunca o dia inteiro pintado, pedido explícito do usuário), inspirado em
 * Google Calendar/Notion Calendar. Ver
 * docs/analise-arquitetural-transferencias-frontend.md, seção "Calendário".
 *
 * Um dot por CATEGORIA presente no dia (não um por evento individual) —
 * decisão deliberada: um dia com 6 despesas mostraria 6 pontos vermelhos
 * idênticos, o que não comunica nada a mais que 1 só. Até
 * `MAX_DOTS_POR_DIA` categorias diferentes são mostradas; acima disso, um
 * "+N" textual substitui o excesso (mesmo princípio de `TagBadge`/coluna de
 * tags do `transacaoTableColumns.tsx`).
 */
export function CalendarioMensal({ ano, mes, eventos, onSelecionarDia, direcao }: CalendarioMensalProps) {
  const dias = useMemo(() => construirGradeMensal(ano, mes), [ano, mes]);

  const eventosPorDia = useMemo(() => {
    const mapa = new Map<string, EventoCalendario[]>();
    for (const evento of eventos) {
      const lista = mapa.get(evento.data) ?? [];
      lista.push(evento);
      mapa.set(evento.data, lista);
    }
    return mapa;
  }, [eventos]);

  return (
    <div className="overflow-hidden">
      <div className="grid grid-cols-7 gap-px pb-2 text-center text-micro font-medium uppercase tracking-wide text-text-tertiary">
        {DIAS_SEMANA.map((dia) => (
          <span key={dia}>{dia}</span>
        ))}
      </div>

      <motion.div
        key={`${ano}-${mes}`}
        initial={{ opacity: 0, x: direcao * 24 }}
        animate={{ opacity: 1, x: 0, transition: { duration: DURATION.moderate, ease: EASE.out } }}
        className="grid grid-cols-7 gap-px rounded-md bg-border-subtle"
      >
        {dias.map((dia) => {
          const eventosDoDia = eventosPorDia.get(dia.iso) ?? [];
          const categoriasPresentes = Array.from(new Set(eventosDoDia.map((e) => e.categoria)));
          const categoriasVisiveis = categoriasPresentes.slice(0, MAX_DOTS_POR_DIA);
          const excedente = categoriasPresentes.length - categoriasVisiveis.length;

          return (
            <button
              key={dia.iso}
              type="button"
              onClick={() => eventosDoDia.length > 0 && onSelecionarDia(dia.iso)}
              disabled={eventosDoDia.length === 0}
              aria-label={
                eventosDoDia.length > 0
                  ? `${dia.diaDoMes}, ${eventosDoDia.length} evento${eventosDoDia.length > 1 ? "s" : ""}`
                  : `${dia.diaDoMes}, sem eventos`
              }
              className={`flex min-h-[4.5rem] flex-col items-center gap-1.5 bg-surface-2 p-2 text-left transition-colors duration-fast ease-out sm:min-h-[5.5rem] ${
                dia.noMesAtual ? "" : "opacity-40"
              } ${eventosDoDia.length > 0 ? "cursor-pointer hover:bg-surface-3" : "cursor-default"}`}
            >
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-sm ${
                  dia.hoje ? "bg-accent font-semibold text-white" : "text-text-primary"
                }`}
              >
                {dia.diaDoMes}
              </span>
              {eventosDoDia.length > 0 && (
                <span className="flex flex-wrap items-center justify-center gap-1">
                  {categoriasVisiveis.map((categoria) => (
                    <span
                      key={categoria}
                      className={`h-1.5 w-1.5 shrink-0 rounded-full ${COR_DOT_POR_CATEGORIA[categoria]}`}
                    />
                  ))}
                  {excedente > 0 && <span className="text-micro text-text-tertiary">+{excedente}</span>}
                </span>
              )}
            </button>
          );
        })}
      </motion.div>
    </div>
  );
}
