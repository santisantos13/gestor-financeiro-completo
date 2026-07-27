"""Router de Relatórios: exportação do resumo do período (mês) em CSV/PDF.

Reaproveita 100% os dados já agregados por `CentralFinanceiraService`
(`visao_mensal`/`graficos_periodo`) via `RelatorioService` - nenhum cálculo
novo, só dois formatos de arquivo para o mesmo resumo que `/graficos` já
exibe em tela. `ano`/`mes` opcionais (mês atual quando omitidos), mesmo
padrão de `/central-financeira/graficos/periodo`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import CurrentUser, get_relatorio_service
from app.services.relatorio_service import RelatorioService

router = APIRouter(prefix="/relatorios", tags=["relatorios"])

RelatorioServiceDep = Annotated[RelatorioService, Depends(get_relatorio_service)]


@router.get("/csv")
def exportar_csv(
    usuario_atual: CurrentUser,
    relatorio_service: RelatorioServiceDep,
    ano: int | None = None,
    mes: int | None = None,
) -> Response:
    conteudo, nome_arquivo = relatorio_service.gerar_csv(usuario_atual.id, ano=ano, mes=mes)
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.get("/pdf")
def exportar_pdf(
    usuario_atual: CurrentUser,
    relatorio_service: RelatorioServiceDep,
    ano: int | None = None,
    mes: int | None = None,
) -> Response:
    conteudo, nome_arquivo = relatorio_service.gerar_pdf(usuario_atual.id, ano=ano, mes=mes)
    return Response(
        content=conteudo,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
