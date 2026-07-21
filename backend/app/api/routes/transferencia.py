"""Router de Transferencia: CRUD protegido, isolado por usuário autenticado.

Sem `PATCH` (campos estruturais - contas e valor - são imutáveis após a
criação) e sem `DELETE` físico (uma transferência incorreta é preservada
como histórico, nunca apagada - ver docstring de `Transferencia.ativo`). A
única transição de estado é a ação explícita `POST /{id}/cancelar`, mesmo
estilo já usado em `Fatura`/`Parcelamento`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_transferencia_service
from app.schemas.transferencia import TransferenciaCreate, TransferenciaRead
from app.services.transferencia_service import TransferenciaService

router = APIRouter(prefix="/transferencias", tags=["transferencias"])

TransferenciaServiceDep = Annotated[TransferenciaService, Depends(get_transferencia_service)]


@router.post("", response_model=TransferenciaRead, status_code=status.HTTP_201_CREATED)
def criar_transferencia(
    dados: TransferenciaCreate, usuario_atual: CurrentUser, transferencia_service: TransferenciaServiceDep
) -> TransferenciaRead:
    transferencia = transferencia_service.criar(dados, usuario_atual.id)
    return TransferenciaRead.model_validate(transferencia)


@router.get("", response_model=list[TransferenciaRead])
def listar_transferencias(
    usuario_atual: CurrentUser,
    transferencia_service: TransferenciaServiceDep,
    apenas_ativas: bool = True,
    conta_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TransferenciaRead]:
    transferencias = transferencia_service.listar(
        usuario_atual.id, apenas_ativas=apenas_ativas, conta_id=conta_id, skip=skip, limit=limit
    )
    return [TransferenciaRead.model_validate(transferencia) for transferencia in transferencias]


@router.get("/{transferencia_id}", response_model=TransferenciaRead)
def obter_transferencia(
    transferencia_id: int, usuario_atual: CurrentUser, transferencia_service: TransferenciaServiceDep
) -> TransferenciaRead:
    transferencia = transferencia_service.obter(transferencia_id, usuario_atual.id)
    return TransferenciaRead.model_validate(transferencia)


@router.post("/{transferencia_id}/cancelar", response_model=TransferenciaRead)
def cancelar_transferencia(
    transferencia_id: int, usuario_atual: CurrentUser, transferencia_service: TransferenciaServiceDep
) -> TransferenciaRead:
    transferencia = transferencia_service.cancelar(transferencia_id, usuario_atual.id)
    return TransferenciaRead.model_validate(transferencia)
