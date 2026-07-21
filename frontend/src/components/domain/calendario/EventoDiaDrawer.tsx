import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, Layers } from "lucide-react";
import { Drawer } from "../../ui/Drawer";
import { formatDate } from "../../../utils/date";
import { formatMoney } from "../../../utils/format";
import { COR_DOT_POR_CATEGORIA, LABEL_CATEGORIA_EVENTO, TEXT_COR_POR_CATEGORIA } from "../../../lib/calendarioCategorias";
import { ICONE_POR_ORIGEM, ROTA_POR_ORIGEM } from "../../../lib/origemNavegacao";
import type { EventoCalendario } from "../../../types/centralFinanceira";

export interface EventoDiaDrawerProps {
  iso: string | null;
  eventos: EventoCalendario[];
  onClose: () => void;
}

function ItemEvento({ evento }: { evento: EventoCalendario }) {
  const navigate = useNavigate();
  const Icon = ICONE_POR_ORIGEM[evento.origem_tipo];
  const construirRota = ROTA_POR_ORIGEM[evento.origem_tipo];
  const destino = construirRota ? construirRota(evento.origem_id) : null;

  return (
    // `previsto` (expansão de Contas Recorrentes, 2026-07-20): ocorrência
    // FUTURA projetada de um template ativo - previsão, não história. O
    // item inteiro fica atenuado + dot vazado (anel, não preenchido) +
    // selo "Previsto", para nunca se confundir com lançamento real.
    <div className={`flex items-start gap-2.5 ${evento.previsto ? "opacity-70" : ""}`}>
      {evento.previsto ? (
        <span
          className={`mt-1 h-2 w-2 shrink-0 rounded-full border-2 ${COR_DOT_POR_CATEGORIA[evento.categoria].replace("bg-", "border-")}`}
          aria-hidden="true"
        />
      ) : (
        <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${COR_DOT_POR_CATEGORIA[evento.categoria]}`} aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-micro uppercase tracking-wide text-text-tertiary">
          <Icon size={12} aria-hidden="true" />
          {LABEL_CATEGORIA_EVENTO[evento.categoria]}
          {evento.previsto && (
            <span className="rounded-full border border-border-subtle px-1.5 py-px normal-case tracking-normal">
              Previsto
            </span>
          )}
        </div>
        <p className="mt-0.5 font-medium text-text-primary">{evento.descricao}</p>
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className={`tabular font-semibold ${TEXT_COR_POR_CATEGORIA[evento.categoria]}`}>
            {evento.categoria === "DESPESA" ? "− " : evento.categoria === "RECEITA" ? "+ " : ""}
            {formatMoney(evento.valor)}
          </span>
          {evento.status && <span className="text-micro text-text-tertiary">{evento.status}</span>}
        </div>
        {destino && (
          <button
            type="button"
            onClick={() => navigate(destino)}
            className="mt-2 text-micro font-medium text-accent transition-colors duration-fast ease-out hover:text-accent-hover"
          >
            Ver detalhes →
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Grupo consolidado de parcelas de Parcelamento (Sprint de Refinamento
 * Premium, item 5, `docs/analise-arquitetural-sprint-refinamento-premium.md`
 * seção 5): "ocultar parcelas individuais, manter eventos agregados" -
 * puramente de apresentação, nenhuma regra nova. Dentro de um mesmo dia, 2+
 * parcelas de parcelamentos DIFERENTES (a única forma de colidir na mesma
 * data, já que cada Parcelamento gera no máximo 1 parcela por mês) somem da
 * lista "achatada" e viram um único cartão com o total, recolhido por
 * padrão - clique para expandir e ver cada parcela individualmente (nada é
 * perdido, só não aparece já expandido por padrão).
 */
function GrupoParcelas({ eventos }: { eventos: EventoCalendario[] }) {
  const [expandido, setExpandido] = useState(false);
  const total = eventos.reduce((soma, e) => soma + Number(e.valor), 0);

  return (
    <div className="rounded-md border border-border-subtle bg-surface-2 p-3">
      <button
        type="button"
        onClick={() => setExpandido((atual) => !atual)}
        className="flex w-full items-center gap-2.5 text-left"
        aria-expanded={expandido}
      >
        {expandido ? (
          <ChevronDown size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
        ) : (
          <ChevronRight size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
        )}
        <Layers size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
        <span className="min-w-0 flex-1 text-sm font-medium text-text-primary">
          {eventos.length} parcelas de compras parceladas
        </span>
        <span className="tabular shrink-0 font-semibold text-negative">− {formatMoney(total)}</span>
      </button>
      {expandido && (
        <ul className="mt-3 space-y-3 border-t border-border-subtle pt-3">
          {eventos.map((evento, index) => (
            <li key={`${evento.origem_tipo}-${evento.origem_id}-${index}`}>
              <ItemEvento evento={evento} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Drawer lateral com todos os eventos de UM dia — aberto ao clicar num dia
 * do `CalendarioMensal`. Cada evento mostra categoria (cor + label),
 * origem (ícone), valor, status e, quando existe rota conhecida
 * (`origemNavegacao.ts`, mesmo mapa da Agenda do Dashboard), um link direto
 * para a tela correspondente — "Fatura → Cartão", "Transferência →
 * Transferências", etc. (pedido explícito do usuário).
 *
 * Sem horário: nenhuma entidade do domínio guarda hora, só `date` (ver
 * models do backend) — mostrar um horário inventado seria informação
 * falsa. Campo omitido de propósito, não esquecido.
 */
export function EventoDiaDrawer({ iso, eventos, onClose }: EventoDiaDrawerProps) {
  const parcelas = eventos.filter((e) => e.origem_tipo === "PARCELAMENTO");
  const outros = eventos.filter((e) => e.origem_tipo !== "PARCELAMENTO");
  // Só agrupa quando há 2+ - uma única parcela no dia não precisa de
  // consolidação, é só mais um evento normal (mesmo tratamento de sempre).
  const agrupaParcelas = parcelas.length > 1;

  return (
    <Drawer
      open={iso != null}
      title={iso ? formatDate(iso) : ""}
      description={`${eventos.length} evento${eventos.length === 1 ? "" : "s"} neste dia`}
      onClose={onClose}
    >
      <ul className="space-y-3">
        {agrupaParcelas ? (
          <li>
            <GrupoParcelas eventos={parcelas} />
          </li>
        ) : (
          parcelas.map((evento, index) => (
            <li key={`${evento.origem_tipo}-${evento.origem_id}-${index}`} className="rounded-md border border-border-subtle bg-surface-2 p-3">
              <ItemEvento evento={evento} />
            </li>
          ))
        )}
        {outros.map((evento, index) => (
          <li key={`${evento.origem_tipo}-${evento.origem_id}-${index}`} className="rounded-md border border-border-subtle bg-surface-2 p-3">
            <ItemEvento evento={evento} />
          </li>
        ))}
      </ul>
    </Drawer>
  );
}
