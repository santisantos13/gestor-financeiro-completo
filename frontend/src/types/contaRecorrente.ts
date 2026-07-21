/**
 * Espelha 1:1 `app/schemas/conta_recorrente.py` — conferido por leitura
 * direta do backend (expansão de Contas Recorrentes, 2026-07-20, ver
 * docs/analise-arquitetural-conta-recorrente-expansao.md).
 *
 * `dia_vencimento` só se aplica a frequências baseadas em meses (MENSAL,
 * BIMESTRAL, TRIMESTRAL, SEMESTRAL, ANUAL) — nulo obrigatório nas baseadas
 * em dias (DIARIA/SEMANAL/QUINZENAL, âncora = `data_inicio`). O backend
 * valida por família; o formulário só condiciona a exibição do campo.
 *
 * `proxima_execucao` é o cursor materializado do backend — a UI mostra
 * "próxima ocorrência" direto daqui, sem recalcular nada no cliente.
 * `status`/`proxima_execucao` nunca são editáveis via PATCH: transições
 * são ações próprias (pausar/reativar/encerrar).
 */
import type { FrequenciaRecorrencia, StatusRecorrencia, TipoTransacao } from "./enums";

export type { FrequenciaRecorrencia, StatusRecorrencia };

export interface ContaRecorrenteRead {
  id: number;
  descricao: string;
  valor: string;
  tipo: TipoTransacao;
  frequencia: FrequenciaRecorrencia;
  dia_vencimento: number | null;
  status: StatusRecorrencia;
  proxima_execucao: string;

  categoria_id: number | null;
  conta_id: number | null;
  cartao_id: number | null;

  data_inicio: string;
  data_fim: string | null;
}

export interface ContaRecorrenteCreate {
  descricao: string;
  valor: string;
  tipo: TipoTransacao;
  frequencia: FrequenciaRecorrencia;
  dia_vencimento?: number | null;

  categoria_id?: number | null;
  conta_id?: number | null;
  cartao_id?: number | null;

  data_inicio: string;
  data_fim?: string | null;
}

/** Semântica de PATCH — campo omitido permanece intocado. */
export interface ContaRecorrenteUpdate {
  descricao?: string;
  valor?: string;
  tipo?: TipoTransacao;
  frequencia?: FrequenciaRecorrencia;
  dia_vencimento?: number | null;

  categoria_id?: number | null;
  conta_id?: number | null;
  cartao_id?: number | null;

  data_inicio?: string;
  data_fim?: string | null;
}

/** Resposta de `POST /contas-recorrentes/sincronizar` — `geradas > 0`
 * decide se os caches são invalidados (evita refetch em cascata a cada
 * login sem novidade). */
export interface SincronizacaoRecorrentesResult {
  geradas: number;
  encerradas: number;
}
