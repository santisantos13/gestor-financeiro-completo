# Análise arquitetural — Módulo de Contas Recorrentes (expansão completa)

Análise prévia à implementação do módulo completo de Contas Recorrentes, seguindo o mesmo
rigor das etapas anteriores. **Status: aguardando aprovação do usuário — nada foi
implementado.** Complementa (não substitui) `docs/analise-arquitetural-conta-recorrente.md`,
que cobriu a primeira etapa (backend MENSAL-only, 2026-07); este documento parte do que
aquele entregou e desenha a expansão pedida em 2026-07-20: todas as frequências, pausa/
reativação/encerramento, frontend completo, projeção no Calendário e caminho de evolução
para lembretes/notificações/automações sem refatoração.

## 0. Escopo pedido nesta etapa

Representar receitas e despesas periódicas (salário, aluguel, energia, água, internet,
assinaturas, academia, seguros etc.) com: frequências diária, semanal, quinzenal, mensal,
bimestral, trimestral, semestral e anual; pausa e reativação; encerramento; geração
automática de transações; integração com Dashboard, Calendário, Contas, Cartões e Metas;
frontend completo (React Query, UX, responsividade, acessibilidade, Motion); e evolução
futura para lembretes/notificações/automações sem refatorações.

## 1. Estado real do backend hoje (o que JÁ existe e funciona)

A primeira etapa entregou um núcleo sólido cuja arquitetura esta expansão preserva
integralmente:

- **Template vs ocorrência**: `ContaRecorrente` é só o template; cada ocorrência é uma
  `Transacao` real com `origem_recorrente_id`. Saldo, extrato, Dashboard, Calendário e
  Agenda já enxergam as ocorrências automaticamente, sem nenhuma integração extra — porque
  são `Transacao` comuns. Esse é o maior ativo do desenho atual e nada aqui o altera.
- **Geração lazy e síncrona**: nunca scheduler/cron. `criar()` gera as ocorrências já
  vencidas; `POST /contas-recorrentes/{id}/gerar-ocorrencias-pendentes` faz o catch-up,
  idempotente (`UniqueConstraint(origem_recorrente_id, data)` como rede de segurança).
- **Composição de Services**: toda ocorrência nasce via `TransacaoService.criar()` — herda
  posse/ativo de Conta/Cartão, resolução de fatura (recorrência no cartão), categoria,
  status (PENDENTE para conta, PAGO forçado para cartão). `ContaRecorrenteService` nunca
  escreve `Transacao` diretamente.
- **CRUD completo**: criar, obter, listar, PATCH (só afeta ocorrências futuras — seguro
  porque ocorrência nunca relê o template), desativar (soft, `ativo=False`), excluir
  (hard, usado só pela cascata de exclusão de Conta).
- **XOR conta/cartão** no banco (`ck_conta_recorrente_cartao_xor_conta`) e no Service.
- **Central Financeira** já classifica transação com `origem_recorrente_id` como
  `TipoEntidadeReferenciavel.CONTA_RECORRENTE` (Agenda/Calendário).

## 2. Gaps entre o escopo pedido e o backend real

1. **Frequências**: só MENSAL funciona. O enum tem SEMANAL/MENSAL/ANUAL (rejeitadas as duas
   últimas com `BusinessRuleError` — YAGNI da etapa 1, decisão do usuário na época). Faltam
   no enum: DIARIA, QUINZENAL, BIMESTRAL, TRIMESTRAL, SEMESTRAL. Faltam as regras de
   avanço de data para todas exceto MENSAL.
2. **`dia_vencimento` (1–31) só tem semântica mensal**: não descreve uma recorrência
   diária/semanal/quinzenal. Gap de modelagem, não só de validação.
3. **Pausa ≠ encerramento**: hoje `ativo=False` conflaciona os dois conceitos, e **não
   existe endpoint de reativação**. Pior: o cursor de geração é derivado da última
   ocorrência gerada, então reativar depois de 3 meses pausado geraria retroativamente 3
   meses de ocorrências — quase nunca o que o usuário quer ao "despausar" uma assinatura
   que ficou suspensa.
4. **Âncora derivada da última ocorrência tem um bug latente**: se o usuário exclui a
   última `Transacao` gerada (pela tela de Transações), o cursor "anda para trás" e a
   próxima sincronização RECRIA a transação que ele apagou de propósito. A
   `UniqueConstraint` impede duplicar data, mas não impede recriar o que foi
   deliberadamente removido.
5. **Sincronização é por-template**: `gerar-ocorrencias-pendentes` exige um id. Não há
   "sincronizar todas as recorrências do usuário" — que é o que o frontend precisa chamar
   ao abrir o app para dar a sensação de geração automática.
6. **Ocorrências futuras são invisíveis**: o Calendário/Agenda só mostram `Transacao` já
   geradas (≤ hoje). O usuário não vê o aluguel do dia 5 do mês que vem — exatamente o
   que mais se espera de um calendário financeiro.
7. **Frontend inexistente**: nenhuma página, rota, item de sidebar, tipo, service ou hook.
   `ROTA_POR_ORIGEM` documenta `CONTA_RECORRENTE` como "sem destino, deferido" (o ícone
   `Repeat` já está reservado em `ICONE_POR_ORIGEM`).
8. **Metas**: aporte recorrente numa Meta é uma `Transferencia` (conta → cofrinho), e
   `ContaRecorrente` só gera `Transacao`. Integração pedida, não suportada pelo modelo
   atual.
9. **Financiamentos**: constam da lista do pedido, mas parcelas de Financiamento/Empréstimo
   JÁ são geradas pelos módulos próprios (`FinanciamentoService` cria as `Transacao` de
   parcela). Modelar um financiamento como ContaRecorrente duplicaria o lançamento.
   Proposta: fora do escopo de Recorrentes por design, documentado — não é gap, é
   fronteira de domínio.

## 3. Modelagem de domínio proposta

### 3.1 Frequência: enum completo + função única de avanço

`FrequenciaRecorrencia` ganha os valores DIARIA, QUINZENAL, BIMESTRAL, TRIMESTRAL,
SEMESTRAL (SEMANAL/ANUAL já existem). Enum é schema-only por string — nenhuma migração de
dados, só de validação.

Toda a aritmética mora numa única função nova em `app/core/datas.py`:

```
avancar_data(data: date, frequencia: FrequenciaRecorrencia, dia_vencimento: int | None) -> date
```

- DIARIA: +1 dia. SEMANAL: +7 dias. QUINZENAL: +15 dias.
- MENSAL: `proximo_mes` + `dia_valido` (código existente, inalterado).
- BIMESTRAL/TRIMESTRAL/SEMESTRAL/ANUAL: generalização `somar_meses(n)` (n = 2/3/6/12) com
  o mesmo clamp de `dia_valido` (dia 31 em fevereiro → 28/29). `proximo_mes` vira caso
  particular `somar_meses(1)` — sem duplicar a regra de clamping que Parcelamento/Fatura
  já usam.

**Semântica de `dia_vencimento` por família de frequência:**

- Frequências **mensais-ou-maiores** (MENSAL, BIMESTRAL, TRIMESTRAL, SEMESTRAL, ANUAL):
  `dia_vencimento` obrigatório, como hoje (dia do mês, clampado).
- Frequências **baseadas em dias** (DIARIA, SEMANAL, QUINZENAL): `dia_vencimento` passa a
  ser **nulo** — a âncora é a própria `data_inicio` (uma semanal iniciada numa sexta
  ocorre toda sexta). Nenhuma coluna nova (`dia_semana` etc.): a `data_inicio` já carrega
  a informação. `dia_vencimento` vira `nullable=True` no model (migração Alembic), com
  validação por família no Service (obrigatório numa família, proibido na outra — erro
  claro nos dois sentidos).

Decisão em aberto (ver seção 12): QUINZENAL como "a cada 15 dias" (proposta) vs "duas
vezes por mês em dias fixos, ex. 5 e 20". A primeira é um intervalo puro (mesma família de
DIARIA/SEMANAL, zero modelagem extra); a segunda exigiria dois dias de vencimento e teria
comportamento estranho em fevereiro. Recomendo a primeira.

### 3.2 Cursor materializado: `proxima_execucao`

Nova coluna `proxima_execucao: date` no model (migração Alembic com backfill: para cada
template existente, calculada a partir da última ocorrência gerada — exatamente o valor
que o código atual derivaria).

Motivação (resolve os gaps 3 e 4 de uma vez):

- **Geração**: `_gerar_ocorrencias_pendentes` vira um laço simples — enquanto
  `proxima_execucao <= min(hoje, data_fim)`: gera a `Transacao`, avança o cursor com
  `avancar_data`, persiste. Idempotência continua dupla (cursor + `UniqueConstraint`).
- **Excluir uma ocorrência não ressuscita nada**: o cursor não olha mais para trás. O
  usuário apaga a transação de julho, o cursor já está em agosto — apagar vira uma decisão
  permanente, como em qualquer outra transação.
- **Pausa/reativação ganham semântica explícita** (seção 5).
- **Lembretes futuros ficam triviais** (seção 11): "o que vence nos próximos N dias" é uma
  query por `proxima_execucao`, sem recalcular nada.

O invariante da etapa 1 ("próxima data derivada da última ocorrência") é substituído
conscientemente: era correto para MENSAL sem pausa, mas não sobrevive a reativação nem a
exclusão manual de ocorrência. Este documento registra a substituição e o porquê.

### 3.3 Ciclo de vida: status explícito

Nova coluna `status: StatusRecorrencia` (enum ATIVA / PAUSADA / ENCERRADA) substituindo o
booleano `ativo` (migração: `ativo=True → ATIVA`, `ativo=False → PAUSADA`).

- **ATIVA**: gera ocorrências normalmente.
- **PAUSADA**: não gera; template intacto; reativável.
- **ENCERRADA**: terminal. `encerrar()` preenche `data_fim = hoje` (se não tiver) e muda o
  status — histórico preservado, nunca mais gera, não reativável (para "reabrir", o
  usuário cria outra igual; manter reversibilidade aqui criaria ambiguidade com PAUSADA).
- `data_fim` atingida naturalmente também encerra: a primeira sincronização após
  `proxima_execucao > data_fim` transiciona ATIVA → ENCERRADA automaticamente (o card sai
  de "ativas" sem ação manual).

Hard delete (`excluir`) continua existindo como hoje, restrito à cascata de exclusão de
Conta + uma exclusão definitiva explícita na UI (com confirmação, ocorrências geradas
preservadas como transações órfãs — mesma regra de Fatura).

## 4. Fluxo completo: criação → execução

1. Usuário cria o template (`POST /contas-recorrentes`): descrição, valor, tipo
   (RECEITA/DESPESA), frequência, dia_vencimento (se aplicável), conta OU cartão,
   categoria, data_inicio, data_fim opcional.
2. Service valida (XOR, datas, dia_vencimento × frequência), grava com status ATIVA e
   `proxima_execucao` = primeira data ≥ data_inicio (para mensais+: `dia_valido` no mês da
   data_inicio, avançando um período se cair antes dela — lógica atual preservada; para
   diárias/semanais/quinzenais: a própria data_inicio).
3. Ainda dentro de `criar()`, roda a geração de pendentes: tudo com `proxima_execucao <=
   hoje` vira `Transacao` imediatamente (caso "pago desde janeiro, cadastrando agora").
4. Daí em diante, a geração acontece na **sincronização global** (seção 6) — para o
   usuário, "automática"; para o sistema, lazy e explícita como sempre.
5. Cada ocorrência em Conta nasce PENDENTE — o usuário confirma o pagamento na tela de
   Transações (regra existente de `TransacaoService`, intocada). Em Cartão, nasce PAGO e
   entra na fatura aberta do ciclo (resolução de fatura existente, intocada).

## 5. Pausa, reativação e encerramento

- `POST /{id}/pausar`: ATIVA → PAUSADA. Nenhum efeito colateral (nada futuro existe para
  desfazer — invariante lazy preservado).
- `POST /{id}/reativar`: PAUSADA → ATIVA, com **decisão explícita do chamador** sobre o
  período pausado, num body `{ "gerar_retroativas": bool }`:
  - `false` (padrão da UI): o cursor pula para a primeira data futura — o período pausado
    fica sem ocorrências (assinatura suspensa: não houve cobrança, não deve haver
    lançamento).
  - `true`: o cursor fica onde estava e a próxima sincronização gera o período pausado
    inteiro (caso "eu paguei mas esqueci de despausar no app").
  Sem esse parâmetro, qualquer escolha unilateral estaria errada para metade dos casos.
- `POST /{id}/encerrar`: ATIVA ou PAUSADA → ENCERRADA (`data_fim = min(data_fim, hoje)`).
- `DELETE /{id}` muda de significado: hoje é soft delete (desativar); passa a ser a
  exclusão definitiva (com as ocorrências preservadas). A UI oferece as três ações com
  vocabulário próprio — Pausar / Encerrar / Excluir — sem sobrecarregar uma só.

## 6. "Geração automática" sem scheduler: sincronização global

Novo endpoint `POST /contas-recorrentes/sincronizar` (sem body): itera os templates ATIVOS
do usuário, roda a geração de pendentes de cada um, retorna um resumo
(`{ geradas: int, encerradas: int }`). Continua sendo o mesmo método interno usado por
`criar()` e pelo endpoint por-template — nenhuma lógica nova, só um laço.

O frontend chama essa mutation **uma vez por sessão**, no mount do `AppLayout` (pós-login),
e invalida os caches se `geradas > 0`. Para o usuário: abriu o app, o salário do dia 5 já
está lá. GETs continuam sem efeito colateral (invariante documentado desde a etapa 1);
scheduler continua inexistente. Quando um dia existir um worker (seção 11), ele chamará
exatamente este mesmo método de Service — zero refatoração.

## 7. Integrações

- **Contas / Cartões / Dashboard**: já resolvidas por construção (ocorrência é `Transacao`).
  A única adição é invalidação React Query correta após sincronizar (seção 9).
- **Calendário — projeção de ocorrências futuras** (gap 6): `calendario_financeiro` ganha,
  além dos eventos reais, eventos **virtuais** projetados dos templates ATIVOS para o mês
  visualizado: partindo de `proxima_execucao`, avança com `avancar_data` enquanto cair
  dentro do mês, sem gravar nada. Cada evento projetado sai com um campo novo
  `previsto: true` no schema de evento (default `false` — mudança aditiva, nenhum consumidor
  atual quebra) e categoria RECEITA/DESPESA normal. O frontend renderiza previstos com
  estilo próprio (dot vazado/tracejado + rótulo "previsto"), distinguindo claramente
  história de projeção. A Agenda ("próximos N dias") recebe o mesmo tratamento — hoje ela
  só mostra PENDENTE reais; passará a incluir os previstos do intervalo.
- **Metas**: aporte recorrente é `Transferencia`, não `Transacao` — fica **fora deste
  módulo**, deliberadamente. A porta para o futuro fica aberta sem custo: o conceito de
  frequência/cursor/avançar_data proposto aqui é agnóstico ao que se gera; uma futura
  `TransferenciaRecorrente` (ou um campo `destino_conta_id` no template, a decidir na
  época) reutiliza `avancar_data`, o padrão de status e a sincronização global sem tocar
  no que esta etapa entrega. Documentado como evolução, não implementado.
- **Financiamentos/Empréstimos**: fronteira explícita — parcelas já nascem dos módulos
  próprios; a UI de Recorrentes não os lista nem permite criá-los (evita duplicação de
  lançamento, gap 9).

## 8. Frontend (novo, completo)

- **Rota `/recorrentes`** + item no Sidebar/MobileNav (ícone `Repeat`, já reservado).
  `ROTA_POR_ORIGEM.CONTA_RECORRENTE = "/recorrentes"` — fecha o "deferido" documentado, e
  clicar num evento de recorrência no Calendário/Agenda passa a navegar.
- **Página**: mesma anatomia de `TransferenciasPage` (lista + `FormDialog`), não DataTable —
  volume é baixo (dezenas, não centenas). Duas seções (Receitas / Despesas), cada linha:
  descrição, valor, badge de frequência, origem (conta/cartão), **próxima ocorrência**
  (direto de `proxima_execucao` — sem cálculo no cliente), badge de status. Card de resumo
  no topo: total mensal estimado de receitas vs despesas recorrentes (normalizando
  frequências para o mês — só apresentação, cálculo no cliente).
- **`RecorrenteFormDialog`** (Tier 2): campos condicionais por frequência
  (dia_vencimento só para mensais+), origem Conta/Cartão com os pickers existentes,
  categoria, período. Edição reutiliza o mesmo dialog (padrão `EstadoDialogo` de
  TransacoesPage). Pausar/Reativar/Encerrar/Excluir: confirmações **inline substituindo o
  conteúdo** (regra de overlays Tier 2 — nunca dois empilhados; reativar pergunta sobre
  retroativas nessa mesma confirmação inline).
- **Responsividade**: lista vira cards empilhados < md (padrão ContasPage); dialog já é
  responsivo por herança do `FormDialog`.
- **Acessibilidade**: `aria-label` por ação com a descrição do item, `aria-expanded` nas
  seções, foco gerenciado pelo `FormDialog` existente, status como texto (badge), não só
  cor.
- **Motion**: entrada da lista com stagger sutil, transição de badge de status
  (`motion-principles.md`), respeitando `useReducedMotion` — nada novo de infraestrutura.

## 9. React Query

- `queryKeys.recorrentes = { all, list(filtros), detail(id) }` — mesmo molde das demais.
- Mutations de template (criar/editar/pausar/reativar/encerrar/excluir): invalidam
  `recorrentes.all` e, porque criação/reativação/sincronização podem gerar `Transacao`,
  chamam `invalidarTransacoes(queryClient, contaId, cartaoId)` — a função existente já
  cobre transações, dashboard, calendário, agenda, contas, cartões e faturas. Nenhuma
  chave nova de invalidação é necessária.
- `useSincronizarRecorrentes`: mutation disparada no mount do `AppLayout` (uma vez por
  sessão, guard com `useRef`); só invalida se `geradas > 0` (evita refetch em cascata a
  cada login sem novidade).
- Projeção do Calendário: nenhum estado novo — vem dentro da resposta existente de
  `["dashboard","calendario"]`.

## 10. Impacto no backend existente (resumo das mudanças)

1. `enums.py`: +5 valores em `FrequenciaRecorrencia`; novo `StatusRecorrencia`.
2. `core/datas.py`: `somar_meses(n)` (generaliza `proximo_mes`) + `avancar_data(...)`.
   Parcelamento/Fatura continuam usando as funções atuais — mudança aditiva.
3. Model + migração Alembic: `dia_vencimento` nullable, +`proxima_execucao` (backfill),
   `ativo` → `status` (backfill ATIVA/PAUSADA).
4. Service: validação dia_vencimento × família de frequência; geração reescrita sobre o
   cursor; `pausar`/`reativar(gerar_retroativas)`/`encerrar`; sincronização global;
   remoção do bloqueio de frequências.
5. Rotas: +`/sincronizar`, +`/pausar`, +`/reativar`, +`/encerrar`; `DELETE` vira exclusão
   definitiva.
6. `central_financeira_service.calendario_financeiro`/`agenda_financeira`: projeção
   virtual com `previsto: true` (campo aditivo no schema de evento).
7. Testes: unit da aritmética de `avancar_data` (todas as frequências, clamps de
   fevereiro/mês curto), ciclo de vida completo, reativação nas duas variantes,
   sincronização idempotente, projeção do calendário. Integração espelhando os fluxos.

Nada em Transacao/Fatura/Parcelamento/Meta muda de comportamento.

## 11. Evolução futura sem refatoração (lembretes, notificações, automações)

O desenho deixa três dobradiças prontas:

- **Lembretes**: "o que vence até D+N" = `SELECT ... WHERE status = ATIVA AND
  proxima_execucao <= :limite` — o cursor materializado é exatamente o índice que um
  `AlertaService` futuro precisa (`TipoAlerta.VENCIMENTO_CONTA_RECORRENTE` já existe no
  enum desde o início do projeto, sem CRUD). Nenhuma coluna nova será necessária.
- **Notificações/push**: consumidoras do mesmo dado; o evento "ocorrência gerada" já tem um
  ponto único de emissão (o método interno de geração) onde um hook/observer pode ser
  acoplado sem tocar na regra.
- **Automação total (scheduler)**: quando existir infraestrutura de background, o worker
  chama `sincronizar` por usuário — o mesmo método público que o frontend usa hoje. A
  migração de "lazy no login" para "scheduled" é uma mudança de *gatilho*, não de domínio.

## 12. Decisões em aberto (para o usuário, antes de implementar)

1. **QUINZENAL**: "a cada 15 dias" (recomendado, seção 3.1) ou "dois dias fixos do mês"?
2. **Reativação — padrão da UI**: pular período pausado por padrão (recomendado), com
   opção explícita de gerar retroativas?
3. **Projeção no Calendário**: projetar só o mês visualizado (recomendado) ou também um
   horizonte na Agenda do Dashboard (D+7/D+15)?
4. **DELETE definitivo**: confirmar a mudança de semântica do `DELETE` (hoje soft) para
   exclusão real com dupla confirmação na UI, alinhando com o vocabulário
   Pausar/Encerrar/Excluir.

## 13. Fases de implementação propostas (após aprovação)

1. **Backend — fundação**: enums, `avancar_data`/`somar_meses`, migração (cursor + status
   + nullable), Service reescrito, novos endpoints, testes.
2. **Backend — projeção**: calendário/agenda com `previsto`, testes.
3. **Frontend — módulo**: tipos, service, hooks, página `/recorrentes`, dialog, sidebar,
   `ROTA_POR_ORIGEM`, sincronização no AppLayout.
4. **Polimento**: responsividade, acessibilidade, Motion, revisão técnica documentada
   (`revisao-tecnica-conta-recorrente.md` atualizada).

## 14. Conclusão

O núcleo da etapa 1 (template/ocorrência, geração lazy, composição via `TransacaoService`)
está correto e é integralmente preservado. As mudanças estruturais desta expansão são três
e todas têm justificativa própria: enum completo com uma única função de avanço de datas
(elimina a restrição MENSAL sem N caminhos de código), cursor materializado
`proxima_execucao` (corrige o bug de regeneração pós-exclusão e habilita pausa/reativação
e lembretes futuros), e status explícito ATIVA/PAUSADA/ENCERRADA (desfaz a conflação do
booleano `ativo`). A "geração automática" é entregue como sincronização lazy no login —
mesma garantia de nunca haver scheduler, mas com a UX de automático — e o mesmo método
servirá um scheduler real no futuro sem refatoração. Aguardando revisão e aprovação.
