import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard, Wallet } from "lucide-react";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { formatMoney } from "../../../utils/format";
import { useCartoesQuery, useContasQuery } from "../../../hooks/useCentralFinanceiraQueries";
import type { CartaoRead, ContaRead } from "../../../types/centralFinanceira";

const QUANTIDADE_PRINCIPAIS = 3;

/**
 * Combina `ContasCard` + `CartoesCard` (antigos) numa lista compacta só —
 * Refinamento Visual, pedido explícito do usuário (referência de outro
 * app: "Contas e Cartões" numa lista única). Cada linha navega para seu
 * próprio destino (`/contas` ou `/cartoes/:id`) — diferente dos dois cards
 * antigos, que tornavam o CARD INTEIRO clicável para um único destino; aqui
 * não faria sentido (duas famílias de destino diferentes na mesma lista).
 * Reaproveita `useContasQuery`/`useCartoesQuery` já existentes — nenhum
 * endpoint novo. Ver docs/analise-arquitetural-dashboard-hero-redesign.md,
 * decisão 4.
 */
export function ContasCartoesCard() {
  const navigate = useNavigate();
  const { data: dadosContas, isLoading: carregandoContas, error: erroContas, refetch: refetchContas } = useContasQuery();
  const { data: dadosCartoes, isLoading: carregandoCartoes, error: erroCartoes, refetch: refetchCartoes } = useCartoesQuery();

  if (carregandoContas || carregandoCartoes) return <LoadingCard lines={4} />;

  if (erroContas || erroCartoes) {
    return (
      <Card>
        <SectionTitle>Contas e cartões</SectionTitle>
        <ErrorMessage error={erroContas ?? erroCartoes} />
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            refetchContas();
            refetchCartoes();
          }}
          className="mt-3"
        >
          Tentar novamente
        </Button>
      </Card>
    );
  }

  const contas = dadosContas?.contas ?? [];
  const cartoes = (dadosCartoes?.cartoes ?? []).filter((cartao) => cartao.ativo);

  if (contas.length === 0 && cartoes.length === 0) return null;

  const principaisContas = [...contas]
    .sort((a, b) => Number(b.saldo_atual) - Number(a.saldo_atual))
    .slice(0, QUANTIDADE_PRINCIPAIS);
  const principaisCartoes = [...cartoes]
    .sort((a, b) => Number(b.limite_disponivel) - Number(a.limite_disponivel))
    .slice(0, QUANTIDADE_PRINCIPAIS);

  const restanteContas = contas.length - principaisContas.length;
  const restanteCartoes = cartoes.length - principaisCartoes.length;

  function irPara(rota: string) {
    return () => navigate(rota);
  }

  function onKeyDownLinha(rota: string) {
    return (event: KeyboardEvent<HTMLLIElement>) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        navigate(rota);
      }
    };
  }

  return (
    <Card>
      <SectionTitle>Contas e cartões</SectionTitle>
      <ul className="space-y-1">
        {principaisContas.map((conta: ContaRead) => (
          <li
            key={`conta-${conta.id}`}
            role="link"
            tabIndex={0}
            onClick={irPara("/contas")}
            onKeyDown={onKeyDownLinha("/contas")}
            className="flex cursor-pointer items-center justify-between gap-2 rounded-md px-1.5 py-1.5 text-sm transition-colors duration-fast ease-out hover:bg-surface-3"
          >
            <span className="flex min-w-0 items-center gap-2 text-text-secondary">
              <InstitutionBadge nome={conta.instituicao} size="sm" />
              <span className="truncate">{conta.nome}</span>
            </span>
            <span className="tabular shrink-0 text-text-primary">{formatMoney(conta.saldo_atual)}</span>
          </li>
        ))}
        {principaisCartoes.map((cartao: CartaoRead) => (
          <li
            key={`cartao-${cartao.id}`}
            role="link"
            tabIndex={0}
            onClick={irPara(`/cartoes/${cartao.id}`)}
            onKeyDown={onKeyDownLinha(`/cartoes/${cartao.id}`)}
            className="flex cursor-pointer items-center justify-between gap-2 rounded-md px-1.5 py-1.5 text-sm transition-colors duration-fast ease-out hover:bg-surface-3"
          >
            <span className="flex min-w-0 items-center gap-2 text-text-secondary">
              <InstitutionBadge nome={cartao.instituicao} size="sm" />
              <span className="truncate">{cartao.nome}</span>
            </span>
            <span className="shrink-0 text-right">
              <span className="block text-caption text-text-tertiary">Limite disponível</span>
              <span className="tabular block text-text-primary">{formatMoney(cartao.limite_disponivel)}</span>
            </span>
          </li>
        ))}
      </ul>
      {(restanteContas > 0 || restanteCartoes > 0) && (
        <div className="mt-2 flex items-center gap-3 border-t border-border-subtle pt-2 text-caption text-text-tertiary">
          {restanteContas > 0 && (
            <button
              type="button"
              onClick={irPara("/contas")}
              className="flex items-center gap-1 transition-colors duration-fast ease-out hover:text-accent"
            >
              <Wallet size={12} aria-hidden="true" />+ {restanteContas} conta(s)
            </button>
          )}
          {restanteCartoes > 0 && (
            <button
              type="button"
              onClick={irPara("/cartoes")}
              className="flex items-center gap-1 transition-colors duration-fast ease-out hover:text-accent"
            >
              <CreditCard size={12} aria-hidden="true" />+ {restanteCartoes} cartão(ões)
            </button>
          )}
        </div>
      )}
    </Card>
  );
}
