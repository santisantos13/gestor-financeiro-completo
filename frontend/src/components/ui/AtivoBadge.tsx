import { Badge } from "./Badge";
import { StatusDot } from "./StatusDot";

export interface AtivoBadgeProps {
  ativo: boolean;
  /** Rótulos com concordância de gênero (ex. "Ativa"/"Inativa" para
   * Conta/Categoria/Tag, "Ativo"/"Inativo" para Cartão) — default
   * masculino. */
  labelAtivo?: string;
  labelInativo?: string;
  className?: string;
}

/**
 * Badge de ativo/inativo — extraído do `<Badge tone={x.ativo ?
 * "positive" : "neutral"}>` duplicado em `contaTableColumns.tsx`/
 * `categoriaTableColumns.tsx`/`tagTableColumns.tsx`/`CartaoResumoCard.tsx`
 * (revisão de UX de Cartões: "não pense apenas no módulo de Cartões,
 * pense no sistema inteiro"). Um só lugar para o estado mais repetido do
 * projeto (toda entidade tem `ativo: boolean`), com `StatusDot` reforçando
 * o estado por uma segunda pista visual (posição/forma, não só tonalidade
 * de fundo) — "estados devem ser percebidos sem precisar ler".
 */
export function AtivoBadge({ ativo, labelAtivo = "Ativo", labelInativo = "Inativo", className }: AtivoBadgeProps) {
  return (
    <Badge tone={ativo ? "positive" : "neutral"} className={className}>
      <StatusDot tone={ativo ? "positive" : "neutral"} className="mr-1" />
      {ativo ? labelAtivo : labelInativo}
    </Badge>
  );
}
