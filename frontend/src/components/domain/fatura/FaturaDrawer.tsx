import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, ChevronDown, Lock, Pencil, Plus, Receipt, Trash2 } from "lucide-react";
import { Drawer } from "../../ui/Drawer";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { ProgressBar } from "../../ui/ProgressBar";
import { Skeleton } from "../../ui/Skeleton";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { CancelButton } from "../../ui/CancelButton";
import { SubmitButton } from "../../ui/SubmitButton";
import { CurrencyField } from "../../ui/CurrencyField";
import { DateField } from "../../ui/DateField";
import { TextField } from "../../ui/TextField";
import {
  useFatura,
  useFecharFatura,
  useRegistrarPagamento,
  useExcluirFatura,
  useAjustarValorPosFechamento,
} from "../../../hooks/useFaturaQueries";
import { useComprasDaFatura, useExcluirTransacao } from "../../../hooks/useTransacaoQueries";
import { useParcelamento } from "../../../hooks/useParcelamentoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage } from "../../../utils/errors";
import { formatMoney } from "../../../utils/format";
import { formatDate, nomeMes } from "../../../utils/date";
import { preverStatusPosPagamento } from "../../../utils/fatura";
import {
  pagamentoFormSchema,
  pagamentoFormValuesParaPayload,
  type PagamentoFormValues,
  ajustePosFechamentoFormSchema,
  ajustePosFechamentoFormValuesParaPayload,
  type AjustePosFechamentoFormValues,
} from "../../../schemas/fatura";
import type { TransacaoRead } from "../../../types/transacao";

export interface FaturaDrawerProps {
  cartaoId: number;
  /** `Cartao.conta_pagamento_id` — necessário para invalidar
   * `contas.detail` corretamente ao registrar um pagamento (o pagamento
   * cria uma `Transacao` de despesa nessa conta, ver
   * docs/analise-arquitetural-refinamento-fatura-pagamento.md, seção 2).
   * `undefined`/`null` só desativa essa invalidação específica (nunca
   * quebra o registro do pagamento em si). */
  contaPagamentoId?: number | null;
  /** `null` = drawer fechado. Escopo é sempre uma fatura só (seção 3 de
   * `docs/analise-arquitetural-fatura-frontend.md`) — trocar de fatura
   * troca o conteúdo do mesmo drawer, nunca acumula. */
  faturaId: number | null;
  onClose: () => void;
  /** Pedido do usuário (2026-07-20): "na aba compras desta fatura, deveria
   * ter como editar e excluir compras daquela fatura". Editar precisa de um
   * `TransacaoFormDialog` (Tier 2) — não pode abrir por cima do próprio
   * Drawer (também Tier 2, ver nota de "Fechar ciclo"/"Excluir fatura" logo
   * abaixo), então este componente só fecha a si mesmo e delega a abertura
   * do formulário para quem o renderiza (`CartaoDetalhePage`, que já possui
   * um `TransacaoFormDialog` próprio para "Nova compra"). */
  onEditarCompra: (transacao: TransacaoRead) => void;
}

const VALORES_VAZIOS_PAGAMENTO: PagamentoFormValues = { valor: "", data: "", descricao: "" };

/**
 * `Drawer` de uma fatura individual — Etapa F10, polido no Refinamento de
 * Fatura/Pagamento (`docs/analise-arquitetural-refinamento-fatura-pagamento.md`).
 * Ações e detalhes de UMA fatura por vez (nunca gerencia a lista inteira,
 * que fica inline na página de detalhes do cartão). Mecânica do `Drawer`
 * em si vem de `docs/analise-arquitetural-overlays.md`, seção 4.5 — este
 * componente só decide o que renderizar dentro.
 *
 * Pagamento total/parcial/personalizado é, do ponto de vista do backend,
 * sempre a mesma chamada com um valor diferente (`FaturaService.registrar_pagamento`
 * aceita qualquer `valor > 0`) — os atalhos abaixo só preenchem o campo,
 * nenhum payload novo. O preview de status pós-pagamento
 * (`preverStatusPosPagamento`) é só apresentação: nunca persistido, some
 * assim que a mutation resolve e os dados reais (`useFatura`) chegam.
 *
 * "Fechar ciclo" e "Excluir fatura" confirmam SUBSTITUINDO o conteúdo do
 * próprio `Drawer` (mesma técnica que `FormDialog` já usa para "Descartar
 * alterações?"), nunca abrindo um `ConfirmAction` separado — Estabilização
 * de Overlays: um `ConfirmAction` (Tier 2, backdrop próprio) montado a
 * partir de dentro de um `Drawer` já aberto (também Tier 2) empilhava dois
 * backdrops de 60% opacidade + blur, compondo para quase preto e cobrindo
 * o próprio Drawer — a regra do projeto (`docs/analise-arquitetural-overlays.md`,
 * seção 2) já dizia "nunca empilha, sempre substitui o conteúdo do
 * primeiro", só não estava implementada aqui ainda.
 *
 * "Compras desta fatura" (pedido do usuário, 2026-07-20): seção
 * expansível ("caso o usuário queira", nunca aberta por padrão) que lista
 * as `Transacao` lançadas neste ciclo (`useComprasDaFatura`, filtro novo
 * `fatura_id` em `GET /transacoes`). Só busca quando expandida — mesmo
 * padrão de `useContaExtrato`/`useAportesLegadosDaMeta` — para o
 * `CartaoDetalhePage` (que pode listar várias faturas de uma vez) nunca
 * disparar N requisições extras ao só carregar a lista.
 *
 * Editar/excluir compras desta lista (pedido do usuário, 2026-07-20): a
 * exclusão confirma SUBSTITUINDO o item da lista (mesma técnica de "Fechar
 * ciclo"/"Excluir fatura" acima — nunca um `ConfirmAction` separado, mesmo
 * motivo). A edição não pode reaproveitar essa técnica porque precisa do
 * `TransacaoFormDialog` inteiro (com todos os campos), que é ele mesmo um
 * overlay Tier 2 — por isso `onEditarCompra` fecha este Drawer e delega a
 * abertura para o pai.
 *
 * "Adicionar valor esquecido" (pedido do usuário, 2026-07-20: "quero
 * adicionar uma transação em uma fatura que já foi fechada e paga, porém
 * tinha esquecido dela antes") — só aparece quando `status !== "ABERTA"`
 * (uma fatura aberta já aceita a compra normalmente, lançada de verdade).
 * Formulário inline, mesma técnica de "Registrar pagamento" logo abaixo
 * (nunca um `FormDialog` separado — mesmo motivo de Tier 2 já explicado
 * acima). Não cria nenhuma `Transacao`: soma o valor direto no total da
 * fatura (`FaturaService.ajustar_valor_pos_fechamento`), com o mesmo
 * efeito sobre `limite_disponivel` que uma compra real teria.
 */
export function FaturaDrawer({ cartaoId, contaPagamentoId, faturaId, onClose, onEditarCompra }: FaturaDrawerProps) {
  const toast = useToast();
  const { data: fatura, isLoading } = useFatura(faturaId);
  const fecharFatura = useFecharFatura(cartaoId);
  const registrarPagamento = useRegistrarPagamento(cartaoId, contaPagamentoId);
  const excluirFatura = useExcluirFatura(cartaoId);
  const ajustarValorPosFechamento = useAjustarValorPosFechamento(cartaoId);

  const [confirmandoFechar, setConfirmandoFechar] = useState(false);
  const [confirmandoExcluir, setConfirmandoExcluir] = useState(false);
  const [pagamentoAberto, setPagamentoAberto] = useState(false);
  const [ajustePosFechamentoAberto, setAjustePosFechamentoAberto] = useState(false);
  // Pedido do usuário (2026-07-20): "seria interessante se cada fatura
  // tivesse o histórico de compras dela caso o usuário queira" - por isso
  // "caso o usuário queira" (expansível, não sempre visível) e só busca
  // quando expandido (useComprasDaFatura(..., expandido), mesmo padrão de
  // useContaExtrato/useAportesLegadosDaMeta).
  const [comprasExpandido, setComprasExpandido] = useState(false);
  const { data: compras, isLoading: carregandoCompras } = useComprasDaFatura(
    faturaId ?? 0,
    comprasExpandido && faturaId != null,
  );

  // Exclusão de uma compra da lista — mesmo padrão de `TransacoesPage`
  // (`useExcluirTransacao` + `useParcelamento` só para a mensagem de
  // confirmação saber o número real de parcelas).
  const [compraParaExcluir, setCompraParaExcluir] = useState<TransacaoRead | null>(null);
  const excluirCompra = useExcluirTransacao(compraParaExcluir?.conta_id, compraParaExcluir?.cartao_id);
  const { data: parcelamentoDaCompra } = useParcelamento(compraParaExcluir?.parcelamento_id ?? null);

  const formPagamento = useForm<PagamentoFormValues>({
    resolver: zodResolver(pagamentoFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS_PAGAMENTO,
  });

  const valorDigitado = useWatch({ control: formPagamento.control, name: "valor" });

  const formAjustePosFechamento = useForm<AjustePosFechamentoFormValues>({
    resolver: zodResolver(ajustePosFechamentoFormSchema),
    mode: "onBlur",
    defaultValues: { valor: "" },
  });

  useEffect(() => {
    if (faturaId == null) {
      setConfirmandoFechar(false);
      setConfirmandoExcluir(false);
      setPagamentoAberto(false);
      setAjustePosFechamentoAberto(false);
      setComprasExpandido(false);
      setCompraParaExcluir(null);
      formPagamento.reset(VALORES_VAZIOS_PAGAMENTO);
      formAjustePosFechamento.reset({ valor: "" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [faturaId]);

  async function confirmarFechar() {
    if (!fatura) return;
    try {
      await fecharFatura.mutateAsync(fatura.id);
      toast.success("Fatura fechada — o valor total foi congelado.");
      setConfirmandoFechar(false);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function onSubmitPagamento(valores: PagamentoFormValues) {
    if (!fatura) return;
    try {
      await registrarPagamento.mutateAsync({ id: fatura.id, dados: pagamentoFormValuesParaPayload(valores) });
      toast.success("Pagamento registrado.");
      setPagamentoAberto(false);
      formPagamento.reset(VALORES_VAZIOS_PAGAMENTO);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExcluir() {
    if (!fatura) return;
    try {
      await excluirFatura.mutateAsync(fatura.id);
      toast.success("Fatura excluída.");
      setConfirmandoExcluir(false);
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function onSubmitAjustePosFechamento(valores: AjustePosFechamentoFormValues) {
    if (!fatura) return;
    try {
      await ajustarValorPosFechamento.mutateAsync({
        id: fatura.id,
        dados: ajustePosFechamentoFormValuesParaPayload(valores),
      });
      toast.success("Valor somado a esta fatura.");
      setAjustePosFechamentoAberto(false);
      formAjustePosFechamento.reset({ valor: "" });
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExcluirCompra() {
    if (!compraParaExcluir) return;
    try {
      await excluirCompra.mutateAsync(compraParaExcluir.id);
      toast.success(`Transação "${compraParaExcluir.descricao}" excluída.`);
      setCompraParaExcluir(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  function editarCompra(compra: TransacaoRead) {
    onEditarCompra(compra);
    onClose();
  }

  const [ano, mes] = fatura ? fatura.mes_referencia.split("-").map(Number) : [0, 0];
  const restante = fatura ? Math.max(0, Number(fatura.valor_total) - Number(fatura.valor_pago)) : 0;

  return (
    <Drawer
      open={faturaId != null}
      onClose={onClose}
      title={fatura ? `${nomeMes(mes)}/${ano}` : "Fatura"}
      description={fatura ? `Fatura do cartão — ${formatDate(fatura.data_vencimento)}` : undefined}
    >
      {isLoading || !fatura ? (
        <div className="space-y-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : confirmandoFechar ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-info-subtle">
              <Lock size={16} className="text-info" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="text-h3 font-semibold text-text-primary">Fechar esta fatura?</h3>
              <p className="mt-1 text-sm text-text-secondary">
                O valor total é congelado a partir de agora — o ciclo deixa de aceitar novas compras.
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setConfirmandoFechar(false)}>
              Continuar aberta
            </Button>
            <Button size="sm" loading={fecharFatura.isPending} onClick={confirmarFechar}>
              Fechar fatura
            </Button>
          </div>
        </div>
      ) : confirmandoExcluir ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-negative-subtle">
              <AlertTriangle size={16} className="text-negative" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="text-h3 font-semibold text-text-primary">Excluir esta fatura?</h3>
              <p className="mt-1 text-sm text-text-secondary">
                Esta ação é permanente. Se esta fatura tiver alguma compra ou pagamento vinculado,
                eles não são apagados — só deixam de estar associados a este ciclo (continuam
                aparecendo em Transações, e você pode editá-los ou removê-los por lá se também
                estiverem errados).
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setConfirmandoExcluir(false)}>
              Cancelar
            </Button>
            <Button variant="danger" size="sm" loading={excluirFatura.isPending} onClick={confirmarExcluir}>
              Excluir
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FinancialBadge status={fatura.status} />
                {fatura.importada && <Badge tone="neutral">Importada</Badge>}
              </div>
              <Receipt size={16} className="text-text-tertiary" aria-hidden="true" />
            </div>

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-caption text-text-tertiary">Fechamento</dt>
                <dd className="text-text-primary">{formatDate(fatura.data_fechamento)}</dd>
              </div>
              <div>
                <dt className="text-caption text-text-tertiary">Vencimento</dt>
                <dd className="text-text-primary">{formatDate(fatura.data_vencimento)}</dd>
              </div>
              <div>
                <dt className="text-caption text-text-tertiary">Valor total</dt>
                <dd className="font-mono tabular text-text-primary">{formatMoney(fatura.valor_total)}</dd>
              </div>
              <div>
                <dt className="text-caption text-text-tertiary">Valor pago</dt>
                <dd className="font-mono tabular text-text-primary">{formatMoney(fatura.valor_pago)}</dd>
              </div>
              {/* Transparência sobre o valor declarado via "Informar saldo
                  já utilizado" (`AjusteSaldoInicialDialog`) — só aparece
                  quando há algo a mostrar, e só enquanto ABERTA (depois de
                  fechada já está embutido em "Valor total" para sempre). */}
              {fatura.status === "ABERTA" && Number(fatura.ajuste_manual) > 0 && (
                <div>
                  <dt className="text-caption text-text-tertiary">Saldo já utilizado (sem transação)</dt>
                  <dd className="font-mono tabular text-text-primary">{formatMoney(fatura.ajuste_manual)}</dd>
                </div>
              )}

              {/* Restante sempre visível (não só no formulário de pagamento) —
                  quem usa o sistema todo dia quer ver o número direto, sem
                  precisar abrir "Registrar pagamento" primeiro. */}
              {fatura.status !== "ABERTA" && (
                <div>
                  <dt className="text-caption text-text-tertiary">Restante</dt>
                  <dd className={`font-mono tabular ${restante > 0 ? "text-negative" : "text-positive"}`}>
                    {formatMoney(restante)}
                  </dd>
                </div>
              )}
            </dl>

            {fatura.status !== "ABERTA" && (
              <ProgressBar
                value={Number(fatura.valor_total) > 0 ? (Number(fatura.valor_pago) / Number(fatura.valor_total)) * 100 : 0}
                tone={fatura.status === "PAGA" ? "positive" : "info"}
                aria-label="Progresso de pagamento da fatura"
              />
            )}

            <div className="border-t border-border-subtle pt-4">
              <button
                type="button"
                onClick={() => setComprasExpandido((atual) => !atual)}
                className="flex w-full items-center justify-between text-left"
                aria-expanded={comprasExpandido}
                aria-label={`${comprasExpandido ? "Recolher" : "Expandir"} compras desta fatura`}
              >
                <span className="text-caption font-medium text-text-tertiary">Compras desta fatura</span>
                <ChevronDown
                  size={14}
                  className={`shrink-0 text-text-tertiary transition-transform duration-fast ease-out ${comprasExpandido ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
              </button>

              {comprasExpandido && (
                <div className="mt-2 space-y-1.5">
                  {carregandoCompras ? (
                    <>
                      <Skeleton className="h-10 w-full" />
                      <Skeleton className="h-10 w-full" />
                    </>
                  ) : !compras || compras.length === 0 ? (
                    <p className="py-1 text-caption text-text-tertiary">Nenhuma compra lançada neste ciclo.</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {compras.map((compra) =>
                        compraParaExcluir?.id === compra.id ? (
                          <li
                            key={compra.id}
                            className="space-y-2 rounded-sm border border-negative/30 bg-negative-subtle px-3 py-2"
                          >
                            <p className="text-caption text-text-primary">
                              {compraParaExcluir.parcelamento_id != null
                                ? `Excluir "${compraParaExcluir.descricao}"? Esta compra possui ${parcelamentoDaCompra?.num_parcelas ?? "várias"} parcelas — todas serão removidas permanentemente (as já em faturas fechadas ficam preservadas como histórico).`
                                : `Excluir "${compraParaExcluir.descricao}"? Esta ação é permanente — o valor de ${formatMoney(compraParaExcluir.valor)} deixa de contar no limite do cartão.`}
                            </p>
                            <div className="flex justify-end gap-2">
                              <Button variant="secondary" size="sm" onClick={() => setCompraParaExcluir(null)}>
                                Cancelar
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                loading={excluirCompra.isPending}
                                onClick={confirmarExcluirCompra}
                              >
                                Excluir
                              </Button>
                            </div>
                          </li>
                        ) : (
                          <li
                            key={compra.id}
                            className="flex items-center justify-between gap-3 rounded-sm border border-border-subtle bg-surface-2 px-3 py-2"
                          >
                            <div className="min-w-0">
                              <p className="truncate text-caption text-text-primary">{compra.descricao}</p>
                              <p className="text-caption text-text-tertiary">{formatDate(compra.data)}</p>
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                              <span className="font-mono tabular text-caption text-text-primary">
                                {formatMoney(compra.valor)}
                              </span>
                              <button
                                type="button"
                                onClick={() => editarCompra(compra)}
                                className="rounded-sm p-1 text-text-tertiary transition-colors hover:text-text-primary"
                                aria-label={`Editar ${compra.descricao}`}
                              >
                                <Pencil size={13} aria-hidden="true" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setCompraParaExcluir(compra)}
                                className="rounded-sm p-1 text-text-tertiary transition-colors hover:text-negative"
                                aria-label={`Excluir ${compra.descricao}`}
                              >
                                <Trash2 size={13} aria-hidden="true" />
                              </button>
                            </div>
                          </li>
                        ),
                      )}
                    </ul>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-2 border-t border-border-subtle pt-4">
              {fatura.status === "ABERTA" && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  onClick={() => setConfirmandoFechar(true)}
                >
                  <Lock size={14} aria-hidden="true" />
                  Fechar ciclo
                </Button>
              )}

              {fatura.status !== "ABERTA" && !pagamentoAberto && (
                <Button variant="secondary" size="sm" className="w-full" onClick={() => setPagamentoAberto(true)}>
                  Registrar pagamento
                </Button>
              )}

              {pagamentoAberto && (
                <div className="rounded-md border border-border-subtle p-3">
                  <Form
                    id="pagamento-fatura-form"
                    form={formPagamento}
                    onSubmit={onSubmitPagamento}
                    className="space-y-3"
                  >
                    {/* Atalhos client-side — só preenchem o campo, o payload
                        enviado é idêntico independentemente de qual botão
                        (ou digitação livre) originou o valor (seção 3 do
                        documento). */}
                    <div className="flex flex-wrap gap-2">
                      {Number(fatura.valor_pago) === 0 && (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => formPagamento.setValue("valor", fatura.valor_total, { shouldDirty: true })}
                        >
                          Pagar total
                        </Button>
                      )}
                      {restante > 0 && (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => formPagamento.setValue("valor", restante.toFixed(2), { shouldDirty: true })}
                        >
                          Pagar restante
                        </Button>
                      )}
                    </div>

                    <CurrencyField name="valor" label="Valor pago" />

                    {/* Preview client-side, não-autoritativo (seção 4 do
                        documento) — descartado assim que a mutation resolve. */}
                    {!!valorDigitado && Number(valorDigitado) > 0 && (
                      <div className="rounded-sm border border-border-subtle bg-surface-2 px-3 py-2 text-caption text-text-tertiary">
                        Depois deste pagamento:{" "}
                        <span className="font-mono tabular text-text-secondary">
                          {formatMoney(Number(fatura.valor_pago) + Number(valorDigitado))}
                        </span>{" "}
                        pago,{" "}
                        <span className="font-mono tabular text-text-secondary">
                          {formatMoney(Math.max(0, restante - Number(valorDigitado)))}
                        </span>{" "}
                        restante — status vira{" "}
                        <FinancialBadge status={preverStatusPosPagamento(fatura, Number(valorDigitado))} />
                      </div>
                    )}

                    <DateField name="data" label="Data do pagamento" />
                    <TextField name="descricao" label="Descrição" optional placeholder="Ex.: Pagamento via Pix" />
                    <FormActions>
                      <CancelButton onClick={() => setPagamentoAberto(false)}>Cancelar</CancelButton>
                      <SubmitButton form="pagamento-fatura-form" loading={registrarPagamento.isPending}>
                        Registrar
                      </SubmitButton>
                    </FormActions>
                  </Form>
                </div>
              )}

              {fatura.status !== "ABERTA" && !ajustePosFechamentoAberto && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  onClick={() => setAjustePosFechamentoAberto(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  Adicionar valor esquecido
                </Button>
              )}

              {ajustePosFechamentoAberto && (
                <div className="rounded-md border border-border-subtle p-3">
                  <p className="mb-3 text-caption text-text-tertiary">
                    Some um valor ao total desta fatura sem criar uma transação — para uma compra que você
                    esqueceu de lançar antes de fechar/pagar o ciclo.
                  </p>
                  <Form
                    id="ajuste-pos-fechamento-form"
                    form={formAjustePosFechamento}
                    onSubmit={onSubmitAjustePosFechamento}
                    className="space-y-3"
                  >
                    <CurrencyField name="valor" label="Valor esquecido" />
                    <FormActions>
                      <CancelButton onClick={() => setAjustePosFechamentoAberto(false)}>Cancelar</CancelButton>
                      <SubmitButton form="ajuste-pos-fechamento-form" loading={ajustarValorPosFechamento.isPending}>
                        Somar à fatura
                      </SubmitButton>
                    </FormActions>
                  </Form>
                </div>
              )}

              <Button
                variant="ghost"
                size="sm"
                className="w-full hover:text-negative"
                onClick={() => setConfirmandoExcluir(true)}
              >
                <Trash2 size={14} aria-hidden="true" />
                Excluir fatura
              </Button>
            </div>
          </div>
      )}
    </Drawer>
  );
}
