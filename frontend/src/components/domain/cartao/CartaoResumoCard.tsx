import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { Card } from "../../ui/Card";
import { AtivoBadge } from "../../ui/AtivoBadge";
import { AnimatedNumber } from "../../ui/AnimatedNumber";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { Skeleton } from "../../ui/Skeleton";
import { CartaoVisual } from "./CartaoVisual";
import { CartaoActionBar } from "./CartaoActionBar";
import { useFaturas } from "../../../hooks/useFaturaQueries";
import { lerVariantePreferida } from "../../../lib/cardThemes";
import { selecionarProximaFatura } from "../../../utils/fatura";
import { diferencaEmDias } from "../../../utils/date";
import { tonePorUtilizacao, tonePorPrazo, TEXT_TONE_CLASS } from "../../../utils/status";
import type { CartaoRead } from "../../../types/cartao";

export interface CartaoResumoCardProps {
  cartao: CartaoRead;
  onEditar: (cartao: CartaoRead) => void;
  onDesativar: (cartao: CartaoRead) => void;
  onReativar: (cartao: CartaoRead) => void;
  onExcluir: (cartao: CartaoRead) => void;
}

/**
 * Card clicável do grid de `/cartoes` — "mini dashboard" pedido na revisão
 * de UX (`docs/analise-arquitetural-revisao-ux-cartoes.md`, seções 3/4).
 * Ordem de leitura dentro do card (storytelling): `CartaoVisual` resolve
 * "qual cartão" + "como está a utilização" (ele já embute badges/dígitos/
 * barra de utilização — não duplicada aqui); logo abaixo, "disponível" em
 * destaque hero resolve "quanto ainda posso gastar"; a seguir, a fatura
 * mais relevante resolve "qual a próxima fatura"; um chip de alerta só
 * aparece quando exige ação; e a `CartaoActionBar` fecha o card.
 *
 * O card inteiro é clicável (navega para a página de detalhes) sem
 * envolver tudo num `<a>` — um `<button>` da Action Bar dentro de um `<a>`
 * seria HTML inválido (elemento interativo aninhado). Em vez disso, o
 * próprio `Card` (um `<div>`) ganha `role="link"` + `tabIndex` +
 * `onClick`/`onKeyDown`, e cada botão da Action Bar já faz
 * `stopPropagation` (`CartaoActionBar`) — mesmo padrão de qualquer elemento
 * interativo dentro de uma linha/card clicável.
 */
export function CartaoResumoCard({ cartao, onEditar, onDesativar, onReativar, onExcluir }: CartaoResumoCardProps) {
  const navigate = useNavigate();
  const { data: faturas, isLoading: carregandoFaturas } = useFaturas(cartao.id);

  const limiteNumero = Number(cartao.limite);
  const disponivelNumero = Number(cartao.limite_disponivel);
  const utilizadoNumero = limiteNumero - disponivelNumero;
  const percentual = limiteNumero > 0 ? (utilizadoNumero / limiteNumero) * 100 : 0;
  const tonePercentual = TEXT_TONE_CLASS[tonePorUtilizacao(percentual)];

  const proximaFatura = selecionarProximaFatura(faturas ?? []);
  const diferencaVencimento = proximaFatura ? diferencaEmDias(proximaFatura.data_vencimento) : null;
  const toneVencimento = diferencaVencimento != null ? tonePorPrazo(diferencaVencimento) : "info";
  const precisaAtencao = proximaFatura?.status === "ATRASADA" || percentual >= 90;

  function abrirDetalhes() {
    navigate(`/cartoes/${cartao.id}`);
  }

  function abrirFaturas() {
    navigate(`/cartoes/${cartao.id}#faturas`);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      abrirDetalhes();
    }
  }

  return (
    <Card
      role="link"
      tabIndex={0}
      onClick={abrirDetalhes}
      onKeyDown={onKeyDown}
      aria-label={`Ver detalhes do cartão ${cartao.nome}`}
      animateEntrance
      className={`flex cursor-pointer flex-col gap-4 ${!cartao.ativo ? "opacity-70" : ""}`}
    >
      <CartaoVisual
        nome={cartao.nome}
        instituicao={cartao.instituicao}
        bandeira={cartao.bandeira}
        ultimosQuatroDigitos={cartao.ultimos_quatro_digitos}
        limite={cartao.limite}
        limiteDisponivel={cartao.limite_disponivel}
        diaFechamento={cartao.dia_fechamento}
        diaVencimento={cartao.dia_vencimento}
        variantId={lerVariantePreferida(cartao.id)}
        className="max-w-none"
      />

      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-caption text-text-tertiary">Disponível</p>
          <AnimatedNumber
            value={cartao.limite_disponivel}
            format="money"
            className="text-h2 font-semibold text-text-primary"
          />
        </div>
        <div className={`text-right text-sm font-medium ${tonePercentual}`}>
          <AnimatedNumber value={percentual} format="percent" /> usado
        </div>
      </div>

      {!cartao.ativo ? (
        <AtivoBadge ativo={false} />
      ) : carregandoFaturas ? (
        <Skeleton className="h-9 w-full" />
      ) : proximaFatura && diferencaVencimento != null ? (
        <div className="flex items-center justify-between gap-2 rounded-md border border-border-subtle bg-surface-1 px-3 py-2 text-sm">
          <FinancialBadge status={proximaFatura.status} />
          <span className={`font-medium ${TEXT_TONE_CLASS[toneVencimento]}`}>
            {proximaFatura.status === "ATRASADA"
              ? `Atrasada há ${Math.abs(diferencaVencimento)}d`
              : `Vence em ${Math.max(0, diferencaVencimento)}d`}
          </span>
        </div>
      ) : null}

      {precisaAtencao && (
        <div className="flex items-center gap-1.5 text-caption text-warning">
          <AlertTriangle size={12} aria-hidden="true" />
          {proximaFatura?.status === "ATRASADA" ? "Fatura atrasada" : "Limite quase no fim"}
        </div>
      )}

      <CartaoActionBar
        ativo={cartao.ativo}
        onEditar={() => onEditar(cartao)}
        onFaturas={abrirFaturas}
        onDesativar={() => onDesativar(cartao)}
        onReativar={() => onReativar(cartao)}
        onExcluir={() => onExcluir(cartao)}
      />
    </Card>
  );
}
