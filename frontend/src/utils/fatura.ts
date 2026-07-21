import type { FaturaRead, StatusFatura } from "../types/fatura";

/**
 * Função pura de apresentação — decide qual fatura, dentre as já
 * carregadas de um cartão (`useFaturas`), é "a próxima" a mostrar em
 * destaque (`CartaoResumoCard`/`ProximaFaturaCard`). Nenhum cálculo de
 * negócio novo: só ordena o que o backend já entregeu, mesmo espírito de
 * `ordenarCategoriasPorHierarquia` (função pura derivada no frontend).
 *
 * Prioridade: `ATRASADA` > `ABERTA` > `PARCIALMENTE_PAGA`/`FECHADA` (ainda
 * pendente de ação) > `PAGA` (só informativo). Dentro dos três primeiros
 * grupos, a fatura com vencimento mais próximo vence a comparação (é a que
 * precisa de atenção primeiro); dentro de `PAGA`, a mais recente vence (é
 * a única que ainda é "relevante" olhar).
 */
const PRIORIDADE: Record<StatusFatura, number> = {
  ATRASADA: 0,
  ABERTA: 1,
  PARCIALMENTE_PAGA: 2,
  FECHADA: 2,
  PAGA: 3,
};

/** Preview client-side de "como fica a fatura depois deste pagamento" —
 * `docs/analise-arquitetural-refinamento-fatura-pagamento.md`, seção 4.
 * Espelha a MESMA prioridade de `FaturaService._derivar_status`
 * (quitada > atrasada > parcial > só fechada), mas é puramente uma função
 * de EXIBIÇÃO: nunca persistida, descartada assim que a mutation real
 * resolve e os dados voltam a vir de `useFatura`/`useFaturas`. Não é uma
 * segunda fonte de verdade — é só o que o backend provavelmente vai
 * responder, mostrado um instante antes de confirmar. */
export function preverStatusPosPagamento(
  fatura: Pick<FaturaRead, "valor_total" | "valor_pago" | "data_vencimento" | "status">,
  valorDigitado: number,
): StatusFatura {
  const valorTotal = Number(fatura.valor_total);
  const novoValorPago = Number(fatura.valor_pago) + (Number.isNaN(valorDigitado) ? 0 : valorDigitado);

  if (valorTotal > 0 && novoValorPago >= valorTotal) return "PAGA";
  if (new Date() > new Date(fatura.data_vencimento) && novoValorPago < valorTotal) return "ATRASADA";
  if (novoValorPago > 0) return "PARCIALMENTE_PAGA";
  return "FECHADA";
}

/**
 * Prioridade de desempate da LISTAGEM de faturas (`CartaoDetalhePage`,
 * pedido do usuário: "paga -> fechada -> aberta"). Critério primário real é
 * `mes_referencia` ascendente (mais antiga primeiro), já garantido pelo
 * backend (`FaturaRepository.listar_do_cartao`) - este mapa só desempata o
 * caso (na prática inexistente, já que `(cartao_id, mes_referencia)` é
 * único) de duas faturas caindo no mesmo mês. Distinta de `PRIORIDADE`
 * acima: aquela decide qual fatura merece DESTAQUE (mais urgente primeiro),
 * esta só ordena uma lista já cronológica.
 */
const PRIORIDADE_LISTAGEM: Record<StatusFatura, number> = {
  PAGA: 0,
  PARCIALMENTE_PAGA: 1,
  FECHADA: 2,
  ATRASADA: 3,
  ABERTA: 4,
};

/** Ordena faturas para exibição em lista: mais antiga → mais recente,
 * com o status como critério de desempate (paga → fechada → aberta). */
export function ordenarFaturasParaListagem(faturas: FaturaRead[]): FaturaRead[] {
  return [...faturas].sort((a, b) => {
    const diferenca = new Date(a.mes_referencia).getTime() - new Date(b.mes_referencia).getTime();
    if (diferenca !== 0) return diferenca;
    return PRIORIDADE_LISTAGEM[a.status] - PRIORIDADE_LISTAGEM[b.status];
  });
}

export function selecionarProximaFatura(faturas: FaturaRead[]): FaturaRead | null {
  if (faturas.length === 0) return null;

  const ordenadas = [...faturas].sort((a, b) => {
    const prioridadeA = PRIORIDADE[a.status];
    const prioridadeB = PRIORIDADE[b.status];
    if (prioridadeA !== prioridadeB) return prioridadeA - prioridadeB;

    const diferenca = new Date(a.data_vencimento).getTime() - new Date(b.data_vencimento).getTime();
    // Grupos com ação pendente: vencimento mais próximo primeiro (ascendente).
    // Grupo só informativo (PAGA): a mais recente primeiro (descendente).
    return prioridadeA <= 2 ? diferenca : -diferenca;
  });

  return ordenadas[0];
}
