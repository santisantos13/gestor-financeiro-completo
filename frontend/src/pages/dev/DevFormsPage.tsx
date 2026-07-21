import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Save } from "lucide-react";
import { useToast } from "../../hooks/useToast";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Form } from "../../components/ui/Form";
import { FormDialog } from "../../components/ui/FormDialog";
import { FormSection } from "../../components/ui/FormSection";
import { FormActions } from "../../components/ui/FormActions";
import { SubmitButton } from "../../components/ui/SubmitButton";
import { CancelButton } from "../../components/ui/CancelButton";
import { TextField } from "../../components/ui/TextField";
import { EmailField } from "../../components/ui/EmailField";
import { PasswordField } from "../../components/ui/PasswordField";
import { TextAreaField } from "../../components/ui/TextAreaField";
import { CurrencyField } from "../../components/ui/CurrencyField";
import { PercentageField } from "../../components/ui/PercentageField";
import { NumberField } from "../../components/ui/NumberField";
import { DateField } from "../../components/ui/DateField";
import { DateTimeField } from "../../components/ui/DateTimeField";
import { SelectField } from "../../components/ui/SelectField";
import { MultiSelectField } from "../../components/ui/MultiSelectField";
import { SearchSelect } from "../../components/ui/SearchSelect";
import { TagsInput } from "../../components/ui/TagsInput";
import { CheckboxField } from "../../components/ui/CheckboxField";
import { SwitchField } from "../../components/ui/SwitchField";
import { RadioGroupField } from "../../components/ui/RadioGroupField";
import { FileUpload } from "../../components/ui/FileUpload";
import { IconPicker } from "../../components/ui/IconPicker";
import { ColorPicker } from "../../components/ui/ColorPicker";

const CATEGORIAS = [
  { value: "moradia", label: "Moradia" },
  { value: "transporte", label: "Transporte" },
  { value: "alimentacao", label: "Alimentação" },
  { value: "lazer", label: "Lazer" },
  { value: "saude", label: "Saúde" },
];

const TAGS_DISPONIVEIS = [
  { value: "fixo", label: "Fixo" },
  { value: "variavel", label: "Variável" },
  { value: "urgente", label: "Urgente" },
  { value: "revisar", label: "Revisar" },
];

const TIPOS = [
  { value: "entrada", label: "Entrada", description: "Dinheiro que entra" },
  { value: "saida", label: "Saída", description: "Dinheiro que sai" },
];

const exemploSchema = z.object({
  nome: z.string().min(1, "Nome é obrigatório").min(3, "Use ao menos 3 caracteres"),
  email: z.string().min(1, "E-mail é obrigatório").email("Formato de e-mail inválido"),
  senha: z.string().min(1, "Senha é obrigatória").min(6, "Use ao menos 6 caracteres"),
  bio: z.string().optional(),
  valor: z.string().min(1, "Informe um valor"),
  percentual: z.string().optional(),
  quantidade: z
    .number({ error: "Informe uma quantidade" })
    .int("Use um número inteiro")
    .positive("Deve ser maior que zero"),
  data: z.string().min(1, "Informe uma data"),
  dataHora: z.string().optional(),
  categoria: z.string().min(1, "Selecione uma categoria"),
  tags: z.array(z.string()).optional(),
  ativo: z.boolean().optional(),
  aceitaTermos: z.boolean().refine((v) => v === true, "É preciso aceitar para continuar"),
  tipo: z.string().min(1, "Selecione uma opção"),
  responsavel: z.string().min(1, "Selecione um responsável"),
  anexos: z.array(z.instanceof(File)).optional(),
});

type ExemploValues = z.infer<typeof exemploSchema>;

const valoresIniciais: ExemploValues = {
  nome: "",
  email: "",
  senha: "",
  bio: "",
  valor: "",
  percentual: "",
  quantidade: undefined as unknown as number,
  data: "",
  dataHora: "",
  categoria: "",
  tags: [],
  ativo: false,
  aceitaTermos: false,
  tipo: "",
  responsavel: "",
  anexos: [],
};

const categoriaDialogSchema = z.object({
  nome: z.string().min(1, "Nome é obrigatório"),
  cor: z.string(),
  icone: z.string(),
});
type CategoriaDialogValues = z.infer<typeof categoriaDialogSchema>;

interface DisabledDemoValues {
  texto: string;
  valor: string;
}

interface TagsDemoValues {
  tags: string[];
}

/**
 * Laboratório visual permanente do sistema de formulários — rota
 * `/dev/forms` (Etapa F5), protegida, fora do `Sidebar` (mesmo padrão de
 * `/dev` e `/dev/tables`). Cobre: formulário completo com praticamente
 * todo tipo de `*Field` desta etapa, validação Zod (`mode: "onBlur"`),
 * foco+scroll automático no primeiro erro (submit vazio), loading/
 * sucesso/erro de submit, `FormDialog` com fechamento confirmado quando
 * há alteração não salva, erro de campo simulado vindo "do servidor"
 * (`setError`, mesma mecânica de mapear um 422 real). Nenhum campo aqui
 * pertence a uma entidade do backend.
 */
export function DevFormsPage() {
  const toast = useToast();
  const [simularErroServidor, setSimularErroServidor] = useState(false);
  const [dialogAberto, setDialogAberto] = useState(false);

  const form = useForm<ExemploValues>({
    resolver: zodResolver(exemploSchema),
    mode: "onBlur",
    defaultValues: valoresIniciais,
  });

  async function onSubmit(values: ExemploValues) {
    await new Promise((resolve) => setTimeout(resolve, 900));

    if (simularErroServidor) {
      form.setError("nome", {
        type: "server",
        message: "Já existe um registro com esse nome (erro 422 simulado do backend).",
      });
      toast.error("Não foi possível salvar — confira os campos destacados.");
      return;
    }

    toast.success(`"${values.nome}" salvo com sucesso (simulado — nada foi enviado de verdade).`);
    form.reset(valoresIniciais);
  }

  const dialogForm = useForm<CategoriaDialogValues>({
    resolver: zodResolver(categoriaDialogSchema),
    mode: "onBlur",
    defaultValues: { nome: "", cor: "", icone: "" },
  });

  async function onSubmitDialog(values: CategoriaDialogValues) {
    await new Promise((resolve) => setTimeout(resolve, 700));
    toast.success(`Categoria "${values.nome}" criada (simulado).`);
    dialogForm.reset({ nome: "", cor: "", icone: "" });
    setDialogAberto(false);
  }

  const disabledDemoForm = useForm<DisabledDemoValues>({
    defaultValues: { texto: "Não editável", valor: "1234.50" },
  });

  const tagsDemoForm = useForm<TagsDemoValues>({
    defaultValues: { tags: ["fixo", "revisar"] },
  });

  return (
    <div className="space-y-10 pb-16">
      <div>
        <h1 className="text-h1 font-semibold text-text-primary">/dev/forms — laboratório de formulários</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Infraestrutura genérica de <code className="font-mono text-text-tertiary">components/ui/</code>{" "}
          criada na Etapa F5 (React Hook Form + Zod), exercitada com dado 100% sintético — sem chamada à
          API, sem entidade real. Ver docs/analise-arquitetural-frontend.md, seção 12.
        </p>
      </div>

      <section>
        <SectionTitle action={<Badge tone="accent">RHF + Zod, mode: onBlur</Badge>}>
          Formulário completo — exemplo com quase todo tipo de campo
        </SectionTitle>
        <Card>
          <Form form={form} onSubmit={onSubmit} className="space-y-6">
            <FormSection title="Identificação" description="TextField, EmailField, PasswordField, TextAreaField.">
              <TextField name="nome" label="Nome" placeholder="Ex.: Assinatura de streaming" />
              <EmailField name="email" label="E-mail" />
              <PasswordField name="senha" label="Senha" />
              <TextAreaField name="bio" label="Observações" optional description="Texto livre, sem limite rígido." />
            </FormSection>

            <FormSection title="Números e máscaras" description="CurrencyField, PercentageField, NumberField.">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <CurrencyField name="valor" label="Valor" />
                <PercentageField name="percentual" label="Percentual" optional />
                <NumberField name="quantidade" label="Quantidade" />
              </div>
            </FormSection>

            <FormSection title="Datas" description="DateField (calendário custom) e DateTimeField.">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <DateField name="data" label="Data" />
                <DateTimeField name="dataHora" label="Data e hora" optional />
              </div>
            </FormSection>

            <FormSection title="Seleção" description="SelectField, MultiSelectField, SearchSelect.">
              <SelectField name="categoria" label="Categoria" options={CATEGORIAS} placeholder="Selecione uma categoria" />
              <MultiSelectField name="tags" label="Tags" options={TAGS_DISPONIVEIS} optional />
              <SearchSelect
                name="responsavel"
                label="Responsável"
                options={CATEGORIAS.map((c) => ({ value: c.value, label: `Time de ${c.label}` }))}
                searchPlaceholder="Buscar responsável..."
              />
            </FormSection>

            <FormSection title="Booleanos e escolha única" description="CheckboxField, SwitchField, RadioGroupField.">
              <SwitchField name="ativo" label="Ativo" description="Alterna um estado ligado/desligado." />
              <RadioGroupField name="tipo" label="Tipo" options={TIPOS} inline />
              <CheckboxField name="aceitaTermos" label="Li e aceito os termos (obrigatório nesta demonstração)" />
            </FormSection>

            <FormSection title="Arquivo" description="FileUpload — infraestrutura apenas, sem integração com Anexo.">
              <FileUpload name="anexos" label="Anexos" optional multiple />
            </FormSection>

            <label className="flex items-center gap-2 text-sm text-text-tertiary">
              <input
                type="checkbox"
                checked={simularErroServidor}
                onChange={(event) => setSimularErroServidor(event.target.checked)}
                className="h-3.5 w-3.5"
              />
              Simular erro 422 do servidor no campo "Nome" ao salvar
            </label>

            <FormActions className="border-t border-border-subtle pt-4">
              <CancelButton onClick={() => form.reset(valoresIniciais)}>Limpar</CancelButton>
              <SubmitButton loading={form.formState.isSubmitting}>
                <Save size={14} aria-hidden="true" />
                Salvar
              </SubmitButton>
            </FormActions>
          </Form>
        </Card>
        <p className="mt-2 text-sm text-text-tertiary">
          Clique em "Salvar" com o formulário vazio para ver validação onBlur, foco automático e scroll até
          o primeiro erro.
        </p>
      </section>

      <section>
        <SectionTitle>FormDialog — modal com confirmação de fechamento (com IconPicker/ColorPicker, Etapa F10)</SectionTitle>
        <Button onClick={() => setDialogAberto(true)}>
          <Plus size={14} aria-hidden="true" />
          Nova categoria (exemplo)
        </Button>
        <p className="mt-2 text-sm text-text-tertiary">
          Digite algo e tente fechar (Esc, clique fora ou "×") sem salvar — o conteúdo do modal troca para
          uma confirmação em vez de abrir um segundo modal por cima (design-system.md, seção 22).{" "}
          <code className="font-mono text-text-tertiary">ColorPicker</code>/
          <code className="font-mono text-text-tertiary">IconPicker</code> evoluíram na Etapa F10 (Rich
          Pickers) sobre o <code className="font-mono text-text-tertiary">RichPicker</code> — registry curado
          de ícones em{" "}
          <code className="font-mono text-text-tertiary">lib/icons.ts</code>, sem convenção do backend para
          seguir (ver docs/analise-arquitetural-categoria-frontend.md, seção 0).{" "}
          <code className="font-mono text-text-tertiary">CategorySelect</code> (o outro componente novo desta
          etapa) não aparece aqui de propósito — é um select de domínio que busca dado real via{" "}
          <code className="font-mono text-text-tertiary">useCategorias</code>, então é exercitado com dado
          real em <code className="font-mono text-text-tertiary">/categorias</code>, mesmo raciocínio que já
          mantém <code className="font-mono text-text-tertiary">ContaFormDialog</code> fora desta página
          (seção "Nota" de <code className="font-mono">/dev</code>).
        </p>

        <FormDialog
          open={dialogAberto}
          title="Nova categoria"
          description="Exemplo de FormDialog completo — nada aqui é enviado de verdade."
          isDirty={dialogForm.formState.isDirty}
          onClose={() => {
            setDialogAberto(false);
            dialogForm.reset({ nome: "", cor: "", icone: "" });
          }}
          footer={(requestClose) => (
            <FormActions>
              <CancelButton onClick={requestClose}>Cancelar</CancelButton>
              <SubmitButton form="dialog-categoria-form" loading={dialogForm.formState.isSubmitting}>
                Criar categoria
              </SubmitButton>
            </FormActions>
          )}
        >
          <Form id="dialog-categoria-form" form={dialogForm} onSubmit={onSubmitDialog} className="space-y-4">
            <TextField name="nome" label="Nome da categoria" placeholder="Ex.: Assinaturas" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <ColorPicker name="cor" label="Cor" optional />
              <IconPicker name="icone" label="Ícone" optional />
            </div>
          </Form>
        </FormDialog>
      </section>

      <section>
        <SectionTitle>Campos desabilitados</SectionTitle>
        <Card>
          <Form form={disabledDemoForm} onSubmit={() => {}}>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField name="texto" label="Campo desabilitado" disabled />
              <CurrencyField name="valor" label="Valor desabilitado" disabled />
            </div>
          </Form>
        </Card>
      </section>

      <section>
        <SectionTitle>TagsInput (isolado)</SectionTitle>
        <Card>
          <Form form={tagsDemoForm} onSubmit={() => {}}>
            <TagsInput name="tags" label="Tags livres" placeholder="Digite e pressione Enter" />
          </Form>
        </Card>
      </section>
    </div>
  );
}
