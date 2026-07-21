import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/TextField";
import { SelectField } from "../../ui/SelectField";
import { IconPicker } from "../../ui/IconPicker";
import { ColorPicker } from "../../ui/ColorPicker";
import { CategorySelect } from "./CategorySelect";
import { CategoryBadge } from "./CategoryBadge";
import {
  categoriaFormSchema,
  categoriaFormValuesParaPayload,
  type CategoriaFormValues,
} from "../../../schemas/categoria";
import { useCriarCategoria, useAtualizarCategoria } from "../../../hooks/useCategoriaQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import { LABEL_TIPO_CATEGORIA } from "./categoriaTableColumns";
import type { CategoriaRead } from "../../../types/categoria";
import type { Control } from "react-hook-form";

const TIPO_OPTIONS = Object.entries(LABEL_TIPO_CATEGORIA).map(([value, label]) => ({ value, label }));

const VALORES_VAZIOS: CategoriaFormValues = {
  nome: "",
  tipo: "AMBOS",
  cor: "",
  icone: "",
  categoria_pai_id: "",
};

function categoriaParaFormulario(categoria: CategoriaRead): CategoriaFormValues {
  return {
    nome: categoria.nome,
    tipo: categoria.tipo,
    cor: categoria.cor ?? "",
    icone: categoria.icone ?? "",
    categoria_pai_id: categoria.categoria_pai_id != null ? String(categoria.categoria_pai_id) : "",
  };
}

/** Preview ao vivo do `CategoryBadge` conforme o usuário escolhe cor/ícone
 * — isolado num componente próprio para que só ele re-renderize a cada
 * mudança (`useWatch` escopado), mesmo padrão de `InstituicaoPreview` em
 * `ContaFormDialog.tsx`. */
function CategoriaPreview({ control }: { control: Control<CategoriaFormValues> }) {
  const nome = useWatch({ control, name: "nome" });
  const cor = useWatch({ control, name: "cor" });
  const icone = useWatch({ control, name: "icone" });
  return <CategoryBadge nome={nome || "Categoria"} cor={cor || null} icone={icone || null} size="md" />;
}

export interface CategoriaFormDialogProps {
  open: boolean;
  /** `null`/`undefined` = modo criação. */
  categoria?: CategoriaRead | null;
  /** Mesmo papel de `ContaFormDialog` — abre em modo leitura. Categoria de
   * sistema (Tarefa #111) NÃO força mais somente-leitura: o backend aceita
   * edição de conteúdo (nome/tipo/cor/icone/categoria_pai_id) para
   * qualquer categoria visível, sistema ou própria. */
  somenteLeitura?: boolean;
  onClose: () => void;
}

/**
 * Modal único de criar/visualizar/editar Categoria — mesma estrutura de
 * `ContaFormDialog` (F6). Duas diferenças novas: `categoria_pai_id` usa
 * `CategorySelect` (exclui a própria categoria e seus descendentes das
 * opções — filtro de UX, não a fonte de verdade do anti-ciclo, que
 * continua 100% no backend) e `cor`/`icone` usam os campos novos do Form
 * System (`ColorPicker`/`IconPicker`, Etapa F10). Ver
 * docs/analise-arquitetural-categoria-frontend.md, seções 8 e 9.
 */
export function CategoriaFormDialog({ open, categoria, somenteLeitura, onClose }: CategoriaFormDialogProps) {
  const toast = useToast();
  const criarCategoria = useCriarCategoria();
  const atualizarCategoria = useAtualizarCategoria();
  const emEdicao = categoria != null;
  const eDoSistema = categoria?.e_do_sistema ?? false;
  const salvando = criarCategoria.isPending || atualizarCategoria.isPending;

  const [editando, setEditando] = useState(!(somenteLeitura && emEdicao));

  const form = useForm<CategoriaFormValues>({
    resolver: zodResolver(categoriaFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      form.reset(categoria ? categoriaParaFormulario(categoria) : VALORES_VAZIOS);
      setEditando(!(somenteLeitura && emEdicao));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, categoria, somenteLeitura]);

  async function onSubmit(values: CategoriaFormValues) {
    const payload = categoriaFormValuesParaPayload(values);
    try {
      if (emEdicao) {
        await atualizarCategoria.mutateAsync({ id: categoria.id, dados: payload });
        toast.success(`Categoria "${values.nome}" atualizada.`);
      } else {
        await criarCategoria.mutateAsync(payload);
        toast.success(`Categoria "${values.nome}" criada.`);
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof CategoriaFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  const titulo = !emEdicao ? "Nova categoria" : editando ? "Editar categoria" : "Detalhes da categoria";
  const descricao = !emEdicao
    ? "Crie uma categoria própria para organizar receitas e despesas."
    : eDoSistema && editando
      ? "Categoria do sistema — disponível para todos os usuários. A edição vale para todo mundo."
      : editando
        ? "Altere os dados da categoria."
        : "Detalhes da categoria.";

  return (
    <FormDialog
      open={open}
      title={titulo}
      description={descricao}
      isDirty={editando && form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) =>
        editando ? (
          <FormActions>
            <CancelButton onClick={requestClose}>Cancelar</CancelButton>
            <SubmitButton form="categoria-form-dialog" loading={salvando}>
              {emEdicao ? "Salvar alterações" : "Criar categoria"}
            </SubmitButton>
          </FormActions>
        ) : (
          <FormActions>
            <CancelButton onClick={requestClose}>Fechar</CancelButton>
            <Button type="button" onClick={() => setEditando(true)}>
              Editar
            </Button>
          </FormActions>
        )
      }
    >
      <Form id="categoria-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        {eDoSistema && editando && (
          <div className="rounded-sm border border-border bg-surface-2 px-3 py-2 text-sm text-text-secondary">
            Categoria do sistema — a edição vale para todos os usuários. Não é possível desativar ou excluir
            (use "Excluir" apenas em categorias próprias).
          </div>
        )}
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <TextField name="nome" label="Nome" placeholder="Ex.: Assinaturas, Aluguel" disabled={!editando} />
          </div>
          <div className="pb-2">
            <CategoriaPreview control={form.control} />
          </div>
        </div>
        <SelectField name="tipo" label="Tipo" options={TIPO_OPTIONS} disabled={!editando} />
        <CategorySelect
          name="categoria_pai_id"
          label="Categoria pai"
          optional
          description="Deixe em branco para uma categoria de primeiro nível."
          disabled={!editando}
          excludeId={categoria?.id}
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ColorPicker name="cor" label="Cor" optional disabled={!editando} />
          <IconPicker name="icone" label="Ícone" optional disabled={!editando} />
        </div>
      </Form>
    </FormDialog>
  );
}
