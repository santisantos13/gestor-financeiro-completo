"""Router de Parcelamento: CRUD protegido, isolado por usuário autenticado.

Sem `PATCH` genérico (campos estruturais são imutáveis após a criação) e
sem `DELETE` físico (hard delete de um Parcelamento com parcelas geradas
quebraria a integridade de `Transacao` - ver
docs/analise-arquitetural-parcelamento.md). A única transição de estado é
a ação explícita `POST /{id}/cancelar`, mesmo estilo já usado em
`Fatura`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_parcelamento_service
from app.schemas.parcelamento import ParcelamentoCreate, ParcelamentoRead
from app.services.parcelamento_service import ParcelamentoService

router = APIRouter(prefix="/parcelamentos", tags=["parcelamentos"])

ParcelamentoServiceDep = Annotated[ParcelamentoService, Depends(get_parcelamento_service)]


@router.post("", response_model=ParcelamentoRead, status_code=status.HTTP_201_CREATED)
def criar_parcelamento(
    dados: ParcelamentoCreate, usuario_atual: CurrentUser, parcelamento_service: ParcelamentoServiceDep
) -> ParcelamentoRead:
    parcelamento = parcelamento_service.criar(dados, usuario_atual.id)
    return ParcelamentoRead.model_validate(parcelamento)


@router.get("", response_model=list[ParcelamentoRead])
def listar_parcelamentos(
    usuario_atual: CurrentUser,
    parcelamento_service: ParcelamentoServiceDep,
    apenas_ativos: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[ParcelamentoRead]:
    parcelamentos = parcelamento_service.listar(
        usuario_atual.id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
    )
    return [ParcelamentoRead.model_validate(parcelamento) for parcelamento in parcelamentos]


@router.get("/{parcelamento_id}", response_model=ParcelamentoRead)
def obter_parcelamento(
    parcelamento_id: int, usuario_atual: CurrentUser, parcelamento_service: ParcelamentoServiceDep
) -> ParcelamentoRead:
    parcelamento = parcelamento_service.obter(parcelamento_id, usuario_atual.id)
    return ParcelamentoRead.model_validate(parcelamento)


@router.post("/{parcelamento_id}/cancelar", response_model=ParcelamentoRead)
def cancelar_parcelamento(
    parcelamento_id: int, usuario_atual: CurrentUser, parcelamento_service: ParcelamentoServiceDep
) -> ParcelamentoRead:
    parcelamento = parcelamento_service.cancelar(parcelamento_id, usuario_atual.id)
    return ParcelamentoRead.model_validate(parcelamento)
