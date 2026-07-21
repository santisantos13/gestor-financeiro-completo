import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Form } from "../../ui/Form";
import { CurrencyField } from "../../ui/CurrencyField";
import { DateField } from "../../ui/DateField";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { useAtualizarTransacao } from "../../../hooks/useTransacaoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage } from "../../../utils/errors";
import type { TransacaoRead } from "../../../types/transacao";

const parcelaEditSchema = z.object({
  valor: z.string().min(1, "Informe o valor."),
  data: z.string().min(1, "Informe a data."),
});

type ParcelaEditFormValues = z.infer<typeof parcelaEditSchema>;

export interface ParcelaContratoEditFormProps {
  parcela: TransacaoRead;
  onSalvo: () => void;
  onCancelar: () => void;
}

/**
 * Corrige valor/data de UMA parcela já lançada de Financiamento ou
 * Empréstimo — pedido do usuário: "após registrar o financiamento o
 * usuário não consegue editar informações importantes ex (valor pago em x
 * parcela, data que pagou em x parcela) caso ele tenha colocado algo
 * errado".
 *
 * Achado real ao investigar antes de escrever qualquer código novo: o
 * backend já permite isso — `TransacaoService.atualizar()` só bloqueia o
 * campo `status` quando `financiamento_id`/`emprestimo_id` está
 * preenchido (protege `saldo_devedor` de desincronizar de uma parcela
 * marcada paga por fora do Service dono, ver docstring do módulo);
 * `valor`/`data` nunca foram travados ali. `saldo_devedor` não precisa
 * (nem deve) ser recalculado aqui: ele é derivado do CRONOGRAMA
 * determinístico (posição da parcela na amortização PRICE/SAC - função
 * pura de principal/taxa/num_parcelas/sistema), nunca do valor gravado na
 * Transacao em si. Corrigir um valor/data digitado errado é só uma
 * correção de registro histórico, não uma mudança de amortização - por
 * isso nenhuma lógica nova de negócio foi necessária no backend, só esta
 * UI que faltava. Reaproveita 100% o PATCH genérico de Transação
 * (`useAtualizarTransacao`), compartilhado entre `FinanciamentoDrawer` e
 * `EmprestimoDrawer` para não duplicar este formulário duas vezes.
 *
 * Substitui o conteúdo do Drawer que o abriu (mesmo padrão já usado pela
 * confirmação de exclusão em ambos os Drawers) — nunca abre um
 * `FormDialog` (Tier 2) por cima de um Drawer (Tier 2) já aberto, a
 * combinação que já causou o bug crítico de backdrop duplicado corrigido
 * na Estabilização de Overlays.
 */
export function ParcelaContratoEditForm({ parcela, onSalvo, onCancelar }: ParcelaContratoEditFormProps) {
  const toast = useToast();
  const atualizar = useAtualizarTransacao();
  const form = useForm<ParcelaEditFormValues>({
    resolver: zodResolver(parcelaEditSchema),
    mode: "onBlur",
    defaultValues: { valor: parcela.valor, data: parcela.data },
  });

  async function onSubmit(valores: ParcelaEditFormValues) {
    try {
      await atualizar.mutateAsync({ id: parcela.id, dados: valores });
      toast.success(`Parcela ${parcela.numero_parcela} corrigida.`);
      onSalvo();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-h3 font-semibold text-text-primary">Corrigir parcela {parcela.numero_parcela}</h3>
        <p className="mt-1 text-sm text-text-secondary">
          Ajusta o valor e/ou a data registrados para esta parcela. Não recalcula o cronograma do
          contrato — só corrige o lançamento, caso algo tenha sido digitado errado.
        </p>
      </div>
      <Form form={form} onSubmit={onSubmit} className="space-y-4">
        <CurrencyField name="valor" label="Valor" />
        <DateField name="data" label="Data" />
        <FormActions>
          <CancelButton onClick={onCancelar} />
          <SubmitButton loading={atualizar.isPending}>Salvar</SubmitButton>
        </FormActions>
      </Form>
    </div>
  );
}
