"""Router de ContaRecorrente: CRUD protegido, isolado por usuário autenticado.

Ciclo de vida por ações explícitas (expansão 2026-07-20,
docs/analise-arquitetural-conta-recorrente-expansao.md):
`POST /{id}/pausar`, `POST /{id}/reativar` (nunca gera retroativos),
`POST /{id}/encerrar`. `DELETE /{id}` NÃO apaga fisicamente - encerra
(status=ENCERRADA), preservando histórico e transações já geradas (decisão
explícita do usuário).

Geração é SEMPRE sob demanda: `POST /{id}/gerar-ocorrencias-pendentes`
(um template) e `POST /sincronizar` (todos os ativos do usuário - chamado
pelo frontend uma vez por sessão, a UX de "geração automática" sem nenhum
scheduler).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_conta_recorrente_service
from app.models.enums import StatusRecorrencia
from app.schemas.conta_recorrente import (
    ContaRecorrenteCreate,
    ContaRecorrenteRead,
    ContaRecorrenteUpdate,
    SincronizacaoRecorrentesResult,
)
from app.schemas.transacao import TransacaoRead
from app.services.conta_recorrente_service import ContaRecorrenteService

router = APIRouter(prefix="/contas-recorrentes", tags=["contas-recorrentes"])

ContaRecorrenteServiceDep = Annotated[ContaRecorrenteService, Depends(get_conta_recorrente_service)]


@router.post("", response_model=ContaRecorrenteRead, status_code=status.HTTP_201_CREATED)
def criar_conta_recorrente(
    dados: ContaRecorrenteCreate,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> ContaRecorrenteRead:
    conta_recorrente = conta_recorrente_service.criar(dados, usuario_atual.id)
    return ContaRecorrenteRead.model_validate(conta_recorrente)


@router.get("", response_model=list[ContaRecorrenteRead])
def listar_contas_recorrentes(
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
    status_filtro: StatusRecorrencia | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[ContaRecorrenteRead]:
    """`status_filtro` omitido lista TUDO (inclusive encerradas - são
    histórico, nunca somem)."""
    contas_recorrentes = conta_recorrente_service.listar(
        usuario_atual.id, status=status_filtro, skip=skip, limit=limit
    )
    return [ContaRecorrenteRead.model_validate(cr) for cr in contas_recorrentes]


@router.post("/sincronizar", response_model=SincronizacaoRecorrentesResult)
def sincronizar_recorrentes(
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> SincronizacaoRecorrentesResult:
    resultado = conta_recorrente_service.sincronizar(usuario_atual.id)
    return SincronizacaoRecorrentesResult(**resultado)


@router.get("/{conta_recorrente_id}", response_model=ContaRecorrenteRead)
def obter_conta_recorrente(
    conta_recorrente_id: int,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> ContaRecorrenteRead:
    conta_recorrente = conta_recorrente_service.obter(conta_recorrente_id, usuario_atual.id)
    return ContaRecorrenteRead.model_validate(conta_recorrente)


@router.patch("/{conta_recorrente_id}", response_model=ContaRecorrenteRead)
def atualizar_conta_recorrente(
    conta_recorrente_id: int,
    dados: ContaRecorrenteUpdate,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> ContaRecorrenteRead:
    conta_recorrente = conta_recorrente_service.atualizar(conta_recorrente_id, dados, usuario_atual.id)
    return ContaRecorrenteRead.model_validate(conta_recorrente)


@router.post("/{conta_recorrente_id}/pausar", response_model=ContaRecorrenteRead)
def pausar_conta_recorrente(
    conta_recorrente_id: int,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> ContaRecorrenteRead:
    conta_recorrente = conta_recorrente_service.pausar(conta_recorrente_id, usuario_atual.id)
    return ContaRecorrenteRead.model_validate(conta_recorrente)


@router.post("/{conta_recorrente_id}/reativar", response_model=ContaRecorrenteRead)
def reativar_conta_recorrente(
    conta_recorrente_id: int,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> ContaRecorrenteRead:
    """Nunca gera retroativos - o cursor pula para a próxima data futura
    (decisão do usuário, 2026-07-20)."""
    conta_recorrente = conta_recorrente_service.reativar(conta_recorrente_id, usuario_atual.id)
    return ContaRecorrenteRead.model_validate(conta_recorrente)


@router.post("/{conta_recorrente_id}/encerrar", response_model=ContaRecorrenteRead)
def encerrar_conta_recorrente(
    conta_recorrente_id: int,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> ContaRecorrenteRead:
    conta_recorrente = conta_recorrente_service.encerrar(conta_recorrente_id, usuario_atual.id)
    return ContaRecorrenteRead.model_validate(conta_recorrente)


@router.post("/{conta_recorrente_id}/gerar-ocorrencias-pendentes", response_model=list[TransacaoRead])
def gerar_ocorrencias_pendentes(
    conta_recorrente_id: int,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> list[TransacaoRead]:
    ocorrencias = conta_recorrente_service.gerar_ocorrencias_pendentes(conta_recorrente_id, usuario_atual.id)
    return [TransacaoRead.model_validate(ocorrencia) for ocorrencia in ocorrencias]


@router.delete("/{conta_recorrente_id}", status_code=status.HTTP_204_NO_CONTENT)
def encerrar_via_delete(
    conta_recorrente_id: int,
    usuario_atual: CurrentUser,
    conta_recorrente_service: ContaRecorrenteServiceDep,
) -> None:
    """DELETE = encerrar (nunca exclusão física) - preserva o template como
    histórico e todas as Transacoes já geradas (decisão do usuário,
    2026-07-20). O hard delete só existe dentro da cascata de exclusão de
    Conta."""
    conta_recorrente_service.encerrar(conta_recorrente_id, usuario_atual.id)
