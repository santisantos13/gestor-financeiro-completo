"""Enums compartilhados entre os models do dominio.

Centralizar aqui evita duplicar as mesmas listas de valores em varios
arquivos e facilita achar "quais status/tipos existem no sistema" em um
unico lugar. Cada Enum herda de (str, enum.Enum) para que o valor gravado
no banco seja o texto legivel (ex: "RECEITA"), nao um numero.
"""
import enum


class Bandeira(str, enum.Enum):
    """Bandeira (rede) de um Cartao de credito."""

    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    ELO = "ELO"
    AMERICAN_EXPRESS = "AMERICAN_EXPRESS"
    HIPERCARD = "HIPERCARD"
    DINERS_CLUB = "DINERS_CLUB"
    OUTRA = "OUTRA"


class TipoConta(str, enum.Enum):
    """Natureza de uma Conta (onde o dinheiro fica guardado)."""

    CORRENTE = "CORRENTE"
    POUPANCA = "POUPANCA"
    CARTEIRA = "CARTEIRA"
    INVESTIMENTO = "INVESTIMENTO"


class TipoCategoria(str, enum.Enum):
    """Restringe se uma Categoria pode ser usada em receitas, despesas ou ambos."""

    RECEITA = "RECEITA"
    DESPESA = "DESPESA"
    AMBOS = "AMBOS"


class TipoTransacao(str, enum.Enum):
    """Substitui a necessidade de tabelas separadas Receita/Despesa."""

    RECEITA = "RECEITA"
    DESPESA = "DESPESA"


class StatusTransacao(str, enum.Enum):
    """Se o lancamento ja efetivamente aconteceu (PAGO) ou ainda vai acontecer (PENDENTE).

    ATENCAO - este campo tem DOIS significados diferentes dependendo de a
    transacao pertencer a uma Conta ou a um Cartao (ver
    docs/analise-arquitetural-transacao.md, secao "StatusTransacao: dois
    significados, nunca confundidos"):

    - Transacao de CONTA (`conta_id` preenchido): `status` E autoritativo.
      PENDENTE = ainda nao aconteceu de verdade, PAGO = ja moveu dinheiro.
      Editavel livremente pelo cliente; consumido direto por
      `ContaRepository.somar_transacoes_pagas` (so soma PAGO).

    - Transacao de CARTAO (`cartao_id` preenchido): `status` NAO E a
      autoridade sobre pagamento da divida - essa autoridade e SEMPRE a
      Fatura (`Fatura.status`/`valor_pago`, derivados a partir de
      `Transacao.fatura_paga_id`). Uma compra no cartao "acontece" no ato,
      independente de quando a fatura correspondente e paga.
      `TransacaoService` forca `status = PAGO` na criacao de toda transacao
      de cartao, ignorando o que o cliente enviar nesse campo -
      `CartaoRepository.somar_gastos_nao_pagos` ja ignora `status` de
      proposito pelo mesmo motivo (ver seu docstring).
    """

    PENDENTE = "PENDENTE"
    PAGO = "PAGO"


class FrequenciaRecorrencia(str, enum.Enum):
    """Periodicidade de uma ContaRecorrente.

    Duas famílias com semânticas de âncora distintas (ver
    `app/core/datas.avancar_data` e
    docs/analise-arquitetural-conta-recorrente-expansao.md, seção 3.1):

    - BASEADAS EM DIAS (DIARIA/SEMANAL/QUINZENAL): avançam um intervalo
      fixo de dias a partir da ocorrência anterior; a âncora é a própria
      `data_inicio` (uma semanal iniciada numa sexta ocorre toda sexta).
      `dia_vencimento` NÃO se aplica (nulo obrigatório).
    - BASEADAS EM MESES (MENSAL/BIMESTRAL/TRIMESTRAL/SEMESTRAL/ANUAL):
      avançam N meses com clamp de dia (`dia_valido` - dia 31 em
      fevereiro vira 28/29). `dia_vencimento` (1-31) é obrigatório.

    QUINZENAL = intervalo fixo de 14 dias (decisão do usuário, 2026-07-20
    - não "duas vezes por mês em dias fixos").
    """

    DIARIA = "DIARIA"
    SEMANAL = "SEMANAL"
    QUINZENAL = "QUINZENAL"
    MENSAL = "MENSAL"
    BIMESTRAL = "BIMESTRAL"
    TRIMESTRAL = "TRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"


class StatusRecorrencia(str, enum.Enum):
    """Ciclo de vida de uma ContaRecorrente (substitui o booleano `ativo`,
    que conflacionava pausa e encerramento - ver
    docs/analise-arquitetural-conta-recorrente-expansao.md, seção 3.3).

    ATIVA gera ocorrências normalmente; PAUSADA não gera mas é reativável
    (reativação NUNCA gera retroativos - o cursor `proxima_execucao` pula
    para a próxima data futura, decisão do usuário 2026-07-20); ENCERRADA
    é terminal (atingiu `data_fim`, foi encerrada manualmente, ou recebeu
    DELETE - que preserva histórico e transações já geradas em vez de
    apagar fisicamente, decisão do usuário 2026-07-20).
    """

    ATIVA = "ATIVA"
    PAUSADA = "PAUSADA"
    ENCERRADA = "ENCERRADA"


class StatusFatura(str, enum.Enum):
    """Ciclo de vida de uma Fatura de cartao de credito.

    So ABERTA e FECHADA sao gravadas de verdade na coluna `status` do banco
    - sao as unicas transicoes causadas por um evento real (fechamento do
    ciclo, com snapshot de valor_total). PARCIALMENTE_PAGA, PAGA e ATRASADA
    NUNCA sao persistidas: sao calculadas por FaturaService a partir de
    valor_pago/valor_total/data_vencimento a cada leitura, e so existem
    como vocabulario da API (ver docs/analise-arquitetural-fatura.md).
    """

    ABERTA = "ABERTA"                        # ciclo corrente, ainda recebendo transacoes
    FECHADA = "FECHADA"                      # ciclo encerrado, valor_total consolidado, nada pago ainda
    PARCIALMENTE_PAGA = "PARCIALMENTE_PAGA"  # [derivado] fechada, com pagamento parcial registrado
    PAGA = "PAGA"                            # [derivado] fechada, valor_pago >= valor_total
    ATRASADA = "ATRASADA"                    # [derivado] fechada, passou data_vencimento sem quitar


class SistemaAmortizacao(str, enum.Enum):
    """Como a parcela de um contrato de credito (Financiamento/Emprestimo)
    e composta entre juros e amortizacao do saldo devedor.
    """

    PRICE = "PRICE"  # parcelas fixas (Tabela Price / Sistema Frances)
    SAC = "SAC"      # parcelas decrescentes (Sistema de Amortizacao Constante)


class FrequenciaContribuicao(str, enum.Enum):
    """Periodicidade de contribuição planejada para uma Meta - opcional,
    escolhida pelo usuário na criação/edição (ver
    docs/analise-arquitetural-metas-refinamento.md, seção 1.1). Usada só
    para calcular `MetaRead.contribuicao_sugerida_por_periodo`
    (`MetaService`); nunca valida nem bloqueia nada."""

    DIARIA = "DIARIA"
    SEMANAL = "SEMANAL"
    QUINZENAL = "QUINZENAL"
    MENSAL = "MENSAL"


class SituacaoPlanejamentoMeta(str, enum.Enum):
    """Classificação transiente (nunca uma coluna) de "planejado x
    realizado" de uma Meta com `data_alvo` - ver
    docs/analise-arquitetural-metas-refinamento.md, seção 2.3. Só schema
    (Pydantic), sem coluna de banco."""

    ADIANTADO = "ADIANTADO"
    DENTRO_DO_PLANEJADO = "DENTRO_DO_PLANEJADO"
    ATRASADO = "ATRASADO"


class StatusContratoCredito(str, enum.Enum):
    """Ciclo de vida de um Financiamento ou Emprestimo."""

    ATIVO = "ATIVO"
    QUITADO = "QUITADO"
    INADIMPLENTE = "INADIMPLENTE"


class TipoPapel(str, enum.Enum):
    """Papel (role) do usuario no sistema, usado para autorizacao.

    So existe USER por enquanto - a arquitetura (ver exigir_papel em
    app/api/deps.py) ja aceita mais de um papel sem precisar ser redesenhada
    quando um segundo valor (ex: ADMIN) for adicionado aqui.
    """

    USER = "USER"


class TipoAlerta(str, enum.Enum):
    """Gatilhos de notificacao suportados pelo sistema."""

    LIMITE_CARTAO = "LIMITE_CARTAO"
    VENCIMENTO_FATURA = "VENCIMENTO_FATURA"
    VENCIMENTO_CONTA_RECORRENTE = "VENCIMENTO_CONTA_RECORRENTE"
    META_ATINGIDA = "META_ATINGIDA"
    SALDO_BAIXO = "SALDO_BAIXO"


class TipoEntidadeReferenciavel(str, enum.Enum):
    """Usado por Alerta e Anexo para apontar polimorficamente a qualquer
    entidade do dominio (entidade_tipo + entidade_id), evitando uma coluna
    de FK opcional por entidade em cada uma dessas duas tabelas. Tambem
    reaproveitado por `EventoAgenda`/`EventoCalendario`
    (`schemas/central_financeira.py`) como `origem_tipo` - ali e so um
    campo de schema (Pydantic), nao uma coluna de banco, entao adicionar um
    membro novo (`TRANSFERENCIA`) nao exige migration.

    ATENCAO (achado da auditoria da Etapa de Transferencias/Calendario):
    `Alerta.entidade_tipo` E uma coluna real (`sa.Enum`, com CHECK
    constraint no SQLite) e a migration inicial
    (`f988db1c148b_modelo_inicial_do_dominio_financeiro.py`) so declarou
    CONTA/CARTAO/FATURA/TRANSACAO/PARCELAMENTO/CONTA_RECORRENTE/META nesse
    CHECK - FINANCIAMENTO/EMPRESTIMO (adicionados a este enum Python depois)
    e agora TRANSFERENCIA NAO estao no CHECK constraint do banco. Isso e
    inofensivo hoje porque a feature de Alerta ainda nao foi implementada
    (nenhum Service grava `Alerta.entidade_tipo`), mas quem for implementar
    Alerta precisa gerar uma migration nova para esses tres valores antes de
    usa-los ali. Nao corrigido agora por ser fora do escopo desta etapa
    (nenhuma regra de negocio de Alerta foi tocada)."""

    CONTA = "CONTA"
    CARTAO = "CARTAO"
    FATURA = "FATURA"
    TRANSACAO = "TRANSACAO"
    PARCELAMENTO = "PARCELAMENTO"
    FINANCIAMENTO = "FINANCIAMENTO"
    EMPRESTIMO = "EMPRESTIMO"
    CONTA_RECORRENTE = "CONTA_RECORRENTE"
    META = "META"
    TRANSFERENCIA = "TRANSFERENCIA"


class CategoriaEventoCalendario(str, enum.Enum):
    """Discriminador de EXIBICAO do Calendario Financeiro
    (`CentralFinanceiraService.calendario_financeiro`) - propositalmente
    separado de `TipoEntidadeReferenciavel` (que serve para NAVEGACAO: "para
    qual tela este evento leva"). Um mesmo `origem_tipo=TRANSACAO` pode ser
    RECEITA (verde) ou DESPESA (vermelho); uma mesma Fatura gera dois
    eventos de cor diferente (fechamento x vencimento). Nenhum dos dois
    enums substitui o outro - `EventoCalendario` carrega os dois campos.
    Schema-only (Pydantic), sem coluna de banco - nenhuma migration
    necessaria para adicionar/remover valores aqui no futuro.
    """

    RECEITA = "RECEITA"
    DESPESA = "DESPESA"
    FATURA_FECHAMENTO = "FATURA_FECHAMENTO"
    FATURA_VENCIMENTO = "FATURA_VENCIMENTO"
    TRANSFERENCIA = "TRANSFERENCIA"
    META = "META"


class CategoriaMovimentacaoConta(str, enum.Enum):
    """Discriminador de exibição/filtro do extrato de uma Conta
    (`ContaService.extrato`, docs/analise-arquitetural-extrato-conta.md) -
    mesma família de `CategoriaEventoCalendario`: schema-only (Pydantic),
    sem coluna de banco, sem migration.

    Derivado sempre a partir de campos que já existem em `Transacao`/
    `Transferencia`, nunca uma regra de negócio nova:
    - RECEITA/DESPESA: `Transacao` "solta" (sem fatura_paga_id/
      financiamento_id/emprestimo_id), discriminada por `Transacao.tipo`.
    - PAGAMENTO_FATURA: `Transacao.fatura_paga_id` preenchido.
    - PAGAMENTO_FINANCIAMENTO: `Transacao.financiamento_id` preenchido.
    - PAGAMENTO_EMPRESTIMO: `Transacao.emprestimo_id` preenchido.
    - TRANSFERENCIA_ENVIADA/TRANSFERENCIA_RECEBIDA: `Transferencia`,
      discriminada por qual lado (`conta_origem_id`/`conta_destino_id`) é a
      conta consultada.

    Compra no cartão de crédito NUNCA aparece aqui - é sempre uma
    `Transacao` com `cartao_id` preenchido e `conta_id` nulo, então já fica
    de fora só pelo filtro `conta_id = X` usado para montar o extrato
    (pedido explícito do usuário: histórico de compra no cartão pertence
    ao Cartão, não à Conta, até a fatura ser paga)."""

    RECEITA = "RECEITA"
    DESPESA = "DESPESA"
    TRANSFERENCIA_ENVIADA = "TRANSFERENCIA_ENVIADA"
    TRANSFERENCIA_RECEBIDA = "TRANSFERENCIA_RECEBIDA"
    PAGAMENTO_FATURA = "PAGAMENTO_FATURA"
    PAGAMENTO_FINANCIAMENTO = "PAGAMENTO_FINANCIAMENTO"
    PAGAMENTO_EMPRESTIMO = "PAGAMENTO_EMPRESTIMO"
