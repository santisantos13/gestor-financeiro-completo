"""Testes unitários de TagService - isolado com um repository FALSO (em
memória, sem banco). Cobre a parte que mais diferencia Tag de Conta/
Categoria: nome único por usuário coexistindo com soft delete (reativação
em vez de erro de duplicidade).
"""
import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.tag import TagCreate, TagUpdate
from app.services.tag_service import TagService


class FakeTagRepository:
    def __init__(self):
        self._tags = {}
        self._proximo_id = 1

    def get(self, id):
        return self._tags.get(id)

    def create(self, tag):
        tag.id = self._proximo_id
        self._proximo_id += 1
        self._tags[tag.id] = tag
        return tag

    def update(self, tag):
        return tag

    def listar_do_usuario(self, usuario_id, *, apenas_ativas=True, skip=0, limit=100):
        resultado = [
            t
            for t in self._tags.values()
            if t.usuario_id == usuario_id and (not apenas_ativas or t.ativo)
        ]
        resultado.sort(key=lambda t: t.nome)
        return resultado[skip : skip + limit]

    def buscar_por_nome(self, usuario_id, nome):
        return next(
            (t for t in self._tags.values() if t.usuario_id == usuario_id and t.nome == nome), None
        )


@pytest.fixture()
def repo():
    return FakeTagRepository()


@pytest.fixture()
def service(repo):
    return TagService(repo)


def _criar(service, usuario_id=1, nome="viagem", cor=None):
    return service.criar(TagCreate(nome=nome, cor=cor), usuario_id)


# --- criar -------------------------------------------------------------

def test_criar_tag_associa_ao_usuario(service):
    tag = _criar(service, usuario_id=42)
    assert tag.id is not None
    assert tag.usuario_id == 42
    assert tag.ativo is True


def test_criar_tag_com_nome_duplicado_no_mesmo_usuario_levanta_conflict_error(service):
    _criar(service, usuario_id=1, nome="viagem")
    with pytest.raises(ConflictError):
        _criar(service, usuario_id=1, nome="viagem")


def test_criar_tag_com_mesmo_nome_em_usuarios_diferentes_e_permitido(service):
    tag_a = _criar(service, usuario_id=1, nome="viagem")
    tag_b = _criar(service, usuario_id=2, nome="viagem")
    assert tag_a.id != tag_b.id


def test_criar_tag_com_nome_de_tag_desativada_reativa_em_vez_de_duplicar(service, repo):
    original = _criar(service, usuario_id=1, nome="viagem")
    service.desativar(original.id, usuario_id=1)

    recriada = _criar(service, usuario_id=1, nome="viagem", cor="#FF0000")

    assert recriada.id == original.id  # mesma linha, reativada
    assert recriada.ativo is True
    assert recriada.cor == "#FF0000"
    assert len(repo._tags) == 1  # nao criou uma segunda linha


# --- obter / listar ------------------------------------------------------

def test_obter_tag_propria(service):
    tag = _criar(service, usuario_id=1)
    assert service.obter(tag.id, usuario_id=1).id == tag.id


def test_obter_tag_de_outro_usuario_levanta_not_found(service):
    tag = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(tag.id, usuario_id=2)


def test_obter_tag_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_tags_do_usuario(service):
    _criar(service, usuario_id=1, nome="Minha")
    _criar(service, usuario_id=2, nome="Do outro")
    resultado = service.listar(usuario_id=1)
    assert [t.nome for t in resultado] == ["Minha"]


def test_listar_filtra_apenas_ativas_por_padrao(service):
    ativa = _criar(service, usuario_id=1, nome="Ativa")
    inativa = _criar(service, usuario_id=1, nome="Inativa")
    service.desativar(inativa.id, usuario_id=1)

    assert [t.nome for t in service.listar(usuario_id=1)] == ["Ativa"]
    assert {t.nome for t in service.listar(usuario_id=1, apenas_ativas=False)} == {"Ativa", "Inativa"}


# --- atualizar -------------------------------------------------------------

def test_atualizar_tag_propria_aplica_apenas_campos_enviados(service):
    tag = _criar(service, usuario_id=1, nome="Original", cor="#000000")
    atualizado = service.atualizar(tag.id, TagUpdate(cor="#FFFFFF"), usuario_id=1)
    assert atualizado.nome == "Original"
    assert atualizado.cor == "#FFFFFF"


def test_atualizar_tag_de_outro_usuario_levanta_not_found(service):
    tag = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.atualizar(tag.id, TagUpdate(nome="Hackeado"), usuario_id=2)


def test_atualizar_nome_para_nome_ja_usado_por_outra_tag_levanta_conflict_error(service):
    _criar(service, usuario_id=1, nome="viagem")
    trabalho = _criar(service, usuario_id=1, nome="trabalho")

    with pytest.raises(ConflictError):
        service.atualizar(trabalho.id, TagUpdate(nome="viagem"), usuario_id=1)


def test_atualizar_reenviando_o_mesmo_nome_nao_levanta_conflict_error(service):
    tag = _criar(service, usuario_id=1, nome="viagem")
    atualizado = service.atualizar(tag.id, TagUpdate(nome="viagem", cor="#123456"), usuario_id=1)
    assert atualizado.cor == "#123456"


# --- desativar ---------------------------------------------------------

def test_desativar_tag_propria(service, repo):
    tag = _criar(service, usuario_id=1)
    service.desativar(tag.id, usuario_id=1)
    assert repo.get(tag.id).ativo is False


def test_desativar_tag_de_outro_usuario_levanta_not_found(service):
    tag = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.desativar(tag.id, usuario_id=2)


def test_desativar_tag_nao_exige_ausencia_de_uso(service, repo):
    """Diferente de Categoria, nao ha checagem de "em uso" - a tag pode ser
    desativada mesmo que (hipoteticamente) esteja vinculada a transacoes,
    porque soft delete nao mexe na tabela de associacao N-N."""
    tag = _criar(service, usuario_id=1)
    service.desativar(tag.id, usuario_id=1)  # nao deve levantar nada
    assert repo.get(tag.id).ativo is False


def test_reativar_tag_sem_enviar_cor_substitui_cor_antiga_por_none(service):
    """Regressao/decisao de design: criar() usa semantica de CRIACAO, nao
    de "restaurar como estava" - o payload e aplicado por completo. Se o
    cliente recriar uma tag desativada sem mandar `cor`, a cor antiga e
    perdida (nao preservada magicamente), porque TagCreate nao distingue
    "campo omitido" de "campo None" (diferente de TagUpdate)."""
    original = _criar(service, usuario_id=1, nome="viagem", cor="#FF0000")
    service.desativar(original.id, usuario_id=1)

    recriada = service.criar(TagCreate(nome="viagem"), usuario_id=1)

    assert recriada.id == original.id
    assert recriada.cor is None


def test_atualizar_renomeando_para_nome_de_tag_inativa_levanta_conflict_error(service):
    """Diferente de criar(), atualizar() NAO reativa/mescla automaticamente:
    aqui ja existe uma tag DIFERENTE (com id, historico e vinculos
    proprios) sendo renomeada - fundir com uma tag inativa silenciosamente
    perderia/confundiria esse vinculo. O usuario precisa decidir
    explicitamente (reativar a antiga primeiro, ou escolher outro nome)."""
    inativa = _criar(service, usuario_id=1, nome="viagem")
    service.desativar(inativa.id, usuario_id=1)
    outra = _criar(service, usuario_id=1, nome="trabalho")

    with pytest.raises(ConflictError):
        service.atualizar(outra.id, TagUpdate(nome="viagem"), usuario_id=1)


def test_atualizar_ativo_true_reativa_tag_diretamente(service, repo):
    """PATCH {"ativo": true} tambem e um caminho valido de reativacao,
    complementar ao "recriar" via criar() - util quando o cliente ja sabe
    o id da tag desativada."""
    tag = _criar(service, usuario_id=1)
    service.desativar(tag.id, usuario_id=1)

    reativada = service.atualizar(tag.id, TagUpdate(ativo=True), usuario_id=1)

    assert reativada.ativo is True
    assert repo.get(tag.id).ativo is True
