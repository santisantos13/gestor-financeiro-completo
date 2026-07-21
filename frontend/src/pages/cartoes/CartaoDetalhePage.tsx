import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Banknote, Plus, Receipt, History, PiggyBank, ShoppingCart, Trash2 } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { BulkActions } from "../../components/ui/BulkActions";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { CurrencyField } from "../../components/ui/CurrencyField";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { FinancialBadge } from "../../components/ui/FinancialBadge";
import { Form } from "../../components/ui/Form";
import { FormActions } from "../../components/ui/FormActions";
import { CancelButton } from "../../components/ui/CancelButton";
import { SubmitButton } from "../../components/ui/SubmitButton";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { MetricCard } from "../../components/ui/MetricCard";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { SelectionCheckbox } from "../../components/ui/SelectionCheckbox";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { CartaoVisual } from "../../components/domain/cartao/CartaoVisual";
import { CartaoFormDialog } from "../../components/domain/cartao/CartaoFormDialog";
import { CartaoActionBar } from "../../components/domain/cartao/CartaoActionBar";
import { ProximaFaturaCard } from "../../components/domain/fatura/ProximaFaturaCard";
import { FaturaDrawer } from "../../components/domain/fatura/FaturaDrawer";
import { PagamentoEmLoteDialog } from "../../components/domain/fatura/PagamentoEmLoteDialog";
import { AjusteSaldoInicialDialog } from "../../components/domain/fatura/AjusteSaldoInicialDialog";
import { TransacaoFormDialog } from "../../components/domain/transacao/TransacaoFormDialog";
import { useCartao, useAtualizarCartao, useDesativarCartao, useExcluirCartao } from "../../hooks/useCartaoQueries";
import { useFaturas, useCriarFatura, useImportarFatura, useExcluirFaturasEmLote } from "../../hooks/useFaturaQueries";
import { useContas } from "../../hooks/useContaQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import { isApiError } from "../../types/api";
import { formatMoney } from "../../utils/format";
import { formatDate, nomeMes } from "../../utils/date";
import { ordenarFaturasParaListagem } from "../../utils/fatura";
import {
  novaFaturaFormSchema,
  novaFaturaFormValuesParaPayload,
  novaFaturaFormValuesParaImportPayload,
  type NovaFaturaFormValues,
} from "../../schemas/fatura";
import { BANDEIRAS } from "../../lib/bandeiras";
import type { FaturaRead } from "../../types/fatura";
import type { TransacaoRead } from "../../types/transacao";

const VALORES_VAZIOS_NOVA_FATURA: NovaFaturaFormValues = { mes_referencia: "", historica: false, valor_total: "" };

/**
 * Página de detalhes do Cartão — `/cartoes/:id`. Reorganizada na revisão de
 * UX de Cartões (`docs/analise-arquitetural-revisao-ux-cartoes.md`, seção
 * 7) na ordem de leitura pedida: qual cartão → quanto posso gastar →
 * utilização → próxima fatura → ações rápidas → faturas → informações do
 * cartão → histórico (placeholder, depende de Transação).
 *
 * Layout de duas colunas preserva a mesma ideia da versão anterior
 * (identidade/números à esquerda, fluxo de ação/atividade à direita), só
 * com o conteúdo redistribuído pelas novas seções.
 */
export function CartaoDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const cartaoId = Number(id);
  const navigate = useNavigate();
  const toast = useToast();

  const { data: cartao, isLoading, error, refetch } = useCartao(cartaoId);
  const { data: faturas, isLoading: carregandoFaturas } = useFaturas(cartaoId);
  // Ordem de exibição pedida pelo usuário: mais antiga -> mais recente,
  // com status como desempate (paga -> fechada -> aberta). O backend já
  // entrega em ordem cronológica (FaturaRepository.listar_do_cartao); só o
  // desempate por status mora no frontend (utils/fatura.ts).
  const faturasOrdenadas = useMemo(() => (faturas ? ordenarFaturasParaListagem(faturas) : undefined), [faturas]);
  const { data: contas } = useContas(false);

  const atualizarCartao = useAtualizarCartao();
  const desativarCartao = useDesativarCartao();
  const excluirCartao = useExcluirCartao();
  const criarFatura = useCriarFatura(cartaoId);
  const importarFatura = useImportarFatura(cartaoId);
  const excluirFaturasEmLote = useExcluirFaturasEmLote(cartaoId);

  const [dialogoEdicaoAberto, setDialogoEdicaoAberto] = useState(false);
  const [confirmandoDesativar, setConfirmandoDesativar] = useState(false);
  const [confirmandoExcluir, setConfirmandoExcluir] = useState(false);
  // Segunda confirmação (pedido explícito do usuário, ver
  // docs/analise-arquitetural-exclusao-cartao-com-historico.md): só abre
  // quando a exclusão "segura" acima é rejeitada com 422 (fatura
  // vinculada) - oferece apagar faturas + transações do cartão junto.
  const [confirmandoExcluirComHistorico, setConfirmandoExcluirComHistorico] = useState(false);
  const [novaFaturaAberta, setNovaFaturaAberta] = useState(false);
  // Pedido do usuário: "na aba de cartões, quero conseguir selecionar
  // quantas parcelas eu quiser" - a causa real não era limite nenhum (o
  // campo de parcelas já é livre, sem teto, ver `TransacaoFormDialog`),
  // era não existir NENHUM jeito de abrir "nova compra" a partir da
  // própria página do cartão - só indo em Transações e escolhendo o
  // cartão manualmente. `valoresIniciais` já existia no
  // `TransacaoFormDialog` pra esse exato propósito, só nunca tinha sido
  // usado aqui de verdade.
  const [novaCompraAberta, setNovaCompraAberta] = useState(false);
  // Editar uma compra a partir de "Compras desta fatura" (`FaturaDrawer`,
  // pedido do usuário 2026-07-20) reaproveita este mesmo `TransacaoFormDialog`
  // em vez de abrir um segundo diálogo - o Drawer só fecha a si mesmo e avisa
  // aqui qual compra editar (ver comentário em `FaturaDrawer.onEditarCompra`;
  // dois overlays Tier 2 abertos ao mesmo tempo empilhariam backdrops, ver
  // docs/analise-arquitetural-overlays.md, seção 2).
  const [compraEmEdicao, setCompraEmEdicao] = useState<TransacaoRead | null>(null);
  const [faturaSelecionadaId, setFaturaSelecionadaId] = useState<number | null>(null);
  // Seleção múltipla de faturas (pedido explícito do usuário: "quero
  // poder selecionar várias faturas para excluir") - reaproveita
  // `SelectionCheckbox`/`BulkActions`, mesma infraestrutura genérica já
  // usada por `DataTable`, sem precisar do `useDataTable` inteiro (essa
  // lista não tem busca/filtro/paginação).
  const [faturasSelecionadasIds, setFaturasSelecionadasIds] = useState<Set<number>>(new Set());

  function alternarSelecaoFatura(faturaId: number) {
    setFaturasSelecionadasIds((atual) => {
      const novo = new Set(atual);
      if (novo.has(faturaId)) {
        novo.delete(faturaId);
      } else {
        novo.add(faturaId);
      }
      return novo;
    });
  }

  // "Selecionar todas" (pedido explícito do usuário) — alterna entre
  // selecionar todas as faturas carregadas e limpar a seleção.
  function alternarSelecaoTodasFaturas() {
    setFaturasSelecionadasIds((atual) =>
      atual.size === (faturas?.length ?? 0) ? new Set() : new Set(faturas?.map((fatura) => fatura.id)),
    );
  }

  async function excluirFaturasSelecionadas(selecionadas: FaturaRead[]) {
    try {
      await excluirFaturasEmLote.mutateAsync(selecionadas.map((fatura) => fatura.id));
      toast.success(
        selecionadas.length === 1
          ? "Fatura excluída definitivamente."
          : `${selecionadas.length} faturas excluídas definitivamente.`,
      );
      setFaturasSelecionadasIds(new Set());
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  // Pagamento em lote (pedido explícito do usuário: "seria interessante
  // poder pagar todas selecionadas") — ids capturados no clique do botão
  // (via `selectedRows` que o próprio `BulkActions` já entrega), nunca lidos
  // de `faturasSelecionadasIds` de novo dentro do diálogo, pra não reagir a
  // uma mudança de seleção feita por baixo enquanto ele está aberto.
  const [faturaIdsPagamentoLote, setFaturaIdsPagamentoLote] = useState<number[] | null>(null);

  function abrirPagamentoEmLote(selecionadas: FaturaRead[]) {
    setFaturaIdsPagamentoLote(selecionadas.map((fatura) => fatura.id));
  }

  function fecharPagamentoEmLote() {
    setFaturaIdsPagamentoLote(null);
    setFaturasSelecionadasIds(new Set());
  }

  function abrirEdicaoCompra(transacao: TransacaoRead) {
    setCompraEmEdicao(transacao);
  }

  function fecharDialogoCompra() {
    setNovaCompraAberta(false);
    setCompraEmEdicao(null);
  }

  const [ajusteSaldoAberto, setAjusteSaldoAberto] = useState(false);

  const formNovaFatura = useForm<NovaFaturaFormValues>({
    resolver: zodResolver(novaFaturaFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS_NOVA_FATURA,
  });
  const historicaAtual = useWatch({ control: formNovaFatura.control, name: "historica" });

  // Suporte a `/cartoes/:id#faturas` (link "Faturas" da Action Bar do
  // `CartaoResumoCard`, seção 5 da revisão de UX) — rola até a seção assim
  // que a página (e os dados) estiverem prontos.
  useEffect(() => {
    if (!isLoading && cartao && window.location.hash === "#faturas") {
      document.getElementById("faturas")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [isLoading, cartao]);

  async function confirmarDesativacao() {
    if (!cartao) return;
    try {
      await desativarCartao.mutateAsync(cartao.id);
      toast.success(`Cartão "${cartao.nome}" desativado.`);
      setConfirmandoDesativar(false);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusao() {
    if (!cartao) return;
    try {
      await excluirCartao.mutateAsync({ id: cartao.id });
      toast.success(`Cartão "${cartao.nome}" excluído definitivamente.`);
      navigate("/cartoes");
    } catch (error) {
      // 422 aqui só acontece por fatura vinculada (BusinessRuleError) -
      // em vez de só mostrar o erro, oferece a opção de apagar tudo junto.
      if (isApiError(error) && error.status === 422) {
        setConfirmandoExcluir(false);
        setConfirmandoExcluirComHistorico(true);
        return;
      }
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExclusaoComHistorico() {
    if (!cartao) return;
    try {
      await excluirCartao.mutateAsync({ id: cartao.id, apagarTransacoes: true });
      toast.success(`Cartão "${cartao.nome}" e todo o seu histórico foram excluídos definitivamente.`);
      navigate("/cartoes");
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  function reativar() {
    if (!cartao) return;
    atualizarCartao.mutate(
      { id: cartao.id, dados: { ativo: true } },
      {
        onSuccess: () => toast.success(`Cartão "${cartao.nome}" reativado.`),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  async function onSubmitNovaFatura(valores: NovaFaturaFormValues) {
    try {
      if (valores.historica) {
        await importarFatura.mutateAsync(novaFaturaFormValuesParaImportPayload(valores, cartaoId));
        toast.success("Fatura histórica importada — já fechada, pronta para registrar o pagamento se precisar.");
      } else {
        await criarFatura.mutateAsync(novaFaturaFormValuesParaPayload(valores, cartaoId));
        toast.success("Fatura criada.");
      }
      setNovaFaturaAberta(false);
      formNovaFatura.reset(VALORES_VAZIOS_NOVA_FATURA);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <LoadingCard lines={4} />
      </div>
    );
  }

  if (error || !cartao) {
    return (
      <div className="space-y-3">
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  const contaPagamento = contas?.find((c) => c.id === cartao.conta_pagamento_id);
  const utilizadoNumero = Number(cartao.limite) - Number(cartao.limite_disponivel);
  const faturaAberta = faturas?.find((f) => f.status === "ABERTA") ?? null;

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate("/cartoes")}>
          <ArrowLeft size={14} aria-hidden="true" />
          Voltar para Cartões
        </Button>
      </div>

      <h1 className="text-h1 font-semibold text-text-primary">{cartao.nome}</h1>

      {/* `minmax(0, ...)` nas DUAS trilhas, não só a esquerda - responsividade
          mobile (2026-07-21): uma trilha `1fr` sozinha ainda tem largura
          mínima implícita igual ao conteúdo (`min-width: auto` da spec do
          Grid), então qualquer linha larga por dentro (ex: item de fatura
          com nome+valor+badge) empurrava a coluna INTEIRA além do viewport
          em vez de encolher - o "corte"/"desalinhamento no zoom out"
          relatado pelo usuário. */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        {/* Coluna esquerda: identidade + números (perguntas 1-3 da ordem de leitura). */}
        <div className="space-y-4">
          <CartaoVisual
            nome={cartao.nome}
            instituicao={cartao.instituicao}
            bandeira={cartao.bandeira}
            ultimosQuatroDigitos={cartao.ultimos_quatro_digitos}
            limite={cartao.limite}
            limiteDisponivel={cartao.limite_disponivel}
            diaFechamento={cartao.dia_fechamento}
            diaVencimento={cartao.dia_vencimento}
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <MetricCard label="Limite total" value={formatMoney(cartao.limite)} />
            <MetricCard label="Disponível" value={formatMoney(cartao.limite_disponivel)} />
            <MetricCard label="Utilizado" value={formatMoney(utilizadoNumero)} />
          </div>

          {/* Informações do cartão (pergunta 6 — dados que hoje só existiam
              dentro do formulário de edição, nunca em modo leitura). */}
          <Card className="space-y-2.5">
            <SectionTitle>Informações do cartão</SectionTitle>
            <dl className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <dt className="text-text-tertiary">Instituição</dt>
                <dd className="text-text-primary">{cartao.instituicao}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-text-tertiary">Bandeira</dt>
                <dd className="text-text-primary">{BANDEIRAS[cartao.bandeira]?.label ?? cartao.bandeira}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-text-tertiary">Fechamento</dt>
                <dd className="text-text-primary">Dia {cartao.dia_fechamento}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-text-tertiary">Vencimento</dt>
                <dd className="text-text-primary">Dia {cartao.dia_vencimento}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-text-tertiary">Conta de pagamento</dt>
                <dd className="text-text-primary">{contaPagamento?.nome ?? "—"}</dd>
              </div>
            </dl>
          </Card>
        </div>

        {/* Coluna direita: próxima fatura, ações, faturas, histórico
            (perguntas 4-8 da ordem de leitura). */}
        <div className="space-y-6">
          <ProximaFaturaCard
            faturas={faturas}
            carregando={carregandoFaturas}
            onAbrirFatura={setFaturaSelecionadaId}
          />

          {cartao.ativo && (
            <Button onClick={() => setNovaCompraAberta(true)}>
              <ShoppingCart size={16} aria-hidden="true" />
              Nova compra
            </Button>
          )}

          <CartaoActionBar
            ativo={cartao.ativo}
            onEditar={() => setDialogoEdicaoAberto(true)}
            onDesativar={() => setConfirmandoDesativar(true)}
            onReativar={reativar}
            onExcluir={() => setConfirmandoExcluir(true)}
          />

          {/* Saldo já utilizado, sem transação — pedido explícito do
              usuário: "poder informar o saldo já utilizado do cartão
              independentemente de transações". Desde a Sprint de
              Refinamento Premium (2026-07), quando NÃO há ciclo aberto
              este botão edita `Cartao.saldo_inicial_utilizado` direto
              (`PATCH /cartoes/{id}`) — nenhuma Fatura é criada nos
              bastidores (era essa criação implícita que confundia o
              usuário). Quando já existe uma fatura ABERTA, continua
              editando `Fatura.ajuste_manual` daquele ciclo especificamente
              (uso diferente: ajustar o ciclo corrente, não o "estado
              inicial" do cartão). Nenhum lançamento aparece em Transações
              em nenhum dos dois casos — só entra no cálculo de
              `limite_disponivel`. */}
          {cartao.ativo && (
            <Button variant="ghost" size="sm" onClick={() => setAjusteSaldoAberto(true)}>
              <PiggyBank size={14} aria-hidden="true" />
              Informar saldo já utilizado
            </Button>
          )}

          <div id="faturas">
            <SectionTitle
              action={
                !novaFaturaAberta && (
                  <Button size="sm" onClick={() => setNovaFaturaAberta(true)}>
                    <Plus size={14} aria-hidden="true" />
                    Nova fatura
                  </Button>
                )
              }
            >
              Faturas
            </SectionTitle>

            {novaFaturaAberta && (
              <Card className="mb-4 mt-3">
                <Form
                  id="nova-fatura-form"
                  form={formNovaFatura}
                  onSubmit={onSubmitNovaFatura}
                  className="flex flex-wrap items-end gap-3"
                >
                  <div className="space-y-1.5">
                    <label htmlFor="nova-fatura-mes" className="block text-sm text-text-secondary">
                      Mês de referência
                    </label>
                    <input
                      id="nova-fatura-mes"
                      type="month"
                      {...formNovaFatura.register("mes_referencia")}
                      className="h-9 rounded-sm border border-border bg-surface-2 px-3 text-body text-text-primary transition-colors duration-fast ease-out focus-visible:border-accent"
                    />
                  </div>

                  {/* Etapa de Onboarding: quem já tinha um ciclo deste
                      cartão antes de usar o app pode importá-lo direto,
                      já fechado, com o valor total que já sabe de cor —
                      sem recriar compra por compra (docs/README, seção
                      "Excluir Fatura mesmo já fechada" / import histórico). */}
                  <div className="flex w-full items-center gap-2.5 basis-full">
                    <Switch
                      id="nova-fatura-historica"
                      checked={historicaAtual}
                      onCheckedChange={(checked) => formNovaFatura.setValue("historica", checked, { shouldDirty: true })}
                    />
                    <label htmlFor="nova-fatura-historica" className="text-sm text-text-secondary">
                      Este ciclo já aconteceu (e já foi pago) antes de eu usar o app
                    </label>
                  </div>

                  {historicaAtual && (
                    <div className="w-full max-w-[200px]">
                      <CurrencyField name="valor_total" label="Valor total da fatura" />
                    </div>
                  )}

                  <FormActions className="!mt-0">
                    <CancelButton
                      onClick={() => {
                        setNovaFaturaAberta(false);
                        formNovaFatura.reset(VALORES_VAZIOS_NOVA_FATURA);
                      }}
                    >
                      Cancelar
                    </CancelButton>
                    <SubmitButton form="nova-fatura-form" loading={criarFatura.isPending || importarFatura.isPending}>
                      {historicaAtual ? "Importar fatura" : "Criar fatura"}
                    </SubmitButton>
                  </FormActions>
                </Form>
              </Card>
            )}

            <div className="mt-3">
              {carregandoFaturas ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : !faturas || faturas.length === 0 ? (
                <Card>
                  <EmptyState
                    icon={Receipt}
                    title="Nenhuma fatura ainda"
                    description="Crie a primeira fatura deste cartão para começar a registrar o ciclo."
                  />
                </Card>
              ) : (
                <>
                  <div className="mb-2 flex items-center gap-2">
                    <SelectionCheckbox
                      label="Selecionar todas as faturas"
                      checked={faturasSelecionadasIds.size === faturas.length}
                      onChange={alternarSelecaoTodasFaturas}
                    />
                    <span className="text-sm text-text-secondary">Selecionar todas</span>
                  </div>

                  <BulkActions<FaturaRead>
                    selectedCount={faturasSelecionadasIds.size}
                    selectedRows={faturas.filter((fatura) => faturasSelecionadasIds.has(fatura.id))}
                    onClearSelection={() => setFaturasSelecionadasIds(new Set())}
                    className="mb-2"
                    actions={[
                      {
                        label: "Pagar selecionadas",
                        icon: Banknote,
                        onClick: abrirPagamentoEmLote,
                      },
                      {
                        label: "Excluir selecionadas",
                        icon: Trash2,
                        tone: "danger",
                        onClick: excluirFaturasSelecionadas,
                        confirmTitle: "Excluir faturas selecionadas?",
                        confirmDescription:
                          "As faturas selecionadas serão apagadas definitivamente. Transações vinculadas a elas não são apagadas — só perdem o vínculo com a fatura.",
                      },
                    ]}
                  />

                  <ul className="space-y-2">
                    {(faturasOrdenadas ?? faturas).map((fatura) => {
                      const [ano, mes] = fatura.mes_referencia.split("-").map(Number);
                      return (
                        <li key={fatura.id}>
                          <div className="flex items-center gap-3 rounded-md border border-border bg-surface-2 px-4 py-3 transition-colors duration-fast ease-out hover:bg-surface-3">
                            <SelectionCheckbox
                              label={`Selecionar fatura de ${nomeMes(mes)}/${ano}`}
                              checked={faturasSelecionadasIds.has(fatura.id)}
                              onChange={() => alternarSelecaoFatura(fatura.id)}
                            />
                            {/* `min-w-0` + `flex-wrap` no lado esquerdo (responsividade
                                mobile, 2026-07-21): sem isso, "Julho/2026 · vence
                                20/07/2026" + badge "Importada" nunca quebrava linha
                                nem encolhia, empurrando o valor/status do lado direito
                                para fora do card em telas estreitas. */}
                            <button
                              type="button"
                              onClick={() => setFaturaSelecionadaId(fatura.id)}
                              className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-x-3 gap-y-1 text-left"
                            >
                              <span className="flex min-w-0 flex-wrap items-center gap-2 text-sm text-text-primary">
                                <Receipt size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                                <span className="truncate">
                                  {nomeMes(mes)}/{ano} · vence {formatDate(fatura.data_vencimento)}
                                </span>
                                {fatura.importada && <Badge tone="neutral">Importada</Badge>}
                              </span>
                              <span className="flex shrink-0 items-center gap-3">
                                <span className="font-mono tabular text-sm text-text-primary">
                                  {formatMoney(fatura.valor_total)}
                                </span>
                                <FinancialBadge status={fatura.status} />
                              </span>
                            </button>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </>
              )}
            </div>
          </div>

          {/* Histórico — placeholder documentado, depende do CRUD de
              Transação (docs/analise-arquitetural-revisao-ux-cartoes.md,
              seção 13). Nenhuma lógica provisória: só um lugar reservado. */}
          <Card className="flex items-center gap-3 text-text-tertiary">
            <History size={18} aria-hidden="true" />
            <p className="text-sm">
              Histórico de compras deste cartão ficará disponível aqui quando o CRUD de Transação existir.
            </p>
          </Card>
        </div>
      </div>

      <CartaoFormDialog open={dialogoEdicaoAberto} cartao={cartao} onClose={() => setDialogoEdicaoAberto(false)} />

      <FaturaDrawer
        cartaoId={cartaoId}
        contaPagamentoId={cartao.conta_pagamento_id}
        faturaId={faturaSelecionadaId}
        onClose={() => setFaturaSelecionadaId(null)}
        onEditarCompra={abrirEdicaoCompra}
      />

      <PagamentoEmLoteDialog
        open={faturaIdsPagamentoLote != null}
        cartaoId={cartaoId}
        contaPagamentoId={cartao.conta_pagamento_id}
        faturaIds={faturaIdsPagamentoLote ?? []}
        onClose={fecharPagamentoEmLote}
      />

      <AjusteSaldoInicialDialog
        open={ajusteSaldoAberto}
        cartao={cartao}
        faturaAberta={faturaAberta}
        onClose={() => setAjusteSaldoAberto(false)}
      />

      <TransacaoFormDialog
        open={novaCompraAberta || compraEmEdicao != null}
        transacao={compraEmEdicao}
        onClose={fecharDialogoCompra}
        valoresIniciais={{ origem: "CARTAO", cartao_id: String(cartao.id) }}
      />

      <ConfirmAction
        open={confirmandoDesativar}
        title={`Desativar "${cartao.nome}"?`}
        description="O cartão deixa de aparecer nas listagens padrão, mas todo o histórico é preservado. Você pode reativá-lo a qualquer momento."
        confirmLabel="Desativar"
        tone="danger"
        loading={desativarCartao.isPending}
        onConfirm={confirmarDesativacao}
        onCancel={() => setConfirmandoDesativar(false)}
      />

      <ConfirmAction
        open={confirmandoExcluir}
        title={`Excluir "${cartao.nome}" definitivamente?`}
        description="Esta ação é permanente e não pode ser desfeita. O cartão será excluído para sempre — só é possível excluir um cartão sem nenhuma fatura vinculada."
        confirmLabel="Excluir definitivamente"
        tone="danger"
        loading={excluirCartao.isPending}
        onConfirm={confirmarExclusao}
        onCancel={() => setConfirmandoExcluir(false)}
      />

      <ConfirmAction
        open={confirmandoExcluirComHistorico}
        title={`Excluir "${cartao.nome}" e todo o histórico?`}
        description="Este cartão tem faturas vinculadas. Para excluí-lo, é preciso apagar junto todas as faturas e todas as transações feitas neste cartão — permanentemente, sem possibilidade de desfazer. Se preferir manter o histórico, desative o cartão em vez de excluir."
        confirmLabel="Apagar tudo e excluir"
        tone="danger"
        loading={excluirCartao.isPending}
        onConfirm={confirmarExclusaoComHistorico}
        onCancel={() => setConfirmandoExcluirComHistorico(false)}
      />
    </div>
  );
}
