"""Router de Emprestimo: CRUD protegido, isolado por usuário autenticado.

Sem `PATCH` genérico (campos estruturais determinam o cronograma inteiro,
imutáveis após a criação). `DELETE /{id}` existe e é sempre permitido,
mesmo com parcelas já pagas - as parcelas/desembolso nunca são apagados,
só perdem o vínculo com o contrato (`emprestimo_id`/`numero_parcela`
desvinculados explicitamente em `EmprestimoService.excluir`, não só via
`ondelete=SET NULL` do banco - ver docstring lá). A única transição de
estado é a ação
explícita `POST /{id}/parcelas/{numero_parcela}/pagar` - nunca
`PATCH /transacoes/{id}` (bloqueado em `TransacaoService` para transações
de contrato de crédito). Ver docs/analise-arquitetural-emprestimo.md.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_emprestimo_service
from app.schemas.emprestimo import EmprestimoCreate, EmprestimoRead
from app.services.emprestimo_service import EmprestimoService

router = APIRouter(prefix="/emprestimos", tags=["emprestimos"])

EmprestimoServiceDep = Annotated[EmprestimoService, Depends(get_emprestimo_service)]


@router.post("", response_model=EmprestimoRead, status_code=status.HTTP_201_CREATED)
def criar_emprestimo(
    dados: EmprestimoCreate, usuario_atual: CurrentUser, emprestimo_service: EmprestimoServiceDep
) -> EmprestimoRead:
    emprestimo = emprestimo_service.criar(dados, usuario_atual.id)
    return EmprestimoRead.model_validate(emprestimo)


@router.get("", response_model=list[EmprestimoRead])
def listar_emprestimos(
    usuario_atual: CurrentUser,
    emprestimo_service: EmprestimoServiceDep,
    apenas_ativos: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[EmprestimoRead]:
    emprestimos = emprestimo_service.listar(
        usuario_atual.id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
    )
    return [EmprestimoRead.model_validate(emprestimo) for emprestimo in emprestimos]


@router.get("/{emprestimo_id}", response_model=EmprestimoRead)
def obter_emprestimo(
    emprestimo_id: int, usuario_atual: CurrentUser, emprestimo_service: EmprestimoServiceDep
) -> EmprestimoRead:
    emprestimo = emprestimo_service.obter(emprestimo_id, usuario_atual.id)
    return EmprestimoRead.model_validate(emprestimo)


@router.delete("/{emprestimo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_emprestimo(
    emprestimo_id: int, usuario_atual: CurrentUser, emprestimo_service: EmprestimoServiceDep
) -> None:
    emprestimo_service.excluir(emprestimo_id, usuario_atual.id)


@router.post("/{emprestimo_id}/parcelas/{numero_parcela}/pagar", response_model=EmprestimoRead)
def pagar_parcela_emprestimo(
    emprestimo_id: int,
    numero_parcela: int,
    usuario_atual: CurrentUser,
    emprestimo_service: EmprestimoServiceDep,
) -> EmprestimoRead:
    emprestimo = emprestimo_service.pagar_parcela(emprestimo_id, numero_parcela, usuario_atual.id)
    return EmprestimoRead.model_validate(emprestimo)
