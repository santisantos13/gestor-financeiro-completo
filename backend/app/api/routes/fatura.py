"""Router de Fatura: CRUD protegido, isolado por usuário autenticado.

Nenhuma rota aceita ou expõe `usuario_id` no payload. Diferente de
Conta/Categoria/Tag/Cartão, Fatura não tem PATCH genérico: seus campos
(datas, cartão) são imutáveis por design (derivados na criação, nunca
editados depois - ver FaturaService._calcular_datas_ciclo), e as únicas
transições de estado válidas (fechar ciclo, registrar pagamento) são
ações de negócio explícitas, não atualizações de campo livre - por isso
viram endpoints próprios em vez de um PATCH genérico e permissivo demais.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_fatura_service
from app.schemas.fatura import (
    FaturaAjusteManualUpdate,
    FaturaAjustePosFechamentoCreate,
    FaturaCreate,
    FaturaExclusaoEmLote,
    FaturaImportarCreate,
    FaturaPagamentoCreate,
    FaturaPagamentoEmLoteCreate,
    FaturaPagamentoEmLoteResult,
    FaturaRead,
)
from app.services.fatura_service import FaturaService

router = APIRouter(prefix="/faturas", tags=["faturas"])

FaturaServiceDep = Annotated[FaturaService, Depends(get_fatura_service)]


@router.post("", response_model=FaturaRead, status_code=status.HTTP_201_CREATED)
def criar_fatura(
    dados: FaturaCreate, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep
) -> FaturaRead:
    fatura = fatura_service.criar(dados, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.post("/importar", response_model=FaturaRead, status_code=status.HTTP_201_CREATED)
def importar_fatura(
    dados: FaturaImportarCreate, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep
) -> FaturaRead:
    """Cria uma fatura HISTÓRICA já fechada com valor total informado
    diretamente - onboarding de quem já tinha vida financeira antes do app
    (ver docs/analise-arquitetural-fatura.md e FaturaImportarCreate)."""
    fatura = fatura_service.importar(dados, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.get("", response_model=list[FaturaRead])
def listar_faturas(
    cartao_id: int,
    usuario_atual: CurrentUser,
    fatura_service: FaturaServiceDep,
    skip: int = 0,
    limit: int = 100,
) -> list[FaturaRead]:
    faturas = fatura_service.listar(cartao_id, usuario_atual.id, skip=skip, limit=limit)
    return [FaturaRead.model_validate(fatura) for fatura in faturas]


@router.get("/{fatura_id}", response_model=FaturaRead)
def obter_fatura(fatura_id: int, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep) -> FaturaRead:
    fatura = fatura_service.obter(fatura_id, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.post("/{fatura_id}/fechar", response_model=FaturaRead)
def fechar_fatura(fatura_id: int, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep) -> FaturaRead:
    fatura = fatura_service.fechar(fatura_id, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.post("/{fatura_id}/pagamentos", response_model=FaturaRead, status_code=status.HTTP_201_CREATED)
def registrar_pagamento(
    fatura_id: int,
    dados: FaturaPagamentoCreate,
    usuario_atual: CurrentUser,
    fatura_service: FaturaServiceDep,
) -> FaturaRead:
    fatura = fatura_service.registrar_pagamento(fatura_id, dados, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.patch("/{fatura_id}/ajuste-manual", response_model=FaturaRead)
def ajustar_saldo_inicial(
    fatura_id: int,
    dados: FaturaAjusteManualUpdate,
    usuario_atual: CurrentUser,
    fatura_service: FaturaServiceDep,
) -> FaturaRead:
    """Declara o saldo já utilizado do ciclo ABERTO diretamente, sem
    vincular a nenhuma Transacao - pedido explícito do usuário."""
    fatura = fatura_service.ajustar_saldo_inicial(fatura_id, dados, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.patch("/{fatura_id}/ajuste-pos-fechamento", response_model=FaturaRead)
def ajustar_valor_pos_fechamento(
    fatura_id: int,
    dados: FaturaAjustePosFechamentoCreate,
    usuario_atual: CurrentUser,
    fatura_service: FaturaServiceDep,
) -> FaturaRead:
    """Soma um valor esquecido a uma fatura já fechada (ou paga/atrasada/
    parcial), sem criar nenhuma Transacao - pedido explícito do usuário
    (2026-07-20): "quero adicionar uma transação em uma fatura que já foi
    fechada e paga, porém tinha esquecido dela antes"."""
    fatura = fatura_service.ajustar_valor_pos_fechamento(fatura_id, dados, usuario_atual.id)
    return FaturaRead.model_validate(fatura)


@router.delete("/{fatura_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_fatura(fatura_id: int, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep) -> None:
    fatura_service.excluir(fatura_id, usuario_atual.id)


@router.post("/excluir-em-lote", status_code=status.HTTP_204_NO_CONTENT)
def excluir_faturas_em_lote(
    dados: FaturaExclusaoEmLote, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep
) -> None:
    """Pedido explícito do usuário: selecionar várias faturas de uma vez e
    excluir todas juntas. `POST` (não `DELETE`) porque precisa de corpo -
    `DELETE /{fatura_id}` continua existindo, inalterado, para o caso de
    uma fatura só. Tudo ou nada: se qualquer id da lista não existir ou não
    for do usuário, a rota inteira falha (404) e NENHUMA fatura é apagada
    (ver `FaturaService.excluir_em_lote`)."""
    fatura_service.excluir_em_lote(dados.fatura_ids, usuario_atual.id)


@router.post("/pagar-em-lote", response_model=FaturaPagamentoEmLoteResult)
def pagar_faturas_em_lote(
    dados: FaturaPagamentoEmLoteCreate, usuario_atual: CurrentUser, fatura_service: FaturaServiceDep
) -> FaturaPagamentoEmLoteResult:
    """Pedido explícito do usuário (2026-07-20): "seria interessante poder
    pagar todas selecionadas" - mesma seleção múltipla de
    `excluir_faturas_em_lote`, agora para registrar pagamento. Diferente da
    exclusão em lote, NÃO é tudo-ou-nada: faturas não elegíveis (ainda
    abertas ou já quitadas) são puladas, não derrubam a requisição inteira
    - ver docstring de `FaturaService.pagar_em_lote`."""
    pagas = fatura_service.pagar_em_lote(dados.fatura_ids, dados.data, usuario_atual.id)
    return FaturaPagamentoEmLoteResult(pagas=pagas)
