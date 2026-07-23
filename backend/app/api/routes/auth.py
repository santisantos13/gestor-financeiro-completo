"""Router de autenticação: registro, login, refresh, logout (escopado e
global) e "quem sou eu".

Cada rota só valida o schema e delega para AuthService - nenhuma decisão
(o que é válido, o que gera token, o que é revogado) mora aqui. Nenhum
try/except: erros de negócio viram HTTP pelos handlers globais registrados
em app/main.py.

A instância de AuthService vem sempre de `Depends(get_auth_service)`
(app/api/deps.py) - essa é a ÚNICA forma oficial de obtê-la neste projeto,
o mesmo padrão que será usado por todo Service de domínio futuro
(get_conta_service etc.). Nenhuma rota constrói AuthService na mão.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CurrentUser, get_auth_service
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    PerfilUpdate,
    RefreshRequest,
    TokenResponse,
    TrocarSenhaRequest,
    UsuarioCreate,
    UsuarioRead,
)
from app.services.auth_service import AuthService, ContextoRequisicao

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def _contexto(request: Request) -> ContextoRequisicao:
    return ContextoRequisicao(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )


@router.post("/registrar", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def registrar(dados: UsuarioCreate, auth_service: AuthServiceDep) -> UsuarioRead:
    usuario = auth_service.registrar(dados)
    return UsuarioRead.model_validate(usuario)


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, request: Request, auth_service: AuthServiceDep) -> TokenResponse:
    # TODO(rate-limit): endpoint sensível a força bruta de credenciais.
    # Quando o rate limiting for implementado, a dependency entra aqui,
    # ex: `Depends(rate_limit("5/minute", chave=dados.email))`, seguindo o
    # mesmo padrão de injeção de dependência já usado no resto do projeto.
    return auth_service.autenticar(dados, _contexto(request))


@router.post("/refresh", response_model=TokenResponse)
def refresh(dados: RefreshRequest, request: Request, auth_service: AuthServiceDep) -> TokenResponse:
    # TODO(rate-limit): mesmo motivo do /login - um refresh token vazado
    # não deveria poder ser testado em loop sem limite.
    # contexto vem da requisicao de refresh ATUAL, nunca da sessao antiga
    # (ver docstring de AuthService.renovar) - por isso Request é
    # obrigatório aqui, igual em /login.
    return auth_service.renovar(dados, _contexto(request))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(dados: LogoutRequest, usuario_atual: CurrentUser, auth_service: AuthServiceDep) -> None:
    auth_service.logout(usuario_atual, dados)


@router.post("/logout-todas", status_code=status.HTTP_204_NO_CONTENT)
def logout_todas(usuario_atual: CurrentUser, auth_service: AuthServiceDep) -> None:
    auth_service.logout_todas(usuario_atual)


@router.get("/me", response_model=UsuarioRead)
def me(usuario_atual: CurrentUser) -> UsuarioRead:
    return UsuarioRead.model_validate(usuario_atual)


@router.patch("/me", response_model=UsuarioRead)
def atualizar_perfil(
    dados: PerfilUpdate, usuario_atual: CurrentUser, auth_service: AuthServiceDep
) -> UsuarioRead:
    usuario = auth_service.atualizar_perfil(usuario_atual, dados)
    return UsuarioRead.model_validate(usuario)


@router.post("/trocar-senha", status_code=status.HTTP_204_NO_CONTENT)
def trocar_senha(
    dados: TrocarSenhaRequest, usuario_atual: CurrentUser, auth_service: AuthServiceDep
) -> None:
    auth_service.trocar_senha(usuario_atual, dados)
