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
import { ColorPicker } from "../../ui/ColorPicker";
import { TagBadge } from "./TagBadge";
import { tagFormSchema, tagFormValuesParaPayload, type TagFormValues } from "../../../schemas/tag";
import { useCriarTag, useAtualizarTag } from "../../../hooks/useTagQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import type { TagRead } from "../../../types/tag";
import type { Control } from "react-hook-form";

const VALORES_VAZIOS: TagFormValues = { nome: "", cor: "" };

function tagParaFormulario(tag: TagRead): TagFormValues {
  return { nome: tag.nome, cor: tag.cor ?? "" };
}

/** Preview ao vivo do `TagBadge` conforme o usuário digita — isolado num
 * componente próprio para que só ele re-renderize a cada mudança
 * (`useWatch` escopado), mesmo padrão de `CategoriaPreview`/
 * `InstituicaoPreview`. */
function TagPreview({ control }: { control: Control<TagFormValues> }) {
  const nome = useWatch({ control, name: "nome" });
  const cor = useWatch({ control, name: "cor" });
  return <TagBadge nome={nome || "Tag"} cor={cor || null} />;
}

export interface TagFormDialogProps {
  open: boolean;
  /** `null`/`undefined` = modo criação. */
  tag?: TagRead | null;
  /** Mesmo papel de `ContaFormDialog`/`CategoriaFormDialog` — abre em modo
   * leitura. Diferente de Categoria, não há `e_do_sistema` a considerar
   * aqui: toda Tag é sempre editável pelo dono. */
  somenteLeitura?: boolean;
  onClose: () => void;
}

/**
 * Modal único de criar/visualizar/editar Tag — mesma estrutura de
 * `ContaFormDialog`/`CategoriaFormDialog` (F6/F7), mas a versão mais
 * enxuta até agora: sem select de relacionamento, sem segunda camada de
 * permissão. Ver docs/analise-arquitetural-tag-frontend.md, seções 7-9.
 */
export function TagFormDialog({ open, tag, somenteLeitura, onClose }: TagFormDialogProps) {
  const toast = useToast();
  const criarTag = useCriarTag();
  const atualizarTag = useAtualizarTag();
  const emEdicao = tag != null;
  const salvando = criarTag.isPending || atualizarTag.isPending;

  const [editando, setEditando] = useState(!(somenteLeitura && emEdicao));

  const form = useForm<TagFormValues>({
    resolver: zodResolver(tagFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      form.reset(tag ? tagParaFormulario(tag) : VALORES_VAZIOS);
      setEditando(!(somenteLeitura && emEdicao));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, tag, somenteLeitura]);

  async function onSubmit(values: TagFormValues) {
    const payload = tagFormValuesParaPayload(values);
    try {
      if (emEdicao) {
        await atualizarTag.mutateAsync({ id: tag.id, dados: payload });
        toast.success(`Tag "${values.nome}" atualizada.`);
      } else {
        await criarTag.mutateAsync(payload);
        toast.success(`Tag "${values.nome}" criada.`);
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof TagFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  const titulo = !emEdicao ? "Nova tag" : editando ? "Editar tag" : "Detalhes da tag";
  const descricao = !emEdicao
    ? "Crie uma tag para classificar receitas e despesas livremente."
    : editando
      ? "Altere os dados da tag."
      : "Detalhes da tag.";

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
            <SubmitButton form="tag-form-dialog" loading={salvando}>
              {emEdicao ? "Salvar alterações" : "Criar tag"}
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
      <Form id="tag-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <TextField name="nome" label="Nome" placeholder="Ex.: reembolsável, viagem-2026" disabled={!editando} />
          </div>
          <div className="pb-2">
            <TagPreview control={form.control} />
          </div>
        </div>
        <ColorPicker name="cor" label="Cor" optional disabled={!editando} />
      </Form>
    </FormDialog>
  );
}
