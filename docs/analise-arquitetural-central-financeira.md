# Análise arquitetural — Central Financeira

Segue o mesmo formato de toda `docs/analise-arquitetural-*.md` anterior: inventário do
que já existe, achados, decisões e o que fica de fora desta etapa. Pré-requisito lido
antes desta análise: `docs/central-financeira-especificacao.md` (spec funcional/UX,
anterior à existência de qualquer CRUD) e `docs/decisao-performance-saldo.md`.

## 0. Delimitação de escopo desta etapa

`docs/central-financeira-especificacao.md` descreve uma Central completa: Resumo,
5 cards de domínio, Agenda, **Alertas** (motor de regras persistido em `Alerta`) e
**Insights** (interface `InsightProvider`, hoje regra determinística, amanhã IA). A
instrução que abriu esta etapa é mais restrita que a spec: apenas os 11 endpoints
agregadores explicitamente listados, e proíbe explicitamente cache, scheduler,
materialized views e IA.

Isso não é um conflito entre os dois documentos — é a spec descrevendo o produto
completo e esta etapa implementando o primeiro corte dele. **Alertas e Insights ficam
fora desta etapa** (a própria spec já os trata como blocos independentes, seção 8:
"cada bloco é tecnicamente independente"). Motivo adicional, não só de escopo: um motor
de alertas ("saldo previsto ficará negativo", "meta atrasada") introduz limiares e
condições que são regra de negócio nova por definição — exatamente o que a instrução
desta etapa proíbe. Insights está explicitamente fora por proibir IA e por também exigir
regra de negócio nova (comparações período-a-período). Ambos continuam disponíveis como
próxima etapa natural, não descartados.

Os 11 endpoints desta etapa: resumo financeiro geral, saldo consolidado, resumo das
contas, resumo dos cartões, resumo das faturas, resumo de financiamentos, resumo de
empréstimos, progresso das metas, agenda financeira (sem Alertas/Insights), visão
mensal, indicadores gerais.

## 1. Inventário — o que já é 100% reutilizável sem nenhuma mudança

Todo Service abaixo já devolve o valor calculado pronto via `obter()`/`listar()` —
a Central só precisa chamar e formatar, exatamente como a instrução exige:

| Service | Campo calculado já anexado | Onde |
|---|---|---|
| `ContaService` | `saldo_atual` (`saldo_inicial` + líquido de `Transacao` PAGA + `Transferencia`) | `_com_saldo`, aplicado em `criar/obter/listar/atualizar` |
| `CartaoService` | `limite_disponivel` (`limite` − gastos não pagos) | `_com_limite_disponivel`, mesmo padrão |
| `FaturaService` | `valor_pago`, `valor_total_calculado`, `status_calculado` (ABERTA/FECHADA/PARCIALMENTE_PAGA/PAGA/ATRASADA) | `_com_valores_calculados`, mesmo padrão |
| `MetaService` | `valor_acumulado`, `percentual` | `_com_progresso`, mesmo padrão |
| `FinanciamentoService`/`EmprestimoService` | `saldo_devedor` (coluna armazenada, exceção documentada) | direto no model, sem recálculo — a Central lê, nunca recalcula |

Nenhum desses cinco Services precisa de qualquer alteração. A Central nunca duplica os
cálculos acima — só lê o resultado já pronto.

## 2. Achados — gaps que pedem exatamente um método público adicional

Estes são os únicos pontos onde um Service existente precisa crescer. Em todos os três
casos abaixo, a mudança é mecânica (mesmo padrão de um filtro/método já existente na
mesma classe, só estendido) e **não introduz nenhuma regra de negócio nova** — é
puramente evitar que a Central seja forçada a (a) duplicar uma agregação em Python ou
(b) fazer uma query cara sem necessidade.

### 2.1 `TransacaoRepository`/`TransacaoService`: falta filtro por `status`

`TransacaoService.listar()` filtra por `conta_id, cartao_id, categoria_id,
parcelamento_id, financiamento_id, emprestimo_id, origem_recorrente_id, meta_id, tipo,
data_inicio, data_fim` — mas **não por `status`** (`PAGO`/`PENDENTE`). "Entradas do mês"
e "Saídas do mês" (Resumo Financeiro) precisam de `tipo` + `status=PAGO` + intervalo de
datas; a Agenda Financeira precisa de `status=PENDENTE` + data futura. Sem esse filtro,
a Central teria que buscar tudo no intervalo e filtrar `status` em Python — decisão
proposta: adicionar `status: StatusTransacao | None = None` em
`TransacaoRepository.listar_do_usuario` e `TransacaoService.listar()`, mesmo padrão já
usado por `tipo` (parâmetro opcional, uma linha de `if` na query). Nenhuma regra nova;
é o mesmo filtro que `ContaRepository.somar_transacoes_pagas` e
`CartaoRepository.somar_gastos_nao_pagos` já aplicam internamente, só que agora exposto
como parâmetro de leitura.

### 2.2 `TransacaoRepository`/`TransacaoService`: falta agregação SQL (`SUM`)

`docs/decisao-performance-saldo.md` já registra a diretriz do projeto: "toda métrica
agregada (somas, contagens) deve ser uma query SQL com `SUM`/`COUNT`/`GROUP BY`, nunca
carregar todas as `Transacao` em Python e somar". Hoje `TransacaoService` não expõe
nenhum método de soma — só `listar()` (linhas paginadas, `limit=100` por padrão). Somar
"Entradas do mês"/"Saídas do mês" chamando `listar()` e somando em Python violaria essa
diretriz e um `limit` default de 100 poderia inclusive dar um resultado errado (silenciosamente
truncado) num mês com mais de 100 lançamentos.

Decisão: adicionar `TransacaoRepository.somar_por_periodo(usuario_id, *, tipo, status,
data_inicio, data_fim) -> Decimal`, mesmo padrão de `case`/`sum` já usado em
`FaturaRepository.somar_transacoes`, e um wrapper público equivalente em
`TransacaoService`. É leitura pura, sem decisão de negócio — a regra "o que conta como
receita/despesa paga" já existe (`TipoTransacao`/`StatusTransacao`), este método só
soma o que já é verdade no banco.

### 2.2.1 Nota sobre "próxima parcela"/"parcelas restantes" de contrato

Financiamento/Empréstimo/Parcelamento usam `TransacaoService.listar(financiamento_id=X,
...)`, que ordena sempre `data.desc()` (mais recente primeiro). Para achar a "próxima
parcela PENDENTE" seria mais natural uma ordem ascendente, que não existe hoje. **Decisão:
não adicionar** parâmetro de ordenação — o número de parcelas por contrato é sempre
pequeno e finito (`num_parcelas`, tipicamente < 500 mesmo em financiamentos longos), então
buscar com `limit=num_parcelas` (já é o padrão usado internamente em
`FinanciamentoService._buscar_parcela`) e escolher a menor data em Python é O(N) sobre um N
pequeno e conhecido — não é o "carregar tudo e somar" que a diretriz de performance
proíbe (que se refere a agregar sobre toda a tabela de transações do usuário, não sobre
o conjunto já pequeno e filtrado de um único contrato). Resolvido por orquestração, sem
mudança de Service.

### 2.3 `FaturaService.listar()` é escopado por `cartao_id` — não é um gap, é orquestração

Não existe (nem precisa existir) um "listar todas as faturas do usuário" — a Central
itera `CartaoService.listar(usuario_id)` (tipicamente poucas unidades de cartões por
usuário) e chama `FaturaService.listar(cartao_id, usuario_id)` por cartão. Isso é
exatamente o padrão de orquestração que a instrução autoriza ("nunca deve acessar
Repositories diretamente... toda informação deve ser obtida reutilizando os Services
atuais") — múltiplas chamadas a um Service já existente não é duplicação de regra, e o
N aqui (número de cartões de uma pessoa física) nunca é grande o suficiente para ser um
gargalo real. Nenhuma mudança em `FaturaService`.

## 3. Verificação cruzada — nenhuma inconsistência de cálculo encontrada

Conferido, campo a campo, que a fonte de cada métrica da spec (seção 4) é única e não
tem dois Services calculando o mesmo número de jeitos diferentes:

- Saldo total = soma de `Conta.saldo_atual` (só `ContaService`, nunca recalculado via
  `Transacao` direto pela Central).
- Patrimônio líquido = soma de saldo (`ContaService`) − soma de `saldo_devedor`
  (`FinanciamentoService`/`EmprestimoService`) − valor em aberto de fatura
  (`FaturaService`) − saldo restante de parcelamento (`ParcelamentoService`) — é
  aritmética pura sobre quatro números já calculados por quatro Services diferentes,
  cada um dono do seu pedaço; a Central nunca refaz nenhum desses cálculos, só soma/
  subtrai os resultados finais.
- Fluxo de caixa = entradas − saídas — mesma natureza (aritmética sobre dois valores já
  agregados via `somar_por_periodo`, seção 2.2).
- Progresso de meta = `MetaService._com_progresso` — única fonte, a Central nunca soma
  `Transacao.meta_id` por conta própria.

## 4. Ponto que fica fora desta etapa por decisão explícita (não é bloqueio arquitetural)

A spec (seção 5) descreve a Agenda Financeira fundindo três fontes: `Transacao
PENDENTE` já materializada, `Fatura` com vencimento futuro, e **ocorrências futuras de
`ContaRecorrente` ainda não materializadas** (projetadas sob demanda, sem persistir).
As duas primeiras fontes são leitura pura de dados já existentes — zero risco. A
terceira exigiria um método novo em `ContaRecorrenteService` que reaproveita a mesma
matemática de data já usada em `_gerar_ocorrencias_pendentes` (`dia_valido`/
`proximo_mes`), mas numa variante **somente leitura** (sem criar `Transacao`), hoje
inexistente — a lógica atual só sabe gerar ocorrências vencidas (`<= hoje`) e sempre
com efeito colateral de escrita.

Como isso está fora dos 11 endpoints explicitamente listados na instrução desta etapa
(que fala em "próximos vencimentos", coberto pelas duas fontes já materializadas) e a
instrução não pede projeção de recorrências futuras não geradas, a Agenda Financeira
desta etapa cobre **parcelas de contrato já lançadas (`Transacao PENDENTE`) e faturas
com vencimento futuro** — não projeta a próxima ocorrência de uma `ContaRecorrente`
ainda não vencida. Isso é registrado aqui como gap consciente (mesmo espírito de
"Open Finance fora de escopo" já registrado na spec, seção 13), não esquecido, e é uma
extensão natural de uma etapa futura caso o usuário queira agenda mostrando também
recorrências que ainda vão vencer.

## 5. Estrutura de implementação decidida

- **Um único Service**, não um por seção: `CentralFinanceiraService`
  (`app/services/central_financeira_service.py`), injetando por construtor os oito
  Services de domínio já existentes (`ContaService`, `CartaoService`, `FaturaService`,
  `TransacaoService`, `FinanciamentoService`, `EmprestimoService`,
  `ParcelamentoService`, `MetaService`) — sem Repository próprio, exatamente como a
  spec exige (seção 8: "os Services da Central Financeira não têm Repository
  próprio"). Um método por endpoint.
  Desvio deliberado da spec (seção 9/11), que sugere um Service por seção e uma
  interface `CardProvider` (Protocol) com registro dinâmico de cards: para exatamente
  11 endpoints fixos e conhecidos hoje, essa abstração é prematura — mesmo raciocínio
  YAGNI já aplicado neste projeto (`IRepository` só existe porque já há mais de uma
  implementação real; `FrequenciaRecorrencia.SEMANAL/ANUAL` ficaram no enum mas sem
  suporte até serem necessárias). Se o número de cards crescer a ponto de um único
  Service ficar difícil de navegar, a divisão em Services por seção (ou o
  `CardProvider`) pode ser feita depois sem quebrar o Router — refatoração interna, não
  mudança de contrato.
- **Um único Router**, `app/api/routes/central_financeira.py`, prefixo
  `/central-financeira`, 11 rotas `GET`, todas atrás de `get_current_user` (nenhuma
  aceita `usuario_id` do cliente).
- **Schemas novos** em `app/schemas/central_financeira.py` — um `Output` por endpoint;
  nenhum `Create`/`Update` (camada 100% somente-leitura).
- **Nenhum Repository novo, nenhuma entidade nova, nenhuma migration** — os dois
  métodos da seção 2 são as únicas mudanças em código de domínio já existente
  (`TransacaoRepository`/`TransacaoService`), e nenhum dos dois altera uma coluna ou
  tabela.

## 6. Migrations

Nenhuma mudança de schema é necessária — os achados da seção 2 são métodos novos sobre
tabelas/colunas que já existem. `alembic revision --autogenerate` não deve detectar
nenhuma alteração; validado após a implementação (seção de testes/revisão técnica).
