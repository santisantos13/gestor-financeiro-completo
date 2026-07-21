"""Testes unitários de FinanciamentoService - isolado com repositories e um
TransacaoService FALSOS (em memória, sem banco). Cobre exatamente o que é
próprio de FinanciamentoService (cronograma de amortização PRICE/SAC,
geração de parcelas + transação de entrada separada, pagamento de parcela
com atualização de saldo_devedor e transição para QUITADO, posse do
usuário) - a validação de posse/ativo de Conta, compatibilidade de
categoria etc. NÃO é reexercitada aqui: já está exaustivamente coberta em
test_transacao_service.py, e FinanciamentoService nunca duplica essa
lógica, apenas delega para TransacaoService (ver
docs/analise-arquitetural-financiamento.md).
"""
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import SistemaAmortizacao, StatusContratoCredito, StatusTransacao
from app.schemas.financiamento import FinanciamentoCreate
from app.services.financiamento_service import FinanciamentoService


class _TransacaoFalsa:
    def __init__(self, dados, usuario_id):
        self.id = None
        self.usuario_id = usuario_id
        self.tipo = dados.tipo
        self.valor = dados.valor
        self.data = dados.data
        self.descricao = dados.descricao
        self.categoria_id = dados.categoria_id
        self.conta_id = dados.conta_id
        self.cartao_id = dados.cartao_id
        self.financiamento_id = dados.financiamento_id
        self.numero_parcela = dados.numero_parcela
        self.status = StatusTransacao.PENDENTE


class FakeTransacaoRepository:
    """Compartilhado com FakeTransacaoService (mesma instância) - assim
    `FinanciamentoService._buscar_parcela` consegue localizar, via
    `transacao_repo.listar_do_usuario`, as parcelas que
    `transacao_service.criar` gerou."""

    def __init__(self):
        self._transacoes = {}
        self._proximo_id = 1

    def create(self, transacao):
        transacao.id = self._proximo_id
        self._proximo_id += 1
        self._transacoes[transacao.id] = transacao
        return transacao

    def get(self, id):
        return self._transacoes.get(id)

    def update(self, transacao):
        return transacao

    def listar_do_usuario(self, usuario_id, *, financiamento_id=None, limit=100, **_ignorado):
        resultado = [t for t in self._transacoes.values() if t.usuario_id == usuario_id]
        if financiamento_id is not None:
            resultado = [t for t in resultado if t.financiamento_id == financiamento_id]
        resultado.sort(key=lambda t: t.numero_parcela or 0)
        return resultado[:limit]


class FakeTransacaoService:
    """Substitui TransacaoService de verdade - FinanciamentoService nunca
    deveria precisar saber COMO uma transação é validada/criada (isso já é
    responsabilidade de TransacaoService, testada à exaustão em
    test_transacao_service.py). Aqui só registramos as chamadas, para
    confirmar que FinanciamentoService de fato DELEGA em vez de duplicar
    lógica. `marcar_parcela_de_contrato_paga` replica o essencial do
    comportamento real (idempotência, checagem de posse/contrato) para que
    os testes de `pagar_parcela` sejam significativos."""

    def __init__(self, transacao_repo):
        self.transacao_repo = transacao_repo
        self.chamadas_criar = []
        self.chamadas_marcar_paga = []

    def criar(self, dados, usuario_id):
        self.chamadas_criar.append((dados, usuario_id))
        return self.transacao_repo.create(_TransacaoFalsa(dados, usuario_id))

    def marcar_parcela_de_contrato_paga(self, transacao_id, usuario_id):
        self.chamadas_marcar_paga.append((transacao_id, usuario_id))
        transacao = self.transacao_repo.get(transacao_id)
        if transacao is None or transacao.usuario_id != usuario_id:
            raise NotFoundError("Transação não encontrada.")
        if transacao.financiamento_id is None:
            raise BusinessRuleError("Esta transação não pertence a um contrato de crédito.")
        if transacao.status == StatusTransacao.PAGO:
            raise BusinessRuleError("Esta parcela já está paga.")
        transacao.status = StatusTransacao.PAGO
        return self.transacao_repo.update(transacao)


class FakeFinanciamentoRepository:
    def __init__(self):
        self._financiamentos = {}
        self._proximo_id = 1

    def create(self, financiamento):
        financiamento.id = self._proximo_id
        self._proximo_id += 1
        self._financiamentos[financiamento.id] = financiamento
        return financiamento

    def get(self, id):
        return self._financiamentos.get(id)

    def update(self, financiamento):
        return financiamento

    def delete(self, financiamento):
        self._financiamentos.pop(financiamento.id, None)

    def listar_do_usuario(self, usuario_id, *, apenas_ativos=True, skip=0, limit=100):
        resultado = [f for f in self._financiamentos.values() if f.usuario_id == usuario_id]
        if apenas_ativos:
            resultado = [f for f in resultado if f.status != StatusContratoCredito.QUITADO]
        resultado.sort(key=lambda f: f.data_inicio, reverse=True)
        return resultado[skip : skip + limit]


@pytest.fixture()
def transacao_repo():
    return FakeTransacaoRepository()


@pytest.fixture()
def transacao_service(transacao_repo):
    return FakeTransacaoService(transacao_repo)


@pytest.fixture()
def financiamento_repo():
    return FakeFinanciamentoRepository()


@pytest.fixture()
def service(financiamento_repo, transacao_repo, transacao_service):
    return FinanciamentoService(financiamento_repo, transacao_repo, transacao_service)


def _criar(
    service,
    usuario_id=1,
    descricao="Apartamento",
    instituicao_financeira="Banco X",
    numero_contrato=None,
    valor_financiado=Decimal("100000.00"),
    valor_entrada=None,
    bem_financiado=None,
    taxa_juros=Decimal("0.0100"),
    sistema_amortizacao=SistemaAmortizacao.PRICE,
    num_parcelas=12,
    cet=None,
    data_inicio=date(2026, 7, 15),
    permite_quitacao_antecipada=True,
    conta_id=10,
    categoria_id=None,
    parcelas_ja_pagas=0,
):
    dados = FinanciamentoCreate(
        descricao=descricao,
        instituicao_financeira=instituicao_financeira,
        numero_contrato=numero_contrato,
        valor_financiado=valor_financiado,
        valor_entrada=valor_entrada,
        bem_financiado=bem_financiado,
        taxa_juros=taxa_juros,
        sistema_amortizacao=sistema_amortizacao,
        num_parcelas=num_parcelas,
        cet=cet,
        data_inicio=data_inicio,
        permite_quitacao_antecipada=permite_quitacao_antecipada,
        conta_id=conta_id,
        categoria_id=categoria_id,
        parcelas_ja_pagas=parcelas_ja_pagas,
    )
    return service.criar(dados, usuario_id)


# --- criar: validações estruturais ------------------------------------------

def test_criar_sem_conta_id_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None)


def test_criar_sem_conta_id_nao_gera_nenhuma_parcela(service, transacao_service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None)
    assert transacao_service.chamadas_criar == []


def test_criar_com_entrada_maior_ou_igual_ao_valor_financiado_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, valor_financiado=Decimal("1000.00"), valor_entrada=Decimal("1000.00"))
    with pytest.raises(BusinessRuleError):
        _criar(service, valor_financiado=Decimal("1000.00"), valor_entrada=Decimal("1500.00"))


# --- criar: estado inicial do contrato ---------------------------------------

def test_criar_status_inicial_e_ativo(service):
    financiamento = _criar(service)
    assert financiamento.status == StatusContratoCredito.ATIVO


def test_criar_saldo_devedor_inicial_igual_ao_valor_financiado_sem_entrada(service):
    financiamento = _criar(service, valor_financiado=Decimal("50000.00"), valor_entrada=None, num_parcelas=10)
    assert financiamento.saldo_devedor == Decimal("50000.00")


def test_criar_saldo_devedor_inicial_desconta_a_entrada(service):
    financiamento = _criar(
        service, valor_financiado=Decimal("50000.00"), valor_entrada=Decimal("10000.00"), num_parcelas=10
    )
    assert financiamento.saldo_devedor == Decimal("40000.00")


# --- criar: parcelas_ja_pagas (Etapa de Onboarding) --------------------------

def test_criar_com_parcelas_ja_pagas_decrementa_saldo_devedor(service):
    # contrato que já estava na metade quando o usuário passou a usar o
    # app - importa direto na criação em vez de exigir 3 chamadas manuais
    # de pagar_parcela logo em seguida.
    financiamento = _criar(
        service, valor_financiado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3, parcelas_ja_pagas=1
    )
    assert financiamento.saldo_devedor == Decimal("200.00")


def test_criar_com_parcelas_ja_pagas_marca_as_transacoes_correspondentes_como_pagas(
    service, transacao_repo
):
    financiamento = _criar(
        service, valor_financiado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3, parcelas_ja_pagas=2
    )
    parcelas = transacao_repo.listar_do_usuario(1, financiamento_id=financiamento.id)
    pagas = {p.numero_parcela for p in parcelas if p.status == StatusTransacao.PAGO}
    assert pagas == {1, 2}


def test_criar_com_parcelas_ja_pagas_igual_ao_total_quita_o_contrato_na_hora(service):
    financiamento = _criar(
        service, valor_financiado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3, parcelas_ja_pagas=3
    )
    assert financiamento.saldo_devedor == Decimal("0.00")
    assert financiamento.status == StatusContratoCredito.QUITADO


def test_criar_com_parcelas_ja_pagas_zero_e_o_comportamento_padrao(service):
    financiamento = _criar(service, valor_financiado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3)
    assert financiamento.saldo_devedor == Decimal("300.00")
    assert financiamento.status == StatusContratoCredito.ATIVO


def test_criar_com_parcelas_ja_pagas_maior_que_num_parcelas_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, num_parcelas=3, parcelas_ja_pagas=4)


def test_criar_com_parcelas_ja_pagas_invalido_nao_gera_nenhuma_parcela(service, transacao_service):
    with pytest.raises(BusinessRuleError):
        _criar(service, num_parcelas=3, parcelas_ja_pagas=4)
    assert transacao_service.chamadas_criar == []


# --- criar: transação de entrada separada ------------------------------------

def test_criar_sem_entrada_nao_gera_transacao_de_entrada(service, transacao_service):
    _criar(service, valor_entrada=None, num_parcelas=5)
    # so as 5 parcelas, nenhuma transacao extra
    assert len(transacao_service.chamadas_criar) == 5


def test_criar_com_entrada_gera_uma_transacao_extra_avulsa(service, transacao_service):
    _criar(service, valor_entrada=Decimal("5000.00"), num_parcelas=5)
    assert len(transacao_service.chamadas_criar) == 6  # 1 entrada + 5 parcelas

    dados_entrada, _usuario_id = transacao_service.chamadas_criar[0]
    assert dados_entrada.valor == Decimal("5000.00")
    assert dados_entrada.financiamento_id is None
    assert dados_entrada.numero_parcela is None
    assert "Entrada" in dados_entrada.descricao


def test_criar_entrada_usa_a_mesma_conta_e_categoria_do_contrato(service, transacao_service):
    _criar(service, valor_entrada=Decimal("5000.00"), conta_id=42, categoria_id=7, num_parcelas=3)
    dados_entrada, _ = transacao_service.chamadas_criar[0]
    assert dados_entrada.conta_id == 42
    assert dados_entrada.categoria_id == 7


# --- criar: geração de parcelas via TransacaoService -------------------------

def test_criar_gera_uma_transacao_por_parcela(service, transacao_service):
    _criar(service, num_parcelas=12)
    assert len(transacao_service.chamadas_criar) == 12


def test_criar_numera_parcelas_de_1_ate_num_parcelas_em_ordem(service, transacao_service):
    _criar(service, num_parcelas=4)
    numeros = [dados.numero_parcela for dados, _ in transacao_service.chamadas_criar]
    assert numeros == [1, 2, 3, 4]


def test_criar_parcelas_sao_despesas_vinculadas_ao_financiamento(service, transacao_service):
    from app.models.enums import TipoTransacao

    financiamento = _criar(service, num_parcelas=3)
    for dados, usuario_id in transacao_service.chamadas_criar:
        assert dados.tipo == TipoTransacao.DESPESA
        assert dados.financiamento_id == financiamento.id
        assert usuario_id == 1


def test_criar_repassa_conta_e_categoria_para_cada_parcela(service, transacao_service):
    _criar(service, conta_id=99, categoria_id=3, num_parcelas=3)
    for dados, _ in transacao_service.chamadas_criar:
        assert dados.conta_id == 99
        assert dados.categoria_id == 3


def test_criar_primeira_parcela_usa_a_propria_data_inicio(service, transacao_service):
    _criar(service, data_inicio=date(2026, 7, 15), num_parcelas=2)
    primeira_data = transacao_service.chamadas_criar[0][0].data
    assert primeira_data == date(2026, 7, 15)


def test_criar_parcelas_seguintes_somam_um_mes_por_vez(service, transacao_service):
    _criar(service, data_inicio=date(2026, 7, 15), num_parcelas=3)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 7, 15), date(2026, 8, 15), date(2026, 9, 15)]


def test_criar_datas_fazem_clamping_de_dia_em_mes_mais_curto(service, transacao_service):
    _criar(service, data_inicio=date(2027, 1, 31), num_parcelas=2)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2027, 1, 31), date(2027, 2, 28)]


# --- cronograma PRICE: invariantes matemáticas -------------------------------

def test_cronograma_price_sem_juros_degenera_em_divisao_simples():
    cronograma = FinanciamentoService._gerar_cronograma(
        Decimal("300.00"), Decimal("0"), 3, SistemaAmortizacao.PRICE
    )
    assert cronograma == [
        (Decimal("100.00"), Decimal("100.00")),
        (Decimal("100.00"), Decimal("100.00")),
        (Decimal("100.00"), Decimal("100.00")),
    ]


def test_cronograma_price_soma_das_amortizacoes_fecha_exatamente_o_principal():
    cronograma = FinanciamentoService._gerar_cronograma(
        Decimal("100000.00"), Decimal("0.0150"), 24, SistemaAmortizacao.PRICE
    )
    soma_amortizacoes = sum(amortizacao for _valor, amortizacao in cronograma)
    assert soma_amortizacoes == Decimal("100000.00")


def test_cronograma_price_parcelas_sao_fixas_exceto_possivelmente_a_ultima():
    cronograma = FinanciamentoService._gerar_cronograma(
        Decimal("100000.00"), Decimal("0.0150"), 24, SistemaAmortizacao.PRICE
    )
    valores = [valor for valor, _amortizacao in cronograma]
    # todas as parcelas, exceto a ultima, sao identicas (parcela fixa)
    assert len(set(valores[:-1])) == 1


def test_cronograma_price_juros_da_primeira_parcela_bate_com_taxa_sobre_o_principal():
    principal = Decimal("100000.00")
    taxa = Decimal("0.0150")
    cronograma = FinanciamentoService._gerar_cronograma(principal, taxa, 24, SistemaAmortizacao.PRICE)
    valor_primeira, amortizacao_primeira = cronograma[0]
    juros_primeira = valor_primeira - amortizacao_primeira
    assert juros_primeira == (principal * taxa).quantize(Decimal("0.01"))


# --- cronograma SAC: invariantes matemáticas ---------------------------------

def test_cronograma_sac_soma_das_amortizacoes_fecha_exatamente_o_principal():
    cronograma = FinanciamentoService._gerar_cronograma(
        Decimal("100000.00"), Decimal("0.0150"), 24, SistemaAmortizacao.SAC
    )
    soma_amortizacoes = sum(amortizacao for _valor, amortizacao in cronograma)
    assert soma_amortizacoes == Decimal("100000.00")


def test_cronograma_sac_amortizacao_constante_exceto_possivelmente_a_ultima():
    cronograma = FinanciamentoService._gerar_cronograma(
        Decimal("100000.00"), Decimal("0.0150"), 24, SistemaAmortizacao.SAC
    )
    amortizacoes = [amortizacao for _valor, amortizacao in cronograma]
    assert len(set(amortizacoes[:-1])) == 1


def test_cronograma_sac_parcelas_sao_estritamente_decrescentes():
    cronograma = FinanciamentoService._gerar_cronograma(
        Decimal("100000.00"), Decimal("0.0150"), 24, SistemaAmortizacao.SAC
    )
    valores = [valor for valor, _amortizacao in cronograma]
    assert all(valores[i] > valores[i + 1] for i in range(len(valores) - 1))


def test_cronograma_sac_e_price_tem_mesmo_valor_total_de_juros_diferente():
    # SAC paga MENOS juros no total que PRICE, para o mesmo contrato -
    # propriedade financeira conhecida (SAC amortiza mais rapido no
    # inicio). Serve de regressao para nao inverter as duas formulas.
    principal = Decimal("100000.00")
    taxa = Decimal("0.0150")
    cronograma_price = FinanciamentoService._gerar_cronograma(principal, taxa, 24, SistemaAmortizacao.PRICE)
    cronograma_sac = FinanciamentoService._gerar_cronograma(principal, taxa, 24, SistemaAmortizacao.SAC)
    total_price = sum(valor for valor, _ in cronograma_price)
    total_sac = sum(valor for valor, _ in cronograma_sac)
    assert total_sac < total_price


# --- obter / listar -----------------------------------------------------------

def test_obter_financiamento_proprio(service):
    financiamento = _criar(service)
    assert service.obter(financiamento.id, usuario_id=1).id == financiamento.id


def test_obter_financiamento_de_outro_usuario_levanta_not_found(service):
    financiamento = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(financiamento.id, usuario_id=2)


def test_obter_financiamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_financiamentos_do_usuario(service):
    _criar(service, usuario_id=1, descricao="Meu", num_parcelas=2)
    _criar(service, usuario_id=2, descricao="Do outro", num_parcelas=2)
    resultado = service.listar(usuario_id=1)
    assert [f.descricao for f in resultado] == ["Meu"]


def test_listar_por_padrao_oculta_financiamentos_quitados(service):
    financiamento = _criar(service, usuario_id=1, num_parcelas=2, taxa_juros=Decimal("0"))
    service.pagar_parcela(financiamento.id, 1, usuario_id=1)
    service.pagar_parcela(financiamento.id, 2, usuario_id=1)
    assert service.listar(usuario_id=1) == []
    assert service.listar(usuario_id=1, apenas_ativos=False) == [financiamento]


# --- excluir -----------------------------------------------------------------

def test_excluir_financiamento_proprio_remove_do_repositorio(service, financiamento_repo):
    financiamento = _criar(service, usuario_id=1, num_parcelas=2)
    service.excluir(financiamento.id, usuario_id=1)
    assert financiamento_repo.get(financiamento.id) is None


def test_excluir_financiamento_com_parcela_paga_e_permitido(service, financiamento_repo):
    """Decisão do usuário ao investigar esta tarefa: exclusão sempre
    permitida, mesmo com parcelas já pagas (a Transacao só perde o vínculo
    no banco real, via ondelete=SET NULL - aqui, com repository falso, só
    confirmamos que o Service não bloqueia a operação)."""
    financiamento = _criar(service, usuario_id=1, num_parcelas=2, taxa_juros=Decimal("0"))
    service.pagar_parcela(financiamento.id, 1, usuario_id=1)
    service.excluir(financiamento.id, usuario_id=1)
    assert financiamento_repo.get(financiamento.id) is None


def test_excluir_financiamento_de_outro_usuario_levanta_not_found(service):
    financiamento = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(financiamento.id, usuario_id=2)


def test_excluir_financiamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.excluir(999, usuario_id=1)


# --- pagar_parcela: validação estrutural -------------------------------------

def test_pagar_parcela_com_numero_fora_da_faixa_levanta_business_rule_error(service):
    financiamento = _criar(service, num_parcelas=5)
    with pytest.raises(BusinessRuleError):
        service.pagar_parcela(financiamento.id, 0, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.pagar_parcela(financiamento.id, 6, usuario_id=1)


def test_pagar_parcela_de_financiamento_de_outro_usuario_levanta_not_found(service):
    financiamento = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.pagar_parcela(financiamento.id, 1, usuario_id=2)


def test_pagar_parcela_de_financiamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.pagar_parcela(999, 1, usuario_id=1)


# --- pagar_parcela: delegação para TransacaoService --------------------------

def test_pagar_parcela_chama_marcar_parcela_de_contrato_paga(service, transacao_service, transacao_repo):
    financiamento = _criar(service, num_parcelas=3)
    parcelas = transacao_repo.listar_do_usuario(1, financiamento_id=financiamento.id)
    parcela_2 = next(p for p in parcelas if p.numero_parcela == 2)

    service.pagar_parcela(financiamento.id, 2, usuario_id=1)

    assert transacao_service.chamadas_marcar_paga == [(parcela_2.id, 1)]
    assert parcela_2.status == StatusTransacao.PAGO


def test_pagar_a_mesma_parcela_duas_vezes_levanta_business_rule_error(service):
    financiamento = _criar(service, num_parcelas=3)
    service.pagar_parcela(financiamento.id, 1, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.pagar_parcela(financiamento.id, 1, usuario_id=1)


# --- pagar_parcela: saldo_devedor e transição para QUITADO -------------------

def test_pagar_parcela_decrementa_saldo_devedor_pela_amortizacao(service):
    financiamento = _criar(
        service, valor_financiado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3
    )
    assert financiamento.saldo_devedor == Decimal("300.00")

    service.pagar_parcela(financiamento.id, 1, usuario_id=1)
    assert financiamento.saldo_devedor == Decimal("200.00")

    service.pagar_parcela(financiamento.id, 2, usuario_id=1)
    assert financiamento.saldo_devedor == Decimal("100.00")


def test_pagar_ultima_parcela_zera_saldo_devedor_e_quita_o_contrato(service):
    financiamento = _criar(
        service, valor_financiado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3
    )
    service.pagar_parcela(financiamento.id, 1, usuario_id=1)
    service.pagar_parcela(financiamento.id, 2, usuario_id=1)
    assert financiamento.status == StatusContratoCredito.ATIVO

    service.pagar_parcela(financiamento.id, 3, usuario_id=1)
    assert financiamento.saldo_devedor == Decimal("0.00")
    assert financiamento.status == StatusContratoCredito.QUITADO


def test_pagar_parcelas_fora_de_ordem_ainda_fecha_saldo_devedor_em_zero(service):
    # o cronograma e determinado pelas condicoes do contrato (imutaveis),
    # nao pela ordem real de pagamento - pagar fora de ordem nao quebra a
    # matematica, so demonstra que amortizacao_k independe de quando a
    # parcela k e efetivamente paga.
    financiamento = _criar(
        service, valor_financiado=Decimal("100000.00"), taxa_juros=Decimal("0.0150"), num_parcelas=6
    )
    for numero_parcela in [3, 1, 6, 2, 5, 4]:
        financiamento = service.pagar_parcela(financiamento.id, numero_parcela, usuario_id=1)

    assert financiamento.saldo_devedor == Decimal("0.00")
    assert financiamento.status == StatusContratoCredito.QUITADO
