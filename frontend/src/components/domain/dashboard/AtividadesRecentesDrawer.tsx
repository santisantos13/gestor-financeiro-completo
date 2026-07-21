import { useNavigate } from "react-router-dom";
import { Drawer } from "../../ui/Drawer";
import { formatDateTime } from "../../../utils/date";
import { formatMoney } from "../../../utils/format";
import { ICONE_POR_ORIGEM, ROTA_POR_ORIGEM } from "../../../lib/origemNavegacao";
import { useAtividadesRecentesQuery } from "../../../hooks/useCentralFinanceiraQueries";
import type { AtividadeRecente } from "../../../types/centralFinanceira";

export interface AtividadesRecentesDrawerProps {
  open: boolean;
  onClose: () => void;
}

function ItemAtividade({ atividade }: { atividade: AtividadeRecente }) {
  const navigate = useNavigate();
  const Icon = ICONE_POR_ORIGEM[atividade.origem_tipo];
  const construirRota = ROTA_POR_ORIGEM[atividade.origem_tipo];
  const destino = construirRota ? construirRota(atividade.origem_id) : null;

  return (
    <li className="rounded-md border border-border-subtle bg-surface-2 p-3">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 shrink-0 rounded-sm bg-surface-3 p-1.5 text-text-tertiary">
          <Icon size={14} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-medium text-text-primary">{atividade.descricao}</p>
          <div className="mt-1 flex items-center justify-between gap-2">
            <span className="text-micro text-text-tertiary">{formatDateTime(atividade.data_hora)}</span>
            {atividade.valor != null && (
              <span className="tabular font-semibold text-text-primary">{formatMoney(atividade.valor)}</span>
            )}
          </div>
          {destino && (
            <button
              type="button"
              onClick={() => {
                navigate(destino);
                // O onClose acontece depois do navigate para o Drawer não
                // "piscar" antes da troca de rota - mesmo comportamento já
                // usado pelo Command Palette (CommandPalette.tsx).
              }}
              className="mt-2 text-micro font-medium text-accent transition-colors duration-fast ease-out hover:text-accent-hover"
            >
              Ver detalhes →
            </button>
          )}
        </div>
      </div>
    </li>
  );
}

/**
 * Central de Atividades (Sprint de Refinamento Premium, item 17) — Drawer
 * aberto a partir de um botão no `Header`, mostra o feed cronológico
 * combinado de `GET /central-financeira/atividades` (Transação/
 * Transferência/Meta concluída, já ordenado pelo backend - ver
 * `CentralFinanceiraService.atividades_recentes`). Mesmo padrão visual de
 * `EventoDiaDrawer` (ícone por origem + link "Ver detalhes" quando a rota é
 * conhecida), aberto globalmente (não preso a um dia específico).
 */
export function AtividadesRecentesDrawer({ open, onClose }: AtividadesRecentesDrawerProps) {
  const { data, isLoading } = useAtividadesRecentesQuery();
  const atividades = data?.atividades ?? [];

  return (
    <Drawer
      open={open}
      title="Atividades recentes"
      description="O que aconteceu na sua vida financeira, do mais novo para o mais antigo"
      onClose={onClose}
    >
      {isLoading ? (
        <p className="text-sm text-text-tertiary">Carregando...</p>
      ) : atividades.length === 0 ? (
        <p className="text-sm text-text-tertiary">Nenhuma atividade registrada ainda.</p>
      ) : (
        <ul className="space-y-3">
          {atividades.map((atividade, index) => (
            <ItemAtividade key={`${atividade.origem_tipo}-${atividade.origem_id}-${index}`} atividade={atividade} />
          ))}
        </ul>
      )}
    </Drawer>
  );
}
