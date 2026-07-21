/**
 * Funções finas e tipadas — um por endpoint de `/contas/*`, mesmo padrão de
 * `centralFinanceiraService.ts`/`authService.ts`. Zero decisão aqui; toda
 * regra vive no backend (`app/api/routes/conta.py`). Consumido
 * exclusivamente por `hooks/useContaQueries.ts`.
 */
import { httpClient } from "../api/httpClient";
import type { ContaCreate, ContaExtrato, ContaRead, ContaUpdate } from "../types/conta";

export const contaService = {
  listar: (apenasAtivas = true) =>
    httpClient.get<ContaRead[]>("/contas", { apenas_ativas: apenasAtivas }),

  obter: (id: number) => httpClient.get<ContaRead>(`/contas/${id}`),

  criar: (dados: ContaCreate) => httpClient.post<ContaRead>("/contas", dados),

  atualizar: (id: number, dados: ContaUpdate) => httpClient.patch<ContaRead>(`/contas/${id}`, dados),

  /** `DELETE /contas/{id}` — soft delete no backend (`ativo = false`),
   * nunca remove a linha. 204 sem corpo. */
  desativar: (id: number) => httpClient.delete<void>(`/contas/${id}`),

  /** `DELETE /contas/{id}/permanente` — exclusão DEFINITIVA (hard delete),
   * Etapa F10 (`docs/analise-arquitetural-exclusao.md`). Ação nova, nunca
   * substitui `desativar`; backend responde 422 se a conta tiver qualquer
   * vínculo real (transação/transferência/cartão/financiamento/empréstimo/
   * recorrência) — a menos que `apagarVinculos` seja `true` (pedido
   * explícito do usuário, ver
   * docs/analise-arquitetural-exclusao-conta-com-historico.md): nesse caso
   * o backend apaga tudo que está vinculado à conta junto com ela, em vez
   * de bloquear. Conta oculta (cofrinho de Meta) continua sempre
   * bloqueada, independente deste parâmetro. */
  excluirPermanente: (id: number, apagarVinculos = false) =>
    httpClient.delete<void>(`/contas/${id}/permanente`, { apagar_vinculos: apagarVinculos }),

  /** `GET /contas/{id}/extrato` — painel "extrato bancário" pedido
   * explicitamente pelo usuário (histórico expansível de
   * `ContaResumoCard`). `ano`/`mes` opcionais, default = mês atual (mesma
   * convenção de ano+mes único já usada por Dashboard/Calendário, nunca um
   * range livre de datas). Ver docs/analise-arquitetural-extrato-conta.md. */
  obterExtrato: (id: number, ano?: number, mes?: number) =>
    httpClient.get<ContaExtrato>(`/contas/${id}/extrato`, { ano, mes }),
};
