/**
 * Espelha 1:1 `app/schemas/parcelamento.py` (backend). Ver
 * app/services/parcelamento_service.py: criar um Parcelamento GERA
 * `num_parcelas` `Transacao` reais na hora (uma por parcela, todas
 * `DESPESA` — o schema nem aceita `tipo`), cada uma já com
 * `parcelamento_id` preenchido. Não existe endpoint de edição — campos
 * estruturais são imutáveis após a criação (mudar exigiria renumerar
 * parcelas já geradas); a única transição é `cancelar`.
 */
export interface ParcelamentoRead {
  id: number;
  descricao: string;
  valor_total: string;
  num_parcelas: number;
  taxa_juros: string | null;
  data_inicio: string;
  ativo: boolean;
  categoria_id: number | null;
  cartao_id: number | null;
  conta_id: number | null;
}

/** `cartao_id` XOR `conta_id` — exatamente um dos dois, validado pelo
 * backend (`ParcelamentoService._validar_estrutura`).
 *
 * `valor_parcela` (opcional): quando informado, TODAS as N parcelas nascem
 * com exatamente este valor em vez de `valor_total` dividido igualmente —
 * existe para quando a loja/operadora já cobra um valor fixo por parcela
 * que embute juros (não bate com uma divisão exata de `valor_total`). Sem
 * ele, o comportamento padrão (divisão exata, resto na última parcela)
 * continua o mesmo de sempre. */
export interface ParcelamentoCreate {
  descricao: string;
  valor_total: string;
  num_parcelas: number;
  taxa_juros?: string | null;
  valor_parcela?: string | null;
  data_inicio: string;
  categoria_id?: number | null;
  cartao_id?: number | null;
  conta_id?: number | null;
}
