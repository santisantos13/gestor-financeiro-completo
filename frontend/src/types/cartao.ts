/**
 * Espelha 1:1 `app/schemas/cartao.py` — conferido por leitura direta do
 * backend (`CartaoCreate`/`CartaoUpdate`/`CartaoRead`). Mesmo tratamento de
 * `types/conta.ts`: todo valor monetário é `string` (nunca `number`),
 * `limite_disponivel` existe só em `CartaoRead` (calculado pelo
 * `CartaoService` a cada leitura, nunca uma coluna — mesmo princípio de
 * `ContaRead.saldo_atual`, **pode ficar negativo de propósito**, nunca
 * "clampado" em zero).
 */
import type { Bandeira } from "./enums";

export type { Bandeira };

export interface CartaoRead {
  id: number;
  nome: string;
  conta_pagamento_id: number;
  instituicao: string;
  bandeira: Bandeira;
  ultimos_quatro_digitos: string;
  limite: string;
  limite_disponivel: string;
  dia_fechamento: number;
  dia_vencimento: number;
  ativo: boolean;
  /** "Estado Inicial do Cartão" — quanto do limite já estava em uso quando
   * o cartão foi cadastrado, declarado direto (sem Fatura/Transacao por
   * trás). Consome `limite_disponivel` permanentemente até o usuário
   * editar/zerar (Sprint de Refinamento Premium, 2026-07). */
  saldo_inicial_utilizado: string;
}

export interface CartaoCreate {
  nome: string;
  conta_pagamento_id: number;
  instituicao: string;
  bandeira: Bandeira;
  ultimos_quatro_digitos: string;
  limite: string;
  dia_fechamento: number;
  dia_vencimento: number;
  saldo_inicial_utilizado?: string;
}

/** Semântica de PATCH — todo campo omitido permanece intocado. Reativar um
 * cartão desativado é `PATCH { ativo: true }`, mesmo endpoint de edição
 * (mesma decisão de Conta/Categoria/Tag). */
export interface CartaoUpdate {
  nome?: string;
  conta_pagamento_id?: number;
  instituicao?: string;
  bandeira?: Bandeira;
  ultimos_quatro_digitos?: string;
  limite?: string;
  dia_fechamento?: number;
  dia_vencimento?: number;
  ativo?: boolean;
  saldo_inicial_utilizado?: string;
}
