# Relatórios — export de CSV/PDF do resumo mensal (2026-07-26)

## 1. Escopo desta entrega

Último item pendente do roadmap. Pedido do usuário foi uma delegação total
("pode seguir oq achar melhor" → "ok siga"), então o escopo concreto ("export
+ tela", frase original do roadmap) foi decidido nesta sessão: exportar o
**mesmo resumo mensal** que a página `/graficos` já exibe em tela (entradas,
saídas, saldo do mês e os 3 agrupamentos de gastos — categoria/cartão/conta),
em dois formatos de arquivo (CSV para planilha, PDF para leitura/impressão).
Backend (`RelatorioService` + 2 rotas) e frontend (página `/relatorios` com
preview antes do download) na mesma sessão.

## 2. Princípio central: zero cálculo novo

Mesma filosofia da Central Financeira (nunca duplicar uma soma que já existe
em algum Service de domínio): `RelatorioService` **não agrega nada por conta
própria**. Ele só chama, nesta ordem:

1. `CentralFinanceiraService.visao_mensal(usuario_id, ano, mes)` — resolve
   `ano`/`mes` (se omitidos, mês corrente) e devolve `entradas`/`saidas`/
   `fluxo_caixa`.
2. `CentralFinanceiraService.graficos_periodo(usuario_id, ano=visao["ano"],
   mes=visao["mes"])` — usa o `ano`/`mes` **já resolvidos** pela chamada
   anterior (nunca os parâmetros originais, possivelmente `None`), devolvendo
   `gastos_por_categoria`/`gastos_por_cartao`/`gastos_por_conta` com nomes já
   resolvidos.

O resultado é o mesmo dict que a página `/graficos` consome via
`useVisaoMensalQuery`/`useGraficosPeriodoQuery` — `RelatorioService` só
formata esse dict em dois formatos de arquivo, nunca refaz nenhuma soma.
Testado explicitamente (`test_gerar_csv_propaga_ano_mes_explicitos_para_visao_mensal`):
`graficos_periodo` é chamado com o `ano`/`mes` resolvido por `visao_mensal`,
não recalculado.

## 3. Por que não exportar transações cruas

Cogitado e descartado: um export linha-a-linha das `Transacao` do período
exigiria resolver `categoria_id`/`cartao_id`/`conta_id` para nome em código
novo, já que `TransacaoRead` só expõe os ids — `RelatorioService` teria que
duplicar essa resolução de nome, que já existe (e já é testada) dentro de
`graficos_periodo`. Construir o export em cima do agregado já resolvido evita
esse código novo por completo, ao custo de o export ser um resumo (totais por
grupo), não um extrato linha-a-linha.

## 4. CSV — decisões de formato

- Delimitador `;` (não `,`): convenção do Excel em locale pt-BR, onde `,` é o
  separador decimal — um CSV com `,` como delimitador abre com todos os
  valores numéricos na coluna errada.
- Prefixo BOM UTF-8 (`"﻿"`) antes do conteúdo: sem isso, o Excel abre
  acentos como caracteres corrompidos.
- Estrutura: um cabeçalho com o mês/ano, um bloco "Resumo do mês"
  (entradas/saídas/saldo), seguido de um bloco por agrupamento (categoria,
  cartão, conta) — cada um pulado silenciosamente se vazio (sem gasto naquele
  agrupamento no período).

## 5. PDF — reportlab em vez de WeasyPrint

`reportlab` (`4.5.1`) foi escolhido sobre `WeasyPrint` (opção mais comum para
gerar PDF a partir de HTML/CSS) porque é **puro Python, sem dependência de
biblioteca nativa** (WeasyPrint exige Cairo/Pango instalados no sistema) —
mais seguro para o deploy no Render, onde não há controle sobre pacotes de
sistema além do que o build do Python já traz. O layout (título, tabelas com
`TableStyle`) é montado diretamente via `SimpleDocTemplate`/`Table`, sem
nenhuma camada de template HTML intermediária.

Formatação de moeda no PDF/CSV é manual (`_moeda`, `R$ 1.234,56`) — o backend
não tem acesso a `Intl`/babel; é uma cópia mínima e deliberada só para o
export, a UI de verdade (frontend) continua usando `formatMoney`.

## 6. Rotas

`GET /relatorios/csv` e `GET /relatorios/pdf`, ambas aceitando `ano`/`mes`
opcionais (mesmo contrato de `visao_mensal`/`graficos_periodo` — omitidos,
usam o mês corrente). Resposta é um `Response` com o `Content-Type` do
formato e `Content-Disposition: attachment; filename="relatorio-AAAA-MM.ext"`
— o nome do arquivo já contém o período resolvido, nunca o que foi
originalmente pedido (relevante quando `ano`/`mes` são omitidos).

## 7. Frontend

### 7.1. `httpClient.ts` — suporte a download binário

Único endpoint do projeto que devolve um corpo binário (CSV/PDF) em vez de
JSON. Refatorado o núcleo do `request<T>` original para um `fetchComRenovacao`
compartilhado (faz o fetch, injeta `Authorization`, tenta renovar sessão uma
vez em 401, normaliza erro em `ApiError` — devolve a `Response` crua, sem
decidir o parse do corpo) — `request<T>` (JSON, via `.json()`) e o novo
`requestArquivo` (blob, via `.blob()` + extração do nome de arquivo do
`Content-Disposition`) chamam esse núcleo comum, evitando duplicar a lógica de
renovação/erro entre os dois. Exposto como `httpClient.baixarArquivo(path,
params, nomePadrao)`.

### 7.2. Download como mutation, não query

`useBaixarRelatorioCsv`/`useBaixarRelatorioPdf` (`hooks/useRelatorioQueries.ts`)
são `useMutation`, apesar de o backend usar `GET` — o resultado nunca é
cacheado/renderizado, é um efeito colateral único (baixar um arquivo) a cada
clique, mesmo raciocínio de outras "ações" do projeto (`useExcluirFaturasEmLote`).
`utils/download.ts:baixarBlob` é o único lugar do frontend que cria um link
`<a download>` temporário — se o projeto ganhar um terceiro formato de export
no futuro, reaproveita o mesmo mecanismo.

### 7.3. Preview antes do download

`RelatoriosPage` mostra o mesmo resumo (entradas/saídas/saldo + contagem de
itens nos agrupamentos) usando os MESMOS hooks que `/graficos` já usa
(`useVisaoMensalQuery`/`useGraficosPeriodoQuery`, mesmo cache do React Query,
nenhum fetch novo além do que a página já dispararia) — o usuário confirma os
números antes de clicar em baixar, nenhum download é "às cegas".

## 8. Testes

Backend: 4 unitários (`tests/unit/test_relatorio_service.py`, fakeia
`CentralFinanceiraService` e confirma o `ano`/`mes` propagado corretamente
entre as duas chamadas, o CSV incluindo resumo + agrupamentos, o PDF sendo
bytes válidos — `startswith(b"%PDF")` — e não quebrando com período vazio) +
6 de integração (`tests/integration/test_relatorio_flow.py`: autenticação
obrigatória nas duas rotas, período vazio não quebra CSV/PDF, CSV reflete uma
transação real, isolamento entre usuários, `ano`/`mes` omitidos usam o mês
corrente).

Frontend: 4 testes (`RelatoriosPage.test.tsx`, mockando `centralFinanceiraService`
e `relatorioService`): preview do resumo, download de CSV, download de PDF, e
erro exibido (via toast) sem chamar `baixarBlob` quando o download falha.

Suíte completa revalidada sem regressão: backend (659 unit + toda a
integração, arquivo por arquivo); frontend (35 testes, `tsc -b`, `vite build`).

## 9. Fora de escopo

- Export de transações linha-a-linha (ver seção 3).
- Agendamento/envio automático de relatório (ex.: e-mail mensal) — só
  download sob demanda.
- Seleção de intervalo de datas arbitrário — sempre um mês por vez, mesmo
  recorte de `/graficos`.
