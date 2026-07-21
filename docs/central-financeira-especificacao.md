# Central Financeira — Especificação Funcional e Arquitetural

Documento de projeto (Product + UX + Arquitetura). Nenhum código foi implementado —
este é o documento a ser validado antes da primeira linha de código.

**Pré-requisito explícito:** a Central Financeira é uma camada de agregação construída
**sobre** os Services de domínio (`ContaService`, `CartaoService`, `FaturaService`,
`FinanciamentoService`, `EmprestimoService`, `ParcelamentoService`, `MetaService`,
`ContaRecorrenteService`), que ainda não existem neste projeto (nenhum CRUD foi
implementado até agora). Ela não é um substituto para eles nem pode ser construída antes
deles — é consumidora, nunca dona, da regra de negócio de cada domínio. Isso é o
princípio mais importante deste documento e volta em quase toda seção abaixo.

---

## 1. Objetivo da Central Financeira

Responder, em menos de 5 segundos de leitura, três perguntas: **"como estou
financeiramente agora?"**, **"o que precisa da minha atenção?"** e **"o que vem por
aí?"** — sem o usuário precisar visitar Contas, Cartões, Financiamentos, Metas e Agenda
separadamente para montar esse quadro na cabeça.

Ela tem dois papéis simultâneos: **painel de leitura** (visão consolidada, escaneável) e
**hub de navegação** (cada card é também uma porta de entrada para o módulo detalhado
correspondente — tocar no card de Financiamentos leva para a lista completa de
financiamentos, não é só decorativo).

Não é objetivo desta tela: permitir edição de dados, listar histórico completo de
qualquer entidade, ou substituir os relatórios detalhados de cada módulo. Ela é um
resumo com atalhos, não um formulário.

## 2. Experiência esperada do usuário

A tela é a primeira coisa que o usuário vê ao abrir o app. A leitura deve funcionar em
camadas de urgência decrescente, de cima para baixo:

1. **O que exige atenção agora** (Alertas) — se existir algo urgente, aparece no topo,
   antes de qualquer número "neutro". Um usuário com uma parcela vencida não deveria
   precisar rolar a tela para descobrir isso.
2. **Onde eu estou** (Resumo Financeiro) — a fotografia do momento: quanto tenho, quanto
   isso vai virar até o fim do mês, se estou ganhando ou perdendo patrimônio.
3. **Detalhamento por domínio** (Cartões, Financiamentos, Empréstimos, Parcelamentos,
   Metas) — cada um como um cartão compacto, não uma lista. Card que não se aplica ao
   usuário (ex: sem financiamento cadastrado) **não aparece** — zero ruído de "R$ 0,00"
   espalhado pela tela. Isso é uma decisão de UX deliberada: nenhum concorrente pesquisado
   resolve isso de forma perfeita, e é um diferencial barato de implementar bem aqui,
   porque a API já vai retornar `null`/omitir a seção quando vazia (ver seção 10).
4. **O que vem a seguir** (Agenda Financeira) — a linha do tempo, para planejamento de
   curto prazo.
5. **Entendimento mais profundo** (Insights) — a camada mais "analítica" e menos urgente,
   naturalmente no fim da rolagem: são interessantes, não acionáveis no mesmo segundo.

Estado vazio (usuário novo, sem nenhuma conta/transação cadastrada): a tela não pode
quebrar nem mostrar uma parede de zeros. Mostra uma versão de onboarding com
chamada-para-ação ("cadastre sua primeira conta"), não o mesmo layout com números zerados.

## 3. Componentes da tela

- **Cabeçalho**: saudação + seletor de período (padrão: mês corrente; permite navegar
  mês anterior/seguinte, já que "Entradas do mês"/"Saídas do mês" dependem de um período).
- **Faixa de Alertas** (condicional — só existe se houver alerta ativo).
- **Bloco de Resumo Financeiro** (sempre visível, é o "cabeçalho financeiro" da tela).
- **Grade de cards por domínio**: Cartões, Financiamentos, Empréstimos, Parcelamentos,
  Metas — cada um um card independente, renderizado condicionalmente.
- **Agenda Financeira**: lista/timeline dos próximos eventos (padrão: 30 dias).
- **Painel de Insights**: carrossel ou lista de 3–5 cartões de insight, renovado
  periodicamente (não a cada carregamento de tela — ver seção 11).

Cada bloco é tecnicamente independente (seção 8) — a tela pode renderizar o Resumo antes
dos Insights terminarem de calcular, sem travar a experiência num único carregamento
monolítico.

## 4. Cards existentes

Para cada card: as métricas pedidas, de onde vêm, e qual Service (existente ou novo,
todos daqui pra frente descritos como "a construir" já que nenhum existe ainda) é dono do
cálculo. A Central nunca implementa a regra ela mesma — só chama e formata.

### 📊 Resumo Financeiro

| Métrica | Origem / cálculo | Service dono |
|---|---|---|
| Saldo total | Soma do saldo de todas as `Conta` ativas do usuário (`saldo_inicial` + `Transacao` + `Transferencia`, calculado, nunca armazenado — já é o padrão do projeto) | `ContaService` |
| Saldo previsto | Saldo total + `Transacao` `PENDENTE` com vencimento até o fim do período + ocorrências futuras de `ContaRecorrente` ainda não materializadas em `Transacao` | `ContaService` + `ContaRecorrenteService` (via orquestração) |
| Entradas do mês | Soma de `Transacao` `tipo=RECEITA`, `status=PAGO`, dentro do período | `TransacaoService` |
| Saídas do mês | Soma de `Transacao` `tipo=DESPESA`, `status=PAGO`, dentro do período | `TransacaoService` |
| Fluxo de caixa | Entradas do mês − Saídas do mês | Calculado na agregação (não é uma consulta nova, é aritmética sobre os dois valores acima) |
| Patrimônio líquido | (Soma de saldo de todas as `Conta`) − (soma de `saldo_devedor` de `Financiamento` + `Emprestimo` + valor em aberto de `Fatura` + saldo restante de `Parcelamento`) | Orquestração entre `ContaService`, `FinanciamentoService`, `EmprestimoService`, `FaturaService`, `ParcelamentoService` |

### 💳 Cartões

| Métrica | Origem / cálculo | Service dono |
|---|---|---|
| Limite disponível | `Cartao.limite` − total da fatura em aberto | `CartaoService` |
| Total utilizado | Soma das faturas em aberto de todos os cartões | `FaturaService` |
| Próximo fechamento | Calculado a partir de `Cartao.dia_fechamento` (data, não armazenado) | `CartaoService` |
| Próximo vencimento | `Fatura.data_vencimento` da fatura fechada mais próxima, não paga | `FaturaService` |
| Valor das faturas | `Fatura.valor_total` (fechada) ou soma corrente das `Transacao` do ciclo (aberta) | `FaturaService` |

### 🏦 Financiamentos

| Métrica | Origem / cálculo | Service dono |
|---|---|---|
| Saldo devedor | `Financiamento.saldo_devedor` (campo armazenado — ver justificativa no README do domínio) | `FinanciamentoService` |
| Próxima parcela | Próxima `Transacao` `PENDENTE` com `financiamento_id` = X, ordenada por data | `FinanciamentoService` |
| Parcelas restantes | `num_parcelas` − contagem de `Transacao` `PAGO` com aquele `financiamento_id` | `FinanciamentoService` |
| Valor total já pago | Soma de `Transacao.valor` `PAGO` com aquele `financiamento_id` | `FinanciamentoService` |
| Evolução do financiamento | Série do saldo devedor ao longo das parcelas já pagas | `FinanciamentoService` — v1 aproxima linearmente a partir das parcelas pagas; evolução futura: snapshot por parcela com juros/amortização reais (ver seção 12) |

### 💰 Empréstimos

| Métrica | Origem / cálculo | Service dono |
|---|---|---|
| Saldo devedor | `Emprestimo.saldo_devedor` | `EmprestimoService` |
| Próximo vencimento | Próxima `Transacao` `PENDENTE` com `emprestimo_id` = X | `EmprestimoService` |
| Valor restante | Igual ao saldo devedor (mesmo campo — evita duas fontes de verdade para o mesmo número) | `EmprestimoService` |

### 📦 Parcelamentos

| Métrica | Origem / cálculo | Service dono |
|---|---|---|
| Compras parceladas | Lista de `Parcelamento` ativos do usuário | `ParcelamentoService` |
| Parcelas restantes | `num_parcelas` − parcelas `PAGO` | `ParcelamentoService` |
| Próximas parcelas | Próximas `Transacao` `PENDENTE` por `parcelamento_id` | `ParcelamentoService` |

### 🎯 Metas

| Métrica | Origem / cálculo | Service dono |
|---|---|---|
| Progresso | Soma de `Transacao.valor` com `meta_id` = X (já é o padrão documentado: sem coluna redundante) | `MetaService` |
| Valor restante | `valor_alvo` − progresso | `MetaService` |
| Prazo | `Meta.data_alvo` | `MetaService` |
| Percentual concluído | progresso / `valor_alvo` × 100 | `MetaService` |

Regra geral de exibição: qualquer card cuja lista de origem esteja vazia (nenhum cartão,
nenhum financiamento...) não é renderizado. Isso é decidido no backend (o endpoint da
seção simplesmente não inclui o bloco), não no frontend — evita a tela "piscar" um card
vazio antes de escondê-lo.

## 5. Agenda Financeira

A Agenda não é uma tabela nova no banco — é uma **projeção** montada por um novo
`AgendaFinanceiraService`, combinando três fontes que já existem:

1. **`Transacao` com `status=PENDENTE` e data futura** — cobre parcelas de
   `Parcelamento`/`Financiamento`/`Emprestimo` já lançadas (a decisão de modelagem deste
   projeto é pré-gerar todas as parcelas de um contrato como `Transacao PENDENTE` no
   momento da criação, então elas já existem no banco, só precisam ser consultadas por
   data) e qualquer transação avulsa futura.
2. **`Fatura`** com vencimento futuro e ainda não paga.
3. **Ocorrências futuras de `ContaRecorrente`** que ainda não viraram `Transacao` —
   diferente das parcelas de contrato, não faz sentido pré-gerar anos de "Netflix
   mensal" como linhas no banco. Essas são **calculadas sob demanda**
   (`ContaRecorrente.dia_vencimento` + `frequencia` a partir da última ocorrência
   conhecida), não persistidas até o momento em que reelmente vencem (aí sim uma rotina
   as materializa em `Transacao`, fora do escopo deste documento).

O `AgendaFinanceiraService` funde essas três fontes num único DTO ordenado por data
(`EventoAgendaDTO`: data, descrição, valor, tipo de origem, referência para navegação).
Ele não duplica nenhuma regra — só pergunta a cada Service de origem "quais são seus
próximos eventos" e ordena o resultado.

## 6. Sistema de Alertas

O domínio já tem a entidade `Alerta` (tipo, referência polimórfica `entidade_tipo` +
`entidade_id`, `condicao`, `ativo`, `ultima_disparada_em`) — ela foi desenhada
justamente para isto. O que falta é o motor que a alimenta.

Um novo `AlertaEngineService` roda um conjunto de **regras** — cada regra é uma unidade
pequena e testável isoladamente (padrão Strategy: uma interface `RegraDeAlerta` com um
método `avaliar(usuario_id) -> list[Alerta]`), por exemplo:

- Conta recorrente vence amanhã → usa `ContaRecorrenteService`
- Saldo previsto ficará negativo → usa o mesmo cálculo do Resumo Financeiro (reaproveitado,
  não recalculado)
- Fatura fecha em 2 dias → usa `FaturaService`
- Meta está atrasada (ritmo de aporte insuficiente para o prazo) → usa `MetaService`
- Financiamento/Empréstimo com parcela vencida (`Transacao PENDENTE` com data no passado)
  → usa `FinanciamentoService`/`EmprestimoService`

O enum `TipoAlerta` já existente precisa crescer (`SALDO_PREVISTO_NEGATIVO`,
`META_ATRASADA`, `PARCELA_VENCIDA` — os demais tipos já existem) quando isso for
implementado; é uma alteração aditiva, não estrutural.

O motor roda sob demanda quando a Central é aberta, mas o resultado é **persistido** na
tabela `Alerta` já existente (não recalculado do zero a cada leitura, nem descartado) —
isso dá de graça um histórico de alertas e a possibilidade de o usuário marcar um alerta
como lido/silenciado, além de já deixar o terreno pronto para notificação push (o alerta
já existe como registro antes de virar notificação).

## 7. Sistema de Insights

Pedido explícito do projeto: regra de negócio agora, IA depois, sem reescrever a
arquitetura quando isso acontecer. Isso é exatamente o mesmo problema que o
`IRepository` já resolveu para persistência (Dependency Inversion) — aplico o mesmo
padrão aqui.

Uma interface `InsightProvider` (`Protocol`, mesmo espírito de `IRepository`) define um
único método: `gerar(usuario_id, periodo) -> list[Insight]`. A V1 implementa
`RegraDeNegocioInsightProvider`: comparações de agregados SQL simples (gasto por
categoria mês atual vs anterior, variação de patrimônio líquido, ritmo de meta,
percentual pago de financiamento) — nenhuma delas é uma consulta cara, são `SUM`/`GROUP
BY` sobre `Transacao` já indexada por `data`/`usuario_id`.

O `InsightService` (o que o Router chama) depende só da interface, não da implementação
regra-de-negócio. Trocar para IA no futuro significa criar `IAInsightProvider`
(consultando um LLM com o histórico financeiro do usuário) e trocar qual implementação é
injetada em `InsightService` — zero mudança no Router, no Schema, ou nos outros
Providers. Os dois podem inclusive coexistir (ex: IA complementa, não substitui, as
regras determinísticas).

## 8. Fluxo de dados

```
Frontend (React)
   │  GET /api/central-financeira/<secao>   (uma chamada por seção, em paralelo)
   ▼
Router (app/api/routes/central_financeira.py)
   │  valida schema, identifica usuário autenticado, delega
   ▼
Service da seção (ex: CentralFinanceiraResumoService)
   │  orquestra — NÃO acessa Repository diretamente
   ▼
Services de domínio já existentes (ContaService, CartaoService, FaturaService,
FinanciamentoService, EmprestimoService, ParcelamentoService, MetaService,
ContaRecorrenteService)
   │  cada um usa seu próprio Repository
   ▼
Banco (via Repository)
```

Ponto de arquitetura central: os Services da Central Financeira **não têm Repository
próprio**. Eles são puramente orquestradores (padrão Facade/Aggregator) — toda regra de
negócio e todo acesso a dado continuam nos Services de domínio já estabelecidos. Isso é o
que garante a resposta à pergunta "como manter a Central desacoplada dos demais módulos":
ela literalmente não sabe o que é uma `Transacao` no nível de SQL, só conhece a interface
pública dos Services que já existem.

## 9. Services responsáveis por cada informação

Consolidado das tabelas da seção 4, mais os três Services novos que a Central introduz:

- **Services de domínio (pré-requisito, ainda não implementados no projeto):**
  `ContaService`, `CartaoService`, `FaturaService`, `TransacaoService`,
  `FinanciamentoService`, `EmprestimoService`, `ParcelamentoService`, `MetaService`,
  `ContaRecorrenteService`.
- **Services novos, exclusivos da Central Financeira:**
  - `CentralFinanceiraService` (ou um por seção — `ResumoFinanceiroService`,
    `PainelCartoesService`, etc.) — orquestra e formata, zero regra de negócio própria.
  - `AgendaFinanceiraService` — funde `Transacao` pendente + `Fatura` + projeção de
    `ContaRecorrente` num DTO ordenado.
  - `AlertaEngineService` — roda as regras de alerta e persiste em `Alerta`.
  - `InsightService` + `InsightProvider` (interface) — gera insights, hoje por regra,
    amanhã por IA, sem trocar o consumidor.

## 10. Endpoints necessários futuramente

Todos autenticados, escopados pelo usuário atual (retomando o P0 já levantado na revisão
técnica anterior: nenhum desses endpoints deve aceitar `usuario_id` do cliente — vem do
token). Um endpoint por seção, não um endpoint monolítico — motivo detalhado na seção 11.

```
GET /api/central-financeira/resumo?periodo=2026-07
GET /api/central-financeira/cartoes
GET /api/central-financeira/financiamentos
GET /api/central-financeira/emprestimos
GET /api/central-financeira/parcelamentos
GET /api/central-financeira/metas
GET /api/central-financeira/agenda?dias=30
GET /api/central-financeira/alertas
GET /api/central-financeira/insights
```

Cada um retorna `null`/lista vazia quando a seção não se aplica ao usuário (ver regra de
exibição da seção 4) — a decisão de esconder o card é tomada pelo backend, o frontend só
obedece.

## 11. Estratégia de performance

**O que precisa ser tempo real** (não pode estar um segundo desatualizado): saldo total,
saldo previsto, limite disponível de cartão, qualquer alerta classificado como crítico
(parcela vencida, saldo previsto negativo). São números que, se errados, levam a uma
decisão financeira ruim do usuário — não vale a pena economizar uma query aqui.

**O que pode ser cacheado**, com o motivo de cada um:

| Informação | TTL sugerido | Motivo |
|---|---|---|
| Insights | Até 24h ou até nova transação relevante | Comparações mensais não mudam a cada segundo |
| Evolução do financiamento (gráfico) | Até 24h | Só muda quando uma parcela é paga |
| Próximo fechamento/vencimento de cartão | Até virar o mês/ciclo | Data fixa dentro do ciclo corrente |
| Agenda Financeira | Poucos minutos | Muda pouco dentro de uma sessão de uso |

**Como evitar consultas pesadas**: toda métrica agregada (somas, contagens) deve ser uma
query SQL com `SUM`/`COUNT`/`GROUP BY`, nunca "carregar todas as `Transacao` em Python e
somar" — os índices já existentes em `Transacao.data` e `Transacao.usuario_id` sustentam
isso. Nenhum card deve gerar uma query por item (ex: uma query por cartão) — cada
Repository de domínio deve oferecer um método agregado por usuário (`somar_faturas_em_
aberto(usuario_id)`), não uma lista de objetos que a Central itera e recalcula.

**Cache físico**: o projeto não tem Redis hoje. Para v1, cache em memória por request
(evitar recalcular o saldo da mesma conta duas vezes dentro da mesma chamada, caso dois
cards dependam dela) já resolve o caso mais comum. Cache entre requests (Redis, com
invalidação orientada a evento — toda escrita em `Transacao`/`Fatura`/etc. invalida a
chave de cache do usuário correspondente) é evolução futura explícita, não pré-requisito
desta etapa.

**Paralelização**: como cada seção é um endpoint independente (seção 10), o frontend já
paraleliza naturalmente fazendo as N chamadas ao mesmo tempo — a seção mais lenta
(provavelmente Insights) não atrasa o Resumo Financeiro.

**Extensibilidade sem reescrever a arquitetura**: cada card é uma implementação de uma
interface `CardProvider` (`Protocol`: `nome`, `aplicavel(usuario_id) -> bool`,
`montar(usuario_id) -> CardDTO`), registrada numa lista central que o endpoint agregador
percorre. Adicionar um card novo é criar uma classe nova e registrá-la — os cards
existentes não são tocados (Open/Closed Principle, o mesmo espírito já usado no
`SQLAlchemyRepository` genérico).

## 12. Possíveis evoluções futuras

- `InsightProvider` por IA consumindo o histórico financeiro completo do usuário.
- Alertas persistidos viram notificação push/e-mail.
- Cenários de saldo previsto (otimista/conservador), inspirado no Monarch.
- Simulador "e se eu quitar essa parcela antecipadamente" sobre `Financiamento`/`Emprestimo`.
- Central customizável: usuário reordena ou oculta cards manualmente.
- Cache distribuído (Redis) com invalidação por evento de escrita.
- Evolução do financiamento com decomposição real de juros/amortização por parcela
  (hoje é uma aproximação linear a partir das parcelas pagas).
- Metas e contas compartilhadas entre mais de um usuário (família).

---

## 13. Análise crítica comparativa com o mercado

Pesquisa rápida sobre posicionamento atual de YNAB, Monarch Money, Copilot Money, Mobills
e Organizze, para calibrar esta proposta contra o que já existe — sem copiar
funcionalidade por funcionalidade.

**YNAB** aposta tudo em disciplina: orçamento base zero, lançamento manual como prática
consciente. Funciona muito bem para quem quer construir hábito, mas exige esforço
constante do usuário — o oposto do "entender em segundos" que é o objetivo declarado
deste projeto. **Não vale copiar** a fricção do lançamento manual como filosofia central,
mas vale copiar a clareza de "pra onde vai cada real": nossa Central já cobre isso com
"saldo previsto" e "fluxo de caixa", que é essencialmente a mesma pergunta que o YNAB
responde de um jeito mais trabalhoso.

**Monarch Money** foca em visão patrimonial completa (net worth, investimentos) e
múltiplos cenários de orçamento (otimista/conservador) — muito forte para quem tem
situação financeira complexa. Nossa Central já inclui patrimônio líquido no Resumo, o que
é um acerto alinhado com essa abordagem. **Vale incorporar como evolução futura** (já
listado na seção 12) a ideia de cenários — hoje nosso "saldo previsto" é um número único,
o Monarch mostra que oferecer uma faixa (otimista/conservador) é mais honesto sobre
incerteza.

**Copilot Money** se diferencia pela fricção mínima: categorização automática via ML e
uma interface de revisão rápida ("swipe to review", ao estilo Tinder) para confirmar
transações. É o mais "hands-off" dos três apps americanos pesquisados — mas é exclusivo
iOS, o que é uma limitação real de alcance. **Vale incorporar o espírito, não a
tecnologia**: nossa arquitetura de Insights por regra determinística já entrega valor
sem exigir input do usuário, mas uma futura "revisão rápida" de transações sem categoria
(hoje fora de escopo) seria uma extensão natural e barata dentro do padrão de Cards já
desenhado aqui.

**Mobills** e **Organizze** são as referências mais próximas do usuário real deste
projeto (mercado brasileiro): Mobills aposta em Open Finance (integração bancária
automática) e dashboards customizáveis; Organizze aposta na simplicidade extrema,
inclusive funcionando offline. A ausência de integração bancária automática (Open
Finance) é a lacuna mais evidente desta proposta frente ao mercado brasileiro — mas é
consciente e correta para o estágio atual do projeto (entrada manual/API própria,
Open Finance é uma integração externa cara e fora de escopo hoje). **Vale registrar
explicitamente como gap conhecido, não ignorar.**

**Crítica ao próprio design antes de fechar:** a Central, como especificada, tem
potencialmente 8 blocos de conteúdo (Resumo + 5 cards de domínio + Agenda + Alertas +
Insights) — nenhum concorrente pesquisado tenta mostrar tanta coisa numa tela só sem
esconder o que não se aplica. A decisão já tomada na seção 4 (card só aparece se houver
dado) é o que evita que esta Central vire uma versão poluída dos concorrentes; sem essa
regra, o risco de sobrecarga visual seria real. Mantida essa disciplina, a proposta cobre
mais superfície que Organizze (mais simples) sem cair na fricção do YNAB (mais manual), o
que é o equilíbrio certo para o objetivo declarado no início deste documento.

## Resumo das decisões que dependem de validação antes da implementação

1. Endpoints granulares por seção (não um endpoint monolítico) — impacta como o frontend
   vai orquestrar o carregamento da tela.
2. Parcelas de `Parcelamento`/`Financiamento`/`Emprestimo` pré-geradas como `Transacao
   PENDENTE` no momento da criação do contrato (decisão que a Agenda Financeira já
   assume como premissa).
3. Alertas calculados por um motor de regras e persistidos na tabela `Alerta` existente,
   não recalculados e descartados a cada carregamento.
4. `InsightProvider` como interface desde o dia um, mesmo com uma única implementação
   hoje.
