"""Testes unitários de AnexoService - isolado com um AnexoRepository FALSO
(em memória) e um TransacaoService FALSO que só implementa `.obter()`.

Cobre o que mais diferencia Anexo das entidades anteriores: posse SEMPRE
transitiva via Transacao (Anexo não tem `usuario_id` próprio), e que toda
checagem de posse reaproveita `TransacaoService.obter()` - nunca duplica
"transacao.usuario_id == usuario_id" no próprio AnexoService (ver
docs/analise-arquitetural-anexo.md).
"""
import pytest

from app.core.exceptions import NotFoundError
from app.schemas.anexo import AnexoCreate
from app.services.anexo_service import AnexoService


class FakeAnexoRepository:
    def __init__(self):
        self._anexos = {}
        self._proximo_id = 1

    def get(self, id):
        return self._anexos.get(id)

    def create(self, anexo):
        anexo.id = self._proximo_id
        self._proximo_id += 1
        self._anexos[anexo.id] = anexo
        return anexo

    def update(self, anexo):
        return anexo

    def listar_por_transacao(self, transacao_id, *, apenas_ativos=True, skip=0, limit=100):
        resultado = [
            a
            for a in self._anexos.values()
            if a.transacao_id == transacao_id and (not apenas_ativos or a.ativo)
        ]
        # ordena por id (ordem de criacao) em vez de data_upload: o fake nao
        # passa pelo flush do SQLAlchemy, entao data_upload (server_default)
        # fica None aqui - o teste real de ordenacao por data_upload esta
        # coberto na integracao, contra o banco de verdade.
        resultado.sort(key=lambda a: a.id)
        return resultado[skip : skip + limit]


class _TransacaoFalsa:
    def __init__(self, id, usuario_id):
        self.id = id
        self.usuario_id = usuario_id


class FakeTransacaoService:
    """Implementa só `.obter()` - o único método de TransacaoService que
    AnexoService de fato usa. Mesmo comportamento real: 404 uniforme tanto
    para "não existe" quanto para "é de outro usuário"."""

    def __init__(self):
        self._transacoes = {}

    def adicionar(self, transacao_id, usuario_id):
        self._transacoes[transacao_id] = _TransacaoFalsa(transacao_id, usuario_id)

    def obter(self, transacao_id, usuario_id):
        transacao = self._transacoes.get(transacao_id)
        if transacao is None or transacao.usuario_id != usuario_id:
            raise NotFoundError("Transação não encontrada.")
        return transacao


@pytest.fixture()
def anexo_repo():
    return FakeAnexoRepository()


@pytest.fixture()
def transacao_service():
    servico = FakeTransacaoService()
    servico.adicionar(transacao_id=10, usuario_id=1)
    servico.adicionar(transacao_id=20, usuario_id=2)
    return servico


@pytest.fixture()
def service(anexo_repo, transacao_service):
    return AnexoService(anexo_repo, transacao_service)


def _criar(
    service,
    usuario_id=1,
    transacao_id=10,
    nome_original="comprovante.pdf",
    caminho_arquivo="/uploads/comprovante.pdf",
    mime_type="application/pdf",
    tamanho_bytes=1024,
):
    dados = AnexoCreate(
        transacao_id=transacao_id,
        nome_original=nome_original,
        caminho_arquivo=caminho_arquivo,
        mime_type=mime_type,
        tamanho_bytes=tamanho_bytes,
    )
    return service.criar(dados, usuario_id)


# --- criar -------------------------------------------------------------

def test_criar_anexo_vinculado_a_transacao_propria(service):
    anexo = _criar(service, usuario_id=1, transacao_id=10)
    assert anexo.id is not None
    assert anexo.transacao_id == 10
    assert anexo.ativo is True


def test_criar_anexo_nao_tem_usuario_id_proprio(service):
    """Regressão direta da decisão de domínio: Anexo NUNCA pertence
    diretamente ao usuário - o model não tem esse atributo."""
    anexo = _criar(service, usuario_id=1, transacao_id=10)
    assert not hasattr(anexo, "usuario_id")


def test_criar_anexo_em_transacao_de_outro_usuario_levanta_not_found(service):
    """Regra de domínio explícita: não permitir anexar arquivos em
    transações de outro usuário."""
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, transacao_id=20)  # transacao 20 e do usuario 2


def test_criar_anexo_em_transacao_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, transacao_id=999)


def test_criar_anexo_normaliza_espacos_no_nome_original(service):
    anexo = _criar(service, usuario_id=1, transacao_id=10, nome_original="  nota.pdf  ")
    assert anexo.nome_original == "nota.pdf"


# --- obter ---------------------------------------------------------------

def test_obter_anexo_de_transacao_propria(service):
    anexo = _criar(service, usuario_id=1, transacao_id=10)
    assert service.obter(anexo.id, usuario_id=1).id == anexo.id


def test_obter_anexo_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_obter_anexo_de_transacao_de_outro_usuario_levanta_not_found(service, anexo_repo):
    """Posse transitiva: mesmo que o anexo exista, se a transação dele foi
    (hipoteticamente) reatribuída a outro usuário, o acesso é negado -
    reaproveitando TransacaoService.obter(), nunca checando
    transacao_id/usuario_id diretamente."""
    anexo = _criar(service, usuario_id=1, transacao_id=10)
    with pytest.raises(NotFoundError):
        service.obter(anexo.id, usuario_id=2)


# --- listar_por_transacao -------------------------------------------------

def test_listar_por_transacao_retorna_apenas_anexos_daquela_transacao(service):
    _criar(service, usuario_id=1, transacao_id=10, nome_original="a.pdf")
    # cria uma segunda transacao do mesmo usuario para confirmar isolamento
    service.transacao_service.adicionar(transacao_id=11, usuario_id=1)
    _criar(service, usuario_id=1, transacao_id=11, nome_original="b.pdf")

    resultado = service.listar_por_transacao(10, usuario_id=1)
    assert [a.nome_original for a in resultado] == ["a.pdf"]


def test_listar_por_transacao_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.listar_por_transacao(20, usuario_id=1)  # transacao 20 e do usuario 2


def test_listar_por_transacao_filtra_apenas_ativos_por_padrao(service):
    ativo = _criar(service, usuario_id=1, transacao_id=10, nome_original="ativo.pdf")
    inativo = _criar(service, usuario_id=1, transacao_id=10, nome_original="inativo.pdf")
    service.desativar(inativo.id, usuario_id=1)

    assert [a.nome_original for a in service.listar_por_transacao(10, usuario_id=1)] == ["ativo.pdf"]
    todos = service.listar_por_transacao(10, usuario_id=1, apenas_ativos=False)
    assert {a.nome_original for a in todos} == {"ativo.pdf", "inativo.pdf"}


# --- desativar (soft delete) ----------------------------------------------

def test_desativar_anexo_propria_transacao(service, anexo_repo):
    anexo = _criar(service, usuario_id=1, transacao_id=10)
    service.desativar(anexo.id, usuario_id=1)
    assert anexo_repo.get(anexo.id).ativo is False


def test_desativar_anexo_de_transacao_de_outro_usuario_levanta_not_found(service):
    anexo = _criar(service, usuario_id=1, transacao_id=10)
    with pytest.raises(NotFoundError):
        service.desativar(anexo.id, usuario_id=2)


def test_desativar_anexo_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.desativar(999, usuario_id=1)


# --- sem PATCH -------------------------------------------------------------

def test_anexo_service_nao_expoe_metodo_atualizar(service):
    """Regressão da decisão confirmada com o usuário: Anexo é
    create+read+soft-delete apenas, sem PATCH."""
    assert not hasattr(service, "atualizar")
