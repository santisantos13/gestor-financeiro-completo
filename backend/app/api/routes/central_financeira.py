"""Router da Central Financeira: 11 endpoints agregadores, 100%
somente-leitura.

Nenhuma rota aceita usuario_id no payload/query - vem sempre de
usuario_atual (CurrentUser), mesmo padrao de todo router do projeto.
Nenhum POST/PATCH/DELETE aqui: a Central nunca escreve nada, so agrega
leituras de Services ja existentes via CentralFinanceiraService (ver
docs/analise-arquitetural-central-financeira.md).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, get_central_financeira_service
from app.schemas.central_financeira import (
    AgendaFinanceiraRead,
    CalendarioFinanceiroRead,
    CentralAtividadesRead,
    IndicadoresGeraisRead,
    ProgressoMetasRead,
    ResumoCartoesAgregadoRead,
    ResumoCartoesRead,
    ResumoContasRead,
    ResumoEmprestimosRead,
    ResumoFaturasRead,
    ResumoFinanceiroRead,
    ResumoFinanciamentosRead,
    SaldoConsolidadoRead,
    VisaoMensalRead,
)
from app.services.central_financeira_service import CentralFinanceiraService

router = APIRouter(prefix="/central-financeira", tags=["central-financeira"])

CentralFinanceiraServiceDep = Annotated[CentralFinanceiraService, Depends(get_central_financeira_service)]

# calendar.monthrange()/date() no Service levantam ValueError (nao uma
# excecao de dominio) para mes/ano fora de faixa - sem handler registrado em
# main.py para ValueError, isso viraria 500 em vez de 422. Validacao de
# formato (nao de regra de negocio) pertence ao Router; ver
# docs/revisao-tecnica-central-financeira.md.
AnoQuery = Annotated[int | None, Query(ge=1900, le=2200)]
MesQuery = Annotated[int | None, Query(ge=1, le=12)]


@router.get("/resumo", response_model=ResumoFinanceiroRead)
def resumo_financeiro(
    usuario_atual: CurrentUser,
    central_service: CentralFinanceiraServiceDep,
    ano: AnoQuery = None,
    mes: MesQuery = None,
) -> ResumoFinanceiroRead:
    dados = central_service.resumo_financeiro(usuario_atual.id, ano=ano, mes=mes)
    return ResumoFinanceiroRead.model_validate(dados)


@router.get("/saldo-consolidado", response_model=SaldoConsolidadoRead)
def saldo_consolidado(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> SaldoConsolidadoRead:
    dados = central_service.saldo_consolidado(usuario_atual.id)
    return SaldoConsolidadoRead.model_validate(dados)


@router.get("/contas", response_model=ResumoContasRead)
def resumo_contas(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ResumoContasRead:
    dados = central_service.resumo_contas(usuario_atual.id)
    return ResumoContasRead.model_validate(dados)


@router.get("/cartoes", response_model=ResumoCartoesRead)
def resumo_cartoes(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ResumoCartoesRead:
    dados = central_service.resumo_cartoes(usuario_atual.id)
    return ResumoCartoesRead.model_validate(dados)


@router.get("/cartoes/agregado", response_model=ResumoCartoesAgregadoRead)
def resumo_cartoes_agregado(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ResumoCartoesAgregadoRead:
    # Panorama do "Dashboard de Cartões" (Sprint de Refinamento Premium,
    # item 3) - rota estática distinta de "/cartoes" (que devolve a lista
    # crua), sem colisão de path no FastAPI.
    dados = central_service.resumo_cartoes_agregado(usuario_atual.id)
    return ResumoCartoesAgregadoRead.model_validate(dados)


@router.get("/faturas", response_model=ResumoFaturasRead)
def resumo_faturas(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ResumoFaturasRead:
    dados = central_service.resumo_faturas(usuario_atual.id)
    return ResumoFaturasRead.model_validate(dados)


@router.get("/financiamentos", response_model=ResumoFinanciamentosRead)
def resumo_financiamentos(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ResumoFinanciamentosRead:
    dados = central_service.resumo_financiamentos(usuario_atual.id)
    return ResumoFinanciamentosRead.model_validate(dados)


@router.get("/emprestimos", response_model=ResumoEmprestimosRead)
def resumo_emprestimos(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ResumoEmprestimosRead:
    dados = central_service.resumo_emprestimos(usuario_atual.id)
    return ResumoEmprestimosRead.model_validate(dados)


@router.get("/metas", response_model=ProgressoMetasRead)
def progresso_metas(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> ProgressoMetasRead:
    dados = central_service.progresso_metas(usuario_atual.id)
    return ProgressoMetasRead.model_validate(dados)


@router.get("/agenda", response_model=AgendaFinanceiraRead)
def agenda_financeira(
    usuario_atual: CurrentUser,
    central_service: CentralFinanceiraServiceDep,
    dias: Annotated[int, Query(ge=0, le=3650)] = 30,
) -> AgendaFinanceiraRead:
    dados = central_service.agenda_financeira(usuario_atual.id, dias=dias)
    return AgendaFinanceiraRead.model_validate(dados)


@router.get("/calendario", response_model=CalendarioFinanceiroRead)
def calendario_financeiro(
    usuario_atual: CurrentUser,
    central_service: CentralFinanceiraServiceDep,
    ano: AnoQuery = None,
    mes: MesQuery = None,
) -> CalendarioFinanceiroRead:
    """Etapa de Transferências/Calendário Financeiro: irmão de `/agenda`
    acima, não uma substituição - ver docstring de
    `CentralFinanceiraService.calendario_financeiro`. `/agenda` continua
    intacto (o widget de Dashboard que já o consome não muda)."""
    dados = central_service.calendario_financeiro(usuario_atual.id, ano=ano, mes=mes)
    return CalendarioFinanceiroRead.model_validate(dados)


@router.get("/atividades", response_model=CentralAtividadesRead)
def atividades_recentes(
    usuario_atual: CurrentUser,
    central_service: CentralFinanceiraServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CentralAtividadesRead:
    """Central de Atividades (Sprint de Refinamento Premium, item 17) -
    feed cronológico combinando Transação/Transferência/Meta concluída,
    ver docstring de `CentralFinanceiraService.atividades_recentes`."""
    dados = central_service.atividades_recentes(usuario_atual.id, limit=limit)
    return CentralAtividadesRead.model_validate(dados)


@router.get("/visao-mensal", response_model=VisaoMensalRead)
def visao_mensal(
    usuario_atual: CurrentUser,
    central_service: CentralFinanceiraServiceDep,
    ano: AnoQuery = None,
    mes: MesQuery = None,
) -> VisaoMensalRead:
    dados = central_service.visao_mensal(usuario_atual.id, ano=ano, mes=mes)
    return VisaoMensalRead.model_validate(dados)


@router.get("/indicadores", response_model=IndicadoresGeraisRead)
def indicadores_gerais(
    usuario_atual: CurrentUser, central_service: CentralFinanceiraServiceDep
) -> IndicadoresGeraisRead:
    dados = central_service.indicadores_gerais(usuario_atual.id)
    return IndicadoresGeraisRead.model_validate(dados)
