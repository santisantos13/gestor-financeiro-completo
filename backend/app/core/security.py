"""Funcoes criptograficas puras de autenticacao: hash de senha, hash de
token de sessao, e criacao/decodificacao de access token JWT.

Este modulo e a UNICA parte do sistema que sabe como um JWT e montado ou
como uma senha e hasheada. Ele nao acessa banco, nao conhece FastAPI, nao
decide regra de negocio - so oferece operacoes criptograficas puras. Quem
decide O QUE FAZER com o resultado (ex: "senha nao confere -> levantar
NaoAutenticadoError") e o AuthService (app/services/auth_service.py) ou a
dependency get_current_user (app/api/deps.py) - sao os UNICOS dois lugares
autorizados a importar este modulo. Nenhum outro Service deve importar JWT
ou bcrypt diretamente (ver README, secao Autenticacao).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import bcrypt
import jwt

from app.core.config import settings

# bcrypt trunca silenciosamente a senha em 72 bytes - validamos isso
# explicitamente em vez de deixar o comportamento ficar implicito (uma
# senha de 100 caracteres pareceria "aceita", mas so os 72 primeiros bytes
# realmente importariam pro hash gerado).
_BCRYPT_MAX_BYTES = 72


class SenhaMuitoLongaError(Exception):
    """Levantada quando a senha excede o limite que o bcrypt suporta."""


def agora_utc_naive() -> datetime:
    """Horário atual em UTC, sem tzinfo ("naive").

    Usado em todo lugar que grava ou compara datas em colunas DateTime do
    banco (ex: SessaoUsuario.expira_em/revogado_em) para bater com o
    formato que o proprio SQLite grava via CURRENT_TIMESTAMP (usado pelo
    TimestampMixin) - misturar datetime "aware" (com tzinfo) e "naive" no
    mesmo lugar levanta erro em Python e gera bugs sutis de comparacao.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro."""
    senha_bytes = senha.encode("utf-8")
    if len(senha_bytes) > _BCRYPT_MAX_BYTES:
        raise SenhaMuitoLongaError(
            f"Senha excede o limite de {_BCRYPT_MAX_BYTES} bytes suportado pelo bcrypt."
        )
    # gensalt() sem argumento usa o work factor padrao do bcrypt instalado
    # (12) - caro o suficiente pra dificultar forca bruta sem deixar o
    # login perceptivelmente lento.
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere se `senha` corresponde ao hash armazenado. Nunca levanta
    excecao para senha errada - so retorna False (quem decide o que fazer
    com isso e o AuthService, nunca este modulo)."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        # hash malformado/corrompido - trata como "nao confere", nunca
        # deixa a excecao vazar detalhe interno pro chamador.
        return False


def gerar_token_sessao() -> str:
    """Gera o valor bruto de um refresh token: uma string aleatoria de alta
    entropia (256 bits), NAO um JWT. So o cliente guarda esse valor - o
    banco guarda apenas o hash dele (ver hash_token_sessao). Ser opaco (sem
    conteudo decodificavel) e deliberado: a UNICA forma de validar um
    refresh token e consultar o banco, o que torna a revogacao (logout)
    real e imediata, sem as limitacoes de um JWT auto-contido.
    """
    return secrets.token_urlsafe(32)


def hash_token_sessao(token: str) -> str:
    """Hash do token de sessao para guardar em SessaoUsuario.token_hash.

    Diferente da senha, um refresh token ja e um segredo de alta entropia
    gerado por `secrets` (nao uma senha escolhida por humano, fraca por
    natureza) - entao nao precisa do custo computacional proposital do
    bcrypt. Um hash rapido e criptograficamente forte (SHA-256) e
    suficiente aqui e evita gastar CPU a toa a cada refresh.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenAcessoGerado(NamedTuple):
    """Retorno de criar_access_token: o token em si mais metadados seguros
    de logar (jti, expira_em) sem precisar decodificar o token de novo."""

    token: str
    jti: str
    expira_em: datetime


class TokenInvalidoError(Exception):
    """Token ausente, mal formado, expirado, com assinatura invalida, ou do
    tipo errado (ex: um token que nao e access sendo usado como um). E um
    erro de baixo nivel - quem chama (AuthService/get_current_user) traduz
    para NaoAutenticadoError, a excecao de dominio."""


def _chave_assinatura() -> str:
    """Unico ponto de resolucao da chave de assinatura JWT.

    Hoje sempre retorna settings.SECRET_KEY. Quando a rotacao de chaves for
    implementada (mais de uma chave valida ao mesmo tempo, identificadas
    por settings.JWT_KEY_ID no header "kid" do token), so esta funcao
    precisa mudar - pra escolher a chave certa por "kid" na verificacao, e
    a chave mais nova na criacao. Nenhum outro lugar deste modulo (nem fora
    dele) deveria saber de onde a chave vem.
    """
    return settings.SECRET_KEY


def criar_access_token(usuario_id: int, papel: str) -> TokenAcessoGerado:
    """Cria um access token JWT de vida curta.

    Claims:
      sub   - id do usuario (string, convencao do JWT)
      papel - papel do usuario no momento da emissao (ver exigir_papel em deps.py)
      type  - "access", distingue de um refresh token (que NAO e JWT neste
              projeto - ver gerar_token_sessao)
      jti   - id unico deste token, seguro de logar (nunca o token inteiro)
      iat/exp - emissao e expiracao, ambos controlados por settings
              (nunca um numero magico espalhado pelo codigo)

    O header "kid" (settings.JWT_KEY_ID) identifica qual chave assinou o
    token - preparo para rotacao futura (ver _chave_assinatura).
    """
    agora = datetime.now(timezone.utc)
    expira_em = agora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(usuario_id),
        "papel": papel,
        "type": "access",
        "jti": jti,
        "iat": agora,
        "exp": expira_em,
    }
    token = jwt.encode(
        payload,
        _chave_assinatura(),
        algorithm=settings.JWT_ALGORITHM,
        headers={"kid": settings.JWT_KEY_ID},
    )
    return TokenAcessoGerado(token=token, jti=jti, expira_em=expira_em)


def decodificar_access_token(token: str) -> dict:
    """Decodifica e valida um access token. Levanta TokenInvalidoError para
    qualquer problema (assinatura invalida, expirado, tipo errado) - nunca
    devolve um payload parcialmente confiavel."""
    try:
        payload = jwt.decode(token, _chave_assinatura(), algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenInvalidoError(str(exc)) from exc

    if payload.get("type") != "access":
        raise TokenInvalidoError("Token nao e um access token.")

    return payload
