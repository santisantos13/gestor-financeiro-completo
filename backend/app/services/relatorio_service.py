"""Service de Relatórios: exporta o resumo financeiro de um mês em CSV/PDF.

Zero cálculo novo aqui - reaproveita 100% os dois métodos de agregação já
existentes em `CentralFinanceiraService` (mesmos dados que a página
`/graficos` exibe em tela): `visao_mensal` (entradas/saídas/fluxo de caixa
do mês) e `graficos_periodo` (gastos por categoria/cartão/conta do mês, já
com nome resolvido). Este Service só formata esse mesmo dict em dois
formatos de arquivo - CSV (para abrir em planilha) e PDF (para ler/
imprimir), nunca refaz nenhuma soma.

Ver docs/analise-arquitetural-relatorios.md.
"""
import csv
import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.central_financeira_service import CentralFinanceiraService

# Só para o cabeçalho do export (CSV/PDF) - a UI de verdade (frontend) usa
# `utils/date.ts:nomeMes`, que já existe; aqui é uma cópia mínima e
# deliberada (backend não tem `Intl`/`babel`, e criar um módulo novo só
# para isso seria mais peso do que o problema pede).
NOME_MES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def _moeda(valor: Decimal) -> str:
    """Formato pt-BR simples (`R$ 1.234,56`) - sem `Intl`/babel disponível
    no backend, formatação manual mínima só para o export (a UI de
    verdade, no frontend, já formata com `formatMoney`)."""
    inteiro, _, decimal = f"{valor:,.2f}".partition(".")
    inteiro = inteiro.replace(",", ".")
    return f"R$ {inteiro},{decimal}"


class RelatorioService:
    def __init__(self, central_financeira_service: CentralFinanceiraService) -> None:
        self.central_financeira_service = central_financeira_service

    def _montar_dados(self, usuario_id: int, ano: int | None, mes: int | None) -> dict:
        visao = self.central_financeira_service.visao_mensal(usuario_id, ano=ano, mes=mes)
        # `visao["ano"]`/`visao["mes"]` já vêm resolvidos (mês atual quando
        # `ano`/`mes` não são informados) - reaproveitado para não duplicar
        # aqui a mesma lógica de "hoje = date.today()" que já existe em
        # `CentralFinanceiraService`.
        periodo = self.central_financeira_service.graficos_periodo(usuario_id, ano=visao["ano"], mes=visao["mes"])
        return {**visao, **periodo}

    def _nome_arquivo(self, dados: dict, extensao: str) -> str:
        return f"relatorio-{dados['ano']:04d}-{dados['mes']:02d}.{extensao}"

    # --- CSV -----------------------------------------------------------------

    def gerar_csv(self, usuario_id: int, *, ano: int | None = None, mes: int | None = None) -> tuple[str, str]:
        dados = self._montar_dados(usuario_id, ano, mes)
        buffer = io.StringIO()
        # `;` como delimitador (não `,`) - Excel em locale pt-BR interpreta
        # `,` como separador decimal, então usa `;` como separador de campo
        # por convenção; BOM UTF-8 no início para acentos abrirem certo.
        buffer.write("﻿")
        writer = csv.writer(buffer, delimiter=";")

        writer.writerow([f"Relatório financeiro - {NOME_MES[dados['mes']]}/{dados['ano']}"])
        writer.writerow([])
        writer.writerow(["Resumo do mês"])
        writer.writerow(["Entradas", str(dados["entradas"])])
        writer.writerow(["Saídas", str(dados["saidas"])])
        writer.writerow(["Saldo do mês", str(dados["fluxo_caixa"])])

        for titulo, chave, campo_nome in (
            ("Gastos por categoria", "gastos_por_categoria", "categoria_nome"),
            ("Gastos por cartão", "gastos_por_cartao", "cartao_nome"),
            ("Gastos por conta", "gastos_por_conta", "conta_nome"),
        ):
            writer.writerow([])
            writer.writerow([titulo])
            writer.writerow([titulo.split(" ")[-1].capitalize(), "Total"])
            for item in dados[chave]:
                writer.writerow([item[campo_nome], str(item["total"])])

        return buffer.getvalue(), self._nome_arquivo(dados, "csv")

    # --- PDF -----------------------------------------------------------------

    def gerar_pdf(self, usuario_id: int, *, ano: int | None = None, mes: int | None = None) -> tuple[bytes, str]:
        dados = self._montar_dados(usuario_id, ano, mes)
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
        estilos = getSampleStyleSheet()
        elementos = [
            Paragraph(f"Relatório financeiro - {NOME_MES[dados['mes']]}/{dados['ano']}", estilos["Title"]),
            Spacer(1, 0.5 * cm),
            Paragraph("Resumo do mês", estilos["Heading2"]),
            self._tabela(
                [["Entradas", _moeda(dados["entradas"])],
                 ["Saídas", _moeda(dados["saidas"])],
                 ["Saldo do mês", _moeda(dados["fluxo_caixa"])]]
            ),
        ]

        for titulo, chave, campo_nome in (
            ("Gastos por categoria", "gastos_por_categoria", "categoria_nome"),
            ("Gastos por cartão", "gastos_por_cartao", "cartao_nome"),
            ("Gastos por conta", "gastos_por_conta", "conta_nome"),
        ):
            itens = dados[chave]
            elementos.append(Spacer(1, 0.6 * cm))
            elementos.append(Paragraph(titulo, estilos["Heading2"]))
            if not itens:
                elementos.append(Paragraph("Nenhum gasto neste período.", estilos["BodyText"]))
                continue
            linhas = [[item[campo_nome], _moeda(item["total"])] for item in itens]
            elementos.append(self._tabela(linhas))

        documento.build(elementos)
        return buffer.getvalue(), self._nome_arquivo(dados, "pdf")

    def _tabela(self, linhas: list[list[str]]) -> Table:
        tabela = Table(linhas, colWidths=[10 * cm, 5 * cm])
        tabela.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return tabela
