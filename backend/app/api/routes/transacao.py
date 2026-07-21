"""Router de Transacao: CRUD protegido, isolado por usuário autenticado.

Nenhuma rota aceita ou expõe `usuario_id`, `fatura_id` ou `fatura_paga_id`
no payload - `usuario_id` vem sempre de `usuario_atual` (CurrentUser),
`fatura_id` é sempre resolvido internamente por `TransacaoService` (via
`FaturaService.resolver_fatura_aberta`), `fatura_paga_id` só é preenchido
pelo fluxo de pagamento de Fatura (`POST /faturas/{id}/pagamentos`), nunca
por aqui. `conta_id`/`cartao_id` são aceitos na criação mas não aparecem
em `TransacaoUpdate` - imutáveis após a criação (ver
docs/analise-arquitetural-transacao.md).
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_transacao_service
from app.models.enums import StatusTransacao, TipoTransacao
from app.schemas.transacao import TransacaoCreate, TransacaoRead, TransacaoUpdate
from app.services.transacao_service import TransacaoService

router = APIRouter(prefix="/transacoes", tags=["transacoes"])

TransacaoServiceDep = Annotated[TransacaoService, Depends(get_transacao_service)]


@router.post("", response_model=TransacaoRead, status_code=status.HTTP_201_CREATED)
def criar_transacao(
    dados: TransacaoCreate, usuario_atual: CurrentUser, transacao_service: TransacaoServiceDep
) -> TransacaoRead:
    transacao = transacao_service.criar(dados, usuario_atual.id)
    return TransacaoRead.model_validate(transacao)


@router.get("", response_model=list[TransacaoRead])
def listar_transacoes(
    usuario_atual: CurrentUser,
    transacao_service: TransacaoServiceDep,
    conta_id: int | None = None,
    cartao_id: int | None = None,
    fatura_id: int | None = None,
    categoria_id: int | None = None,
    parcelamento_id: int | None = None,
    financiamento_id: int | None = None,
    emprestimo_id: int | None = None,
    origem_recorrente_id: int | None = None,
    meta_id: int | None = None,
    tipo: TipoTransacao | None = None,
    status: StatusTransacao | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    apenas_conta: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[TransacaoRead]:
    transacoes = transacao_service.listar(
        usuario_atual.id,
        conta_id=conta_id,
        cartao_id=cartao_id,
        fatura_id=fatura_id,
        categoria_id=categoria_id,
        parcelamento_id=parcelamento_id,
        financiamento_id=financiamento_id,
        emprestimo_id=emprestimo_id,
        origem_recorrente_id=origem_recorrente_id,
        meta_id=meta_id,
        tipo=tipo,
        status=status,
        data_inicio=data_inicio,
        data_fim=data_fim,
        apenas_conta=apenas_conta,
        skip=skip,
        limit=limit,
    )
    return [TransacaoRead.model_validate(transacao) for transacao in transacoes]


@router.get("/{transacao_id}", response_model=TransacaoRead)
def obter_transacao(
    transacao_id: int, usuario_atual: CurrentUser, transacao_service: TransacaoServiceDep
) -> TransacaoRead:
    transacao = transacao_service.obter(transacao_id, usuario_atual.id)
    return TransacaoRead.model_validate(transacao)


@router.patch("/{transacao_id}", response_model=TransacaoRead)
def atualizar_transacao(
    transacao_id: int,
    dados: TransacaoUpdate,
    usuario_atual: CurrentUser,
    transacao_service: TransacaoServiceDep,
) -> TransacaoRead:
    transacao = transacao_service.atualizar(transacao_id, dados, usuario_atual.id)
    return TransacaoRead.model_validate(transacao)


@router.delete("/{transacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_transacao(
    transacao_id: int, usuario_atual: CurrentUser, transacao_service: TransacaoServiceDep
) -> None:
    transacao_service.excluir(transacao_id, usuario_atual.id)
