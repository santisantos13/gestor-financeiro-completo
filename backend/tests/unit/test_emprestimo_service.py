"""Testes unitários de EmprestimoService - isolado com repositories e um
TransacaoService FALSOS (em memória, sem banco). Cobre exatamente o que é
próprio de EmprestimoService (geração do desembolso como Transacao de
RECEITA sempre obrigatória, geração de parcelas via cronograma PRICE/SAC
compartilhado com Financiamento em app/core/amortizacao.py, pagamento de
parcela com atualização de saldo_devedor e transição para QUITADO, posse
do usuário) - a validação de posse/ativo de Conta, compatibilidade de
categoria etc. NÃO é reexercitada aqui: já está exaustivamente coberta em
test_transacao_service.py, e EmprestimoService nunca duplica essa lógica,
apenas delega para TransacaoService. As invariantes matemáticas do
cronograma PRICE/SAC (soma das amortizações, parcela fixa/decrescente,
etc.) já são exaustivamente testadas em test_financiamento_service.py
contra a mesma função compartilhada `app.core.amortizacao.gerar_cronograma`
- não duplicadas aqui. Ver docs/analise-arquitetural-emprestimo.md.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import SistemaAmortizacao, StatusContratoCredito, StatusTransacao, TipoTransacao
from app.schemas.emprestimo import EmprestimoCreate
from app.services.emprestimo_service import EmprestimoService


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
        self.emprestimo_id = dados.emprestimo_id
        self.numero_parcela = dados.numero_parcela
        self.status = StatusTransacao.PENDENTE


class FakeTransacaoRepository:
    """Compartilhado com FakeTransacaoService (mesma instância) - assim
    `EmprestimoService._buscar_parcela` consegue localizar, via
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

    def listar_do_usuario(self, usuario_id, *, emprestimo_id=None, limit=100, **_ignorado):
        resultado = [t for t in self._transacoes.values() if t.usuario_id == usuario_id]
        if emprestimo_id is not None:
            resultado = [t for t in resultado if t.emprestimo_id == emprestimo_id]
        resultado.sort(key=lambda t: t.numero_parcela or 0)
        return resultado[:limit]


class FakeTransacaoService:
    """Substitui TransacaoService de verdade - EmprestimoService nunca
    deveria precisar saber COMO uma transação é validada/criada. Aqui só
    registramos as chamadas, para confirmar que EmprestimoService de fato
    DELEGA em vez de duplicar lógica. `marcar_parcela_de_contrato_paga`
    replica o essencial do comportamento real (idempotência, checagem de
    posse/contrato) para que os testes de `pagar_parcela` sejam
    significativos."""

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
        if transacao.emprestimo_id is None:
            raise BusinessRuleError("Esta transação não pertence a um contrato de crédito.")
        if transacao.status == StatusTransacao.PAGO:
            raise BusinessRuleError("Esta parcela já está paga.")
        transacao.status = StatusTransacao.PAGO
        return self.transacao_repo.update(transacao)


class FakeEmprestimoRepository:
    def __init__(self):
        self._emprestimos = {}
        self._proximo_id = 1

    def create(self, emprestimo):
        emprestimo.id = self._proximo_id
        self._proximo_id += 1
        self._emprestimos[emprestimo.id] = emprestimo
        return emprestimo

    def get(self, id):
        return self._emprestimos.get(id)

    def update(self, emprestimo):
        return emprestimo

    def delete(self, emprestimo):
        self._emprestimos.pop(emprestimo.id, None)

    def listar_do_usuario(self, usuario_id, *, apenas_ativos=True, skip=0, limit=100):
        resultado = [e for e in self._emprestimos.values() if e.usuario_id == usuario_id]
        if apenas_ativos:
            resultado = [e for e in resultado if e.status != StatusContratoCredito.QUITADO]
        resultado.sort(key=lambda e: e.data_inicio, reverse=True)
        return resultado[skip : skip + limit]


@pytest.fixture()
def transacao_repo():
    return FakeTransacaoRepository()


@pytest.fixture()
def transacao_service(transacao_repo):
    return FakeTransacaoService(transacao_repo)


@pytest.fixture()
def emprestimo_repo():
    return FakeEmprestimoRepository()


@pytest.fixture()
def service(emprestimo_repo, transacao_repo, transacao_service):
    return EmprestimoService(emprestimo_repo, transacao_repo, transacao_service)


def _criar(
    service,
    usuario_id=1,
    descricao="Empréstimo pessoal",
    instituicao_financeira="Banco X",
    numero_contrato=None,
    valor_liberado=Decimal("10000.00"),
    finalidade=None,
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
    dados = EmprestimoCreate(
        descricao=descricao,
        instituicao_financeira=instituicao_financeira,
        numero_contrato=numero_contrato,
        valor_liberado=valor_liberado,
        finalidade=finalidade,
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


def test_criar_sem_conta_id_nao_gera_nenhuma_transacao(service, transacao_service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None)
    assert transacao_service.chamadas_criar == []


# --- criar: estado inicial do contrato ---------------------------------------

def test_criar_status_inicial_e_ativo(service):
    emprestimo = _criar(service)
    assert emprestimo.status == StatusContratoCredito.ATIVO


def test_criar_saldo_devedor_inicial_igual_ao_valor_liberado(service):
    # diferente de Financiamento: nao existe "entrada" a descontar - o
    # valor inteiro liberado e o principal a ser amortizado.
    emprestimo = _criar(service, valor_liberado=Decimal("50000.00"), num_parcelas=10)
    assert emprestimo.saldo_devedor == Decimal("50000.00")


# --- criar: parcelas_ja_pagas (Etapa de Onboarding) --------------------------

def test_criar_com_parcelas_ja_pagas_decrementa_saldo_devedor(service):
    emprestimo = _criar(
        service, valor_liberado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3, parcelas_ja_pagas=1
    )
    assert emprestimo.saldo_devedor == Decimal("200.00")


def test_criar_com_parcelas_ja_pagas_marca_as_transacoes_correspondentes_como_pagas(
    service, transacao_repo
):
    emprestimo = _criar(
        service, valor_liberado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3, parcelas_ja_pagas=2
    )
    parcelas = transacao_repo.listar_do_usuario(1, emprestimo_id=emprestimo.id)
    pagas = {p.numero_parcela for p in parcelas if p.status == StatusTransacao.PAGO}
    assert pagas == {1, 2}


def test_criar_com_parcelas_ja_pagas_igual_ao_total_quita_o_contrato_na_hora(service):
    emprestimo = _criar(
        service, valor_liberado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3, parcelas_ja_pagas=3
    )
    assert emprestimo.saldo_devedor == Decimal("0.00")
    assert emprestimo.status == StatusContratoCredito.QUITADO


def test_criar_com_parcelas_ja_pagas_maior_que_num_parcelas_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, num_parcelas=3, parcelas_ja_pagas=4)


# --- criar: transação de desembolso (sempre gerada, tipo RECEITA) -----------

def test_criar_sempre_gera_transacao_de_desembolso(service, transacao_service):
    _criar(service, num_parcelas=5)
    # 1 desembolso + 5 parcelas
    assert len(transacao_service.chamadas_criar) == 6


def test_criar_desembolso_e_do_tipo_receita_avulso_sem_vinculo_ao_contrato(service, transacao_service):
    _criar(service, valor_liberado=Decimal("8000.00"), num_parcelas=5)
    dados_desembolso, _usuario_id = transacao_service.chamadas_criar[0]
    assert dados_desembolso.tipo == TipoTransacao.RECEITA
    assert dados_desembolso.valor == Decimal("8000.00")
    assert dados_desembolso.emprestimo_id is None
    assert dados_desembolso.numero_parcela is None
    assert "Desembolso" in dados_desembolso.descricao


def test_criar_desembolso_usa_a_mesma_conta_e_categoria_do_contrato(service, transacao_service):
    _criar(service, conta_id=42, categoria_id=7, num_parcelas=3)
    dados_desembolso, _ = transacao_service.chamadas_criar[0]
    assert dados_desembolso.conta_id == 42
    assert dados_desembolso.categoria_id == 7


# --- criar: geração de parcelas via TransacaoService -------------------------

def test_criar_gera_uma_transacao_de_desembolso_mais_uma_por_parcela(service, transacao_service):
    _criar(service, num_parcelas=12)
    assert len(transacao_service.chamadas_criar) == 13  # 1 desembolso + 12 parcelas


def test_criar_numera_parcelas_de_1_ate_num_parcelas_em_ordem(service, transacao_service):
    _criar(service, num_parcelas=4)
    # ignora a primeira chamada (desembolso, numero_parcela=None)
    numeros = [dados.numero_parcela for dados, _ in transacao_service.chamadas_criar[1:]]
    assert numeros == [1, 2, 3, 4]


def test_criar_parcelas_sao_despesas_vinculadas_ao_emprestimo(service, transacao_service):
    emprestimo = _criar(service, num_parcelas=3)
    for dados, usuario_id in transacao_service.chamadas_criar[1:]:
        assert dados.tipo == TipoTransacao.DESPESA
        assert dados.emprestimo_id == emprestimo.id
        assert usuario_id == 1


def test_criar_repassa_conta_e_categoria_para_cada_parcela(service, transacao_service):
    _criar(service, conta_id=99, categoria_id=3, num_parcelas=3)
    for dados, _ in transacao_service.chamadas_criar[1:]:
        assert dados.conta_id == 99
        assert dados.categoria_id == 3


def test_criar_primeira_parcela_usa_a_propria_data_inicio(service, transacao_service):
    _criar(service, data_inicio=date(2026, 7, 15), num_parcelas=2)
    primeira_parcela_data = transacao_service.chamadas_criar[1][0].data
    assert primeira_parcela_data == date(2026, 7, 15)


def test_criar_parcelas_seguintes_somam_um_mes_por_vez(service, transacao_service):
    _criar(service, data_inicio=date(2026, 7, 15), num_parcelas=3)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar[1:]]
    assert datas == [date(2026, 7, 15), date(2026, 8, 15), date(2026, 9, 15)]


def test_criar_datas_fazem_clamping_de_dia_em_mes_mais_curto(service, transacao_service):
    _criar(service, data_inicio=date(2027, 1, 31), num_parcelas=2)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar[1:]]
    assert datas == [date(2027, 1, 31), date(2027, 2, 28)]


# --- criar: cronograma PRICE/SAC compartilhado (checagem leve) --------------

def test_criar_price_gera_parcelas_de_valor_fixo_exceto_a_ultima(service, transacao_service):
    _criar(service, valor_liberado=Decimal("100000.00"), taxa_juros=Decimal("0.0150"),
           sistema_amortizacao=SistemaAmortizacao.PRICE, num_parcelas=12)
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar[1:]]
    assert len(set(valores[:-1])) == 1


def test_criar_sac_gera_parcelas_decrescentes(service, transacao_service):
    _criar(service, valor_liberado=Decimal("100000.00"), taxa_juros=Decimal("0.0150"),
           sistema_amortizacao=SistemaAmortizacao.SAC, num_parcelas=12)
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar[1:]]
    assert all(valores[i] > valores[i + 1] for i in range(len(valores) - 1))


# --- obter / listar -----------------------------------------------------------

def test_obter_emprestimo_proprio(service):
    emprestimo = _criar(service)
    assert service.obter(emprestimo.id, usuario_id=1).id == emprestimo.id


def test_obter_emprestimo_de_outro_usuario_levanta_not_found(service):
    emprestimo = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(emprestimo.id, usuario_id=2)


def test_obter_emprestimo_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_emprestimos_do_usuario(service):
    _criar(service, usuario_id=1, descricao="Meu", num_parcelas=2)
    _criar(service, usuario_id=2, descricao="Do outro", num_parcelas=2)
    resultado = service.listar(usuario_id=1)
    assert [e.descricao for e in resultado] == ["Meu"]


def test_listar_por_padrao_oculta_emprestimos_quitados(service):
    emprestimo = _criar(service, usuario_id=1, num_parcelas=2, taxa_juros=Decimal("0"))
    service.pagar_parcela(emprestimo.id, 1, usuario_id=1)
    service.pagar_parcela(emprestimo.id, 2, usuario_id=1)
    assert service.listar(usuario_id=1) == []
    assert service.listar(usuario_id=1, apenas_ativos=False) == [emprestimo]


# --- excluir -----------------------------------------------------------------

def test_excluir_emprestimo_proprio_remove_do_repositorio(service, emprestimo_repo):
    emprestimo = _criar(service, usuario_id=1, num_parcelas=2)
    service.excluir(emprestimo.id, usuario_id=1)
    assert emprestimo_repo.get(emprestimo.id) is None


def test_excluir_emprestimo_com_parcela_paga_e_permitido(service, emprestimo_repo):
    emprestimo = _criar(service, usuario_id=1, num_parcelas=2, taxa_juros=Decimal("0"))
    service.pagar_parcela(emprestimo.id, 1, usuario_id=1)
    service.excluir(emprestimo.id, usuario_id=1)
    assert emprestimo_repo.get(emprestimo.id) is None


def test_excluir_emprestimo_de_outro_usuario_levanta_not_found(service):
    emprestimo = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(emprestimo.id, usuario_id=2)


def test_excluir_emprestimo_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.excluir(999, usuario_id=1)


# --- pagar_parcela: validação estrutural -------------------------------------

def test_pagar_parcela_com_numero_fora_da_faixa_levanta_business_rule_error(service):
    emprestimo = _criar(service, num_parcelas=5)
    with pytest.raises(BusinessRuleError):
        service.pagar_parcela(emprestimo.id, 0, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.pagar_parcela(emprestimo.id, 6, usuario_id=1)


def test_pagar_parcela_de_emprestimo_de_outro_usuario_levanta_not_found(service):
    emprestimo = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.pagar_parcela(emprestimo.id, 1, usuario_id=2)


def test_pagar_parcela_de_emprestimo_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.pagar_parcela(999, 1, usuario_id=1)


# --- pagar_parcela: delegação para TransacaoService --------------------------

def test_pagar_parcela_chama_marcar_parcela_de_contrato_paga(service, transacao_service, transacao_repo):
    emprestimo = _criar(service, num_parcelas=3)
    parcelas = transacao_repo.listar_do_usuario(1, emprestimo_id=emprestimo.id)
    parcela_2 = next(p for p in parcelas if p.numero_parcela == 2)

    service.pagar_parcela(emprestimo.id, 2, usuario_id=1)

    assert transacao_service.chamadas_marcar_paga == [(parcela_2.id, 1)]
    assert parcela_2.status == StatusTransacao.PAGO


def test_pagar_a_mesma_parcela_duas_vezes_levanta_business_rule_error(service):
    emprestimo = _criar(service, num_parcelas=3)
    service.pagar_parcela(emprestimo.id, 1, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.pagar_parcela(emprestimo.id, 1, usuario_id=1)


# --- pagar_parcela: saldo_devedor e transição para QUITADO -------------------

def test_pagar_parcela_decrementa_saldo_devedor_pela_amortizacao(service):
    emprestimo = _criar(
        service, valor_liberado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3
    )
    assert emprestimo.saldo_devedor == Decimal("300.00")

    service.pagar_parcela(emprestimo.id, 1, usuario_id=1)
    assert emprestimo.saldo_devedor == Decimal("200.00")

    service.pagar_parcela(emprestimo.id, 2, usuario_id=1)
    assert emprestimo.saldo_devedor == Decimal("100.00")


def test_pagar_ultima_parcela_zera_saldo_devedor_e_quita_o_contrato(service):
    emprestimo = _criar(
        service, valor_liberado=Decimal("300.00"), taxa_juros=Decimal("0"), num_parcelas=3
    )
    service.pagar_parcela(emprestimo.id, 1, usuario_id=1)
    service.pagar_parcela(emprestimo.id, 2, usuario_id=1)
    assert emprestimo.status == StatusContratoCredito.ATIVO

    service.pagar_parcela(emprestimo.id, 3, usuario_id=1)
    assert emprestimo.saldo_devedor == Decimal("0.00")
    assert emprestimo.status == StatusContratoCredito.QUITADO


def test_pagar_parcelas_fora_de_ordem_ainda_fecha_saldo_devedor_em_zero(service):
    emprestimo = _criar(
        service, valor_liberado=Decimal("100000.00"), taxa_juros=Decimal("0.0150"), num_parcelas=6
    )
    for numero_parcela in [3, 1, 6, 2, 5, 4]:
        emprestimo = service.pagar_parcela(emprestimo.id, numero_parcela, usuario_id=1)

    assert emprestimo.saldo_devedor == Decimal("0.00")
    assert emprestimo.status == StatusContratoCredito.QUITADO
