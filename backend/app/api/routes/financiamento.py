"""Router de Financiamento: CRUD protegido, isolado por usuário autenticado.

Sem `PATCH` genérico (campos estruturais determinam o cronograma de
amortização inteiro, imutáveis após a criação). `DELETE /{id}` existe
(Tarefa "excluir financiamento") e é sempre permitido, mesmo com parcelas
já pagas - as parcelas nunca são apagadas, só perdem o vínculo com o
contrato (`financiamento_id`/`numero_parcela` desvinculados explicitamente
em `FinanciamentoService.excluir`, não só via `ondelete=SET NULL` do banco -
ver docstring lá). A única transição de estado é a ação
explícita `POST /{id}/parcelas/{numero_parcela}/pagar` - nunca
`PATCH /transacoes/{id}` (bloqueado em `TransacaoService` para transações
de contrato de crédito).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_financiamento_service
from app.schemas.financiamento import FinanciamentoCreate, FinanciamentoRead
from app.services.financiamento_service import FinanciamentoService

router = APIRouter(prefix="/financiamentos", tags=["financiamentos"])

FinanciamentoServiceDep = Annotated[FinanciamentoService, Depends(get_financiamento_service)]


@router.post("", response_model=FinanciamentoRead, status_code=status.HTTP_201_CREATED)
def criar_financiamento(
    dados: FinanciamentoCreate, usuario_atual: CurrentUser, financiamento_service: FinanciamentoServiceDep
) -> FinanciamentoRead:
    financiamento = financiamento_service.criar(dados, usuario_atual.id)
    return FinanciamentoRead.model_validate(financiamento)


@router.get("", response_model=list[FinanciamentoRead])
def listar_financiamentos(
    usuario_atual: CurrentUser,
    financiamento_service: FinanciamentoServiceDep,
    apenas_ativos: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[FinanciamentoRead]:
    financiamentos = financiamento_service.listar(
        usuario_atual.id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
    )
    return [FinanciamentoRead.model_validate(financiamento) for financiamento in financiamentos]


@router.get("/{financiamento_id}", response_model=FinanciamentoRead)
def obter_financiamento(
    financiamento_id: int, usuario_atual: CurrentUser, financiamento_service: FinanciamentoServiceDep
) -> FinanciamentoRead:
    financiamento = financiamento_service.obter(financiamento_id, usuario_atual.id)
    return FinanciamentoRead.model_validate(financiamento)


@router.delete("/{financiamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_financiamento(
    financiamento_id: int, usuario_atual: CurrentUser, financiamento_service: FinanciamentoServiceDep
) -> None:
    financiamento_service.excluir(financiamento_id, usuario_atual.id)


@router.post("/{financiamento_id}/parcelas/{numero_parcela}/pagar", response_model=FinanciamentoRead)
def pagar_parcela_financiamento(
    financiamento_id: int,
    numero_parcela: int,
    usuario_atual: CurrentUser,
    financiamento_service: FinanciamentoServiceDep,
) -> FinanciamentoRead:
    financiamento = financiamento_service.pagar_parcela(financiamento_id, numero_parcela, usuario_atual.id)
    return FinanciamentoRead.model_validate(financiamento)
