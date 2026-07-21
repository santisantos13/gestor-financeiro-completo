# Revisão técnica — Sistema de Formulários (Etapa F5)

Revisão final da etapa, mesmo padrão de toda revisão técnica anterior do projeto
(backend, F1/F2/F3/F4 do frontend). Escopo: infraestrutura reutilizável de formulários
para todo o restante do projeto — nenhuma entidade real, nenhuma regra de negócio,
nenhum CRUD implementado ainda. Ver `docs/analise-arquitetural-frontend.md`, seção 12
(contrato original: React Hook Form + Zod + primitivos do Design System).

## 1. O que foi entregue

**Base RHF + Zod.** `react-hook-form`, `zod` e `@hookform/resolvers` já estavam
instalados desde a Etapa F1 (aprovados em `docs/analise-arquitetural-frontend.md`,
seção 2) — nenhuma dependência nova nesta etapa. Todo formulário usa
`useForm({ resolver: zodResolver(schema), mode: "onBlur" })`; o schema Zod valida só
formato/obrigatoriedade (`z.string().min(1)`, `z.string().email()`, etc.) — nunca uma
regra que dependa de estado do servidor, que continua exclusivamente como
`BusinessRuleError` no backend.

**Dez peças estruturais** em `components/ui/`: `Form` (provê `FormProvider`, `noValidate`,
e o comportamento de foco+scroll automático até o primeiro erro num submit inválido),
`FormDialog` (modal de criar/editar, ver seção 3), `FormSection` (`fieldset`/`legend`
para agrupar campos relacionados), `FormField` (chrome de label+slot+descrição/erro que
todo `*Field` compõe por dentro), `FormLabel`, `FormDescription`, `FormError`
(`ValidationMessage` — fade+slide-down sem shake), `FormActions`, `SubmitButton`
(`type="submit"`, aceita `loading`), `CancelButton` (`type="button"`, nunca dispara
submit por engano).

**Dezessete campos genéricos**: `TextField`, `EmailField` (ícone `Mail`),
`PasswordField` (alternância mostrar/ocultar), `TextAreaField`, `NumberField`,
`CurrencyField`, `PercentageField`, `DateField` (calendário custom via `DateInput`
compartilhado — nunca `<input type=date>` nativo), `DateTimeField` (compõe `DateInput`
+ um campo de hora mascarado inline), `SelectField` (wrapper `Controller` do `Select`
já existente da F2), `MultiSelectField`, `SearchSelect` (base dos futuros
`CategorySelect`/`AccountSelect`/`CardSelect`/`TagSelect` de domínio, F6+),
`TagsInput`, `CheckboxField`, `SwitchField`, `RadioGroupField` (novo primitivo
`Radio.tsx`, par de `Checkbox`), `FileUpload` (arrastar-e-soltar + seleção por clique,
**infraestrutura apenas** — não conhece `Anexo`, não envia nada).

**Máscaras** (`utils/mask.ts`, puramente funções de dígito, sem biblioteca pesada):
moeda e percentual usam a mesma técnica ("dígito de calculadora" — os últimos N dígitos
são sempre a parte decimal, digitar da esquerda pra direita empurra o valor, como um
caixa eletrônico); número genérico reaproveita a mesma função com casas decimais
configuráveis; data usa uma máscara progressiva `DD/MM/AAAA` + conversão para
`AAAA-MM-DD` só quando os 8 dígitos formam uma data de calendário real (`dateDigitsToIso`
valida, ex., que 31/02 não existe). Todas as funções são puras e teoricamente testáveis
isoladamente (nenhuma depende de estado de componente).

**Rota `/dev/forms`** (`pages/dev/DevFormsPage.tsx`): protegida, fora do `Sidebar` (mesmo
padrão de `/dev` e `/dev/tables`). Um formulário completo cobrindo quase todo tipo de
campo desta etapa com validação Zod real; um `FormDialog` de exemplo demonstrando
fechamento com confirmação; um botão que simula um erro 422 "do servidor" no campo
"Nome" via `form.setError` (mesma mecânica de mapear um erro real de API); campos
desabilitados; um `TagsInput` isolado. Nenhuma chamada à API em nenhum lugar da página.

## 2. Decisões tomadas sem pausar — e por quê

- **`FormField` não injeta props via `cloneElement`.** A ideia inicial mais óbvia seria
  `FormField` receber um `children` arbitrário e injetar `id`/`aria-invalid` nele
  automaticamente. Rejeitada: com inputs compostos (`Select`, `DateInput`) nem sempre o
  `children` repassa props extras para o nó DOM certo, e a injeção via `cloneElement`
  fica frágil silenciosamente (funciona até não funcionar, sem erro de tipo). Decisão:
  cada `*Field` monta seu próprio input com `id`/`name`/`aria-invalid` corretos e usa
  `FormField` só para o chrome ao redor — mais verboso por campo, muito mais robusto no
  conjunto.
- **`FormDialog.footer` é uma função, não um nó pronto.** Se fosse um `ReactNode` fixo,
  o botão "Cancelar" dentro dele só teria acesso ao `onClose` bruto passado pelo
  consumidor — pulando a checagem de "há alteração não salva?" que `Esc`/backdrop já
  respeitam. `footer: (requestClose) => ReactNode` garante que **todo** caminho de
  fechar passa pelo mesmo `requestClose` interno.
- **`CurrencyInput`/`PercentageInput`/`NumberInput` puros não viraram componentes
  separados** (diferente do par `CurrencyInput`/`MoneyInput` sugerido em
  `docs/analise-arquitetural-frontend.md`, seção 12). Só `DateInput` ganhou essa
  separação (usado por `DateField` **e** `DateTimeField` — reuso real). Para
  moeda/percentual/número não havia um segundo consumidor nesta etapa; a lógica de
  máscara reutilizável já vive em `utils/mask.ts` (puramente funcional), que é a
  camada que de fato precisava ser compartilhada. Se um filtro de valor mínimo em
  tabela (mencionado na seção 12 do doc de arquitetura) precisar da mesma máscara no
  futuro, extrair um `CurrencyInput` nesse momento é imediato — os `Field`s já isolam
  toda a lógica de máscara em `utils/mask.ts`, não duplicada inline.
- **`Select.tsx` (Etapa F2) ganhou `id`/`name` opcionais no seu tipo de props.** Sem
  isso, `SelectField` não conseguia associar `<label htmlFor>` ao botão de gatilho nem
  dar ao `Form` um `[name="..."]` para achar o campo no scroll-to-error. Mudança aditiva
  e retrocompatível (props opcionais, comportamento de quem já usava `Select` sem elas
  não muda).
- **Ícone de sucesso do `Toast` (F1) passou a desenhar o check via `pathLength`.**
  `motion-principles.md`, seção 5.7, já especificava esse comportamento exato para
  "sucesso" — o `Toast` da F1 usava o ícone estático `CheckCircle2` do `lucide-react`.
  Como esta etapa pede explicitamente motion de "sucesso" e todo formulário bem-sucedido
  desta etapa usa `Toast`, alinhar o ícone ao documento canônico agora evita um
  descompasso silencioso entre "o que o doc pede" e "o que já existia". Mudança pequena
  e aditiva (só o ícone de sucesso; erro/info continuam com os ícones estáticos do
  `lucide-react`).
- **`NumberField` guarda `number`, `CurrencyField`/`PercentageField` guardam `string`.**
  Decisão consciente para espelhar o backend: campos `Decimal` do backend chegam/saem
  como string (nunca `number`, arquitetura-frontend.md, seção 0), então moeda/percentual
  seguem essa convenção; `NumberField` (contagens genéricas, ex. "número de parcelas")
  não representa um `Decimal` do backend, então usa `number` puro — mais natural para
  Zod (`z.number().int()`) e para quem for somar/comparar o valor depois.

## 3. Como a etapa cumpre "CRUD novo com o mínimo de código"

Objetivo explícito do pedido. Um formulário de criar/editar uma entidade futura (F6+)
precisa, na prática, de: um `schemas/<entidade>.ts` (Zod, só formato), um `useForm` com
esse schema, um `FormDialog` envolvendo um `Form`, e um `*Field` por campo do backend —
nenhum desses `*Field` precisa ser reescrito por entidade. Ex.: um formulário de Conta
(nome, saldo inicial, tipo) seria `TextField` (nome) + `CurrencyField` (saldo inicial) +
`SelectField` (tipo) dentro de um `FormDialog`, sem nenhum HTML de label/erro/máscara
escrito à mão. `FormActions`/`SubmitButton`/`CancelButton` já cobrem o rodapé padrão.

## 4. Validação realizada

- **`tsc -b`** (build incremental do projeto inteiro) — limpo, verificado após cada
  lote de componentes novos e novamente no fechamento da etapa.
- **`vite build`** — limpo (`2454 módulos transformados`; bundle de produção ~582KB
  minificado — o aviso de chunk grande já existia desde a F3/F4 e cresce com mais
  infraestrutura no mesmo bundle sem code-splitting, não é um erro novo desta etapa).
- **Consistência do mount**: como em etapas anteriores, algumas edições feitas via
  ferramenta de edição (`AppRoutes.tsx`, `Select.tsx`, `RadioGroupField.tsx`,
  `ToastContext.tsx`, `DevFormsPage.tsx`) foram reportadas como corretas/completas pela
  ferramenta e confirmadas corretas por leitura direta, mas o `bash`/`tsc` do lado do
  sandbox chegou a ver conteúdo desatualizado ou corrompido (bytes NUL) logo em
  seguida — mesma instabilidade de mount já documentada nas revisões de F3/F4. Corrigido
  reescrevendo cada arquivo afetado inteiro via heredoc no `bash`, com verificação de
  bytes/NUL, antes de cada `tsc -b` que finalmente ficou limpo.
- **Erro real de tipos do Zod v4 corrigido durante a implementação**: a opção
  `invalid_type_error` (API do Zod v3) não existe mais no `z.number()` do Zod v4
  instalado (`"zod": "^4.4.3"`) — substituída pela opção unificada `error`. Pego pelo
  próprio `tsc -b`, não por inspeção manual.
- **Validação visual no navegador**: pendente de confirmação do usuário — recomendado
  `npm run dev:full` na raiz do projeto e abrir `http://localhost:5173/dev/forms`,
  exercitar o formulário completo (validação onBlur, foco+scroll no erro, máscaras,
  submit com loading/sucesso/erro simulado), o `FormDialog` (abertura/fechamento,
  confirmação de descarte) e os campos desabilitados. Esta revisão cobre tudo que é
  verificável sem olhos humanos (tipos, build); o critério de pronto pedido pelo usuário
  também exige essa confirmação visual antes de encerrar a etapa por completo.

## 5. Riscos conhecidos / dívida técnica sinalizada, não corrigida agora

- **Bundle de produção sem code-splitting** (~582KB minificado) — mesmo aviso já
  sinalizado nas revisões de F3 e F4, cresce a cada etapa que adiciona infraestrutura
  ao mesmo bundle. Ainda não urgente para um app de usuário único; candidato a
  `React.lazy` quando o app crescer mais.
- **`DateInput` não suporta seleção de intervalo nem atalhos de navegação por teclado
  dentro do grid do calendário** (só clique) — suficiente para o uso pedido nesta
  etapa (uma data por vez), mas um formulário futuro que precise de intervalo de datas
  exigiria uma extensão deste componente, não um novo do zero. A digitação no campo de
  texto continua funcionando por teclado normalmente (`DD/MM/AAAA` direto), só o
  popover de calendário em si não tem navegação por seta ainda.
- **`FileUpload` não valida tamanho/tipo de arquivo** — é puramente infraestrutura de
  coleta local (`File[]`), como pedido explicitamente ("sem integração com Anexo
  ainda"); validação de tamanho/extensão é decisão que só faz sentido quando o contrato
  real de upload (ainda não definido pelo backend) existir.
- **`SearchSelect`/`MultiSelectField` são só client-side**, mesma decisão já registrada
  para o sistema de tabelas (`docs/analise-arquitetural-frontend.md`, seção 13) —
  suficiente para as listas pequenas de um usuário único; um select de domínio futuro
  com volume maior precisaria decidir busca assíncrona antes de reaproveitar
  `SearchSelect` como está.

## 6. Conclusão

Etapa F5 implementada seguindo `docs/analise-arquitetural-frontend.md` (seção 12),
`docs/design-system.md` (seções 15/17/22) e `docs/motion-principles.md` (seções 5.6,
5.7, 10), sem nenhuma entidade real, regra de negócio ou alteração de contrato de API —
puramente infraestrutura de apresentação, pronta para ser consumida por qualquer CRUD
futuro compondo `*Field`s + `FormDialog` + um schema Zod por entidade, sem reescrever
label/erro/máscara/modal do zero em cada tela. Build e typecheck limpos. Falta apenas a
confirmação visual do usuário no navegador, em `/dev/forms`, para considerar a etapa
inteiramente encerrada.
