# Análise arquitetural — CRUD frontend de Anexo

Registro da decisão de UI antes do código, mesmo processo de sempre. Backend já existia
completo e sem alterações necessárias (`docs/analise-arquitetural-anexo.md`): Router/Service/
Repository/testes já cobrem `POST /anexos`, `GET /anexos?transacao_id=`, `GET /anexos/{id}`,
`DELETE /anexos/{id}` (soft delete). Esta etapa é 100% frontend.

## Restrição estrutural que molda toda a tela: Anexo não tem listagem global

`AnexoRepository`/`AnexoService` só expõem `listar_por_transacao(transacao_id, ...)` — não
existe (e não deveria existir, por design: posse é transitiva via Transação, nunca direta do
usuário) um endpoint "todos os anexos do usuário". Por isso não há como esta etapa produzir uma
página própria tipo `/anexos` com uma tabela de todos os anexos, ao contrário de Categoria/Tag/
Cartão/Meta. A "tela própria" pedida é necessariamente **escopada a UMA transação por vez** —
um Drawer (Tier 2, mesmo padrão de `FinanciamentoDrawer`/`FaturaDrawer`), não uma rota de
listagem.

## Ponto de entrada: nova `RowAction` em `TransacoesPage`, não dentro do `TransacaoFormDialog`

Duas opções foram consideradas: (a) uma seção "Anexos" dentro do `TransacaoFormDialog` (o modal
de criar/editar), ou (b) uma ação de linha dedicada (ícone `Paperclip`) na tabela, ao lado de
Editar/Excluir, abrindo um Drawer à parte.

Decisão: **(b)**. Motivos:

- `TransacaoFormDialog` também serve para CRIAR uma transação nova, que ainda não tem `id` —
  anexar um arquivo exige um `transacao_id` que só existe depois de salvar. Misturar as duas
  responsabilidades no mesmo modal criaria um estado intermediário confuso ("salve a transação
  primeiro para poder anexar").
- Drawer (Tier 2) é o padrão já estabelecido no projeto para "gerenciar uma coleção-filha de
  uma entidade específica sem sair da lista" — `FinanciamentoDrawer` (cronograma de parcelas),
  `FaturaDrawer` (compras da fatura). Anexo é o mesmo formato: lista + adicionar + remover,
  filha de uma entidade específica.
- Mantém `TransacaoFormDialog` sem crescer em responsabilidade — ele continua sendo só o
  formulário de campos da transação em si.

## Sem upload real de arquivo: formulário é de metadados, por decisão já tomada no backend

O model/schema de `Anexo` foi desenhado explicitamente como **metadados apenas** —
`caminho_arquivo` é uma referência textual (caminho local, URL, chave de storage externo), e
armazenar o binário em si está fora de escopo (`docs/analise-arquitetural-anexo.md`, seção
"Escopo explicitamente fora"). Não existe endpoint de upload multipart, nem infraestrutura de
storage. Construir uma UI que finge fazer upload real (barra de progresso, "arquivo enviado")
seria inventar um contrato que o backend não tem.

A tela reflete isso honestamente: um formulário pequeno com `Nome do arquivo` e
`Caminho ou link` (texto livre, com texto de apoio explicando que é só uma referência de onde o
arquivo está guardado — Drive, Dropbox, pasta local etc.). Como conveniência, um botão
"Selecionar arquivo" abre o seletor nativo do SO (`<input type="file">`) só para **ler
metadados reais** do arquivo escolhido pelo navegador (`File.name`/`File.type`/`File.size`) e
pré-preencher `nome_original`/`mime_type`/`tamanho_bytes` — nenhum byte do arquivo é lido, lido
em memória ou enviado; o campo `Caminho ou link` continua editável manualmente, já que o
navegador não expõe o caminho real do arquivo por segurança (`C:\fakepath\...`).

## Sem edição, exclusão com confirmação inline (não `ConfirmAction` empilhado)

`AnexoCreate`/`AnexoRead` sem `AnexoUpdate` — decisão já confirmada no backend, sem PATCH. A
lista não tem ação de editar.

Exclusão (soft delete) usa confirmação **inline por linha** (o item vira "Remover este anexo?
[Cancelar] [Remover]" no lugar, mesma técnica já usada em `FinanciamentoDrawer` para excluir o
contrato inteiro) em vez de abrir um `ConfirmAction` (Tier 2) por cima do Drawer (Tier 2) já
aberto — essa combinação é o bug de backdrop duplicado já corrigido/documentado na Estabilização
de Overlays (`docs/analise-arquitetural-overlays.md`). Nunca dois overlays Tier 2 ao mesmo
tempo.

## Invalidação de cache

`queryKeys.anexos.list(transacaoId)` é a única chave nova. Criar/excluir um Anexo não muda
saldo, limite, categoria ou qualquer agregado do Dashboard/Central Financeira — é só metadado
de arquivo, então nenhuma outra chave (`transacoes`, `dashboard.*`) precisa ser invalidada.
