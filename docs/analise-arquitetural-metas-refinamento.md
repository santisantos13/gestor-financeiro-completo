# Refinamento de Metas — planejamento de contribuição, planejado x realizado, previsão de conclusão, celebração e histórico

Pedido do usuário (verbatim, resumido): enriquecer a experiência de Metas usando os dados já
existentes, sem alterar nenhuma regra de negócio já validada (unicidade de descrição, soft delete,
`valor_acumulado`/`percentual` sempre via soma de `Transacao.meta_id`, exclusão definitiva
desvinculando aportes) — e adicionando **só os campos realmente necessários**. Sete pedidos
concretos: (1) planejamento de contribuição por frequência, (2) acompanhamento planejado x
realizado, (3) previsão de conclusão, (4) celebração na primeira conclusão, (5) histórico da meta,
(6) integração com Dashboard/Central de Objetivos sem duplicar lógica, (7) documentar antes de
implementar qualquer mudança de backend.

Esta análise cobre exatamente isso: o que é campo novo (persistido), o que é cálculo novo
(transiente, no backend) e o que é só apresentação (frontend), com as fórmulas exatas.

## 0. Decisão estrutural: onde mora cada cálculo

O pedido diz duas coisas em tensão aparente: "todo cálculo de regra de negócio continua
pertencendo ao backend" e, ao mesmo tempo, esta etapa é inteiramente sobre números de
apoio/apresentação (nunca substituem `valor_acumulado`/`percentual` oficiais). A leitura adotada:
**os cálculos de planejamento (frequência, planejado x realizado, previsão) deixam de ser
recalculados a cada tela e passam a ser campos transientes calculados UMA VEZ no
`MetaService`, no mesmo padrão de `valor_acumulado`/`percentual`** — não porque virem regra de
negócio que valida/bloqueia algo, mas porque:

1. O pedido explicita "não quero duplicação de lógica" e "essas informações devem aparecer
   naturalmente também no Dashboard e na futura Central de Objetivos" — se o cálculo morasse no
   Frontend, cada novo lugar que precisasse dele reimplementaria a mesma fórmula (ou importaria a
   função certa manualmente, arriscando divergência). Calculado uma vez no Service, qualquer
   consumidor de `MetaRead` (página `/metas`, Dashboard, futura Central de Objetivos) ganha os
   números de graça.
2. Existe hoje uma função **equivalente, mas menos completa**, inteiramente no Frontend:
   `utils/meta.ts::calcularVelocidadeMeta` (`ritmoAtualPorMes`/`ritmoNecessarioPorMes`/`noRitmo`),
   explicitamente documentada como "métrica de apresentação" quando a Etapa F12 foi construída.
   Os pedidos 1-3 desta etapa (contribuição sugerida por período, planejado x realizado, situação
   do planejamento, previsão de conclusão) **cobrem e superam** o que essa função fazia. Mantê-la
   ao lado dos novos campos do backend seria exatamente a duplicação de lógica que o pedido pede
   para evitar — por isso ela é **removida** nesta etapa, e `MetaResumoCard` passa a consumir só
   os campos novos de `MetaRead`.

Isso **não muda nenhuma regra de negócio existente**: `calcularVelocidadeMeta` nunca foi regra de
negócio (não valida nada, não bloqueia nada, é só uma projeção informativa) — é uma
função de apresentação sendo consolidada no lugar certo, exatamente o tipo de melhoria que o
pedido do usuário autoriza ("enriquecer a experiência... usando os dados já existentes").

## 1. Planejamento de contribuição — novo campo persistido + cálculo derivado

### 1.1 Novo campo: `Meta.frequencia_contribuicao`

Único campo genuinamente novo que precisa ser **persistido** (é uma escolha do usuário, não algo
derivável de dados existentes). Novo enum `FrequenciaContribuicao` (`app/models/enums.py`):

```python
class FrequenciaContribuicao(str, enum.Enum):
    DIARIA = "DIARIA"
    SEMANAL = "SEMANAL"
    QUINZENAL = "QUINZENAL"
    MENSAL = "MENSAL"
```

Todas as quatro frequências pedidas fazem sentido para um app de metas de economia pessoal (um
objetivo pequeno/de curto prazo pode fazer mais sentido com contribuição diária ou semanal; um
objetivo maior, mensal) — nenhuma foi descartada. Coluna `nullable=True`, sem valor obrigatório:
uma Meta sem frequência escolhida simplesmente não exibe a contribuição sugerida por período (mas
continua exibindo planejado x realizado e previsão de conclusão, que dependem só de `data_alvo`,
não de frequência — ver seção 2). `MetaCreate`/`MetaUpdate` ganham
`frequencia_contribuicao: FrequenciaContribuicao | None = None`.

### 1.2 Cálculo: `contribuicao_sugerida_por_periodo` (transiente, `MetaRead`)

```
dias_por_periodo = {DIARIA: 1, SEMANAL: 7, QUINZENAL: 15, MENSAL: 30}[frequencia]
dias_restantes = (data_alvo - hoje).dias
periodos_restantes = max(1, ceil(dias_restantes / dias_por_periodo))
contribuicao_sugerida_por_periodo = valor_restante / periodos_restantes
```

`None` quando: `frequencia_contribuicao` não definida, `data_alvo` não definida, `dias_restantes <=
0` (prazo já vencido — não há "sugestão" válida, só o fato de estar atrasada, já coberto por
`situacaoDaMeta` no Frontend) ou a meta já está concluída (`percentual >= 100`).

`MENSAL = 30 dias` é uma aproximação deliberada (não usa meses de calendário exatos como
`app/core/datas.py::proximo_mes` faz para ciclos de Fatura) — decisão consciente porque este é um
número de **apoio**, explicitamente non-autoritativo ("esse cálculo é apenas uma informação de
apoio... nunca substitui o cálculo oficial"), então a precisão de dia exato de calendário não
compensa a complexidade adicional. Documentado aqui para não ser confundido com a exatidão de
`FaturaService._calcular_datas_ciclo`.

## 2. Planejado x realizado — cálculos derivados de `data_alvo` (frequência não é necessária aqui)

### 2.1 `valor_planejado_ate_hoje`

Projeção linear simples desde a criação da meta até o prazo, alcançando `valor_alvo` exatamente na
`data_alvo`:

```
dias_totais = (data_alvo - criado_em.date()).dias
dias_decorridos = clamp(0, dias_totais, (hoje - criado_em.date()).dias)
valor_planejado_ate_hoje = valor_alvo * dias_decorridos / dias_totais
```

`None` quando `data_alvo` é `None` ou `dias_totais <= 0` (meta criada com prazo já vencido — caso
degenerado, sem uma "linha de planejamento" válida a desenhar).

### 2.2 `diferenca_planejado_realizado`

```
diferenca_planejado_realizado = valor_acumulado - valor_planejado_ate_hoje
```

Positivo = acima do planejado ("Você está R$ 350 acima do planejado"); negativo = abaixo
("R$ 180 abaixo do planejado"). `None` quando `valor_planejado_ate_hoje` é `None`.

### 2.3 `situacao_planejamento` (novo enum, só transiente — nunca persistido)

```python
class SituacaoPlanejamentoMeta(str, enum.Enum):
    ADIANTADO = "ADIANTADO"
    DENTRO_DO_PLANEJADO = "DENTRO_DO_PLANEJADO"
    ATRASADO = "ATRASADO"
```

Banda de tolerância de **2% do valor_alvo** (decisão de produto, documentada aqui por não haver
uma "resposta certa" matemática — existe para não fazer o indicador oscilar entre estados por
flutuações naturais de poucos reais em torno do planejado exato):

```
tolerancia = valor_alvo * 0.02
if diferenca_planejado_realizado > tolerancia: ADIANTADO
elif diferenca_planejado_realizado < -tolerancia: ATRASADO
else: DENTRO_DO_PLANEJADO
```

`None` quando `diferenca_planejado_realizado` é `None` OU a meta já está concluída (`percentual >=
100` já tem seu próprio badge de situação geral — "Concluída" — que tem prioridade; comparar
"planejado x realizado" de uma corrida que já terminou não agrega [ver seção 4 sobre o badge de
conclusão]).

## 3. Previsão de conclusão

### 3.1 `data_prevista_conclusao`

```
dias_decorridos = max(1, (hoje - criado_em.date()).dias)
ritmo_diario = valor_acumulado / dias_decorridos
dias_necessarios = ceil(valor_restante / ritmo_diario)
data_prevista_conclusao = hoje + dias_necessarios
```

`None` quando: a meta já está concluída (não há "previsão" para algo que já aconteceu),
`valor_acumulado <= 0` (nenhum sinal real de progresso — "se não houver dados suficientes para uma
previsão confiável, simplesmente não exiba"), ou `dias_necessarios` resultaria numa data absurda
(> 100 anos no ritmo atual — sinal de ritmo tão baixo que a "previsão" não seria útil/confiável,
mesmo critério de "não exibir sem dados suficientes"). Não depende de `data_alvo`/`frequencia`: é
puramente "no ritmo atual, quando você chega lá", para o usuário comparar com o próprio prazo (que
já aparece ao lado, em `formatarPrazoMeta`).

## 4. Celebração ao concluir uma Meta — exceção explícita e documentada à filosofia "confiança silenciosa"

`docs/design-system.md`/`docs/analise-arquitetural-metas-frontend.md` (seção 3.2) registravam,
deliberadamente, que a conclusão de uma Meta NÃO teria confete/som/modal — só o crossfade do Badge
para "Concluída". O pedido desta etapa pede explicitamente confete/fogos discretos, pequena
animação, badge e mensagem de parabéns, com a ressalva "não quero algo exagerado... elegante,
memorável e coerente com o resto do sistema". Isso é tratado como uma **atualização consciente e
explícita** dessa decisão anterior, feita pelo próprio usuário — não uma violação silenciosa do
design system. Registrado aqui para constar: o restante do produto continua sem gamificação (sem
XP, sem streak, sem medalhas) — esta é a única exceção, e só no momento exato da primeira
conclusão.

Implementação restrita e elegante:
- Burst de confete pequeno (poucas dezenas de partículas, cores dos tokens semânticos do projeto —
  `--color-positive`/`--color-accent`/`--color-info` — nunca cores arbitrárias fora do sistema),
  ~1.5s de duração, `motion/react` (já é dependência do projeto, sem lib nova).
- Badge "Meta concluída" (reaproveita `SITUACAO_META_TONE.CONCLUIDA`/label já existentes).
- Uma frase curta de parabéns, no mesmo tom sóbrio do resto do produto (nunca superlativos
  vazios) — ex. "Meta concluída — parabéns pela disciplina."
- Som: **não implementado nesta etapa**. O pedido marca som como opcional e condicionado a
  preferências do usuário; o projeto não tem hoje nenhuma infraestrutura de áudio/preferências de
  som, e criar isso só para um efeito sonoro pontual seria desproporcional ao pedido ("elegante",
  não "exagerado"). Documentado como possível extensão futura, não implementado agora.

### 4.1 Novo campo persistido: `Meta.concluida_em`

Necessário para (a) a celebração acontecer **só uma vez** (sem repetir toda vez que o usuário
reabre a tela) e (b) o histórico (seção 5: "data de conclusão", "tempo necessário para concluir").
`date | None`, `nullable=True`.

**Trigger de escrita**: diferente de toda outra entidade do projeto, Meta não tem uma ação
explícita de "concluir" vinda do usuário — o progresso é sempre derivado ao vivo de
`Transacao.meta_id`, podendo inclusive oscilar acima e abaixo de 100% ao longo do tempo (um aporte
retirado depois de bater a meta, por exemplo). Não existe outro ponto de gancho limpo além do
próprio cálculo de progresso. Por isso, `MetaService._com_progresso` (o único lugar que já
calcula `percentual` a cada leitura) observa a transição e persiste **uma única vez**:

```python
if meta.percentual >= 100 and meta.concluida_em is None:
    meta.concluida_em = date.today()
    self.meta_repo.update(meta)
```

Nunca é desfeito (uma vez atingida, "concluída pela primeira vez" é um fato histórico — mesmo que
`percentual` caia depois de uma retirada, a comemoração já aconteceu e o "recorde" permanece).
`update()` só dá `flush()` (nunca `commit()`, ver `SQLAlchemyRepository`/`get_db`) — o `commit`
real acontece no fim do request como qualquer outra escrita, então esta escrita "durante uma
leitura" nunca fica pendurada fora de uma transação real nem quebra o padrão de commit por
request já estabelecido.

**Gatilho da animação no Frontend**: `concluida_em` (vindo do backend) diz **que** a meta foi
concluída; **se já mostramos a comemoração para o usuário** é estado de UI pura, guardado em
`localStorage` (`meta-celebrada-{id}`) — não é regra de negócio, é só "já vi essa comemoração
nesta janela/navegador", mesmo raciocínio de preferências puramente visuais já persistidas em
`localStorage` no projeto (`lib/cardThemes.ts`). `MetaResumoCard` dispara a celebração quando
`meta.concluida_em != null && !localStorage.getItem('meta-celebrada-' + meta.id)`, e marca a flag
imediatamente depois.

## 5. Histórico da Meta

Tudo já disponível ou coberto pelos campos acima — nenhum campo novo além dos já descritos:
- Data de criação: `criado_em` (já exposto).
- Data de conclusão: `concluida_em` (novo, seção 4.1).
- Tempo necessário para concluir: `concluida_em - criado_em` (calculado no Frontend, é subtração
  de datas, não uma regra de negócio — mesmo espírito de `diferencaEmDias` já usado em todo o
  projeto).
- Valor objetivo/acumulado: já existentes.
- Histórico de contribuições: já existe (`useAportesDaMeta`, lista de `Transacao` com
  `meta_id`), exibido ao expandir o card — nesta etapa só ganha visibilidade adicional dentro da
  mesma seção expandida (nenhuma consulta nova).
- "Evolução do progresso" (pedido): interpretado como o histórico de aportes já listado
  (cada aporte É um ponto de evolução) — um gráfico de série temporal dedicado fica fora de
  escopo desta etapa (adicionaria uma superfície visual nova não pedida explicitamente com esse
  nível de detalhe; o pedido também não especifica formato de gráfico). Documentado como possível
  extensão futura.

## 6. Integração com Dashboard/Central de Objetivos

Como os cálculos passam a morar no `MetaRead` (backend), `MetasCard` (Dashboard) ganha acesso aos
mesmos campos sem nenhuma query nova — só passa a ler `situacao_planejamento`/
`data_prevista_conclusao` como qualquer outro campo já calculado, mesmo padrão de
`destaqueDaMeta` já existente ali. Nenhuma duplicação: um único lugar (backend) calcula, qualquer
tela consome.

## 7. Resumo do que muda

**Backend (regras de apresentação centralizadas, nenhuma regra de negócio existente alterada):**
- Migração: `metas.frequencia_contribuicao` (enum, nullable) + `metas.concluida_em` (date,
  nullable).
- `app/models/enums.py`: `FrequenciaContribuicao` (persistido) e `SituacaoPlanejamentoMeta`
  (só transiente/apresentação, não é coluna).
- `MetaCreate`/`MetaUpdate`: `+frequencia_contribuicao`.
- `MetaRead`: `+frequencia_contribuicao`, `+concluida_em`, `+contribuicao_sugerida_por_periodo`,
  `+valor_planejado_ate_hoje`, `+diferenca_planejado_realizado`, `+situacao_planejamento`,
  `+data_prevista_conclusao`.
- `MetaService._com_progresso`: cresce para calcular todos os campos acima e persistir
  `concluida_em` na primeira transição.

**Frontend:**
- `MetaFormDialog`: campo opcional "Frequência de contribuição".
- `utils/meta.ts`: remove `calcularVelocidadeMeta`/`VelocidadeMeta` (substituído pelos campos do
  backend); ganha formatadores de apresentação (frase de planejado x realizado, label de
  frequência, label/tone de `situacao_planejamento`).
- `MetaResumoCard`: nova frase de contribuição sugerida, planejado x realizado, previsão de
  conclusão, histórico (datas + tempo até concluir), celebração única via `localStorage`.
- `MetasCard` (Dashboard): passa a poder usar os mesmos campos sem lógica nova.

Nenhuma regra de negócio existente (unicidade de descrição, soft delete, exclusão definitiva,
`valor_acumulado` sempre via `Transacao.meta_id`, `conta_id` organizacional) é alterada.

## 8. Status e decisões tomadas durante a implementação

Backend e Frontend desta etapa estão implementados e validados (545 testes unit + 38 integration
de Meta + 26 de Central Financeira, todos verdes; `tsc -b` e `vite build` limpos). Duas decisões
concretas, tomadas durante a implementação, que vale registrar:

- **`types/centralFinanceira.ts::MetaRead`** era uma interface local, um subconjunto manual mais
  antigo (sem os campos desta etapa). Confirmado no backend que `ProgressoMetasRead.metas` já
  reusa literalmente `app.schemas.meta.MetaRead` (não uma cópia reduzida) — então a correção
  correta não foi "adicionar os campos novos a uma segunda cópia", e sim migrar `MetaRead` para
  ser reexportado de `types/meta.ts`, o mesmo padrão já usado para `ContaRead` desde a Etapa F6.
  Zero alteração de backend necessária para isto: o dado já vinha completo, só o tipo do Frontend
  estava desatualizado.
- **`MetasCard` (Dashboard) `destaqueDaMeta`**: a heurística antiga "Vence em breve" (prazo a ≤14
  dias, calculada no cliente) foi mantida só como fallback para metas sem `situacao_planejamento`
  (ex. sem `data_alvo`). Quando `situacao_planejamento === "ATRASADO"` já vem pronto do backend,
  o card usa esse sinal diretamente (via `SITUACAO_PLANEJAMENTO_LABEL`/`TONE` de `utils/meta.ts`,
  reaproveitados — não redeclarados) em vez de continuar adivinhando urgência só pela proximidade
  da data. Isso é estritamente uma migração de "proxy client-side" para "sinal real do backend",
  não uma lógica nova.
