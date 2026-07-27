/**
 * Espelha 1:1 `app/schemas/alerta.py` — conferido por leitura direta do
 * backend (`AlertaCreate`/`AlertaUpdate`/`AlertaRead`). `TipoAlerta` já
 * existe em `types/enums.ts` (reaproveitado, não redeclarado aqui) —
 * `entidade_tipo` nunca aparece em nenhum schema, nem aqui: é detalhe
 * interno do backend (derivado de `tipo`), o frontend só precisa de
 * `tipo` + `entidade_id` para montar o payload e escolher qual picker de
 * entidade mostrar (ver `schemas/alerta.ts`).
 *
 * `condicao` tem formato dependente de `tipo` (documentado uma única vez
 * no backend, `AlertaService._normalizar_condicao` — não duplicado aqui
 * além do necessário para tipar):
 * - LIMITE_CARTAO: `{ limite_percentual: number }` — obrigatório.
 * - VENCIMENTO_FATURA / VENCIMENTO_CONTA_RECORRENTE: `{ dias_antes: number }`
 *   — opcional, backend aplica default de 3 dias quando omitido.
 * - META_ATINGIDA: sempre `null`.
 * - SALDO_BAIXO: `{ valor_minimo: number }` — obrigatório.
 *
 * `disparado`/`mensagem` são campos CALCULADOS em tempo real pelo backend
 * a cada leitura (nunca um histórico persistido) — `null` quando o alerta
 * está pausado (`ativo=false`), nunca avaliado nesse caso.
 */
import type { TipoAlerta } from "./enums";

export type { TipoAlerta };

export interface CondicaoLimiteCartao {
  limite_percentual: number;
}

export interface CondicaoDiasAntes {
  dias_antes: number;
}

export interface CondicaoSaldoMinimo {
  valor_minimo: number;
}

export type AlertaCondicao = CondicaoLimiteCartao | CondicaoDiasAntes | CondicaoSaldoMinimo | null;

export interface AlertaRead {
  id: number;
  tipo: TipoAlerta;
  entidade_id: number | null;
  condicao: AlertaCondicao;
  ativo: boolean;
  ultima_disparada_em: string | null;
  criado_em: string;
  disparado: boolean | null;
  mensagem: string | null;
}

export interface AlertaCreate {
  tipo: TipoAlerta;
  entidade_id: number;
  condicao?: AlertaCondicao;
}

/** Semântica de PATCH — campo omitido permanece intocado. `tipo`/
 * `entidade_id` são imutáveis após a criação (retargetar é, na prática, um
 * alerta diferente — ver docstring de `AlertaUpdate` no backend), por isso
 * nem aparecem aqui. */
export interface AlertaUpdate {
  condicao?: AlertaCondicao;
  ativo?: boolean;
}
