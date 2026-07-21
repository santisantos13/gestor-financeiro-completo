"""Router de Cartao: CRUD protegido, isolado por usuário autenticado.

Nenhuma rota aceita ou expõe `usuario_id` no payload - ele vem sempre de
`usuario_atual` (CurrentUser), nunca do cliente, mesmo padrão de
Conta/Categoria/Tag.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_cartao_service
from app.schemas.cartao import CartaoCreate, CartaoRead, CartaoUpdate
from app.services.cartao_service import CartaoService

router = APIRouter(prefix="/cartoes", tags=["cartoes"])

CartaoServiceDep = Annotated[CartaoService, Depends(get_cartao_service)]


@router.post("", response_model=CartaoRead, status_code=status.HTTP_201_CREATED)
def criar_cartao(
    dados: CartaoCreate, usuario_atual: CurrentUser, cartao_service: CartaoServiceDep
) -> CartaoRead:
    cartao = cartao_service.criar(dados, usuario_atual.id)
    return CartaoRead.model_validate(cartao)


@router.get("", response_model=list[CartaoRead])
def listar_cartoes(
    usuario_atual: CurrentUser,
    cartao_service: CartaoServiceDep,
    apenas_ativos: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[CartaoRead]:
    cartoes = cartao_service.listar(usuario_atual.id, apenas_ativos=apenas_ativos, skip=skip, limit=limit)
    return [CartaoRead.model_validate(cartao) for cartao in cartoes]


@router.get("/{cartao_id}", response_model=CartaoRead)
def obter_cartao(cartao_id: int, usuario_atual: CurrentUser, cartao_service: CartaoServiceDep) -> CartaoRead:
    cartao = cartao_service.obter(cartao_id, usuario_atual.id)
    return CartaoRead.model_validate(cartao)


@router.patch("/{cartao_id}", response_model=CartaoRead)
def atualizar_cartao(
    cartao_id: int, dados: CartaoUpdate, usuario_atual: CurrentUser, cartao_service: CartaoServiceDep
) -> CartaoRead:
    cartao = cartao_service.atualizar(cartao_id, dados, usuario_atual.id)
    return CartaoRead.model_validate(cartao)


@router.delete("/{cartao_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_cartao(cartao_id: int, usuario_atual: CurrentUser, cartao_service: CartaoServiceDep) -> None:
    cartao_service.desativar(cartao_id, usuario_atual.id)


@router.delete("/{cartao_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cartao_permanente(
    cartao_id: int,
    usuario_atual: CurrentUser,
    cartao_service: CartaoServiceDep,
    apagar_transacoes: Annotated[bool, Query()] = False,
) -> None:
    """Exclusão definitiva (hard delete) - Etapa F10,
    `docs/analise-arquitetural-exclusao.md`, seção 1.

    `apagar_transacoes=true` (pedido explícito do usuário, ver
    docs/analise-arquitetural-exclusao-cartao-com-historico.md): quando o
    cartão tem fatura vinculada, em vez de bloquear com 422, apaga as
    faturas e as transações feitas neste cartão junto com ele. Default
    `False` preserva o comportamento original."""
    cartao_service.excluir(cartao_id, usuario_atual.id, apagar_transacoes=apagar_transacoes)
