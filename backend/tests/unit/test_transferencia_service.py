"""Testes unitários de TransferenciaService - isolado com repositories
FALSOS (em memória, sem banco). Cobre validação estrutural (origem !=
destino - mesma família do CheckConstraint do model), posse cruzada das
duas Contas envolvidas (origem e destino precisam ser do mesmo usuário e
estar ativas) e o cancelamento (soft delete via `ativo`, preservando
histórico). Transferencia NUNCA fala com Transacao/TransacaoRepository -
decisão explícita reafirmada nesta etapa, ver
docs/revisao-tecnica-transferencia.md.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.schemas.transferencia import TransferenciaCreate
from app.services.transferencia_service import TransferenciaService


class FakeTransferenciaRepository:
    def __init__(self):
        self._transferencias = {}
        self._proximo_id = 1

    def get(self, id):
        return self._transferencias.get(id)

    def create(self, transferencia):
        transferencia.id = self._proximo_id
        self._proximo_id += 1
        self._transferencias[transferencia.id] = transferencia
        return transferencia

    def update(self, transferencia):
        return transferencia

    def delete(self, transferencia):
        self._transferencias.pop(transferencia.id, None)

    def listar_do_usuario(
        self, usuario_id, *, apenas_ativas=True, conta_id=None, data_inicio=None, data_fim=None, skip=0, limit=100
    ):
        resultado = [
            t
            for t in self._transferencias.values()
            if t.usuario_id == usuario_id
            and (not apenas_ativas or t.ativo)
            and (conta_id is None or conta_id in (t.conta_origem_id, t.conta_destino_id))
            and (data_inicio is None or t.data >= data_inicio)
            and (data_fim is None or t.data <= data_fim)
        ]
        resultado.sort(key=lambda t: (t.data, t.id), reverse=True)
        return resultado[skip : skip + limit]


class _ContaFalsa:
    def __init__(self, id, usuario_id, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.ativo = ativo


class FakeContaRepository:
    def __init__(self):
        self._contas = {}

    def adicionar(self, conta_id, usuario_id, ativo=True):
        self._contas[conta_id] = _ContaFalsa(conta_id, usuario_id, ativo)

    def get(self, id):
        return self._contas.get(id)


@pytest.fixture()
def transferencia_repo():
    return FakeTransferenciaRepository()


@pytest.fixture()
def conta_repo():
    repo = FakeContaRepository()
    repo.adicionar(conta_id=100, usuario_id=1)  # origem valida
    repo.adicionar(conta_id=200, usuario_id=1)  # destino valida
    repo.adicionar(conta_id=101, usuario_id=1, ativo=False)  # inativa, mesmo usuario
    repo.adicionar(conta_id=300, usuario_id=2)  # de outro usuario
    return repo


@pytest.fixture()
def service(transferencia_repo, conta_repo):
    return TransferenciaService(transferencia_repo, conta_repo)


def _criar(
    service,
    usuario_id=1,
    conta_origem_id=100,
    conta_destino_id=200,
    valor=Decimal("300.00"),
    data=date(2026, 7, 14),
    descricao="Reserva de emergência",
):
    dados = TransferenciaCreate(
        conta_origem_id=conta_origem_id,
        conta_destino_id=conta_destino_id,
        valor=valor,
        data=data,
        descricao=descricao,
    )
    return service.criar(dados, usuario_id)


# --- criar: estrutura (origem != destino) -----------------------------------

def test_criar_com_origem_igual_destino_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_origem_id=100, conta_destino_id=100)


# --- criar: posse cruzada de conta_origem/conta_destino ---------------------

def test_criar_com_contas_proprias_e_aceito(service):
    transferencia = _criar(service, conta_origem_id=100, conta_destino_id=200)
    assert transferencia.id is not None
    assert transferencia.usuario_id == 1
    assert transferencia.conta_origem_id == 100
    assert transferencia.conta_destino_id == 200
    assert transferencia.valor == Decimal("300.00")
    assert transferencia.ativo is True


def test_criar_com_conta_origem_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, conta_origem_id=300, conta_destino_id=200)


def test_criar_com_conta_destino_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, conta_origem_id=100, conta_destino_id=300)


def test_criar_com_conta_origem_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, conta_origem_id=999, conta_destino_id=200)


def test_criar_com_conta_destino_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, conta_origem_id=100, conta_destino_id=999)


def test_criar_com_conta_origem_inativa_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_origem_id=101, conta_destino_id=200)


def test_criar_com_conta_destino_inativa_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_origem_id=100, conta_destino_id=101)


# --- obter / listar -----------------------------------------------------

def test_obter_transferencia_propria(service):
    transferencia = _criar(service)
    assert service.obter(transferencia.id, usuario_id=1).id == transferencia.id


def test_obter_transferencia_de_outro_usuario_levanta_not_found(service):
    transferencia = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(transferencia.id, usuario_id=2)


def test_obter_transferencia_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_transferencias_do_usuario(service, conta_repo):
    conta_repo.adicionar(conta_id=400, usuario_id=2)
    conta_repo.adicionar(conta_id=401, usuario_id=2)
    _criar(service, usuario_id=1, conta_origem_id=100, conta_destino_id=200)
    _criar(service, usuario_id=2, conta_origem_id=400, conta_destino_id=401)

    resultado = service.listar(usuario_id=1)
    assert len(resultado) == 1
    assert resultado[0].usuario_id == 1


def test_listar_por_padrao_oculta_transferencias_canceladas(service):
    transferencia = _criar(service)
    service.cancelar(transferencia.id, usuario_id=1)

    assert service.listar(usuario_id=1) == []
    assert service.listar(usuario_id=1, apenas_ativas=False) == [transferencia]


# --- cancelar -------------------------------------------------------------

def test_cancelar_marca_ativo_como_false(service):
    transferencia = _criar(service)
    cancelada = service.cancelar(transferencia.id, usuario_id=1)
    assert cancelada.ativo is False


def test_cancelar_transferencia_ja_cancelada_levanta_business_rule_error(service):
    transferencia = _criar(service)
    service.cancelar(transferencia.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.cancelar(transferencia.id, usuario_id=1)


def test_cancelar_transferencia_de_outro_usuario_levanta_not_found(service):
    transferencia = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.cancelar(transferencia.id, usuario_id=2)


def test_cancelar_transferencia_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.cancelar(999, usuario_id=1)


# --- excluir (hard delete) - novo, criado para a cascata de Conta ----------

def test_excluir_apaga_a_linha_de_verdade(service, transferencia_repo):
    transferencia = _criar(service)
    service.excluir(transferencia.id, usuario_id=1)
    assert transferencia_repo.get(transferencia.id) is None


def test_excluir_transferencia_ja_cancelada_tambem_e_permitido(service, transferencia_repo):
    transferencia = _criar(service)
    service.cancelar(transferencia.id, usuario_id=1)
    service.excluir(transferencia.id, usuario_id=1)
    assert transferencia_repo.get(transferencia.id) is None


def test_excluir_transferencia_de_outro_usuario_levanta_not_found(service):
    transferencia = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(transferencia.id, usuario_id=2)


def test_excluir_transferencia_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.excluir(999, usuario_id=1)
