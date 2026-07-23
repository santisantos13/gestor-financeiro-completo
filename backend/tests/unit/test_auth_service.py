"""Testes unitários de AuthService - toda a regra de negócio de
autenticação, isolada com repositories FALSOS (em memória, sem banco). É
exatamente o que a interface IRepository (app/repositories/base.py) existe
pra permitir: testar a lógica do Service sem SQLAlchemy nem banco real.
"""
import pytest

from app.core.exceptions import AcessoNegadoError, ConflictError, NaoAutenticadoError
from app.core.security import agora_utc_naive
from app.schemas.auth import LoginRequest, LogoutRequest, PerfilUpdate, RefreshRequest, TrocarSenhaRequest, UsuarioCreate
from app.services.auth_service import AuthService, ContextoRequisicao


class FakeUsuarioRepository:
    """Substitui UsuarioRepository nos testes: mesma interface (get,
    create, buscar_por_email), guardando tudo em um dict em memória."""

    def __init__(self):
        self._usuarios = {}
        self._proximo_id = 1

    def buscar_por_email(self, email):
        return next((u for u in self._usuarios.values() if u.email == email), None)

    def get(self, id):
        return self._usuarios.get(id)

    def create(self, usuario):
        usuario.id = self._proximo_id
        self._proximo_id += 1
        self._usuarios[usuario.id] = usuario
        return usuario

    def update(self, usuario):
        return usuario


class FakeSessaoUsuarioRepository:
    """Substitui SessaoUsuarioRepository nos testes: mesma interface
    (buscar_por_token_hash, create, update, revogar_todas_do_usuario)."""

    def __init__(self):
        self._sessoes = {}
        self._proximo_id = 1

    def buscar_por_token_hash(self, token_hash):
        return next((s for s in self._sessoes.values() if s.token_hash == token_hash), None)

    def create(self, sessao):
        sessao.id = self._proximo_id
        self._proximo_id += 1
        self._sessoes[sessao.id] = sessao
        return sessao

    def update(self, sessao):
        return sessao

    def revogar_todas_do_usuario(self, usuario_id):
        quantidade = 0
        for sessao in self._sessoes.values():
            if sessao.usuario_id == usuario_id and sessao.revogado_em is None:
                sessao.revogado_em = agora_utc_naive()
                quantidade += 1
        return quantidade


@pytest.fixture()
def service():
    return AuthService(FakeUsuarioRepository(), FakeSessaoUsuarioRepository())


def _registrar(service, email="ana@example.com", senha="12345678"):
    return service.registrar(UsuarioCreate(nome="Ana", email=email, senha=senha))


def _login(service, email="ana@example.com", senha="12345678"):
    return service.autenticar(LoginRequest(email=email, senha=senha), ContextoRequisicao())


def test_registrar_cria_usuario_com_senha_hasheada(service):
    usuario = _registrar(service)
    assert usuario.id is not None
    assert usuario.senha_hash != "12345678"


def test_registrar_com_email_duplicado_levanta_conflict_error(service):
    _registrar(service)
    with pytest.raises(ConflictError):
        service.registrar(UsuarioCreate(nome="Outra Ana", email="ana@example.com", senha="87654321"))


def test_autenticar_com_credenciais_corretas_retorna_tokens(service):
    _registrar(service)
    resposta = _login(service)
    assert resposta.access_token
    assert resposta.refresh_token
    assert resposta.token_type == "bearer"


def test_autenticar_com_senha_errada_levanta_nao_autenticado(service):
    _registrar(service)
    with pytest.raises(NaoAutenticadoError):
        service.autenticar(LoginRequest(email="ana@example.com", senha="errada123"), ContextoRequisicao())


def test_autenticar_com_email_inexistente_levanta_a_mesma_excecao_que_senha_errada(service):
    # mensagem/comportamento identicos por design - nao revela se o e-mail existe
    with pytest.raises(NaoAutenticadoError):
        service.autenticar(LoginRequest(email="ninguem@example.com", senha="qualquer1"), ContextoRequisicao())


def test_autenticar_com_email_inexistente_ainda_roda_verificacao_de_senha(service, monkeypatch):
    """Regressao de canal de tempo: login com e-mail inexistente deve
    chamar security.verificar_senha() do mesmo jeito que login com senha
    errada, senao a resposta desse caso fica mensuravelmente mais rapida
    (sem rodar bcrypt) e um atacante consegue distinguir "e-mail existe" de
    "e-mail nao existe" so pelo tempo de resposta, mesmo com mensagem e log
    identicos nos dois casos."""
    from app.services import auth_service as auth_service_module

    chamadas = []
    original = auth_service_module.security.verificar_senha

    def _espiao(senha, senha_hash):
        chamadas.append(senha_hash)
        return original(senha, senha_hash)

    monkeypatch.setattr(auth_service_module.security, "verificar_senha", _espiao)

    with pytest.raises(NaoAutenticadoError):
        service.autenticar(LoginRequest(email="ninguem@example.com", senha="qualquer1"), ContextoRequisicao())

    assert len(chamadas) == 1
    assert chamadas[0] == auth_service_module._HASH_FANTASMA


def test_autenticar_usuario_inativo_levanta_nao_autenticado(service):
    usuario = _registrar(service)
    usuario.ativo = False
    with pytest.raises(NaoAutenticadoError):
        _login(service)


def test_renovar_com_refresh_token_valido_emite_novo_par_e_revoga_o_antigo(service):
    _registrar(service)
    tokens = _login(service)

    novos_tokens = service.renovar(RefreshRequest(refresh_token=tokens.refresh_token), ContextoRequisicao())
    assert novos_tokens.refresh_token != tokens.refresh_token

    # o token antigo, ja rotacionado, nao pode ser usado de novo
    with pytest.raises(NaoAutenticadoError):
        service.renovar(RefreshRequest(refresh_token=tokens.refresh_token), ContextoRequisicao())


def test_renovar_com_refresh_token_invalido_levanta_nao_autenticado(service):
    with pytest.raises(NaoAutenticadoError):
        service.renovar(RefreshRequest(refresh_token="token-que-nunca-existiu"), ContextoRequisicao())


def test_renovar_usa_o_contexto_da_requisicao_atual_nao_o_da_sessao_anterior(service):
    """Regressao: o refresh ja teve um bug em que ip/user_agent da sessao
    NOVA ficavam presos ao valor da sessao antiga em vez de refletir de
    onde a requisicao de refresh atual veio."""
    _registrar(service)
    tokens = service.autenticar(
        LoginRequest(email="ana@example.com", senha="12345678"),
        ContextoRequisicao(user_agent="dispositivo-A", ip="10.0.0.1"),
    )

    contexto_atual = ContextoRequisicao(user_agent="dispositivo-B", ip="200.0.0.9")
    service.renovar(RefreshRequest(refresh_token=tokens.refresh_token), contexto_atual)

    nova_sessao = next(
        s for s in service.sessao_repo._sessoes.values() if s.revogado_em is None
    )
    assert nova_sessao.user_agent == "dispositivo-B"
    assert nova_sessao.ip == "200.0.0.9"


def test_logout_revoga_apenas_a_sessao_daquele_token(service):
    usuario = _registrar(service)
    tokens_1 = _login(service)
    tokens_2 = _login(service)

    service.logout(usuario, LogoutRequest(refresh_token=tokens_1.refresh_token))

    # sessao 1 nao renova mais...
    with pytest.raises(NaoAutenticadoError):
        service.renovar(RefreshRequest(refresh_token=tokens_1.refresh_token), ContextoRequisicao())
    # ...mas a sessao 2 continua ativa (nao foi um logout global)
    novos = service.renovar(RefreshRequest(refresh_token=tokens_2.refresh_token), ContextoRequisicao())
    assert novos.access_token


def test_logout_de_sessao_de_outro_usuario_levanta_acesso_negado(service):
    _registrar(service, email="ana@example.com")
    usuario_b = _registrar(service, email="bruno@example.com")
    tokens_a = _login(service, email="ana@example.com")

    with pytest.raises(AcessoNegadoError):
        service.logout(usuario_b, LogoutRequest(refresh_token=tokens_a.refresh_token))


def test_logout_com_token_inexistente_e_idempotente_nao_levanta_erro(service):
    usuario = _registrar(service)
    service.logout(usuario, LogoutRequest(refresh_token="nunca-existiu"))  # nao deve levantar


def test_logout_todas_revoga_todas_as_sessoes_do_usuario(service):
    usuario = _registrar(service)
    tokens_1 = _login(service)
    tokens_2 = _login(service)

    quantidade = service.logout_todas(usuario)
    assert quantidade == 2

    with pytest.raises(NaoAutenticadoError):
        service.renovar(RefreshRequest(refresh_token=tokens_1.refresh_token), ContextoRequisicao())
    with pytest.raises(NaoAutenticadoError):
        service.renovar(RefreshRequest(refresh_token=tokens_2.refresh_token), ContextoRequisicao())


def test_atualizar_perfil_troca_nome_e_email(service):
    usuario = _registrar(service)
    atualizado = service.atualizar_perfil(usuario, PerfilUpdate(nome="Ana Paula", email="ana.paula@example.com"))
    assert atualizado.nome == "Ana Paula"
    assert atualizado.email == "ana.paula@example.com"


def test_atualizar_perfil_so_altera_campo_informado(service):
    usuario = _registrar(service)
    service.atualizar_perfil(usuario, PerfilUpdate(nome="Ana Paula"))
    assert usuario.nome == "Ana Paula"
    assert usuario.email == "ana@example.com"  # inalterado


def test_atualizar_perfil_com_email_ja_usado_por_outro_usuario_levanta_conflict_error(service):
    _registrar(service, email="ana@example.com")
    usuario_b = _registrar(service, email="bruno@example.com")
    with pytest.raises(ConflictError):
        service.atualizar_perfil(usuario_b, PerfilUpdate(email="ana@example.com"))


def test_atualizar_perfil_mantendo_o_proprio_email_nao_conflita_consigo_mesmo(service):
    usuario = _registrar(service)
    # nao deve levantar ConflictError so por reenviar o mesmo e-mail que ja e dele
    atualizado = service.atualizar_perfil(usuario, PerfilUpdate(nome="Ana", email="ana@example.com"))
    assert atualizado.email == "ana@example.com"


def test_trocar_senha_com_senha_atual_correta_atualiza_o_hash(service):
    usuario = _registrar(service)
    hash_antigo = usuario.senha_hash
    service.trocar_senha(usuario, TrocarSenhaRequest(senha_atual="12345678", senha_nova="novaSenha123"))
    assert usuario.senha_hash != hash_antigo
    # login com a senha nova deve funcionar
    resposta = _login(service, senha="novaSenha123")
    assert resposta.access_token


def test_trocar_senha_com_senha_atual_incorreta_levanta_nao_autenticado(service):
    usuario = _registrar(service)
    with pytest.raises(NaoAutenticadoError):
        service.trocar_senha(usuario, TrocarSenhaRequest(senha_atual="errada12", senha_nova="novaSenha123"))
