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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

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
    # Etapa de Gráficos: `_saldo_inicial_total` lê o campo BRUTO (não
    # `saldo_atual`, já calculado) - default 0 preserva todo teste
    # pré-existente que nunca olhava esse campo.
    saldo_inicial: Decimal = Decimal("0")


@dataclass
class _Categoria:
    id: int
    nome: str
    cor: str | None = None
    icone: str | None = None


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
    # Etapa de Gráficos: `somar_liquido_por_mes` (fake) só conta Transacao
    # DE CONTA (mesma regra do real, ver TransacaoRepository) - default
    # `None` é deliberado (diferente do "implicitamente de conta" do
    # comentário acima): nenhum teste pré-existente exercita os métodos
    # novos desta etapa, então não há teste antigo para quebrar.
    conta_id: int | None = None
    importada: bool = False
    categoria_id: int | None = None


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

    # `calendario_financeiro` passou a chamar isto em vez de
    # `listar_recentes(..., limit=3)` (correção do bug "vencimento de
    # fatura não aparece", 2026-07-22) - o fake filtra exatamente como o
    # Repository real (`FaturaRepository.listar_no_periodo`), sem nenhum
    # corte por quantidade.
    def listar_no_periodo(self, cartao_id, usuario_id, data_inicio, data_fim):
        return [
            f
            for f in self._faturas_por_cartao.get(cartao_id, [])
            if data_inicio <= f.data_fechamento <= data_fim or data_inicio <= f.data_vencimento <= data_fim
        ]


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

    # --- Etapa de Gráficos - fakes ingênuos em Python (o SQL SUM/GROUP BY é
    # responsabilidade do Repository real, testado separadamente em
    # test_transacao_repository.py; aqui só a INTERFACE precisa bater).

    def somar_liquido_por_mes(self, usuario_id, *, data_fim):
        acumulado = defaultdict(lambda: Decimal("0"))
        for t in self._transacoes:
            if t.conta_id is None or t.status != StatusTransacao.PAGO or t.importada or t.data > data_fim:
                continue
            sinal = 1 if t.tipo == TipoTransacao.RECEITA else -1
            acumulado[(t.data.year, t.data.month)] += sinal * t.valor
        return [SimpleNamespace(ano=ano, mes=mes, liquido=valor) for (ano, mes), valor in acumulado.items()]

    def somar_por_mes(self, usuario_id, *, tipo, status, data_inicio, data_fim):
        acumulado = defaultdict(lambda: Decimal("0"))
        for t in self._transacoes:
            if t.tipo != tipo or t.status != status or not (data_inicio <= t.data <= data_fim):
                continue
            acumulado[(t.data.year, t.data.month)] += t.valor
        return [SimpleNamespace(ano=ano, mes=mes, total=valor) for (ano, mes), valor in acumulado.items()]

    def somar_agrupado_por_categoria(self, usuario_id, *, tipo, status, data_inicio, data_fim):
        acumulado = defaultdict(lambda: Decimal("0"))
        for t in self._transacoes:
            if t.tipo != tipo or t.status != status or not (data_inicio <= t.data <= data_fim):
                continue
            acumulado[t.categoria_id] += t.valor
        return [SimpleNamespace(categoria_id=cid, total=valor) for cid, valor in acumulado.items()]

    def somar_agrupado_por_cartao(self, usuario_id, *, status, data_inicio, data_fim):
        acumulado = defaultdict(lambda: Decimal("0"))
        for t in self._transacoes:
            if (
                t.cartao_id is None
                or t.tipo != TipoTransacao.DESPESA
                or t.status != status
                or not (data_inicio <= t.data <= data_fim)
            ):
                continue
            acumulado[t.cartao_id] += t.valor
        return [SimpleNamespace(cartao_id=cid, total=valor) for cid, valor in acumulado.items()]


class FakeCategoriaService:
    def __init__(self, categorias):
        self._categorias = categorias

    def listar(self, usuario_id, *, apenas_ativas=True, incluir_ocultas=False, skip=0, limit=100):
        return list(self._categorias)[skip : skip + limit]


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

    def listar(self, usuario_id, *, apenas_ativas=True, data_inicio=None, data_fim=None, skip=0, limit=100):
        resultado = list(self._transferencias)
        if apenas_ativas:
            resultado = [t for t in resultado if t.ativo]
        if data_inicio is not None:
            resultado = [t for t in resultado if t.data >= data_inicio]
        if data_fim is not None:
            resultado = [t for t in resultado if t.data <= data_fim]
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
    categorias=(),
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
        categoria_service=FakeCategoriaService(list(categorias)),
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


def test_calendario_financeiro_fatura_com_fechamento_e_vencimento_em_meses_diferentes():
    """Caso realista mais comum (fechamento dia 25, vencimento dia 5 do mês
    seguinte) - nenhum teste pré-existente cobria fechamento/vencimento em
    MESES DIFERENTES, só o caso (mais raro) de ambos caindo no mesmo mês
    (`test_calendario_financeiro_fatura_gera_evento_de_fechamento_e_vencimento_quando_ambos_no_mes`).
    Bug relatado pelo usuário (2026-07-22): "vencimento de fatura não
    aparece" - este teste confirma que a condição `data_inicio <=
    fatura.data_vencimento <= data_fim` já trata os dois eventos de forma
    independente (não exige que ambos caiam no mesmo mês consultado)."""
    cartao = _Cartao(id=1, nome="Nubank")
    fatura = _Fatura(
        id=1, cartao_id=1, status_calculado=StatusFatura.FECHADA, valor_total_calculado=Decimal("400"),
        data_fechamento=date(2026, 1, 25), data_vencimento=date(2026, 2, 5),
    )
    service = _service(cartoes=[cartao], faturas_por_cartao={1: [fatura]})

    eventos_janeiro = service.calendario_financeiro(usuario_id=1, ano=2026, mes=1)["eventos"]
    assert len(eventos_janeiro) == 1
    assert eventos_janeiro[0]["categoria"] == CategoriaEventoCalendario.FATURA_FECHAMENTO
    assert eventos_janeiro[0]["data"] == date(2026, 1, 25)

    eventos_fevereiro = service.calendario_financeiro(usuario_id=1, ano=2026, mes=2)["eventos"]
    assert len(eventos_fevereiro) == 1
    assert eventos_fevereiro[0]["categoria"] == CategoriaEventoCalendario.FATURA_VENCIMENTO
    assert eventos_fevereiro[0]["data"] == date(2026, 2, 5)


def test_calendario_financeiro_fatura_vencimento_aparece_mesmo_com_3_faturas_mais_recentes():
    """Antes da correção de 2026-07-22, `calendario_financeiro` buscava com
    `listar_recentes(..., limit=3)` (as 3 faturas mais RECENTES por
    `mes_referencia`) - um cartão com 3+ faturas mais novas que a do mês
    consultado fazia o vencimento dela sumir do calendário (bug real
    relatado pelo usuário: "vencimento de fatura não aparece", reproduzível
    ao navegar para um mês passado, ou com faturas futuras já criadas).
    Trocado por `listar_no_periodo` (filtra direto pela janela de data, sem
    nenhum corte por quantidade) - este teste prova que o vencimento
    aparece mesmo havendo 3 faturas mais recentes que ela."""
    cartao = _Cartao(id=1, nome="Nubank")
    fatura_mais_recente_1 = _Fatura(
        id=2, cartao_id=1, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("100"),
        mes_referencia=date(2026, 4, 1), data_fechamento=date(2026, 4, 25), data_vencimento=date(2026, 5, 5),
    )
    fatura_mais_recente_2 = _Fatura(
        id=3, cartao_id=1, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("100"),
        mes_referencia=date(2026, 3, 1), data_fechamento=date(2026, 3, 25), data_vencimento=date(2026, 4, 5),
    )
    fatura_mais_recente_3 = _Fatura(
        id=4, cartao_id=1, status_calculado=StatusFatura.ABERTA, valor_total_calculado=Decimal("100"),
        mes_referencia=date(2026, 2, 1), data_fechamento=date(2026, 2, 25), data_vencimento=date(2026, 3, 5),
    )
    fatura_alvo = _Fatura(
        id=1, cartao_id=1, status_calculado=StatusFatura.FECHADA, valor_total_calculado=Decimal("400"),
        mes_referencia=date(2026, 1, 1), data_fechamento=date(2026, 1, 25), data_vencimento=date(2026, 2, 5),
    )
    service = _service(
        cartoes=[cartao],
        faturas_por_cartao={
            1: [fatura_mais_recente_1, fatura_mais_recente_2, fatura_mais_recente_3, fatura_alvo],
        },
    )

    eventos_fevereiro = service.calendario_financeiro(usuario_id=1, ano=2026, mes=2)["eventos"]
    categorias = {e["categoria"] for e in eventos_fevereiro}
    assert CategoriaEventoCalendario.FATURA_VENCIMENTO in categorias
    assert CategoriaEventoCalendario.FATURA_FECHAMENTO in categorias


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


# --- gráficos (docs/analise-arquitetural-graficos.md) ---------------------------

def test_graficos_tendencias_calcula_saldo_acumulado_e_fluxo_do_mes():
    conta = _Conta(id=1, saldo_atual=Decimal("1420"), saldo_inicial=Decimal("1000"))
    receita = _Transacao(
        id=1, valor=Decimal("500"), data=HOJE, descricao="Salário", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.RECEITA, conta_id=1,
    )
    despesa = _Transacao(
        id=2, valor=Decimal("80"), data=HOJE, descricao="Mercado", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.DESPESA, conta_id=1,
    )
    service = _service(contas=[conta], transacoes=[receita, despesa])

    resultado = service.graficos_tendencias(usuario_id=1, meses=3)["meses"]

    assert len(resultado) == 3
    # Os 2 meses anteriores não têm nenhum lançamento - saldo fica no
    # "ponto de partida" (saldo_inicial_total), entradas/saidas em zero.
    assert resultado[0]["saldo_total"] == Decimal("1000")
    assert resultado[0]["entradas"] == Decimal("0")
    assert resultado[1]["saldo_total"] == Decimal("1000")
    # Mês atual (último da lista): saldo acumulado reflete a receita/despesa
    # de hoje, entradas/saidas são só deste mês.
    assert resultado[2]["ano"] == HOJE.year
    assert resultado[2]["mes"] == HOJE.month
    assert resultado[2]["saldo_total"] == Decimal("1420")
    assert resultado[2]["entradas"] == Decimal("500")
    assert resultado[2]["saidas"] == Decimal("80")


def test_graficos_tendencias_compra_no_cartao_entra_em_saidas_mas_nao_no_saldo():
    """Diferente da Transacao de conta: compra no cartão (`conta_id=None`,
    `cartao_id` preenchido) não afeta o saldo da conta diretamente (só
    afetaria quando a fatura fosse PAGA, o que geraria outra Transacao com
    `conta_id` preenchido) - mas já entra em "saídas do mês", mesma
    semântica de `resumo_financeiro`/`visao_mensal` hoje."""
    conta = _Conta(id=1, saldo_atual=Decimal("1000"), saldo_inicial=Decimal("1000"))
    compra_cartao = _Transacao(
        id=1, valor=Decimal("200"), data=HOJE, descricao="Compra cartão", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.DESPESA, cartao_id=9, conta_id=None,
    )
    service = _service(contas=[conta], transacoes=[compra_cartao])

    resultado = service.graficos_tendencias(usuario_id=1, meses=1)["meses"][0]

    assert resultado["saldo_total"] == Decimal("1000")
    assert resultado["saidas"] == Decimal("200")


def test_graficos_tendencias_ignora_transacao_importada_no_saldo_mas_conta_em_entradas():
    """Mesma regra de `ContaRepository.somar_transacoes_pagas` (saldo real
    da conta): parcela `importada=True` (onboarding de Financiamento/
    Empréstimo pré-existente) não deduz/soma o saldo - mas continua
    contando em "entradas/saídas do mês" (mesmo comportamento de
    `resumo_financeiro` hoje, que nunca filtrou `importada`)."""
    conta = _Conta(id=1, saldo_atual=Decimal("1000"), saldo_inicial=Decimal("1000"))
    receita_importada = _Transacao(
        id=1, valor=Decimal("300"), data=HOJE, descricao="Parcela antiga", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.RECEITA, conta_id=1, importada=True,
    )
    service = _service(contas=[conta], transacoes=[receita_importada])

    resultado = service.graficos_tendencias(usuario_id=1, meses=1)["meses"][0]

    assert resultado["saldo_total"] == Decimal("1000")
    assert resultado["entradas"] == Decimal("300")


def test_graficos_tendencias_usuario_sem_historico_devolve_baseline_em_todos_os_meses():
    conta = _Conta(id=1, saldo_atual=Decimal("500"), saldo_inicial=Decimal("500"))
    service = _service(contas=[conta])

    resultado = service.graficos_tendencias(usuario_id=1, meses=6)["meses"]

    assert len(resultado) == 6
    assert all(ponto["saldo_total"] == Decimal("500") for ponto in resultado)
    assert all(ponto["entradas"] == Decimal("0") and ponto["saidas"] == Decimal("0") for ponto in resultado)


def test_graficos_periodo_agrupa_por_categoria_com_bucket_sem_categoria():
    categoria = _Categoria(id=1, nome="Mercado", cor="#FF0000", icone="shopping-cart")
    com_categoria = _Transacao(
        id=1, valor=Decimal("100"), data=HOJE, descricao="Compra", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.DESPESA, categoria_id=1,
    )
    sem_categoria = _Transacao(
        id=2, valor=Decimal("40"), data=HOJE, descricao="Avulsa", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.DESPESA, categoria_id=None,
    )
    service = _service(transacoes=[com_categoria, sem_categoria], categorias=[categoria])

    resultado = service.graficos_periodo(usuario_id=1, ano=HOJE.year, mes=HOJE.month)["gastos_por_categoria"]

    por_id = {item["categoria_id"]: item for item in resultado}
    assert por_id[1]["categoria_nome"] == "Mercado"
    assert por_id[1]["categoria_cor"] == "#FF0000"
    assert por_id[1]["total"] == Decimal("100")
    assert por_id[None]["categoria_nome"] == "Sem categoria"
    assert por_id[None]["total"] == Decimal("40")
    # Maior gasto primeiro.
    assert resultado[0]["categoria_id"] == 1


def test_graficos_periodo_agrupa_por_cartao():
    cartao_a = _Cartao(id=1, nome="Nubank")
    cartao_b = _Cartao(id=2, nome="Inter")
    compra_a = _Transacao(
        id=1, valor=Decimal("300"), data=HOJE, descricao="Compra A", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.DESPESA, cartao_id=1,
    )
    compra_b = _Transacao(
        id=2, valor=Decimal("150"), data=HOJE, descricao="Compra B", status=StatusTransacao.PAGO,
        tipo=TipoTransacao.DESPESA, cartao_id=2,
    )
    service = _service(cartoes=[cartao_a, cartao_b], transacoes=[compra_a, compra_b])

    resultado = service.graficos_periodo(usuario_id=1, ano=HOJE.year, mes=HOJE.month)["gastos_por_cartao"]

    assert len(resultado) == 2
    assert resultado[0] == {"cartao_id": 1, "cartao_nome": "Nubank", "total": Decimal("300")}
    assert resultado[1] == {"cartao_id": 2, "cartao_nome": "Inter", "total": Decimal("150")}


def test_graficos_periodo_sem_lancamentos_devolve_listas_vazias():
    resultado = _service().graficos_periodo(usuario_id=1)
    assert resultado["gastos_por_categoria"] == []
    assert resultado["gastos_por_cartao"] == []
