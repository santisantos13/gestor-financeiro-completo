"""Router de Tag: CRUD protegido.

Nenhuma rota aceita `usuario_id` no payload - vem sempre de `usuario_atual`
(CurrentUser).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_tag_service
from app.schemas.tag import TagCreate, TagRead, TagUpdate, TagUso
from app.services.tag_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])

TagServiceDep = Annotated[TagService, Depends(get_tag_service)]


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def criar_tag(dados: TagCreate, usuario_atual: CurrentUser, tag_service: TagServiceDep) -> TagRead:
    tag = tag_service.criar(dados, usuario_atual.id)
    return TagRead.model_validate(tag)


@router.get("", response_model=list[TagRead])
def listar_tags(
    usuario_atual: CurrentUser,
    tag_service: TagServiceDep,
    apenas_ativas: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[TagRead]:
    tags = tag_service.listar(usuario_atual.id, apenas_ativas=apenas_ativas, skip=skip, limit=limit)
    return [TagRead.model_validate(tag) for tag in tags]


@router.get("/{tag_id}", response_model=TagRead)
def obter_tag(tag_id: int, usuario_atual: CurrentUser, tag_service: TagServiceDep) -> TagRead:
    tag = tag_service.obter(tag_id, usuario_atual.id)
    return TagRead.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagRead)
def atualizar_tag(
    tag_id: int, dados: TagUpdate, usuario_atual: CurrentUser, tag_service: TagServiceDep
) -> TagRead:
    tag = tag_service.atualizar(tag_id, dados, usuario_atual.id)
    return TagRead.model_validate(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_tag(tag_id: int, usuario_atual: CurrentUser, tag_service: TagServiceDep) -> None:
    tag_service.desativar(tag_id, usuario_atual.id)


@router.get("/{tag_id}/uso", response_model=TagUso)
def obter_uso_tag(tag_id: int, usuario_atual: CurrentUser, tag_service: TagServiceDep) -> TagUso:
    """Consultado pelo frontend antes de confirmar a exclusão definitiva
    - Etapa F10, `docs/analise-arquitetural-exclusao.md`, seção 2.3."""
    return TagUso(transacoes_vinculadas=tag_service.contar_uso(tag_id, usuario_atual.id))


@router.delete("/{tag_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_tag_permanente(tag_id: int, usuario_atual: CurrentUser, tag_service: TagServiceDep) -> None:
    """Exclusão definitiva (hard delete) - Etapa F10,
    `docs/analise-arquitetural-exclusao.md`, seção 1."""
    tag_service.excluir(tag_id, usuario_atual.id)
