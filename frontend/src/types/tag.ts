/**
 * Espelha 1:1 `app/schemas/tag.py` — conferido por leitura direta do
 * backend (`TagCreate`/`TagUpdate`/`TagRead`), não de documentação. Ver
 * docs/analise-arquitetural-tag-frontend.md, seção 2.1.
 *
 * Diferente de `CategoriaRead`, não há campo computado equivalente a
 * `e_do_sistema` — toda Tag pertence a um usuário, sem exceção.
 */

export interface TagRead {
  id: number;
  nome: string;
  cor: string | null;
  ativo: boolean;
}

export interface TagCreate {
  nome: string;
  cor?: string | null;
}

/** Semântica de PATCH no backend — todo campo omitido permanece intocado.
 * Inclui `ativo`: reativar uma tag desativada é um PATCH `{ ativo: true }`,
 * mesmo endpoint usado para editar qualquer outro campo (mesmo padrão de
 * `ContaUpdate`/`CategoriaUpdate`). */
export interface TagUpdate {
  nome?: string;
  cor?: string | null;
  ativo?: boolean;
}

/** Espelha `TagUso` (`app/schemas/tag.py`) — resposta de
 * `GET /tags/{id}/uso`, Etapa F10 (Exclusão definitiva,
 * `docs/analise-arquitetural-exclusao.md`, seção 2.3). Só informativo: Tag
 * nunca bloqueia exclusão por uso. */
export interface TagUso {
  transacoes_vinculadas: number;
}
