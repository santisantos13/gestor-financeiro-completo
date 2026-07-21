"""Testes unitários de CategoriaService - isolado com um repository FALSO
(em memória, sem banco). Cobre a parte que mais diferencia Categoria de
Conta: visibilidade em três níveis (sistema/própria/de outro usuário),
prevenção de auto-referência e ciclo, e bloqueio de exclusão com
subcategoria ativa.
"""
import pytest

from app.core.exceptions import AcessoNegadoError, BusinessRuleError, NotFoundError
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate
from app.services.categoria_service import CategoriaService


class FakeCategoriaRepository:
    def __init__(self):
        self._categorias = {}
        self._proximo_id = 1
        self._ocultas = set()  # {(usuario_id, categoria_id)}
        self._transacoes_por_usuario = set()  # {(categoria_id, usuario_id)}

    def get(self, id):
        return self._categorias.get(id)

    def create(self, categoria):
        categoria.id = self._proximo_id
        self._proximo_id += 1
        self._categorias[categoria.id] = categoria
        return categoria

    def update(self, categoria):
        return categoria

    def listar_visiveis_do_usuario(
        self, usuario_id, *, apenas_ativas=True, incluir_ocultas=False, skip=0, limit=100
    ):
        resultado = [
            c
            for c in self._categorias.values()
            if (c.usuario_id is None or c.usuario_id == usuario_id)
            and (not apenas_ativas or c.ativo)
            and (incluir_ocultas or (usuario_id, c.id) not in self._ocultas)
        ]
        resultado.sort(key=lambda c: c.nome)
        return resultado[skip : skip + limit]

    def existe_subcategoria_ativa(self, categoria_id):
        return any(
            c.categoria_pai_id == categoria_id and c.ativo for c in self._categorias.values()
        )

    def esta_oculta_para_usuario(self, categoria_id, usuario_id):
        return (usuario_id, categoria_id) in self._ocultas

    def ocultar_para_usuario(self, categoria_id, usuario_id):
        self._ocultas.add((usuario_id, categoria_id))

    def reexibir_para_usuario(self, categoria_id, usuario_id):
        self._ocultas.discard((usuario_id, categoria_id))

    def existe_transacao_vinculada_do_usuario(self, categoria_id, usuario_id):
        return (categoria_id, usuario_id) in self._transacoes_por_usuario


@pytest.fixture()
def repo():
    return FakeCategoriaRepository()


@pytest.fixture()
def service(repo):
    return CategoriaService(repo)


def _criar(service, usuario_id=1, nome="Categoria", categoria_pai_id=None):
    dados = CategoriaCreate(nome=nome, categoria_pai_id=categoria_pai_id)
    return service.criar(dados, usuario_id)


def _criar_categoria_do_sistema(repo, nome="Sistema"):
    """Categorias do sistema não passam por Service.criar (não é possível
    criá-las via API) - inseridas direto no repo, simulando um seed."""
    from app.models import Categoria

    categoria = Categoria(nome=nome, usuario_id=None, ativo=True)
    return repo.create(categoria)


# --- criar -------------------------------------------------------------

def test_criar_categoria_associa_ao_usuario(service):
    categoria = _criar(service, usuario_id=42)
    assert categoria.id is not None
    assert categoria.usuario_id == 42
    assert categoria.ativo is True


def test_criar_subcategoria_com_pai_proprio_valido(service):
    pai = _criar(service, usuario_id=1, nome="Pai")
    filha = _criar(service, usuario_id=1, nome="Filha", categoria_pai_id=pai.id)
    assert filha.categoria_pai_id == pai.id


def test_criar_subcategoria_com_pai_do_sistema_e_permitido(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    filha = _criar(service, usuario_id=1, nome="Filha", categoria_pai_id=sistema.id)
    assert filha.categoria_pai_id == sistema.id


def test_criar_categoria_com_pai_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, categoria_pai_id=999)


def test_criar_categoria_com_pai_de_outro_usuario_levanta_not_found(service):
    pai_de_outro = _criar(service, usuario_id=2, nome="Pai do outro")
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, categoria_pai_id=pai_de_outro.id)


# --- obter / listar ------------------------------------------------------

def test_obter_categoria_do_sistema_e_visivel_para_qualquer_usuario(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    resultado = service.obter(sistema.id, usuario_id=999)
    assert resultado.id == sistema.id


def test_obter_categoria_propria(service):
    categoria = _criar(service, usuario_id=1)
    resultado = service.obter(categoria.id, usuario_id=1)
    assert resultado.id == categoria.id


def test_obter_categoria_de_outro_usuario_levanta_not_found(service):
    categoria = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(categoria.id, usuario_id=2)


def test_obter_categoria_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_sistema_e_proprias_mas_nao_de_outro_usuario(service, repo):
    _criar_categoria_do_sistema(repo, nome="Sistema")
    _criar(service, usuario_id=1, nome="Minha")
    _criar(service, usuario_id=2, nome="Do outro")

    resultado = service.listar(usuario_id=1)

    nomes = {c.nome for c in resultado}
    assert nomes == {"Sistema", "Minha"}


# --- atualizar -------------------------------------------------------------

def test_atualizar_categoria_do_sistema_e_permitido(service, repo):
    """Tarefa #111 - edição livre: campos de conteúdo de uma categoria de
    sistema agora podem ser alterados por qualquer usuário autenticado
    (a linha é compartilhada por todos - a edição vale pra todo mundo,
    igual à visibilidade)."""
    sistema = _criar_categoria_do_sistema(repo)
    atualizado = service.atualizar(
        sistema.id, CategoriaUpdate(nome="Renomeada", cor="#112233", icone="star"), usuario_id=1
    )
    assert atualizado.nome == "Renomeada"
    assert atualizado.cor == "#112233"
    assert atualizado.icone == "star"


def test_atualizar_categoria_do_sistema_com_ativo_false_levanta_acesso_negado(service, repo):
    """Diferente de editar conteúdo: desativar uma categoria de sistema via
    PATCH {"ativo": false} continua bloqueado - tiraria a categoria de TODOS
    os usuários, não só de quem editou, e isso nunca foi pedido (mesma regra
    de desativar()/excluir())."""
    sistema = _criar_categoria_do_sistema(repo)
    with pytest.raises(AcessoNegadoError):
        service.atualizar(sistema.id, CategoriaUpdate(ativo=False), usuario_id=1)


def test_atualizar_categoria_de_outro_usuario_levanta_not_found(service):
    categoria = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.atualizar(categoria.id, CategoriaUpdate(nome="Hackeado"), usuario_id=2)


def test_atualizar_categoria_propria_aplica_apenas_campos_enviados(service):
    categoria = _criar(service, usuario_id=1, nome="Original")
    atualizado = service.atualizar(categoria.id, CategoriaUpdate(nome="Novo"), usuario_id=1)
    assert atualizado.nome == "Novo"


def test_atualizar_pai_para_ela_mesma_levanta_business_rule_error(service):
    categoria = _criar(service, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.atualizar(categoria.id, CategoriaUpdate(categoria_pai_id=categoria.id), usuario_id=1)


def test_atualizar_criando_ciclo_levanta_business_rule_error(service):
    a = _criar(service, usuario_id=1, nome="A")
    b = _criar(service, usuario_id=1, nome="B", categoria_pai_id=a.id)
    c = _criar(service, usuario_id=1, nome="C", categoria_pai_id=b.id)

    # A -> B -> C ja existe; tentar fazer A apontar pra C fecharia o ciclo
    with pytest.raises(BusinessRuleError):
        service.atualizar(a.id, CategoriaUpdate(categoria_pai_id=c.id), usuario_id=1)


def test_atualizar_pai_para_categoria_de_outro_usuario_levanta_not_found(service):
    minha = _criar(service, usuario_id=1)
    pai_de_outro = _criar(service, usuario_id=2)
    with pytest.raises(NotFoundError):
        service.atualizar(minha.id, CategoriaUpdate(categoria_pai_id=pai_de_outro.id), usuario_id=1)


def test_atualizar_removendo_pai_nao_valida_ciclo(service):
    a = _criar(service, usuario_id=1, nome="A")
    b = _criar(service, usuario_id=1, nome="B", categoria_pai_id=a.id)

    atualizado = service.atualizar(b.id, CategoriaUpdate(categoria_pai_id=None), usuario_id=1)
    assert atualizado.categoria_pai_id is None


# --- desativar ---------------------------------------------------------

def test_desativar_categoria_propria(service, repo):
    categoria = _criar(service, usuario_id=1)
    service.desativar(categoria.id, usuario_id=1)
    assert repo.get(categoria.id).ativo is False


def test_desativar_categoria_do_sistema_levanta_acesso_negado(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    with pytest.raises(AcessoNegadoError):
        service.desativar(sistema.id, usuario_id=1)


def test_desativar_categoria_de_outro_usuario_levanta_not_found(service):
    categoria = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.desativar(categoria.id, usuario_id=2)


def test_desativar_categoria_com_subcategoria_ativa_levanta_business_rule_error(service):
    pai = _criar(service, usuario_id=1, nome="Pai")
    _criar(service, usuario_id=1, nome="Filha", categoria_pai_id=pai.id)

    with pytest.raises(BusinessRuleError):
        service.desativar(pai.id, usuario_id=1)


def test_desativar_categoria_com_subcategoria_ja_inativa_e_permitido(service, repo):
    pai = _criar(service, usuario_id=1, nome="Pai")
    filha = _criar(service, usuario_id=1, nome="Filha", categoria_pai_id=pai.id)
    service.desativar(filha.id, usuario_id=1)

    service.desativar(pai.id, usuario_id=1)  # nao deve levantar

    assert repo.get(pai.id).ativo is False


def test_atualizar_ativo_false_com_subcategoria_ativa_levanta_business_rule_error(service):
    """Regressao: PATCH {"ativo": false} e um atalho pro mesmo efeito de
    DELETE - tem que respeitar a mesma regra de negocio (nao desativar com
    subcategoria ativa), senao um cliente contornaria desativar() so
    trocando de endpoint."""
    pai = _criar(service, usuario_id=1, nome="Pai")
    _criar(service, usuario_id=1, nome="Filha", categoria_pai_id=pai.id)

    with pytest.raises(BusinessRuleError):
        service.atualizar(pai.id, CategoriaUpdate(ativo=False), usuario_id=1)


def test_atualizar_ativo_false_sem_subcategoria_ativa_e_permitido(service, repo):
    categoria = _criar(service, usuario_id=1)
    service.atualizar(categoria.id, CategoriaUpdate(ativo=False), usuario_id=1)
    assert repo.get(categoria.id).ativo is False


def test_atualizar_reenviando_ativo_true_nao_dispara_checagem_de_subcategoria(service):
    """Reenviar ativo=true (categoria ja ativa) nao e uma desativacao - nao
    deve rodar a checagem de subcategoria (que so faz sentido pra quem esta
    DESLIGANDO ativo, nao pra quem manda o mesmo valor de novo)."""
    pai = _criar(service, usuario_id=1, nome="Pai")
    _criar(service, usuario_id=1, nome="Filha", categoria_pai_id=pai.id)

    atualizado = service.atualizar(pai.id, CategoriaUpdate(ativo=True, nome="Pai renomeado"), usuario_id=1)
    assert atualizado.nome == "Pai renomeado"
    assert atualizado.ativo is True


# --- ocultar/reexibir para usuário (Sprint de Refinamento Premium, item 4) --

def test_ocultar_categoria_do_sistema_para_usuario(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    service.ocultar_para_usuario(sistema.id, usuario_id=1)
    assert repo.esta_oculta_para_usuario(sistema.id, usuario_id=1) is True


def test_ocultar_nao_afeta_visibilidade_de_outro_usuario(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    service.ocultar_para_usuario(sistema.id, usuario_id=1)

    resultado_1 = service.listar(usuario_id=1)
    resultado_2 = service.listar(usuario_id=2)

    assert sistema.id not in {c.id for c in resultado_1}
    assert sistema.id in {c.id for c in resultado_2}


def test_ocultar_categoria_propria_levanta_business_rule_error(service):
    """Ocultar só faz sentido para categoria de sistema - categoria própria
    já tem desativar()/excluir() normais."""
    categoria = _criar(service, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.ocultar_para_usuario(categoria.id, usuario_id=1)


def test_ocultar_categoria_com_transacao_vinculada_do_usuario_levanta_business_rule_error(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    repo._transacoes_por_usuario.add((sistema.id, 1))
    with pytest.raises(BusinessRuleError):
        service.ocultar_para_usuario(sistema.id, usuario_id=1)


def test_ocultar_categoria_de_outro_usuario_privada_levanta_not_found(service):
    categoria_de_outro = _criar(service, usuario_id=2)
    with pytest.raises(NotFoundError):
        service.ocultar_para_usuario(categoria_de_outro.id, usuario_id=1)


def test_reexibir_categoria_oculta(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    service.ocultar_para_usuario(sistema.id, usuario_id=1)
    service.reexibir_para_usuario(sistema.id, usuario_id=1)
    assert repo.esta_oculta_para_usuario(sistema.id, usuario_id=1) is False


def test_reexibir_categoria_nao_oculta_e_idempotente(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    service.reexibir_para_usuario(sistema.id, usuario_id=1)  # nao deve levantar
    assert repo.esta_oculta_para_usuario(sistema.id, usuario_id=1) is False


def test_obter_categoria_expoe_oculta_para_mim(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    service.ocultar_para_usuario(sistema.id, usuario_id=1)

    resultado = service.obter(sistema.id, usuario_id=1)
    assert resultado.oculta_para_mim is True

    resultado_outro = service.obter(sistema.id, usuario_id=2)
    assert resultado_outro.oculta_para_mim is False


def test_listar_incluir_ocultas_devolve_categoria_oculta(service, repo):
    sistema = _criar_categoria_do_sistema(repo)
    service.ocultar_para_usuario(sistema.id, usuario_id=1)

    sem_ocultas = service.listar(usuario_id=1)
    com_ocultas = service.listar(usuario_id=1, incluir_ocultas=True)

    assert sistema.id not in {c.id for c in sem_ocultas}
    assert sistema.id in {c.id for c in com_ocultas}
