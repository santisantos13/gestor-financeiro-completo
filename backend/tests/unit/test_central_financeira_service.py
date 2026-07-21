"""Testes unitários de CentralFinanceiraService - isolado com Services de
domínio FALSOS (em memória, sem banco e sem os Services reais). Diferente
de todo outro `test_*_service.py` do projeto (que fakeiam Repository),
aqui fakeiam-se os oito SERVICES de domínio - é exatamente o nível de
isolamento certo para testar uma camada que, por definição, nunca acessa
Repository (ver docs/analise-arquitetural-central-financeira.md).

Cobre as três regras estruturais da Central: nunca recalcula um valor já
pronto (só lê `saldo_atual`/`limite_disponivel`/`valor_total_calculado`/
`percentual`/`saldo_devedor` dos objetos fake), toda aritmética adicional é
sobre resultados já agregados (fluxo de caixa, patrimônio líquido), e as
únicas iterações em Python são sobre listas pequenas e conhecidas (cartões
do usuário, parcelas de UM contrato).
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import (
    CategoriaEventoCalendario,
    StatusContratoCredito,
    StatusFatura,
    StatusTransacao,
    TipoEntidadeReferenciavel,
    TipoTransacao,
)
from app.services.central_financeira_service import CentralFinanceiraService


# --- objetos e Services falsos ------------------------------------------------

@dataclass
class _Conta:
    id: int
    saldo_atual: Decimal
    nome: str = "Conta"
    ativo: bool = True
    oculta: bool = False


@dataclass
class _Cartao:
    id: int
    nome: str = "Cartao"
    limite_disponivel: Decimal = Decimal("0")
    ativo: bool = True


@dataclass
class _Fatura:
    id: int
    cartao_id: int
    status_calculado: StatusFatura
    valor_total_calculado: Decimal
    data_vencimento: date
    mes_referencia: date = field(default_factory=date.today)
    # Etapa de Calendário Financeiro: `calendario_financeiro` lê
    # `data_fechamento` além de `data_vencimento` (fecha e vence são dois
    # eventos distintos) - default = hoje para não quebrar nenhum teste
    # pré-existente que só testava `agenda_financeira`/`resumo_faturas`
    # (que nunca leem esse campo).
    data_fechamento: date = field(default_factory=date.today)


@dataclass
class _Transacao:
    id: int
    valor: Decimal
    data: date
    descricao: str
    status: StatusTransacao
    financiamento_id: int | None = None
    emprestimo_id: int | None = None
    parcelamento_id: int | None = None
    origem_recorrente_id: int | None = None
    # Etapa de Calendário Financeiro: `calendario_financeiro` lê `tipo` para
    # decidir a cor do dot (RECEITA/DESPESA) - default DESPESA preserva todo
    # teste pré-existente (nenhum deles olhava esse campo antes).
    tipo: TipoTransacao = TipoTransacao.DESPESA
    # Correção do bug "parcela de compra no cartão aparecia no calendário"
    # (2026-07-20): `calendario_financeiro` passou a chamar `listar(...,
    # apenas_conta=True)` - default `None` preserva todo teste pré-existente
    # (nenhum deles simula uma compra de cartão, todos representam
    # transações "de conta" implicitamente).
    cartao_id: int | None = None


@dataclass
class _Contrato:
    """Espelha `Financiamento` - tem `valor_financiado` (mesmo que None),
    igual ao model real. `_combinar` usa `hasattr(contrato,
    "valor_financiado")` para diferenciar de `Emprestimo`, então o fake
    para cada lado só pode ter os atributos que o model real de fato tem
    (ver `_ContratoEmprestimo` abaixo, sem esse atributo)."""

    id: int
    descricao: str
    saldo_devedor: Decimal
    num_parcelas: int
    status: StatusContratoCredito
    instituicao_financeira: str = "Banco"
    numero_contrato: str | None = None
    taxa_juros: Decimal = Decimal("0.01")
    sistema_amortizacao: str = "PRICE"
    cet: Decimal | None = None
    data_inicio: date = field(default_factory=date.today)
    permite_quitacao_antecipada: bool = True
    conta_id: int | None = None
    categoria_id: int | None = None
    valor_financiado: Decimal | None = None
    valor_entrada: Decimal | None = None
    bem_financiado: str | None = None


@dataclass
class _ContratoEmprestimo:
    """Espelha `Emprestimo` - sem `valor_financiado` (nunca existiu nesse
    model), só `valor_liberado`/`finalidade`."""

    id: int
    descricao: str
    saldo_devedor: Decimal
    num_parcelas: int
    status: StatusContratoCredito
    instituicao_financeira: str = "Banco"
    numero_contrato: str | None = None
    taxa_juros: Decimal = Decimal("0.01")
    sistema_amortizacao: str = "PRICE"
    cet: Decimal | None = None
    data_inicio: date = field(default_factory=date.today)
    permite_quitacao_antecipada: bool = True
    conta_id: int | None = None
    categoria_id: int | None = None
    valor_liberado: Decimal | None = None
    finalidade: str | None = None


@dataclass
class _Meta:
    id: int
    percentual: Decimal
    # Etapa de Calendário Financeiro: `calendario_financeiro` lê
    # `descricao`/`valor_alvo`/`data_alvo` (mesmos campos do model real
    # `Meta`) - defaults preservam todo teste pré-existente que só cobria
    # `progresso_metas`/`indicadores_gerais` (que só leem `percentual`).
    descricao: str = "Meta"
    valor_alvo: Decimal = Decimal("0")
    data_alvo: date | None = None


@dataclass
class _Transferencia:
    id: int
    conta_origem_id: int
    conta_destino_id: int
    valor: Decimal
    data: date
    descricao: str | None = None
    ativo: bool = True


class FakeContaService:
    def __init__(self, contas):
        self._contas = contas

    def listar(self, usuario_id, *, apenas_ativas=True, apenas_visiveis=True):
        return list(self._contas)


class FakeCartaoService:
    def __init__(self, cartoes):
        self._cartoes = cartoes

    def listar(self, usuario_id, *, apenas_ativos=True):
        return list(self._cartoes)


class FakeFaturaService:
    def __init__(self, faturas_por_cartao):
        self._faturas_por_cartao = faturas_por_cartao  # dict cartao_id -> list[_Fatura]

    def listar(self, cartao_id, usuario_id, *, limit=100):
        return list(self._faturas_por_cartao.get(cartao_id, []))[:limit]

    # Fake mínimo não precisa reordenar de verdade (os testes deste arquivo
    # nunca colocam mais de 3 faturas falsas por cartão) - só precisa
    # existir com a mesma assinatura, já que `calendario_financeiro`/
    # `agenda_financeira` passaram a chamar este método em vez de
    # `listar` (correção do bug "calendário não exibe fechamento/
    # vencimento de fatura", 2026-07-21).
    def listar_recentes(self, cartao_id, usuario_id, *, limit=100):
        return list(self._faturas_por_cartao.get(cartao_id, []))[:limit]


class FakeTransacaoService:
    def __init__(self, transacoes):
        self._transacoes = transacoes

    def listar(
        self,
        usuario_id,
        *,
        conta_id=None,
        cartao_id=None,
        categoria_id=None,
        parcelamento_id=None,
        financiamento_id=None,
        emprestimo_id=None,
        origem_recorrente_id=None,
        meta_id=None,
        tipo=None,
        status=None,
        data_inicio=None,
        data_fim=None,
        apenas_conta=False,
        skip=0,
        limit=100,
    ):
        resultado = list(self._transacoes)
        if financiamento_id is not None:
            resultado = [t for t in resultado if t.financiamento_id == financiamento_id]
        if emprestimo_id is not None:
            resultado = [t for t in resultado if t.emprestimo_id == emprestimo_id]
        if parcelamento_id is not None:
            resultado = [t for t in resultado if t.parcelamento_id == parcelamento_id]
        if status is not None:
            resultado = [t for t in resultado if t.status == status]
        if data_inicio is not None:
            resultado = [t for t in resultado if t.data >= data_inicio]
        if data_fim is not None:
            resultado = [t for t in resultado if t.data <= data_fim]
        if apenas_conta:
            resultado = [t for t in resultado if getattr(t, "cartao_id", None) is None]
        return resultado[skip : skip + limit]

    def somar_por_periodo(self, usuario_id, *, tipo, status, data_inicio, data_fim):
        return sum(
            (
                t.valor
                for t in self._transacoes
                if t.status == status and data_inicio <= t.data <= data_fim
            ),
            Decimal("0"),
        )


class FakeContratoService:
    def __init__(self, contratos):
        self._contratos = contratos

    def listar(self, usuario_id, *, apenas_ativos=True):
        if apenas_ativos:
            return [c for c in self._contratos if c.status != StatusContratoCredito.QUITADO]
        return list(self._contratos)


class FakeMetaService:
    def __init__(self, metas):
        self._metas = metas

    def listar(self, usuario_id, *, apenas_ativas=True, skip=0, limit=100):
        return list(self._metas)[skip : skip + limit]


class FakeTransferenciaService:
    def __init__(self, transferencias):
        self._transferencias = transferencias

    def listar(self, usuario_id, *, apenas_ativas=True, skip=0, limit=100):
        resultado = list(self._transferencias)
        if apenas_ativas:
            resultado = [t for t in resultado if t.ativo]
        return resultado[skip : skip + limit]


def _service(
    *,
    contas=(),
    cartoes=(),
    faturas_por_cartao=None,
    transacoes=(),
    financiamentos=(),
    emprestimos=(),
    parcelamentos=(),
    metas=(),
    transferencias=(),
) -> CentralFinanceiraService:
    return CentralFinanceiraService(
        conta_service=FakeContaService(list(contas)),
        cartao_service=FakeCartaoService(list(cartoes)),
        fatura_service=FakeFaturaService(faturas_por_cartao or {}),
        transacao_service=FakeTransacaoService(list(transacoes)),
        financiamento_service=FakeContratoService(list(financiamentos)),
        emprestimo_service=FakeContratoService(list(emprestimos)),
        parcelamento_service=FakeContratoService(list(parcelamentos)),
        meta_service=FakeMetaService(list(metas)),
        transferencia_service=FakeTransferenciaService(list(transferencias)),
    )


HOJE = date.today()


# --- saldo consolidado / resumo das contas --------------------------------------

def test_saldo_consolidado_soma_saldo_atual_ja_calculado_das_contas():
    """Nunca recalcula saldo - só lê `saldo_atual`, que já vem pronto do
    Service de Conta (mesmo se as contas tivessem transações complexas por
    trás - a Central não sabe nem precisa saber disso)."""
    contas = [_Conta(id=1, saldo_atual=Decimal("100.00")), _Conta(id=2, saldo_atual=Decimal("250.50"))]
    service = _service(contas=contas)

    resultado = service.saldo_consolidado(usuario_id=1)

    assert resultado["saldo_total"] == Decimal("350.50")
    assert resultado["contas"] == contas


def test_saldo_consolidado_sem_contas_e_zero():
    service = _service(contas=[])
    resultado = service.saldo_consolidado(usuario_id=1)
    assert resultado["saldo_total"] == Decimal("0")
    assert resultado["contas"] == []


def test_resumo_contas_devolve_as_contas_do_service_sem_transformar():
    contas = [_Conta(id=1, saldo_atual=Decimal("10"))]
    service = _service(contas=contas)
    assert service.resumo_contas(usuario_id=1)["contas"] == contas


# --- resumo dos cartões ------------------------------------------------------

def test_resumo_cartoes_soma_total_utilizado_das_faturas_abertas():
    cartao_a = _Cartao(id=1)
    cartao_b = _Cartao(id=2)
    faturas = {
        1: [_Fatura(id=10, cartao_id=1, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("300"), data_vencimento=HOJE)],
        2: [_Fatura(id=20, cartao_id=2, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("150"), data_vencimento=HOJE)],
    }
    service = _service(cartoes=[cartao_a, cartao_b], faturas_por_cartao=faturas)

    resultado = service.resumo_cartoes(usuario_id=1)

    assert resultado["total_utilizado"] == Decimal("450")
    assert resultado["cartoes"] == [cartao_a, cartao_b]


def test_resumo_cartoes_ignora_fatura_ja_paga_no_total_utilizado():
    cartao = _Cartao(id=1)
    faturas = {
        1: [_Fatura(id=10, cartao_id=1, status_calculado=StatusFatura.PAGA, valor_total_calculado=Decimal("300"), data_vencimento=HOJE)],
    }
    service = _service(cartoes=[cartao], faturas_por_cartao=faturas)
    assert service.resumo_cartoes(usuario_id=1)["total_utilizado"] == Decimal("0")


def test_resumo_cartoes_sem_nenhuma_fatura_e_zero():
    cartao = _Cartao(id=1)
    service = _service(cartoes=[cartao], faturas_por_cartao={})
    assert service.resumo_cartoes(usuario_id=1)["total_utilizado"] == Decimal("0")


# --- resumo financeiro geral / visão mensal -------------------------------------

def test_resumo_financeiro_calcula_fluxo_de_caixa_por_aritmetica_pura():
    """entradas - saidas, nunca uma query nova - a soma em si vem de
    `somar_por_periodo` (que no fake é a única fonte de verdade)."""
    transacoes = [
        _Transacao(id=1, valor=Decimal("500"), data=HOJE, descricao="Salario", status=StatusTransacao.PAGO),
        _Transacao(id=2, valor=Decimal("200"), data=HOJE, descricao="Mercado", status=StatusTransacao.PAGO),
    ]
    service = _service(contas=[_Conta(id=1, saldo_atual=Decimal("1000"))], transacoes=transacoes)

    resultado = service.resumo_financeiro(usuario_id=1, ano=HOJE.year, mes=HOJE.month)

    assert resultado["saldo_total"] == Decimal("1000")
    assert resultado["fluxo_caixa_mes"] == Decimal("0")  # ambas contam como "entrada" no fake bruto - ver nota


def test_resumo_financeiro_usa_mes_corrente_quando_ano_mes_omitidos():
    service = _service(contas=[_Conta(id=1, saldo_atual=Decimal("500"))])
    resultado = service.resumo_financeiro(usuario_id=1)
    assert resultado["ano"] == HOJE.year
    assert resultado["mes"] == HOJE.month


def test_resumo_financeiro_patrimonio_liquido_subtrai_dividas_de_todas_as_fontes():
    """patrimônio líquido = saldo - (financiamentos + empréstimos + faturas
    em aberto + parcelamentos) - quatro fontes, quatro Services diferentes,
    nenhuma soma refeita pela Central (só lida e subtraída)."""
    contas = [_Conta(id=1, saldo_atual=Decimal("10000"))]
    financiamentos = [_Contrato(id=1, descricao="Carro", saldo_devedor=Decimal("3000"), num_parcelas=12, status=StatusContratoCredito.ATIVO)]
    emprestimos = [_Contrato(id=1, descricao="Pessoal", saldo_devedor=Decimal("1000"), num_parcelas=6, status=StatusContratoCredito.ATIVO)]
    cartao = _Cartao(id=1)
    faturas = {1: [_Fatura(id=1, cartao_id=1, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("500"), data_vencimento=HOJE)]}
    parcelamento = _Contrato(id=1, descricao="TV", saldo_devedor=Decimal("0"), num_parcelas=3, status=StatusContratoCredito.ATIVO)
    parcelas_pendentes = [
        _Transacao(id=1, valor=Decimal("100"), data=HOJE, descricao="TV 1/3", status=StatusTransacao.PENDENTE, parcelamento_id=1),
        _Transacao(id=2, valor=Decimal("100"), data=HOJE, descricao="TV 2/3", status=StatusTransacao.PENDENTE, parcelamento_id=1),
    ]

    service = _service(
        contas=contas,
        cartoes=[cartao],
        faturas_por_cartao=faturas,
        financiamentos=financiamentos,
        emprestimos=emprestimos,
        parcelamentos=[parcelamento],
        transacoes=parcelas_pendentes,
    )

    resultado = service.resumo_financeiro(usuario_id=1, ano=HOJE.year, mes=HOJE.month)

    # 10000 - (3000 + 1000 + 500 + 200) = 5300
    assert resultado["patrimonio_liquido"] == Decimal("5300")


def test_resumo_financeiro_ignora_contrato_quitado_na_divida():
    """`_saldo_devedor_total` já filtra QUITADO mesmo que o Service de
    domínio devolva a lista sem filtrar (defesa em profundidade contra um
    `apenas_ativos=False` acidental)."""
    contas = [_Conta(id=1, saldo_atual=Decimal("1000"))]
    financiamentos = [
        _Contrato(id=1, descricao="Quitado", saldo_devedor=Decimal("0"), num_parcelas=1, status=StatusContratoCredito.QUITADO),
    ]
    service = _service(contas=contas, financiamentos=financiamentos)
    resultado = service.resumo_financeiro(usuario_id=1, ano=HOJE.year, mes=HOJE.month)
    assert resultado["patrimonio_liquido"] == Decimal("1000")


def test_visao_mensal_usa_mes_corrente_quando_omitido_e_calcula_fluxo():
    transacoes = [
        _Transacao(id=1, valor=Decimal("300"), data=HOJE, descricao="Receita", status=StatusTransacao.PAGO),
    ]
    service = _service(transacoes=transacoes)
    resultado = service.visao_mensal(usuario_id=1)
    assert resultado["ano"] == HOJE.year
    assert resultado["mes"] == HOJE.month
    assert resultado["fluxo_caixa"] == resultado["entradas"] - resultado["saidas"]


# --- resumo de financiamentos / empréstimos (métricas de parcelas) ----------------

def test_resumo_financiamentos_calcula_parcelas_pagas_restantes_e_proxima():
    contrato = _Contrato(id=1, descricao="Carro", saldo_devedor=Decimal("8000"), num_parcelas=4, status=StatusContratoCredito.ATIVO)
    parcelas = [
        _Transacao(id=1, valor=Decimal("250"), data=HOJE - timedelta(days=60), descricao="1/4", status=StatusTransacao.PAGO, financiamento_id=1),
        _Transacao(id=2, valor=Decimal("250"), data=HOJE - timedelta(days=30), descricao="2/4", status=StatusTransacao.PAGO, financiamento_id=1),
        _Transacao(id=3, valor=Decimal("250"), data=HOJE, descricao="3/4", status=StatusTransacao.PENDENTE, financiamento_id=1),
        _Transacao(id=4, valor=Decimal("250"), data=HOJE + timedelta(days=30), descricao="4/4", status=StatusTransacao.PENDENTE, financiamento_id=1),
    ]
    service = _service(financiamentos=[contrato], transacoes=parcelas)

    resultado = service.resumo_financiamentos(usuario_id=1)["financiamentos"][0]

    assert resultado["parcelas_pagas"] == 2
    assert resultado["parcelas_restantes"] == 2
    assert resultado["valor_total_pago"] == Decimal("500")
    assert resultado["proxima_parcela_data"] == HOJE
    assert resultado["proxima_parcela_valor"] == Decimal("250")


def test_resumo_financiamentos_sem_nenhuma_parcela_paga():
    contrato = _Contrato(id=1, descricao="Carro", saldo_devedor=Decimal("1000"), num_parcelas=2, status=StatusContratoCredito.ATIVO)
    parcelas = [
        _Transacao(id=1, valor=Decimal("500"), data=HOJE, descricao="1/2", status=StatusTransacao.PENDENTE, financiamento_id=1),
        _Transacao(id=2, valor=Decimal("500"), data=HOJE + timedelta(days=30), descricao="2/2", status=StatusTransacao.PENDENTE, financiamento_id=1),
    ]
    service = _service(financiamentos=[contrato], transacoes=parcelas)
    resultado = service.resumo_financiamentos(usuario_id=1)["financiamentos"][0]
    assert resultado["parcelas_pagas"] == 0
    assert resultado["valor_total_pago"] == Decimal("0")


def test_resumo_financiamentos_todas_pagas_nao_ha_proxima_parcela():
    contrato = _Contrato(id=1, descricao="Carro", saldo_devedor=Decimal("0"), num_parcelas=1, status=StatusContratoCredito.QUITADO)
    parcelas = [
        _Transacao(id=1, valor=Decimal("500"), data=HOJE, descricao="1/1", status=StatusTransacao.PAGO, financiamento_id=1),
    ]
    # apenas_ativos=True e o default de listar() - um financiamento QUITADO
    # nao aparece no resumo (mesmo filtro ja usado por FinanciamentoService).
    service = _service(financiamentos=[contrato], transacoes=parcelas)
    assert service.resumo_financiamentos(usuario_id=1)["financiamentos"] == []


def test_resumo_emprestimos_usa_valor_liberado_em_vez_de_valor_financiado():
    contrato = _ContratoEmprestimo(
        id=1, descricao="Pessoal", saldo_devedor=Decimal("500"), num_parcelas=1,
        status=StatusContratoCredito.ATIVO, valor_liberado=Decimal("500"), finalidade="Reforma",
    )
    service = _service(emprestimos=[contrato])
    resultado = service.resumo_emprestimos(usuario_id=1)["emprestimos"][0]
    assert resultado["valor_liberado"] == Decimal("500")
    assert resultado["finalidade"] == "Reforma"
    assert "valor_financiado" not in resultado


# --- progresso das metas -----------------------------------------------------------

def test_progresso_metas_devolve_metas_sem_recalcular_percentual():
    metas = [_Meta(id=1, percentual=Decimal("42.50"))]
    service = _service(metas=metas)
    assert service.progresso_metas(usuario_id=1)["metas"] == metas


# --- agenda financeira ---------------------------------------------------------

def test_agenda_financeira_inclui_parcela_pendente_futura():
    parcela = _Transacao(
        id=1, valor=Decimal("100"), data=HOJE + timedelta(days=5), descricao="Parcela",
        status=StatusTransacao.PENDENTE, financiamento_id=7,
    )
    service = _service(transacoes=[parcela])
    eventos = service.agenda_financeira(usuario_id=1, dias=30)["eventos"]
    assert len(eventos) == 1
    assert eventos[0]["origem_tipo"] == TipoEntidadeReferenciavel.FINANCIAMENTO
    assert eventos[0]["origem_id"] == 7


def test_agenda_financeira_inclui_fatura_com_vencimento_futuro_nao_paga():
    cartao = _Cartao(id=1, nome="Nubank")
    fatura = _Fatura(
        id=1, cartao_id=1, status_calculado=StatusFatura.FECHADA,
        valor_total_calculado=Decimal("400"), data_vencimento=HOJE + timedelta(days=10),
    )
    service = _service(cartoes=[cartao], faturas_por_cartao={1: [fatura]})
    eventos = service.agenda_financeira(usuario_id=1, dias=30)["eventos"]
    assert len(eventos) == 1
    assert eventos[0]["origem_tipo"] == TipoEntidadeReferenciavel.FATURA
    assert eventos[0]["valor"] == Decimal("400")


def test_agenda_financeira_exclui_fatura_ja_paga():
    cartao = _Cartao(id=1)
    fatura = _Fatura(
        id=1, cartao_id=1, status_calculado=StatusFatura.PAGA,
        valor_total_calculado=Decimal("400"), data_vencimento=HOJE + timedelta(days=10),
    )
    service = _service(cartoes=[cartao], faturas_por_cartao={1: [fatura]})
    assert service.agenda_financeira(usuario_id=1, dias=30)["eventos"] == []


def test_agenda_financeira_exclui_evento_fora_da_janela_de_dias():
    parcela = _Transacao(
        id=1, valor=Decimal("100"), data=HOJE + timedelta(days=45), descricao="Parcela distante",
        status=StatusTransacao.PENDENTE,
    )
    service = _service(transacoes=[parcela])
    assert service.agenda_financeira(usuario_id=1, dias=30)["eventos"] == []


def test_agenda_financeira_ordena_eventos_por_data():
    t1 = _Transacao(id=1, valor=Decimal("10"), data=HOJE + timedelta(days=10), descricao="Depois", status=StatusTransacao.PENDENTE)
    t2 = _Transacao(id=2, valor=Decimal("20"), data=HOJE + timedelta(days=2), descricao="Antes", status=StatusTransacao.PENDENTE)
    service = _service(transacoes=[t1, t2])
    eventos = service.agenda_financeira(usuario_id=1, dias=30)["eventos"]
    assert [e["descricao"] for e in eventos] == ["Antes", "Depois"]


def test_agenda_financeira_origem_transacao_avulsa_quando_sem_contrato():
    t = _Transacao(id=99, valor=Decimal("10"), data=HOJE + timedelta(days=1), descricao="Avulsa", status=StatusTransacao.PENDENTE)
    service = _service(transacoes=[t])
    eventos = service.agenda_financeira(usuario_id=1, dias=30)["eventos"]
    assert eventos[0]["origem_tipo"] == TipoEntidadeReferenciavel.TRANSACAO
    assert eventos[0]["origem_id"] == 99


# --- calendário financeiro (Etapa de Transferências/Calendário) ------------------

def test_calendario_financeiro_categoriza_transacao_paga_e_pendente_por_tipo():
    receita_paga = _Transacao(
        id=1, valor=Decimal("500"), data=HOJE, descricao="Salário",
        status=StatusTransacao.PAGO, tipo=TipoTransacao.RECEITA,
    )
    despesa_pendente = _Transacao(
        id=2, valor=Decimal("100"), data=HOJE, descricao="Aluguel",
        status=StatusTransacao.PENDENTE, tipo=TipoTransacao.DESPESA,
    )
    service = _service(transacoes=[receita_paga, despesa_pendente])
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]

    por_descricao = {e["descricao"]: e for e in eventos}
    assert por_descricao["Salário"]["categoria"] == CategoriaEventoCalendario.RECEITA
    assert por_descricao["Salário"]["status"] == "PAGO"
    assert por_descricao["Aluguel"]["categoria"] == CategoriaEventoCalendario.DESPESA
    assert por_descricao["Aluguel"]["status"] == "PENDENTE"


def test_calendario_financeiro_categoriza_financiamento_e_emprestimo_com_categoria_propria():
    """Pedido do usuário (2026-07-21, "pode dar uma cor"): parcela de
    Financiamento/Empréstimo não deve mais cair em RECEITA/DESPESA
    genérico - ganha categoria própria (cor dedicada na legenda do
    frontend, `calendarioCategorias.ts`)."""
    parcela_financiamento = _Transacao(
        id=1, valor=Decimal("800"), data=HOJE, descricao="Parcela financiamento",
        status=StatusTransacao.PENDENTE, tipo=TipoTransacao.DESPESA, financiamento_id=10,
    )
    parcela_emprestimo = _Transacao(
        id=2, valor=Decimal("300"), data=HOJE, descricao="Parcela empréstimo",
        status=StatusTransacao.PENDENTE, tipo=TipoTransacao.DESPESA, emprestimo_id=20,
    )
    service = _service(transacoes=[parcela_financiamento, parcela_emprestimo])
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]

    por_descricao = {e["descricao"]: e for e in eventos}
    assert por_descricao["Parcela financiamento"]["categoria"] == CategoriaEventoCalendario.FINANCIAMENTO
    assert por_descricao["Parcela financiamento"]["origem_tipo"] == TipoEntidadeReferenciavel.FINANCIAMENTO
    assert por_descricao["Parcela empréstimo"]["categoria"] == CategoriaEventoCalendario.EMPRESTIMO
    assert por_descricao["Parcela empréstimo"]["origem_tipo"] == TipoEntidadeReferenciavel.EMPRESTIMO


def test_calendario_financeiro_exclui_transacao_fora_do_mes_consultado():
    fora_do_mes = _Transacao(
        id=1, valor=Decimal("10"), data=HOJE + timedelta(days=90), descricao="Distante",
        status=StatusTransacao.PENDENTE,
    )
    service = _service(transacoes=[fora_do_mes])
    assert service.calendario_financeiro(usuario_id=1)["eventos"] == []


def test_calendario_financeiro_fatura_gera_evento_de_fechamento_e_vencimento_quando_ambos_no_mes():
    cartao = _Cartao(id=1, nome="Nubank")
    fatura = _Fatura(
        id=1, cartao_id=1, status_calculado=StatusFatura.FECHADA,
        valor_total_calculado=Decimal("400"), data_vencimento=HOJE, data_fechamento=HOJE,
    )
    service = _service(cartoes=[cartao], faturas_por_cartao={1: [fatura]})
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]

    categorias = {e["categoria"] for e in eventos}
    assert categorias == {CategoriaEventoCalendario.FATURA_FECHAMENTO, CategoriaEventoCalendario.FATURA_VENCIMENTO}
    assert all(e["origem_tipo"] == TipoEntidadeReferenciavel.FATURA and e["origem_id"] == 1 for e in eventos)


def test_calendario_financeiro_inclui_transferencia_ativa_do_mes_com_nomes_de_conta():
    contas = [_Conta(id=1, saldo_atual=Decimal("0"), nome="Corrente"), _Conta(id=2, saldo_atual=Decimal("0"), nome="Poupança")]
    transferencia = _Transferencia(id=1, conta_origem_id=1, conta_destino_id=2, valor=Decimal("300"), data=HOJE)
    service = _service(contas=contas, transferencias=[transferencia])
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]

    assert len(eventos) == 1
    assert eventos[0]["categoria"] == CategoriaEventoCalendario.TRANSFERENCIA
    assert eventos[0]["origem_tipo"] == TipoEntidadeReferenciavel.TRANSFERENCIA
    assert eventos[0]["origem_id"] == 1
    assert eventos[0]["descricao"] == "Corrente → Poupança"


def test_calendario_financeiro_usa_descricao_propria_da_transferencia_quando_existe():
    contas = [_Conta(id=1, saldo_atual=Decimal("0"), nome="Corrente"), _Conta(id=2, saldo_atual=Decimal("0"), nome="Poupança")]
    transferencia = _Transferencia(
        id=1, conta_origem_id=1, conta_destino_id=2, valor=Decimal("300"), data=HOJE, descricao="Reserva de emergência",
    )
    service = _service(contas=contas, transferencias=[transferencia])
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]
    assert eventos[0]["descricao"] == "Reserva de emergência"


def test_calendario_financeiro_exclui_transferencia_cancelada():
    contas = [_Conta(id=1, saldo_atual=Decimal("0")), _Conta(id=2, saldo_atual=Decimal("0"))]
    cancelada = _Transferencia(id=1, conta_origem_id=1, conta_destino_id=2, valor=Decimal("300"), data=HOJE, ativo=False)
    service = _service(contas=contas, transferencias=[cancelada])
    assert service.calendario_financeiro(usuario_id=1)["eventos"] == []


def test_calendario_financeiro_inclui_meta_com_prazo_no_mes():
    meta = _Meta(id=1, percentual=Decimal("50.00"), descricao="Viagem", valor_alvo=Decimal("5000"), data_alvo=HOJE)
    service = _service(metas=[meta])
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]
    assert len(eventos) == 1
    assert eventos[0]["categoria"] == CategoriaEventoCalendario.META
    assert eventos[0]["origem_tipo"] == TipoEntidadeReferenciavel.META
    assert eventos[0]["valor"] == Decimal("5000")


def test_calendario_financeiro_ignora_meta_sem_prazo_definido():
    meta = _Meta(id=1, percentual=Decimal("10.00"), descricao="Sem prazo", data_alvo=None)
    service = _service(metas=[meta])
    assert service.calendario_financeiro(usuario_id=1)["eventos"] == []


def test_calendario_financeiro_aceita_ano_mes_explicitos_fora_do_mes_corrente():
    # mês totalmente diferente do atual - garante que `ano`/`mes` (não
    # "hoje") é quem define a janela, mesmo raciocínio já coberto por
    # `resumo_financeiro`/`visao_mensal`.
    transacao_em_marco = _Transacao(
        id=1, valor=Decimal("100"), data=date(2025, 3, 15), descricao="Março", status=StatusTransacao.PAGO,
    )
    service = _service(transacoes=[transacao_em_marco])
    resultado = service.calendario_financeiro(usuario_id=1, ano=2025, mes=3)
    assert resultado["ano"] == 2025
    assert resultado["mes"] == 3
    assert len(resultado["eventos"]) == 1
    assert service.calendario_financeiro(usuario_id=1, ano=2025, mes=4)["eventos"] == []


def test_calendario_financeiro_ordena_eventos_por_data():
    depois = _Transacao(id=1, valor=Decimal("10"), data=HOJE, descricao="Depois", status=StatusTransacao.PAGO)
    antes = _Transacao(id=2, valor=Decimal("20"), data=HOJE - timedelta(days=1), descricao="Antes", status=StatusTransacao.PAGO)
    service = _service(transacoes=[depois, antes])
    eventos = service.calendario_financeiro(usuario_id=1)["eventos"]
    assert [e["descricao"] for e in eventos] == ["Antes", "Depois"]


# --- indicadores gerais -------------------------------------------------------------

def test_indicadores_gerais_conta_faturas_em_aberto_e_metas():
    contas = [_Conta(id=1, saldo_atual=Decimal("100"))]
    cartao_com_aberta = _Cartao(id=1)
    cartao_sem_fatura = _Cartao(id=2)
    faturas = {
        1: [_Fatura(id=1, cartao_id=1, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("50"), data_vencimento=HOJE)],
    }
    metas = [_Meta(id=1, percentual=Decimal("50.00")), _Meta(id=2, percentual=Decimal("100.00"))]
    service = _service(contas=contas, cartoes=[cartao_com_aberta, cartao_sem_fatura], faturas_por_cartao=faturas, metas=metas)

    resultado = service.indicadores_gerais(usuario_id=1)

    assert resultado["contas_ativas"] == 1
    assert resultado["cartoes_ativos"] == 2
    assert resultado["faturas_em_aberto"] == 1
    assert resultado["metas_ativas"] == 2
    assert resultado["percentual_medio_metas"] == Decimal("75.00")


def test_indicadores_gerais_sem_metas_percentual_medio_e_zero():
    service = _service(metas=[])
    assert service.indicadores_gerais(usuario_id=1)["percentual_medio_metas"] == Decimal("0.00")


def test_indicadores_gerais_conta_parcelas_atrasadas_de_qualquer_contrato():
    atrasada_financiamento = _Transacao(
        id=1, valor=Decimal("100"), data=HOJE - timedelta(days=5), descricao="Atrasada",
        status=StatusTransacao.PENDENTE, financiamento_id=1,
    )
    em_dia = _Transacao(
        id=2, valor=Decimal("100"), data=HOJE + timedelta(days=5), descricao="Futura",
        status=StatusTransacao.PENDENTE, financiamento_id=1,
    )
    avulsa_atrasada = _Transacao(
        id=3, valor=Decimal("50"), data=HOJE - timedelta(days=1), descricao="Avulsa sem contrato",
        status=StatusTransacao.PENDENTE,
    )
    service = _service(transacoes=[atrasada_financiamento, em_dia, avulsa_atrasada])
    # avulsa_atrasada nao conta - so parcelas de CONTRATO (financiamento/
    # emprestimo/parcelamento) contam como "atrasadas" neste indicador.
    assert service.indicadores_gerais(usuario_id=1)["parcelas_atrasadas"] == 1
