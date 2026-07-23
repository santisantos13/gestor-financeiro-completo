"""Service de autenticação.

Toda decisão sobre registro, login, refresh e logout mora aqui - é o ÚNICO
Service deste projeto autorizado a importar app/core/security.py (JWT/
bcrypt). Nenhum outro Service deve decodificar token ou comparar hash de
senha diretamente; se algum dia precisar saber "quem é o usuário atual",
a resposta é sempre a dependency get_current_user() (app/api/deps.py), que
por sua vez também só fala com app/core/security.py e com UsuarioRepository
- nunca com AuthService (evita um ciclo de dependência entre Service e
dependency de FastAPI).
"""
import logging
from datetime import timedelta
from typing import NamedTuple

from app.core import security
from app.core.config import settings
from app.core.exceptions import AcessoNegadoError, ConflictError, NaoAutenticadoError
from app.core.security import agora_utc_naive
from app.models import SessaoUsuario, Usuario
from app.models.enums import TipoPapel
from app.repositories.sessao_usuario_repository import SessaoUsuarioRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    PerfilUpdate,
    RefreshRequest,
    TokenResponse,
    TrocarSenhaRequest,
    UsuarioCreate,
)

logger = logging.getLogger(__name__)

# Hash bcrypt valido, mas de uma senha que nao pertence a ninguem. Usado em
# autenticar() para que um e-mail inexistente gaste, propositalmente, o
# mesmo tempo de CPU que um e-mail existente com senha errada (ambos
# chamam bcrypt.checkpw uma vez). Sem isso, a resposta de "e-mail
# inexistente" seria mensuravelmente mais rapida (nao chega a rodar
# bcrypt) do que "senha errada" - um canal de tempo que revelaria quais
# e-mails tem conta mesmo com mensagem e log identicos (ver autenticar()).
_HASH_FANTASMA = "$2b$12$j6xo/IMjtTL5tfxJtilgJewO4B1K27LwqVlm3cCSBikjhRrgbk.3O"


class ContextoRequisicao(NamedTuple):
    """Metadados da requisição HTTP relevantes para a sessão. Nunca
    influenciam uma decisão de autorização - só ficam guardados na
    SessaoUsuario para o usuário reconhecer o dispositivo depois (ex: numa
    futura tela "meus dispositivos conectados")."""

    user_agent: str | None = None
    ip: str | None = None


class AuthService:
    def __init__(self, usuario_repo: UsuarioRepository, sessao_repo: SessaoUsuarioRepository) -> None:
        self.usuario_repo = usuario_repo
        self.sessao_repo = sessao_repo

    def registrar(self, dados: UsuarioCreate) -> Usuario:
        """Cria um novo usuário. E-mail duplicado é erro de negócio
        (ConflictError -> 409), não um detalhe de banco (constraint
        violation) vazando pra fora do Service."""
        if self.usuario_repo.buscar_por_email(dados.email) is not None:
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")

        # papel/ativo sao passados explicitamente (em vez de depender do
        # default da coluna, que so e aplicado pelo SQLAlchemy durante um
        # flush de verdade) - mantem o Service correto mesmo fora do
        # caminho feliz com banco real, ex: testes unitarios com repository
        # falso, que nunca fazem flush.
        usuario = Usuario(
            nome=dados.nome,
            email=dados.email,
            senha_hash=security.hash_senha(dados.senha),
            papel=TipoPapel.USER,
            ativo=True,
        )
        usuario = self.usuario_repo.create(usuario)
        logger.info("usuario_registrado usuario_id=%s", usuario.id)
        return usuario

    def autenticar(self, dados: LoginRequest, contexto: ContextoRequisicao) -> TokenResponse:
        """Confere e-mail/senha e, se válidos, emite um novo par de tokens
        e uma nova SessaoUsuario."""
        usuario = self.usuario_repo.buscar_por_email(dados.email)

        # security.verificar_senha() e chamado SEMPRE, mesmo quando o
        # usuario nao existe (contra o hash fantasma acima) - se pulassemos
        # essa chamada para e-mail inexistente, a resposta desse caso
        # seria consistentemente mais rapida que a de "senha errada"
        # (que roda bcrypt de verdade), e um atacante conseguiria
        # descobrir e-mails cadastrados so medindo o tempo de resposta,
        # mesmo com mensagem e log identicos nos dois casos.
        hash_para_comparar = usuario.senha_hash if usuario is not None else _HASH_FANTASMA
        senha_confere = security.verificar_senha(dados.senha, hash_para_comparar)

        if usuario is None or not senha_confere:
            logger.warning("login_invalido email=%s ip=%s", dados.email, contexto.ip)
            raise NaoAutenticadoError("E-mail ou senha inválidos.")

        if not usuario.ativo:
            logger.warning("login_invalido usuario_id=%s motivo=usuario_inativo ip=%s", usuario.id, contexto.ip)
            raise NaoAutenticadoError("E-mail ou senha inválidos.")

        resposta = self._emitir_tokens(usuario, contexto)
        logger.info("login_sucesso usuario_id=%s ip=%s", usuario.id, contexto.ip)
        return resposta

    def renovar(self, dados: RefreshRequest, contexto: ContextoRequisicao) -> TokenResponse:
        """Troca um refresh token válido por um par de tokens novo.

        Rotation: a sessão associada ao token usado é revogada e uma nova
        é criada no lugar - se um refresh token vazar, ele só pode ser
        usado uma vez antes de virar inválido, reduzindo a janela de
        exploração de um token roubado.

        `contexto` vem da requisição de refresh ATUAL (não da sessão
        antiga): ip/user_agent descrevem de onde o cliente está se
        reconectando agora, o que é o dado relevante para reconhecimento de
        dispositivo/detecção de anomalia - reaproveitar o contexto da
        sessão anterior deixaria esses campos parados no valor do login
        original para sempre, mesmo que os refreshes seguintes venham de
        rede/dispositivo diferentes.
        """
        sessao, usuario = self._validar_sessao(dados.refresh_token)

        sessao.revogado_em = agora_utc_naive()
        self.sessao_repo.update(sessao)

        resposta = self._emitir_tokens(usuario, contexto)
        logger.info("refresh_realizado usuario_id=%s sessao_anterior_id=%s", usuario.id, sessao.id)
        return resposta

    def logout(self, usuario_atual: Usuario, dados: LogoutRequest) -> None:
        """Encerra APENAS a sessão associada ao refresh token informado."""
        sessao = self.sessao_repo.buscar_por_token_hash(security.hash_token_sessao(dados.refresh_token))
        if sessao is None:
            # idempotente: um token que ja nao existe (ou ja foi revogado)
            # nao e erro - o resultado desejado (sessao encerrada) ja e
            # verdade, entao nao ha nada a fazer.
            return

        if sessao.usuario_id != usuario_atual.id:
            logger.warning(
                "tentativa_acesso_nao_autorizada usuario_id=%s sessao_id=%s motivo=logout_de_sessao_alheia",
                usuario_atual.id,
                sessao.id,
            )
            raise AcessoNegadoError("Esta sessão não pertence ao usuário autenticado.")

        sessao.revogado_em = agora_utc_naive()
        self.sessao_repo.update(sessao)
        logger.info("logout usuario_id=%s sessao_id=%s", usuario_atual.id, sessao.id)

    def logout_todas(self, usuario_atual: Usuario) -> int:
        """Encerra TODAS as sessões ativas do usuário (ex: "sair de todos os
        dispositivos"). Retorna quantas sessões foram revogadas."""
        quantidade = self.sessao_repo.revogar_todas_do_usuario(usuario_atual.id)
        logger.info("logout_global usuario_id=%s sessoes_revogadas=%s", usuario_atual.id, quantidade)
        return quantidade

    def atualizar_perfil(self, usuario_atual: Usuario, dados: PerfilUpdate) -> Usuario:
        """Atualiza nome e/ou e-mail do usuário autenticado. `exclude_unset`
        (não `exclude_none`) porque `None` explícito não é um valor válido
        para nenhum dos dois campos (`PerfilUpdate` já garante isso via
        `EmailStr`/`min_length=1`) - só campos omitidos pelo cliente devem
        ser ignorados."""
        alteracoes = dados.model_dump(exclude_unset=True)

        novo_email = alteracoes.get("email")
        if novo_email is not None and novo_email != usuario_atual.email:
            if self.usuario_repo.buscar_por_email(novo_email) is not None:
                raise ConflictError("Já existe um usuário cadastrado com este e-mail.")
            usuario_atual.email = novo_email

        if "nome" in alteracoes:
            usuario_atual.nome = alteracoes["nome"]

        usuario_atual = self.usuario_repo.update(usuario_atual)
        logger.info("perfil_atualizado usuario_id=%s", usuario_atual.id)
        return usuario_atual

    def trocar_senha(self, usuario_atual: Usuario, dados: TrocarSenhaRequest) -> None:
        """Troca a senha do usuário autenticado, exigindo a senha atual.

        Não invalida sessões existentes (diferente de um "logout de todos os
        dispositivos" explícito, que já existe como ação separada em
        `logout_todas`) - decisão deliberada de manter os dois fluxos
        independentes, para não surpreender quem só queria trocar a senha
        com um logout forçado em outro aparelho."""
        if not security.verificar_senha(dados.senha_atual, usuario_atual.senha_hash):
            logger.warning("troca_senha_invalida usuario_id=%s motivo=senha_atual_incorreta", usuario_atual.id)
            raise NaoAutenticadoError("Senha atual incorreta.")

        usuario_atual.senha_hash = security.hash_senha(dados.senha_nova)
        self.usuario_repo.update(usuario_atual)
        logger.info("senha_trocada usuario_id=%s", usuario_atual.id)

    def _validar_sessao(self, refresh_token: str) -> tuple[SessaoUsuario, Usuario]:
        sessao = self.sessao_repo.buscar_por_token_hash(security.hash_token_sessao(refresh_token))
        if sessao is None or sessao.revogado_em is not None or sessao.expira_em <= agora_utc_naive():
            logger.warning("tentativa_acesso_nao_autorizada motivo=refresh_token_invalido_ou_expirado")
            raise NaoAutenticadoError("Sessão expirada ou inválida. Faça login novamente.")

        usuario = self.usuario_repo.get(sessao.usuario_id)
        if usuario is None or not usuario.ativo:
            logger.warning(
                "tentativa_acesso_nao_autorizada usuario_id=%s motivo=usuario_inativo_ou_removido",
                sessao.usuario_id,
            )
            raise NaoAutenticadoError("Sessão expirada ou inválida. Faça login novamente.")

        return sessao, usuario

    def _emitir_tokens(self, usuario: Usuario, contexto: ContextoRequisicao) -> TokenResponse:
        access = security.criar_access_token(usuario_id=usuario.id, papel=usuario.papel.value)

        token_bruto = security.gerar_token_sessao()
        expira_em = agora_utc_naive() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        sessao = SessaoUsuario(
            usuario_id=usuario.id,
            token_hash=security.hash_token_sessao(token_bruto),
            expira_em=expira_em,
            user_agent=contexto.user_agent,
            ip=contexto.ip,
        )
        self.sessao_repo.create(sessao)

        return TokenResponse(
            access_token=access.token,
            refresh_token=token_bruto,
            expira_em_segundos=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
