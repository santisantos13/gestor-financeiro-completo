import { useMemo, useState, type KeyboardEvent, type MouseEvent } from "react";
import {
  ArrowDownCircle,
  ArrowLeftRight,
  ArrowUpCircle,
  ChevronDown,
  Landmark,
  Receipt,
  type LucideIcon,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { StatusDot } from "../../ui/StatusDot";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { AnimatedNumber } from "../../ui/AnimatedNumber";
import { Skeleton } from "../../ui/Skeleton";
import { PeriodoSeletor } from "../dashboard/PeriodoSeletor";
import { ContaActionBar } from "./ContaActionBar";
import { LABEL_TIPO_CONTA } from "./contaTableColumns";
import { useContaExtrato } from "../../../hooks/useContaQueries";
import { formatMoney } from "../../../utils/format";
import { formatDate, nomeMes } from "../../../utils/date";
import { DURATION, EASE } from "../../../lib/motion";
import type { ContaRead, MovimentacaoConta } from "../../../types/conta";
import type { CategoriaMovimentacaoConta } from "../../../types/enums";

export interface ContaResumoCardProps {
  conta: ContaRead;
  onEditar: (conta: ContaRead) => void;
  onDesativar: (conta: ContaRead) => void;
  onReativar: (conta: ContaRead) => void;
  onExcluir: (conta: ContaRead) => void;
}

type FiltroRapidoExtrato = "TODOS" | "ENTRADAS" | "SAIDAS" | "TRANSFERENCIAS" | "PAGAMENTOS";

const FILTROS_RAPIDOS: FiltroRapidoExtrato[] = ["TODOS", "ENTRADAS", "SAIDAS", "TRANSFERENCIAS", "PAGAMENTOS"];

const LABEL_FILTRO_RAPIDO: Record<FiltroRapidoExtrato, string> = {
  TODOS: "Todos",
  ENTRADAS: "Entradas",
  SAIDAS: "Saídas",
  TRANSFERENCIAS: "Transferências",
  PAGAMENTOS: "Pagamentos",
};

const ICONE_CATEGORIA: Record<CategoriaMovimentacaoConta, LucideIcon> = {
  RECEITA: ArrowDownCircle,
  DESPESA: ArrowUpCircle,
  TRANSFERENCIA_ENVIADA: ArrowLeftRight,
  TRANSFERENCIA_RECEBIDA: ArrowLeftRight,
  PAGAMENTO_FATURA: Receipt,
  PAGAMENTO_FINANCIAMENTO: Landmark,
  PAGAMENTO_EMPRESTIMO: Landmark,
};

function passaNoFiltroRapido(categoria: CategoriaMovimentacaoConta, filtro: FiltroRapidoExtrato): boolean {
  switch (filtro) {
    case "TODOS":
      return true;
    case "ENTRADAS":
      return categoria === "RECEITA" || categoria === "TRANSFERENCIA_RECEBIDA";
    case "SAIDAS":
      return categoria !== "RECEITA" && categoria !== "TRANSFERENCIA_RECEBIDA";
    case "TRANSFERENCIAS":
      return categoria === "TRANSFERENCIA_ENVIADA" || categoria === "TRANSFERENCIA_RECEBIDA";
    case "PAGAMENTOS":
      return (
        categoria === "PAGAMENTO_FATURA" ||
        categoria === "PAGAMENTO_FINANCIAMENTO" ||
        categoria === "PAGAMENTO_EMPRESTIMO"
      );
  }
}

/**
 * Linha compacta de Conta (Refinamento de densidade, pedido explícito do
 * usuário: os cards grandes do grid original "deixam a tela pesada e
 * exigem muita rolagem" — trocado por uma lista densa e escaneável,
 * parecida com um aplicativo bancário, sem perder nenhuma funcionalidade).
 * Renderizada como uma LINHA (não um `Card` próprio — a "sensação de
 * lista" pedida vem do container único em `ContasPage`, que usa
 * `divide-y` entre as linhas em vez de N cards com borda/sombra
 * empilhados). Logo à esquerda, nome em destaque + tipo/instituição como
 * legenda secundária, saldo alinhado à direita numa coluna de largura
 * fixa (`sm:w-32`, para os valores de todas as contas ficarem alinhados
 * verticalmente entre si), status como microindicador discreto
 * (`StatusDot` + texto, nunca mais um badge colorido cheio), ações
 * agrupadas e chevron por último — mesma ordem visual pedida.
 *
 * Clicar em qualquer ponto da linha (ou no chevron, que é só um ícone
 * dentro da mesma área clicável, não um botão separado) expande INLINE
 * abaixo dela um painel "extrato bancário" — resumo do período, mini
 * resumo do mês corrente, filtros rápidos e histórico cronológico. Ver
 * docs/analise-arquitetural-extrato-conta.md.
 *
 * Responsivo: no desktop tudo cabe numa linha só (`sm:flex-row`); no
 * mobile o bloco logo+nome+saldo forma a primeira linha e ações+chevron
 * caem para uma segunda linha (`flex-col` até o breakpoint `sm`),
 * preservando a "sensação de lista" em vez de virar um card empilhado.
 *
 * O extrato só é buscado quando a linha é de fato expandida
 * (`useContaExtrato(..., expandido)`, mesmo padrão de
 * `useAportesLegadosDaMeta`) — a página `/contas` nunca dispara N
 * requisições extras ao carregar. `PeriodoSeletor` (ano+mes, mesmo
 * componente já usado por Dashboard/Calendário/Transações) navega o
 * "resumo do período"; os filtros rápidos (Todos/Entradas/Saídas/
 * Transferências/Pagamentos) são 100% client-side sobre a lista já
 * carregada, mesmo padrão de `filtroRapido` em `MetasPage`.
 */
export function ContaResumoCard({ conta, onEditar, onDesativar, onReativar, onExcluir }: ContaResumoCardProps) {
  const [expandido, setExpandido] = useState(false);
  const hoje = new Date();
  const [ano, setAno] = useState(hoje.getFullYear());
  const [mes, setMes] = useState(hoje.getMonth() + 1);
  const [filtroRapido, setFiltroRapido] = useState<FiltroRapidoExtrato>("TODOS");

  const { data: extrato, isLoading: carregandoExtrato } = useContaExtrato(conta.id, ano, mes, expandido);

  const movimentacoesFiltradas = useMemo<MovimentacaoConta[]>(
    () => (extrato?.movimentacoes ?? []).filter((m) => passaNoFiltroRapido(m.categoria, filtroRapido)),
    [extrato, filtroRapido],
  );

  function alternarExpansao() {
    setExpandido((v) => !v);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      alternarExpansao();
    }
  }

  function pararPropagacao(event: MouseEvent<HTMLDivElement>) {
    event.stopPropagation();
  }

  return (
    <div className={!conta.ativo ? "opacity-70" : ""}>
      <div
        role="button"
        tabIndex={0}
        onClick={alternarExpansao}
        onKeyDown={onKeyDown}
        aria-expanded={expandido}
        aria-label={`${expandido ? "Recolher" : "Expandir"} extrato da conta ${conta.nome}`}
        className="flex cursor-pointer flex-col gap-2 px-4 py-3 transition-colors duration-fast ease-out hover:bg-surface-3 sm:flex-row sm:items-center sm:gap-4"
      >
        {/* logo + nome/subtítulo + saldo (mobile, inline na mesma linha) */}
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <InstitutionBadge nome={conta.instituicao} size="md" className="shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-text-primary">{conta.nome}</p>
            <p className="truncate text-caption text-text-tertiary">
              {LABEL_TIPO_CONTA[conta.tipo] ?? conta.tipo}
              {conta.instituicao ? ` · ${conta.instituicao}` : ""}
            </p>
          </div>
          <AnimatedNumber
            value={conta.saldo_atual}
            format="money"
            className="shrink-0 text-sm font-semibold text-text-primary sm:hidden"
          />
        </div>

        {/* saldo (desktop) - coluna de largura fixa, alinha entre todas as linhas */}
        <div className="hidden shrink-0 text-right sm:block sm:w-32">
          <AnimatedNumber value={conta.saldo_atual} format="money" className="text-sm font-semibold text-text-primary" />
        </div>

        {/* status - microindicador discreto, nunca um badge colorido cheio */}
        <div className="flex shrink-0 items-center gap-1.5 text-caption text-text-tertiary sm:w-16">
          <StatusDot tone={conta.ativo ? "positive" : "neutral"} />
          {conta.ativo ? "Ativa" : "Inativa"}
        </div>

        {/* ações + chevron - agrupados à direita, sempre na mesma linha entre si */}
        <div className="flex shrink-0 items-center justify-end gap-2" onClick={pararPropagacao}>
          <ContaActionBar
            ativo={conta.ativo}
            onEditar={() => onEditar(conta)}
            onDesativar={() => onDesativar(conta)}
            onReativar={() => onReativar(conta)}
            onExcluir={() => onExcluir(conta)}
          />
          <ChevronDown
            size={16}
            className={`shrink-0 text-text-tertiary transition-transform duration-fast ease-out ${expandido ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expandido && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto", transition: { duration: DURATION.moderate, ease: EASE.out } }}
            exit={{ opacity: 0, height: 0, transition: { duration: DURATION.fast, ease: EASE.in } }}
            className="overflow-hidden"
          >
            <div
              className="space-y-3 border-t border-border-subtle bg-surface-1 px-4 py-3"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-caption font-medium text-text-tertiary">
                  Extrato de {nomeMes(mes)}/{ano}
                </p>
                <PeriodoSeletor
                  ano={ano}
                  mes={mes}
                  onChange={(novoAno, novoMes) => {
                    setAno(novoAno);
                    setMes(novoMes);
                  }}
                />
              </div>

              {carregandoExtrato || !extrato ? (
                <div className="space-y-1.5">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-5 w-full" />
                </div>
              ) : (
                <>
                  <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-caption sm:grid-cols-3">
                    <div>
                      <dt className="text-text-tertiary">Saldo inicial</dt>
                      <dd className="text-text-secondary">{formatMoney(extrato.resumo.saldo_inicial)}</dd>
                    </div>
                    <div>
                      <dt className="text-text-tertiary">Entradas</dt>
                      <dd className="font-medium text-positive">{formatMoney(extrato.resumo.entradas_periodo)}</dd>
                    </div>
                    <div>
                      <dt className="text-text-tertiary">Saídas</dt>
                      <dd className="font-medium text-negative">{formatMoney(extrato.resumo.saidas_periodo)}</dd>
                    </div>
                    <div>
                      <dt className="text-text-tertiary">Saldo líquido</dt>
                      <dd className="text-text-secondary">{formatMoney(extrato.resumo.saldo_liquido_periodo)}</dd>
                    </div>
                    <div>
                      <dt className="text-text-tertiary">Última movimentação</dt>
                      <dd className="text-text-secondary">
                        {extrato.resumo.ultima_movimentacao ? formatDate(extrato.resumo.ultima_movimentacao) : "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-text-tertiary">Movimentações</dt>
                      <dd className="text-text-secondary">{extrato.resumo.quantidade_movimentacoes}</dd>
                    </div>
                  </dl>

                  <div className="rounded-md border border-border-subtle bg-surface-1 px-3 py-2">
                    <p className="mb-1.5 text-caption font-medium text-text-tertiary">Resumo deste mês</p>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-caption sm:grid-cols-3">
                      <span className="text-text-secondary">
                        Entradas <span className="font-medium text-positive">{formatMoney(extrato.resumo_mes_atual.entradas_mes)}</span>
                      </span>
                      <span className="text-text-secondary">
                        Saídas <span className="font-medium text-negative">{formatMoney(extrato.resumo_mes_atual.saidas_mes)}</span>
                      </span>
                      <span className="text-text-secondary">
                        Saldo <span className="font-medium text-text-primary">{formatMoney(extrato.resumo_mes_atual.saldo_mes)}</span>
                      </span>
                      {extrato.resumo_mes_atual.maior_entrada && (
                        <span className="text-text-secondary">
                          Maior entrada <span className="font-medium">{formatMoney(extrato.resumo_mes_atual.maior_entrada.valor)}</span>
                        </span>
                      )}
                      {extrato.resumo_mes_atual.maior_saida && (
                        <span className="text-text-secondary">
                          Maior saída <span className="font-medium">{formatMoney(extrato.resumo_mes_atual.maior_saida.valor)}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {FILTROS_RAPIDOS.map((filtro) => (
                      <button
                        key={filtro}
                        type="button"
                        onClick={() => setFiltroRapido(filtro)}
                        className={`rounded-full px-2.5 py-1 text-micro font-medium transition-colors duration-fast ease-out ${
                          filtroRapido === filtro
                            ? "bg-accent text-text-onAccent"
                            : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                        }`}
                      >
                        {LABEL_FILTRO_RAPIDO[filtro]}
                      </button>
                    ))}
                  </div>

                  <p className="text-caption font-medium text-text-tertiary">Histórico</p>
                  {movimentacoesFiltradas.length === 0 ? (
                    <p className="text-caption text-text-tertiary">Nenhuma movimentação neste período.</p>
                  ) : (
                    <ul className="max-h-64 space-y-1.5 overflow-y-auto">
                      {movimentacoesFiltradas.map((movimentacao) => {
                        const Icone = ICONE_CATEGORIA[movimentacao.categoria];
                        return (
                          <li
                            key={`${movimentacao.origem_tipo}-${movimentacao.origem_id}-${movimentacao.categoria}-${movimentacao.data}-${movimentacao.valor}`}
                            className="flex items-center justify-between gap-2 text-sm"
                          >
                            <span className="flex min-w-0 items-center gap-2 text-text-secondary">
                              <Icone size={13} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                              <span className="truncate">
                                {formatDate(movimentacao.data)} — {movimentacao.descricao}
                              </span>
                            </span>
                            <span
                              className={`tabular shrink-0 font-medium ${movimentacao.positivo ? "text-positive" : "text-negative"}`}
                            >
                              {movimentacao.positivo ? "+" : "-"} {formatMoney(movimentacao.valor)}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
