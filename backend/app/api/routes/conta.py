"""Router de Conta: CRUD protegido, isolado por usuário autenticado.

Nenhuma rota aceita ou expõe `usuario_id` no payload - ele vem sempre de
`usuario_atual` (CurrentUser), nunca do cliente, para um usuário nunca
conseguir criar/ler/alterar dado em nome de outro só manipulando o corpo
da requisição.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_conta_service
from app.schemas.conta import ContaCreate, ContaExtratoRead, ContaRead, ContaUpdate
from app.services.conta_service import ContaService

router = APIRouter(prefix="/contas", tags=["contas"])

ContaServiceDep = Annotated[ContaService, Depends(get_conta_service)]


@router.post("", response_model=ContaRead, status_code=status.HTTP_201_CREATED)
def criar_conta(dados: ContaCreate, usuario_atual: CurrentUser, conta_service: ContaServiceDep) -> ContaRead:
    conta = conta_service.criar(dados, usuario_atual.id)
    return ContaRead.model_validate(conta)


@router.get("", response_model=list[ContaRead])
def listar_contas(
    usuario_atual: CurrentUser,
    conta_service: ContaServiceDep,
    apenas_ativas: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[ContaRead]:
    contas = conta_service.listar(usuario_atual.id, apenas_ativas=apenas_ativas, skip=skip, limit=limit)
    return [ContaRead.model_validate(conta) for conta in contas]


@router.get("/{conta_id}", response_model=ContaRead)
def obter_conta(conta_id: int, usuario_atual: CurrentUser, conta_service: ContaServiceDep) -> ContaRead:
    conta = conta_service.obter(conta_id, usuario_atual.id)
    return ContaRead.model_validate(conta)


@router.get("/{conta_id}/extrato", response_model=ContaExtratoRead)
def obter_extrato_conta(
    conta_id: int,
    usuario_atual: CurrentUser,
    conta_service: ContaServiceDep,
    ano: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> ContaExtratoRead:
    """Painel "extrato bancário" da Conta - pedido explícito do usuário
    (docs/analise-arquitetural-extrato-conta.md). `ano`/`mes` opcionais,
    default = mês atual (mesma convenção de
    `GET /central-financeira/calendario`)."""
    return conta_service.extrato(conta_id, usuario_atual.id, ano=ano, mes=mes)


@router.patch("/{conta_id}", response_model=ContaRead)
def atualizar_conta(
    conta_id: int, dados: ContaUpdate, usuario_atual: CurrentUser, conta_service: ContaServiceDep
) -> ContaRead:
    conta = conta_service.atualizar(conta_id, dados, usuario_atual.id)
    return ContaRead.model_validate(conta)


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_conta(conta_id: int, usuario_atual: CurrentUser, conta_service: ContaServiceDep) -> None:
    conta_service.desativar(conta_id, usuario_atual.id)


@router.delete("/{conta_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_conta_permanente(
    conta_id: int,
    usuario_atual: CurrentUser,
    conta_service: ContaServiceDep,
    apagar_vinculos: Annotated[bool, Query()] = False,
) -> None:
    """Exclusão definitiva (hard delete) - Etapa F10,
    `docs/analise-arquitetural-exclusao.md`, seção 1. Rota nova (não
    reaproveita `DELETE /{conta_id}` acima, que já significa "desativar").

    `apagar_vinculos=true` (pedido explícito do usuário, ver
    docs/analise-arquitetural-exclusao-conta-com-historico.md): quando a
    conta tem qualquer vínculo (transações, transferências, cartões,
    financiamentos/empréstimos, recorrências), em vez de bloquear com 422,
    apaga tudo isso junto com a conta. Default `False` preserva o
    comportamento original. Não tem efeito sobre conta oculta (cofrinho de
    Meta) - essa continua sempre bloqueada."""
    conta_service.excluir(conta_id, usuario_atual.id, apagar_vinculos=apagar_vinculos)
