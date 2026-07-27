"""Testes unitários de RelatorioService - isolado com um `CentralFinanceiraService`
FALSO (stub com só os 2 métodos que `RelatorioService` de fato chama:
`visao_mensal`/`graficos_periodo`). RelatorioService não faz nenhum cálculo
próprio (zero soma/agregação) - só formata o dict que esses dois métodos
devolvem em dois formatos de arquivo, então o teste cobre exatamente isso:
o CONTEÚDO do CSV/PDF bate com os dados do stub, sem nenhuma lógica de
negócio nova para testar.
"""
from decimal import Decimal

from app.services.relatorio_service import RelatorioService


class _CentralFinanceiraServiceFalso:
    def __init__(self, visao: dict, periodo: dict) -> None:
        self._visao = visao
        self._periodo = periodo
        self.chamadas_visao = []
        self.chamadas_periodo = []

    def visao_mensal(self, usuario_id, *, ano=None, mes=None):
        self.chamadas_visao.append((usuario_id, ano, mes))
        return self._visao

    def graficos_periodo(self, usuario_id, *, ano=None, mes=None):
        self.chamadas_periodo.append((usuario_id, ano, mes))
        return self._periodo


def _service(ano=2026, mes=7, entradas=Decimal("5000.00"), saidas=Decimal("3200.50")):
    visao = {"ano": ano, "mes": mes, "entradas": entradas, "saidas": saidas, "fluxo_caixa": entradas - saidas}
    periodo = {
        "gastos_por_categoria": [
            {"categoria_id": 1, "categoria_nome": "Alimentação", "categoria_cor": "#fff", "categoria_icone": None, "total": Decimal("800.00")},
            {"categoria_id": None, "categoria_nome": "Sem categoria", "categoria_cor": None, "categoria_icone": None, "total": Decimal("50.00")},
        ],
        "gastos_por_cartao": [
            {"cartao_id": 1, "cartao_nome": "Nubank", "total": Decimal("400.00")},
        ],
        "gastos_por_conta": [
            {"conta_id": 1, "conta_nome": "Conta Corrente", "total": Decimal("1950.50")},
        ],
    }
    return RelatorioService(_CentralFinanceiraServiceFalso(visao, periodo))


def test_gerar_csv_inclui_resumo_e_agrupamentos():
    service = _service()
    conteudo, nome_arquivo = service.gerar_csv(usuario_id=1)

    assert nome_arquivo == "relatorio-2026-07.csv"
    assert "Relatório financeiro - Julho/2026" in conteudo
    assert "Entradas;5000.00" in conteudo
    assert "Saídas;3200.50" in conteudo
    assert "Saldo do mês;1799.50" in conteudo
    assert "Alimentação;800.00" in conteudo
    assert "Sem categoria;50.00" in conteudo
    assert "Nubank;400.00" in conteudo
    assert "Conta Corrente;1950.50" in conteudo


def test_gerar_csv_propaga_ano_mes_explicitos_para_visao_mensal():
    service = _service()
    service.gerar_csv(usuario_id=7, ano=2025, mes=3)

    central = service.central_financeira_service
    assert central.chamadas_visao == [(7, 2025, 3)]
    # `graficos_periodo` é chamado com o ano/mes JÁ RESOLVIDO por
    # `visao_mensal` (nunca recalculado aqui) - resolvido pelo stub como o
    # ano/mes fixo de `_service()` (2026/7), não o 2025/3 pedido.
    assert central.chamadas_periodo == [(7, 2026, 7)]


def test_gerar_pdf_produz_bytes_validos_de_pdf():
    service = _service()
    conteudo, nome_arquivo = service.gerar_pdf(usuario_id=1)

    assert nome_arquivo == "relatorio-2026-07.pdf"
    assert isinstance(conteudo, bytes)
    assert conteudo.startswith(b"%PDF")
    assert len(conteudo) > 0


def test_gerar_pdf_sem_nenhum_gasto_no_periodo_nao_quebra():
    visao = {"ano": 2026, "mes": 1, "entradas": Decimal("0"), "saidas": Decimal("0"), "fluxo_caixa": Decimal("0")}
    periodo = {"gastos_por_categoria": [], "gastos_por_cartao": [], "gastos_por_conta": []}
    service = RelatorioService(_CentralFinanceiraServiceFalso(visao, periodo))

    conteudo, nome_arquivo = service.gerar_pdf(usuario_id=1)

    assert nome_arquivo == "relatorio-2026-01.pdf"
    assert conteudo.startswith(b"%PDF")
