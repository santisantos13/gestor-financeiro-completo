import { useMemo, useState } from "react";
import { Plus, Wallet } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { SearchBar } from "../../components/ui/SearchBar";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { ContaFormDialog } from "../../components/domain/conta/ContaFormDialog";
import { ContaResumoCard } from "../../components/domain/conta/ContaResumoCard";
import { LABEL_TIPO_CONTA } from "../../components/domain/conta/contaTableColumns";
import {
  useContas,
  useAtualizarConta,
  useDesativarConta,
  useExcluirConta,
} from "../../hooks/useContaQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import { isApiError } from "../../types/api";
import type { ContaRead, TipoConta } from "../../types/conta";

interface EstadoDialogoConta {
  aberto: boolean;
  conta: ContaRead | null;
  somenteLeitura: boolean;
}

const DIALOGO_FECHADO: EstadoDialogoConta = { aberto: false, conta: null, somenteLeitura: false };

type FiltroTipo = "TODAS" | TipoConta;

const FILTROS_TIPO: FiltroTipo[] = ["TODAS", "CORRENTE", "POUPANCA", "CARTEIRA", "INVESTIMENTO"];

const LABEL_FILTRO_TIPO: Record<FiltroTipo, string> = {
  TODAS: "Todas",
  CORRENTE: LABEL_TIPO_CONTA.CORRENTE,
  POUPANCA: LABEL_TIPO_CONTA.POUPANCA,
  CARTEIRA: LABEL_TIPO_CONTA.CARTEIRA,
  INVESTIMENTO: LABEL_TIPO_CONTA.INVESTIMENTO,
};

type CriterioOrdenacao = "SALDO" | "NOME";

const CRITERIO_OPTIONS = [
  { value: "SALDO", label: "Maior saldo" },
  { value: "NOME", label: "Nome (A-Z)" },
];

/**
 * Página `/contas` — reescrita para grid de `ContaResumoCard` (pedido
 * explícito do usuário: "cada conta deve ser responsável pelo seu próprio
 * histórico financeiro"; clicar/expandir uma conta revela o extrato
 * inline, sem navegar). `DataTable` não suporta painel de detalhe inline
 * (confirmado por inspeção) — mesmo trade-off já aceito para Meta
 * (`MetasPage`, ver docs/analise-arquitetural-extrato-conta.md). Filtro
 * rápido por tipo + busca + ordenação são 100% client-side sobre a lista
 * já carregada; "mostrar inativas" continua controlando o parâmetro
 * `apenas_ativas` do backend (comportamento original, inalterado). Os três
 * `ConfirmAction` de desativação/exclusão são os mesmos de antes, sem
 * nenhuma mudança de regra de negócio.
 */
export function ContasPage() {
  const toast = useToast();
  const [mostrarInativas, setMostrarInativas] = useState(false);
  const { data: contas, isLoading, error, refetch } = useContas(!mostrarInativas);

  const [filtroTipo, setFiltroTipo] = useState<FiltroTipo>("TODAS");
  const [busca, setBusca] = useState("");
  const [criterio, setCriterio] = useState<CriterioOrdenacao>("SALDO");

  const [dialogo, setDialogo] = useState<EstadoDialogoConta>(DIALOGO_FECHADO);
  const [contaParaDesativar, setContaParaDesativar] = useState<ContaRead | null>(null);
  const [contaParaExcluir, setContaParaExcluir] = useState<ContaRead | null>(null);
  // Segunda confirmação (pedido explícito do usuário, ver
  // docs/analise-arquitetural-exclusao-conta-com-historico.md): só abre
  // quando a exclusão "segura" acima é rejeitada com 422 (vínculo) -
  // oferece apagar tudo vinculado à conta junto.
  const [contaParaExcluirComVinculos, setContaParaExcluirComVinculos] = useState<ContaRead | null>(null);

  const atualizarConta = useAtualizarConta();
  const desativarConta = useDesativarConta();
  const excluirConta = useExcluirConta();

  const contasFiltradas = useMemo(() => {
    let lista = contas ?? [];
    if (filtroTipo !== "TODAS") {
      lista = lista.filter((conta) => conta.tipo === filtroTipo);
    }
    if (busca.trim()) {
      const termo = busca.trim().toLowerCase();
      lista = lista.filter(
        (conta) =>
          conta.nome.toLowerCase().includes(termo) || (conta.instituicao ?? "").toLowerCase().includes(termo),
      );
    }
    const ordenada = [...lista];
    if (criterio === "SALDO") {
      ordenada.sort((a, b) => Number(b.saldo_atual) - Number(a.saldo_atual));
    } else {
      ordenada.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    }
    return ordenada;
  }, [contas, filtroTipo, busca, criterio]);

  function abrirCriacao() {
    setDialogo({ aberto: true, conta: null, somenteLeitura: false });
  }

  function abrirEdicao(conta: ContaRead) {
    setDialogo({ aberto: true, conta, somenteLeitura: false });
  }

  function fecharDialogo() {
    setDialogo((atual) => ({ ...atual, aberto: false }));
  }

  async function confirmarDesativacao() {
    if (!contaParaDesativar) return;
    try {
      await desativarConta.mutateAsync(contaParaDesativar.id);
      toast.success(`Conta "${contaParaDesativar.nome}" desativada.`);
      setContaParaDesativar(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusao() {
    if (!contaParaExcluir) return;
    try {
      await excluirConta.mutateAsync({ id: contaParaExcluir.id });
      toast.success(`Conta "${contaParaExcluir.nome}" excluída definitivamente.`);
      setContaParaExcluir(null);
    } catch (error) {
      // 422 aqui só acontece por vínculo (BusinessRuleError) - em vez de
      // só mostrar o erro, oferece a opção de apagar tudo junto. Conta
      // oculta (cofrinho de Meta) também cai em 422, mas a segunda
      // confirmação também falha nesse caso (backend bloqueia sempre) -
      // o próprio erro do segundo pedido comunica isso ao usuário.
      if (isApiError(error) && error.status === 422) {
        setContaParaExcluirComVinculos(contaParaExcluir);
        setContaParaExcluir(null);
        return;
      }
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusaoComVinculos() {
    if (!contaParaExcluirComVinculos) return;
    try {
      await excluirConta.mutateAsync({ id: contaParaExcluirComVinculos.id, apagarVinculos: true });
      toast.success(
        `Conta "${contaParaExcluirComVinculos.nome}" e todo o seu histórico foram excluídos definitivamente.`,
      );
      setContaParaExcluirComVinculos(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  function reativar(conta: ContaRead) {
    atualizarConta.mutate(
      { id: conta.id, dados: { ativo: true } },
      {
        onSuccess: () => toast.success(`Conta "${conta.nome}" reativada.`),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  const criterioOptions = CRITERIO_OPTIONS;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Contas</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Contas correntes, poupanças, carteiras e investimentos onde seu dinheiro fica guardado.
          </p>
        </div>
        <Button onClick={abrirCriacao}>
          <Plus size={16} aria-hidden="true" />
          Nova conta
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="mostrar-inativas"
          checked={mostrarInativas}
          onCheckedChange={setMostrarInativas}
          aria-label="Mostrar contas inativas"
        />
        <label htmlFor="mostrar-inativas" className="cursor-pointer text-sm text-text-secondary">
          Mostrar contas inativas
        </label>
      </div>

      {!isLoading && contas && contas.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-1.5">
            {FILTROS_TIPO.map((filtro) => (
              <button
                key={filtro}
                type="button"
                onClick={() => setFiltroTipo(filtro)}
                className={`rounded-full px-3 py-1 text-caption font-medium transition-colors duration-fast ease-out ${
                  filtroTipo === filtro
                    ? "bg-accent text-text-onAccent"
                    : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                }`}
              >
                {LABEL_FILTRO_TIPO[filtro]}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <SearchBar
              value={busca}
              onChange={setBusca}
              placeholder="Buscar por nome ou instituição..."
              className="w-full sm:w-56"
            />
            <Select
              options={criterioOptions}
              value={criterio}
              onChange={(valor) => setCriterio(valor as CriterioOrdenacao)}
              aria-label="Ordenar contas"
              className="w-full sm:w-40"
            />
          </div>
        </div>
      )}

      {error ? (
        <Card>
          <ErrorMessage error={error} />
          <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
            Tentar novamente
          </Button>
        </Card>
      ) : isLoading ? (
        <div className="divide-y divide-border-subtle overflow-hidden rounded-lg border border-border bg-surface-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <Skeleton className="h-9 w-9 shrink-0 rounded-full" />
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-20 shrink-0" />
            </div>
          ))}
        </div>
      ) : !contas || contas.length === 0 ? (
        <Card>
          <EmptyState
            icon={Wallet}
            title="Nenhuma conta ainda"
            description="Cadastre sua primeira conta corrente, poupança, carteira ou investimento para começar a acompanhar seu dinheiro."
            action={
              <Button size="sm" onClick={abrirCriacao}>
                <Plus size={14} aria-hidden="true" />
                Nova conta
              </Button>
            }
          />
        </Card>
      ) : contasFiltradas.length === 0 ? (
        <Card>
          <EmptyState icon={Wallet} title="Nenhuma conta encontrada" description="Ajuste o filtro ou a busca para ver outras contas." />
        </Card>
      ) : (
        // Lista densa (pedido explícito do usuário: os cards grandes do
        // grid original "deixam a tela pesada e exigem muita rolagem") -
        // um único container com `divide-y` entre as linhas, em vez de N
        // `Card`s empilhados com borda/sombra próprias - mesma "sensação
        // de lista" de um aplicativo bancário. Ver docstring de
        // `ContaResumoCard`.
        <div className="divide-y divide-border-subtle overflow-hidden rounded-lg border border-border bg-surface-2">
          {contasFiltradas.map((conta) => (
            <ContaResumoCard
              key={conta.id}
              conta={conta}
              onEditar={abrirEdicao}
              onDesativar={(c) => setContaParaDesativar(c)}
              onReativar={reativar}
              onExcluir={(c) => setContaParaExcluir(c)}
            />
          ))}
        </div>
      )}

      <ContaFormDialog
        open={dialogo.aberto}
        conta={dialogo.conta}
        somenteLeitura={dialogo.somenteLeitura}
        onClose={fecharDialogo}
      />

      <ConfirmAction
        open={contaParaDesativar != null}
        title={contaParaDesativar ? `Desativar "${contaParaDesativar.nome}"?` : ""}
        description="A conta deixa de aparecer nas listagens padrão, mas todo o histórico de transações é preservado. Você pode reativá-la a qualquer momento."
        confirmLabel="Desativar"
        tone="danger"
        loading={desativarConta.isPending}
        onConfirm={confirmarDesativacao}
        onCancel={() => setContaParaDesativar(null)}
      />

      <ConfirmAction
        open={contaParaExcluir != null}
        title={contaParaExcluir ? `Excluir "${contaParaExcluir.nome}" definitivamente?` : ""}
        description="Esta ação é permanente e não pode ser desfeita. A conta será excluída para sempre — só é possível excluir uma conta sem nenhuma transação, transferência, cartão ou contrato vinculado."
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirConta.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setContaParaExcluir(null)}
      />

      <ConfirmAction
        open={contaParaExcluirComVinculos != null}
        title={
          contaParaExcluirComVinculos
            ? `Excluir "${contaParaExcluirComVinculos.nome}" e todo o histórico?`
            : ""
        }
        description="Esta conta tem transações, transferências, cartões ou contratos vinculados. Para excluí-la, é preciso apagar tudo isso junto — transações, transferências, cartões (com faturas e transações deles), financiamentos e empréstimos — permanentemente, sem possibilidade de desfazer. Se preferir manter o histórico, desative a conta em vez de excluir."
        confirmLabel="Apagar tudo e excluir"
        tone="danger"
        loading={excluirConta.isPending}
        onConfirm={confirmarExclusaoComVinculos}
        onCancel={() => setContaParaExcluirComVinculos(null)}
      />
    </div>
  );
}
