/**
 * Espelha 1:1 `app/schemas/categoria.py` — conferido por leitura direta do
 * backend (`CategoriaCreate`/`CategoriaUpdate`/`CategoriaRead`), não de
 * documentação. Ver docs/analise-arquitetural-categoria-frontend.md, seção
 * 2.1.
 *
 * `e_do_sistema` é um `@computed_field` do backend (`usuario_id is None`)
 * — o frontend nunca infere isso comparando `usuario_id` manualmente, só
 * lê o campo já pronto.
 */
import type { TipoCategoria } from "./enums";

export type { TipoCategoria };

export interface CategoriaRead {
  id: number;
  nome: string;
  tipo: TipoCategoria;
  cor: string | null;
  icone: string | null;
  categoria_pai_id: number | null;
  ativo: boolean;
  /** `true` = categoria do sistema (semeada, visível a todos, somente
   * leitura); `false` = categoria própria do usuário logado, livremente
   * editável. */
  e_do_sistema: boolean;
  /** Sprint de Refinamento Premium, item 4: `true` quando o usuário logado
   * pediu para não ver mais esta categoria de SISTEMA (nunca é `true` para
   * categoria própria - o conceito não existe pra ela). Não afeta os
   * outros usuários - a categoria continua existindo normalmente para
   * eles. Ver `docs/analise-arquitetural-sprint-refinamento-premium.md`,
   * seção 4. */
  oculta_para_mim: boolean;
}

export interface CategoriaCreate {
  nome: string;
  tipo: TipoCategoria;
  cor?: string | null;
  icone?: string | null;
  categoria_pai_id?: number | null;
}

/** Semântica de PATCH no backend — todo campo omitido permanece intocado.
 * Inclui `ativo`: reativar uma categoria desativada é um PATCH
 * `{ ativo: true }`, mesmo endpoint usado para editar qualquer outro
 * campo (mesmo padrão de `ContaUpdate`). Categorias de sistema rejeitam
 * qualquer PATCH com 403 (`AcessoNegadoError`), independentemente de quais
 * campos forem enviados. */
export interface CategoriaUpdate {
  nome?: string;
  tipo?: TipoCategoria;
  cor?: string | null;
  icone?: string | null;
  categoria_pai_id?: number | null;
  ativo?: boolean;
}
