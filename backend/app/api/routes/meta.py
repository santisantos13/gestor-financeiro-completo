"""Router de Meta: CRUD protegido.

Nenhuma rota aceita `usuario_id` no payload - vem sempre de `usuario_atual`
(CurrentUser). Diferente de Financiamento/Empréstimo, Meta tem `PATCH`
(nenhum campo aqui determina um cronograma imutável gerado na criação).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_meta_service
from app.schemas.meta import MetaCreate, MetaRead, MetaUpdate
from app.services.meta_service import MetaService

router = APIRouter(prefix="/metas", tags=["metas"])

MetaServiceDep = Annotated[MetaService, Depends(get_meta_service)]


@router.post("", response_model=MetaRead, status_code=status.HTTP_201_CREATED)
def criar_meta(dados: MetaCreate, usuario_atual: CurrentUser, meta_service: MetaServiceDep) -> MetaRead:
    meta = meta_service.criar(dados, usuario_atual.id)
    return MetaRead.model_validate(meta)


@router.get("", response_model=list[MetaRead])
def listar_metas(
    usuario_atual: CurrentUser,
    meta_service: MetaServiceDep,
    apenas_ativas: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[MetaRead]:
    metas = meta_service.listar(usuario_atual.id, apenas_ativas=apenas_ativas, skip=skip, limit=limit)
    return [MetaRead.model_validate(meta) for meta in metas]


@router.get("/{meta_id}", response_model=MetaRead)
def obter_meta(meta_id: int, usuario_atual: CurrentUser, meta_service: MetaServiceDep) -> MetaRead:
    meta = meta_service.obter(meta_id, usuario_atual.id)
    return MetaRead.model_validate(meta)


@router.patch("/{meta_id}", response_model=MetaRead)
def atualizar_meta(
    meta_id: int, dados: MetaUpdate, usuario_atual: CurrentUser, meta_service: MetaServiceDep
) -> MetaRead:
    meta = meta_service.atualizar(meta_id, dados, usuario_atual.id)
    return MetaRead.model_validate(meta)


@router.delete("/{meta_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_meta(meta_id: int, usuario_atual: CurrentUser, meta_service: MetaServiceDep) -> None:
    meta_service.desativar(meta_id, usuario_atual.id)


@router.delete("/{meta_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_meta_permanente(meta_id: int, usuario_atual: CurrentUser, meta_service: MetaServiceDep) -> None:
    """Exclusão definitiva (hard delete) - nunca bloqueada por aportes
    vinculados (mesmo padrão de Fatura/Cartão)."""
    meta_service.excluir(meta_id, usuario_atual.id)
