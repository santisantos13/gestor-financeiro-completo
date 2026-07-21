"""Router de Anexo: CRUD protegido (sem PATCH - decisão explícita, ver
docs/analise-arquitetural-anexo.md), posse sempre transitiva via Transacao.

Nenhuma rota aceita `usuario_id` no payload - vem sempre de `usuario_atual`
(CurrentUser), e a posse de `transacao_id` é sempre validada por
`AnexoService` reaproveitando `TransacaoService`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_anexo_service
from app.schemas.anexo import AnexoCreate, AnexoRead
from app.services.anexo_service import AnexoService

router = APIRouter(prefix="/anexos", tags=["anexos"])

AnexoServiceDep = Annotated[AnexoService, Depends(get_anexo_service)]


@router.post("", response_model=AnexoRead, status_code=status.HTTP_201_CREATED)
def criar_anexo(dados: AnexoCreate, usuario_atual: CurrentUser, anexo_service: AnexoServiceDep) -> AnexoRead:
    anexo = anexo_service.criar(dados, usuario_atual.id)
    return AnexoRead.model_validate(anexo)


@router.get("", response_model=list[AnexoRead])
def listar_anexos(
    transacao_id: int,
    usuario_atual: CurrentUser,
    anexo_service: AnexoServiceDep,
    apenas_ativos: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[AnexoRead]:
    anexos = anexo_service.listar_por_transacao(
        transacao_id, usuario_atual.id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
    )
    return [AnexoRead.model_validate(anexo) for anexo in anexos]


@router.get("/{anexo_id}", response_model=AnexoRead)
def obter_anexo(anexo_id: int, usuario_atual: CurrentUser, anexo_service: AnexoServiceDep) -> AnexoRead:
    anexo = anexo_service.obter(anexo_id, usuario_atual.id)
    return AnexoRead.model_validate(anexo)


@router.delete("/{anexo_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_anexo(anexo_id: int, usuario_atual: CurrentUser, anexo_service: AnexoServiceDep) -> None:
    anexo_service.desativar(anexo_id, usuario_atual.id)
