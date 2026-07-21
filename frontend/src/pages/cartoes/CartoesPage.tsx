import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard, Plus } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { MetricCard } from "../../components/ui/MetricCard";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { SearchBar } from "../../components/ui/SearchBar";
import { FilterBar } from "../../components/ui/FilterBar";
import { CartaoFormDialog } from "../../components/domain/cartao/CartaoFormDialog";
import { CartaoResumoCard } from "../../components/domain/cartao/CartaoResumoCard";
import { useCartoes, useAtualizarCartao, useDesativarCartao, useExcluirCartao } from "../../hooks/useCartaoQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import { isApiError } from "../../types/api";
import { formatMoney } from "../../utils/format";
import { BANDEIRAS } from "../../lib/bandeiras";
import type { CartaoRead } from "../../types/cartao";
import type { FilterDef } from "../../types/table";

interface EstadoDialogoCartao {
  aberto: boolean;
  cartao: CartaoRead | null;
}

const DIALOGO_FECHADO: EstadoDialogoCartao = { aberto: false, cartao: null };

const FILTROS: FilterDef<CartaoRead>[] = [
  {
    key: "bandeira",
    label: "Bandeira",
    options: Object.entries(BANDEIRAS).map(([value, info]) => ({ value, label: info.label })),
    predicate: (cartao, value) => cartao.bandeira === value,
  },
];

/**
 * Página `/cartoes` — revisão de UX (`docs/analise-arquitetural-revisao-ux-cartoes.md`,
 * seção 2). Grid de `CartaoResumoCard` (mini dashboard clicável) em vez de
 * `DataTable`: um cartão é tratado como um dos objetos mais importantes do
 * sistema, não como uma linha de registro. Busca/filtro/switch
 * reconstruídos localmente (a mesma UI de sempre, só sem a maquinaria de
 * ordenação/paginação de `DataTable`, que este volume de dados nunca
 * precisou de verdade).
 */
export function CartoesPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const [mostrarInativos, setMostrarInativos] = useState(false);
  const { data: cartoes, isLoading, error, refetch } = useCartoes(!mostrarInativos);

  const [busca, setBusca] = useState("");
  const [filtros, setFiltros] = useState<Record<string, string>>({});

  const [dialogo, setDialogo] = useState<EstadoDialogoCartao>(DIALOGO_FECHADO);
  const [cartaoParaDesativar, setCartaoParaDesativar] = useState<CartaoRead | null>(null);
  const [cartaoParaExcluir, setCartaoParaExcluir] = useState<CartaoRead | null>(null);
  // Segunda confirmação (pedido explícito do usuário, ver
  // docs/analise-arquitetural-exclusao-cartao-com-historico.md): só abre
  // quando a exclusão "segura" acima é rejeitada com 422 (fatura
  // vinculada) - oferece apagar faturas + transações do cartão junto.
  const [cartaoParaExcluirComHistorico, setCartaoParaExcluirComHistorico] = useState<CartaoRead | null>(
    null,
  );

  const atualizarCartao = useAtualizarCartao();
  const desativarCartao = useDesativarCartao();
  const excluirCartao = useExcluirCartao();

  const cartoesFiltrados = useMemo(() => {
    const lista = cartoes ?? [];
    const buscaNormalizada = busca.trim().toLowerCase();
    return lista.filter((cartao) => {
      if (buscaNormalizada) {
        const alvo = `${cartao.nome} ${cartao.instituicao} ${cartao.ultimos_quatro_digitos}`.toLowerCase();
        if (!alvo.includes(buscaNormalizada)) return false;
      }
      return FILTROS.every((filtro) => {
        const valor = filtros[filtro.key];
        if (!valor) return true;
        return filtro.predicate(cartao, valor);
      });
    });
  }, [cartoes, busca, filtros]);

  const indicadores = useMemo(() => {
    const lista = cartoes ?? [];
    const limiteTotal = lista.reduce((soma, c) => soma + Number(c.limite), 0);
    const disponivelTotal = lista.reduce((soma, c) => soma + Number(c.limite_disponivel), 0);
    return {
      limiteTotal,
      disponivelTotal,
      utilizadoTotal: limiteTotal - disponivelTotal,
      quantidade: lista.length,
    };
  }, [cartoes]);

  function abrirCriacao() {
    setDialogo({ aberto: true, cartao: null });
  }

  function abrirEdicao(cartao: CartaoRead) {
    setDialogo({ aberto: true, cartao });
  }

  function fecharDialogo() {
    setDialogo((atual) => ({ ...atual, aberto: false }));
  }

  /** Pedido do usuário: quem já usava o cartão antes de entrar no app
   * precisa achar "Registrar saldo já gasto neste cartão" (ajuste de saldo
   * inicial, `CartaoDetalhePage`) sem precisar já saber que essa ação
   * existe — landing direto no detalhe do cartão recém-criado coloca o
   * usuário ao lado dela, sem exigir nenhuma tela/regra nova. */
  function aoCriarCartao(cartaoCriado: CartaoRead) {
    navigate(`/cartoes/${cartaoCriado.id}`);
  }

  async function confirmarDesativacao() {
    if (!cartaoParaDesativar) return;
    try {
      await desativarCartao.mutateAsync(cartaoParaDesativar.id);
      toast.success(`Cartão "${cartaoParaDesativar.nome}" desativado.`);
      setCartaoParaDesativar(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusao() {
    if (!cartaoParaExcluir) return;
    try {
      await excluirCartao.mutateAsync({ id: cartaoParaExcluir.id });
      toast.success(`Cartão "${cartaoParaExcluir.nome}" excluído definitivamente.`);
      setCartaoParaExcluir(null);
    } catch (error) {
      // 422 aqui só acontece por fatura vinculada (BusinessRuleError) -
      // em vez de só mostrar o erro, oferece a opção de apagar tudo junto.
      if (isApiError(error) && error.status === 422) {
        setCartaoParaExcluirComHistorico(cartaoParaExcluir);
        setCartaoParaExcluir(null);
        return;
      }
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusaoComHistorico() {
    if (!cartaoParaExcluirComHistorico) return;
    try {
      await excluirCartao.mutateAsync({ id: cartaoParaExcluirComHistorico.id, apagarTransacoes: true });
      toast.success(
        `Cartão "${cartaoParaExcluirComHistorico.nome}" e todo o seu histórico foram excluídos definitivamente.`,
      );
      setCartaoParaExcluirComHistorico(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  function reativar(cartao: CartaoRead) {
    atualizarCartao.mutate(
      { id: cartao.id, dados: { ativo: true } },
      {
        onSuccess: () => toast.success(`Cartão "${cartao.nome}" reativado.`),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Cartões</h1>
          <p className="mt-1 text-sm text-text-secondary">Cartões de crédito e seus limites disponíveis.</p>
        </div>
        <Button onClick={abrirCriacao}>
          <Plus size={16} aria-hidden="true" />
          Novo cartão
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard label="Limite total" value={formatMoney(indicadores.limiteTotal)} />
        <MetricCard label="Utilizado" value={formatMoney(indicadores.utilizadoTotal)} />
        <MetricCard label="Disponível" value={formatMoney(indicadores.disponivelTotal)} />
        <MetricCard label="Cartões ativos" value={String(indicadores.quantidade)} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <SearchBar
            value={busca}
            onChange={setBusca}
            placeholder="Buscar por nome, instituição ou últimos 4 dígitos..."
            className="w-64"
          />
          <FilterBar
            filters={FILTROS}
            activeFilters={filtros}
            onFilterChange={(key, value) => setFiltros((atual) => ({ ...atual, [key]: value }))}
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="mostrar-inativos"
            checked={mostrarInativos}
            onCheckedChange={setMostrarInativos}
            aria-label="Mostrar cartões inativos"
          />
          <label htmlFor="mostrar-inativos" className="cursor-pointer text-sm text-text-secondary">
            Mostrar cartões inativos
          </label>
        </div>
      </div>

      {error ? (
        <Card>
          <ErrorMessage error={error} />
          <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
            Tentar novamente
          </Button>
        </Card>
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="space-y-4">
              <Skeleton className="aspect-[1.586/1] w-full rounded-xl" />
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-9 w-full" />
            </Card>
          ))}
        </div>
      ) : cartoesFiltrados.length === 0 ? (
        <Card>
          <EmptyState
            icon={CreditCard}
            title={cartoes && cartoes.length > 0 ? "Nada encontrado" : "Nenhum cartão ainda"}
            description={
              cartoes && cartoes.length > 0
                ? "Tente ajustar a busca ou os filtros."
                : "Cadastre seu primeiro cartão de crédito para começar."
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cartoesFiltrados.map((cartao) => (
            <CartaoResumoCard
              key={cartao.id}
              cartao={cartao}
              onEditar={abrirEdicao}
              onDesativar={setCartaoParaDesativar}
              onReativar={reativar}
              onExcluir={setCartaoParaExcluir}
            />
          ))}
        </div>
      )}

      <CartaoFormDialog open={dialogo.aberto} cartao={dialogo.cartao} onClose={fecharDialogo} onCriado={aoCriarCartao} />

      <ConfirmAction
        open={cartaoParaDesativar != null}
        title={cartaoParaDesativar ? `Desativar "${cartaoParaDesativar.nome}"?` : ""}
        description="O cartão deixa de aparecer nas listagens padrão, mas todo o histórico é preservado. Você pode reativá-lo a qualquer momento."
        confirmLabel="Desativar"
        tone="danger"
        loading={desativarCartao.isPending}
        onConfirm={confirmarDesativacao}
        onCancel={() => setCartaoParaDesativar(null)}
      />

      <ConfirmAction
        open={cartaoParaExcluir != null}
        title={cartaoParaExcluir ? `Excluir "${cartaoParaExcluir.nome}" definitivamente?` : ""}
        description="Esta ação é permanente e não pode ser desfeita. O cartão será excluído para sempre — só é possível excluir um cartão sem nenhuma fatura vinculada."
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirCartao.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setCartaoParaExcluir(null)}
      />

      <ConfirmAction
        open={cartaoParaExcluirComHistorico != null}
        title={
          cartaoParaExcluirComHistorico
            ? `Excluir "${cartaoParaExcluirComHistorico.nome}" e todo o histórico?`
            : ""
        }
        description="Este cartão tem faturas vinculadas. Para excluí-lo, é preciso apagar junto todas as faturas e todas as transações feitas neste cartão — permanentemente, sem possibilidade de desfazer. Se preferir manter o histórico, desative o cartão em vez de excluir."
        confirmLabel="Apagar tudo e excluir"
        tone="danger"
        loading={excluirCartao.isPending}
        onConfirm={confirmarExclusaoComHistorico}
        onCancel={() => setCartaoParaExcluirComHistorico(null)}
      />
    </div>
  );
}
