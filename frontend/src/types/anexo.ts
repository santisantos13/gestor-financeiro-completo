/**
 * Espelha 1:1 `app/schemas/anexo.py` — conferido por leitura direta do
 * backend. Sem `AnexoUpdate`: Anexo é create + read + soft-delete apenas,
 * decisão já confirmada no backend (ver docs/analise-arquitetural-anexo.md).
 *
 * `caminho_arquivo` é só uma referência textual (caminho local, URL, chave
 * de storage externo) — o backend nunca armazena o binário em si (ver
 * docs/analise-arquitetural-anexo-frontend.md).
 */
export interface AnexoRead {
  id: number;
  transacao_id: number;
  nome_original: string;
  caminho_arquivo: string;
  mime_type: string | null;
  tamanho_bytes: number | null;
  data_upload: string;
  ativo: boolean;
}

export interface AnexoCreate {
  transacao_id: number;
  nome_original: string;
  caminho_arquivo: string;
  mime_type?: string | null;
  tamanho_bytes?: number | null;
}
