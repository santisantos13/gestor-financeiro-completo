"""Testes unitários de app/core/security.py - funções criptográficas puras,
sem tocar em banco ou HTTP. Cobrem o que a OWASP considera básico pra este
tipo de função: senha errada nunca confere, token adulterado/expirado/do
tipo errado é sempre rejeitado.
"""
from datetime import timedelta

import jwt
import pytest

from app.core import security


def test_hash_senha_gera_hash_diferente_da_senha_original():
    hash_gerado = security.hash_senha("minhasenha123")
    assert hash_gerado != "minhasenha123"
    assert hash_gerado.startswith("$2b$")  # prefixo padrao do bcrypt


def test_verificar_senha_aceita_senha_correta():
    hash_gerado = security.hash_senha("minhasenha123")
    assert security.verificar_senha("minhasenha123", hash_gerado) is True


def test_verificar_senha_rejeita_senha_errada():
    hash_gerado = security.hash_senha("minhasenha123")
    assert security.verificar_senha("outrasenha", hash_gerado) is False


def test_verificar_senha_com_hash_corrompido_retorna_false_sem_levantar_excecao():
    assert security.verificar_senha("qualquer", "isso-nao-e-um-hash-bcrypt-valido") is False


def test_hash_senha_recusa_senha_maior_que_limite_do_bcrypt():
    senha_longa = "a" * 73
    with pytest.raises(security.SenhaMuitoLongaError):
        security.hash_senha(senha_longa)


def test_gerar_token_sessao_produz_valores_diferentes_a_cada_chamada():
    assert security.gerar_token_sessao() != security.gerar_token_sessao()


def test_hash_token_sessao_e_deterministico():
    token = security.gerar_token_sessao()
    assert security.hash_token_sessao(token) == security.hash_token_sessao(token)


def test_hash_token_sessao_nao_e_reversivel_para_o_token_original():
    token = security.gerar_token_sessao()
    assert security.hash_token_sessao(token) != token


def test_criar_e_decodificar_access_token_roundtrip():
    gerado = security.criar_access_token(usuario_id=7, papel="USER")
    payload = security.decodificar_access_token(gerado.token)

    assert payload["sub"] == "7"
    assert payload["papel"] == "USER"
    assert payload["type"] == "access"
    assert payload["jti"] == gerado.jti


def test_decodificar_access_token_rejeita_token_adulterado():
    gerado = security.criar_access_token(usuario_id=7, papel="USER")
    # troca um caractere no MEIO da assinatura (nao o ultimo) - o ultimo
    # caractere de um base64url sem padding pode ter bits "nao usados" que
    # nem sempre mudam o byte decodificado, o que tornaria o teste instavel.
    meio = len(gerado.token) // 2
    caractere_trocado = "A" if gerado.token[meio] != "A" else "B"
    token_adulterado = gerado.token[:meio] + caractere_trocado + gerado.token[meio + 1 :]

    with pytest.raises(security.TokenInvalidoError):
        security.decodificar_access_token(token_adulterado)


def test_decodificar_access_token_rejeita_token_expirado():
    from datetime import datetime, timezone

    payload = {
        "sub": "7",
        "papel": "USER",
        "type": "access",
        "jti": "abc",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    from app.core.config import settings

    token_expirado = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(security.TokenInvalidoError):
        security.decodificar_access_token(token_expirado)


def test_decodificar_access_token_rejeita_token_que_nao_e_do_tipo_access():
    from datetime import datetime, timezone

    payload = {
        "sub": "7",
        "papel": "USER",
        "type": "refresh",  # tipo errado - so "access" deveria passar aqui
        "jti": "abc",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    from app.core.config import settings

    token_tipo_errado = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(security.TokenInvalidoError):
        security.decodificar_access_token(token_tipo_errado)


def test_decodificar_access_token_rejeita_assinatura_de_outra_chave():
    payload = {
        "sub": "7",
        "papel": "USER",
        "type": "access",
        "jti": "abc",
    }
    token_outra_chave = jwt.encode(payload, "chave-completamente-diferente", algorithm="HS256")

    with pytest.raises(security.TokenInvalidoError):
        security.decodificar_access_token(token_outra_chave)
