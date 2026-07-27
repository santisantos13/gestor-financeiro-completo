"""Router de Alerta: CRUD protegido.

Nenhuma rota aceita `usuario_id` no payload - vem sempre de `usuario_atual`
(`CurrentUser`). Diferente de Meta/Financiamento, não existe uma rota de
"desativar" (soft delete) separada: `ativo` já é um campo comum do
`AlertaUpdate` (pausar/reativar é só um `PATCH`), então `DELETE` aqui é
sempre a exclusão definitiva (mesmo raciocínio de `entidade_tipo`/
`tipo` serem imutáveis - ver docstring de `AlertaUpdate`).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_alerta_service
from app.schemas.alerta import AlertaCreate, AlertaRead, AlertaUpdate
from app.services.alerta_service import AlertaService

router = APIRouter(prefix="/alertas", tags=["alertas"])

AlertaServiceDep = Annotated[AlertaService, Depends(get_alerta_service)]


@router.post("", response_model=AlertaRead, status_code=status.HTTP_201_CREATED)
def criar_alerta(dados: AlertaCreate, usuario_atual: CurrentUser, alerta_service: AlertaServiceDep) -> AlertaRead:
    alerta = alerta_service.criar(dados, usuario_atual.id)
    return AlertaRead.model_validate(alerta)


@router.get("", response_model=list[AlertaRead])
def listar_alertas(
    usuario_atual: CurrentUser, alerta_service: AlertaServiceDep, apenas_ativos: bool = False
) -> list[AlertaRead]:
    alertas = alerta_service.listar(usuario_atual.id, apenas_ativos=apenas_ativos)
    return [AlertaRead.model_validate(alerta) for alerta in alertas]


@router.get("/{alerta_id}", response_model=AlertaRead)
def obter_alerta(alerta_id: int, usuario_atual: CurrentUser, alerta_service: AlertaServiceDep) -> AlertaRead:
    alerta = alerta_service.obter(alerta_id, usuario_atual.id)
    return AlertaRead.model_validate(alerta)


@router.patch("/{alerta_id}", response_model=AlertaRead)
def atualizar_alerta(
    alerta_id: int, dados: AlertaUpdate, usuario_atual: CurrentUser, alerta_service: AlertaServiceDep
) -> AlertaRead:
    alerta = alerta_service.atualizar(alerta_id, dados, usuario_atual.id)
    return AlertaRead.model_validate(alerta)


@router.delete("/{alerta_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_alerta(alerta_id: int, usuario_atual: CurrentUser, alerta_service: AlertaServiceDep) -> None:
    alerta_service.excluir(alerta_id, usuario_atual.id)
