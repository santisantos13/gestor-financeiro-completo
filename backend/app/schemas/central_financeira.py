"""Schemas de saída da Central Financeira: `app/api/routes/central_financeira.py`.

Camada 100% somente-leitura - não existe `Create`/`Update` aqui, e nenhum
schema tem `usuario_id` (a Central nunca aceita esse campo do cliente,
mesmo padrão de toda rota autenticada do projeto). Todo valor exposto aqui
já foi calculado por um Service de domínio existente (`ContaRead.saldo_atual`,
`CartaoRead.limite_disponivel`, `FaturaRead.valor_total`/`status`,
`MetaRead.valor_acumulado`/`percentual`, `FinanciamentoRead`/
`EmprestimoRead.saldo_devedor`) - os schemas abaixo só agrupam/formatam,
nunca recalculam. Ver docs/analise-arquitetural-central-financeira.md.
"""
from datetime import date, datetime
from decimal import Decimal

from app.models.enums import CategoriaEventoCalendario, TipoEntidadeReferenciavel
from app.schemas.base import OrmBaseModel
from app.schemas.cartao import CartaoRead
from app.schemas.conta import ContaRead
from app.schemas.emprestimo import EmprestimoRead
from app.schemas.fatura import FaturaRead
from app.schemas.financiamento import FinanciamentoRead
from app.schemas.meta import MetaRead


class ContaSaldoResumo(OrmBaseModel):
    """Recorte mínimo de Conta usado dentro de `SaldoConsolidadoRead` -
    `ContaRead` completo já existe e é o que `GET /central-financeira/contas`
    devolve; aqui só o necessário para a foto de saldo consolidado."""

    id: int
    nome: str
    saldo_atual: Decimal


class SaldoConsolidadoRead(OrmBaseModel):
    saldo_total: Decimal
    contas: list[ContaSaldoResumo]


class ResumoContasRead(OrmBaseModel):
    contas: list[ContaRead]


class ResumoCartoesRead(OrmBaseModel):
    cartoes: list[CartaoRead]
    total_utilizado: Decimal


class UsoCartao(OrmBaseModel):
    """Um item da distribuição de uso por cartão, dentro de
    `ResumoCartoesAgregadoRead` - `percentual_usado` é lido de
    `CartaoRead.limite`/`limite_disponivel` (já calculados por
    `CartaoService`), nunca recalculado aqui."""

    cartao_id: int
    nome: str
    percentual_usado: Decimal


class ProximoVencimentoFatura(OrmBaseModel):
    cartao_id: int
    cartao_nome: str
    fatura_id: int
    data_vencimento: date
    valor_total: Decimal


class ResumoCartoesAgregadoRead(OrmBaseModel):
    """Panorama agregado para o "Dashboard de Cartões" (Sprint de
    Refinamento Premium, item 3) - deliberadamente SEM nenhum gráfico por
    cartão individual (isso é `/cartoes/:id`). Todo valor é soma/contagem
    sobre a lista de `CartaoRead`/`FaturaRead` que os Services de domínio
    já devolvem calculados - mesmas 3 regras estruturais do topo deste
    arquivo."""

    limite_total: Decimal
    limite_disponivel_total: Decimal
    limite_usado_total: Decimal
    percentual_usado_geral: Decimal
    quantidade_cartoes: int
    faturas_em_aberto: int
    proximos_vencimentos: list[ProximoVencimentoFatura]
    distribuicao_uso: list[UsoCartao]


class ResumoFaturasRead(OrmBaseModel):
    faturas: list[FaturaRead]


class FinanciamentoResumo(FinanciamentoRead):
    """`FinanciamentoRead` + métricas de acompanhamento que a Central
    orquestra a partir de `TransacaoService` (parcelas do contrato) - nenhuma
    delas é recalculada aqui, só lida via `TransacaoService.listar`."""

    parcelas_pagas: int
    parcelas_restantes: int
    valor_total_pago: Decimal
    proxima_parcela_data: date | None
    proxima_parcela_valor: Decimal | None


class ResumoFinanciamentosRead(OrmBaseModel):
    financiamentos: list[FinanciamentoResumo]


class EmprestimoResumo(EmprestimoRead):
    parcelas_pagas: int
    parcelas_restantes: int
    valor_total_pago: Decimal
    proxima_parcela_data: date | None
    proxima_parcela_valor: Decimal | None


class ResumoEmprestimosRead(OrmBaseModel):
    emprestimos: list[EmprestimoResumo]


class ProgressoMetasRead(OrmBaseModel):
    metas: list[MetaRead]


class EventoAgenda(OrmBaseModel):
    """Um evento futuro na Agenda Financeira - projeção somente-leitura, sem
    tabela própria (ver docs/analise-arquitetural-central-financeira.md,
    seção 4). `origem_tipo` reaproveita `TipoEntidadeReferenciavel` (já
    existente para `Alerta`/`Anexo`) em vez de um enum novo."""

    data: date
    descricao: str
    valor: Decimal
    origem_tipo: TipoEntidadeReferenciavel
    origem_id: int


class AgendaFinanceiraRead(OrmBaseModel):
    eventos: list[EventoAgenda]


class ResumoFinanceiroRead(OrmBaseModel):
    ano: int
    mes: int
    saldo_total: Decimal
    entradas_mes: Decimal
    saidas_mes: Decimal
    fluxo_caixa_mes: Decimal
    patrimonio_liquido: Decimal


class VisaoMensalRead(OrmBaseModel):
    ano: int
    mes: int
    entradas: Decimal
    saidas: Decimal
    fluxo_caixa: Decimal


class IndicadoresGeraisRead(OrmBaseModel):
    contas_ativas: int
    cartoes_ativos: int
    faturas_em_aberto: int
    financiamentos_ativos: int
    emprestimos_ativos: int
    metas_ativas: int
    percentual_medio_metas: Decimal
    parcelas_atrasadas: int


class EventoCalendario(OrmBaseModel):
    """Um evento do Calendário Financeiro mensal
    (`GET /central-financeira/calendario`) - endpoint NOVO, irmão de
    `EventoAgenda`/`AgendaFinanceiraRead` acima, não uma substituição: a
    Agenda (widget do Dashboard) continua servindo "próximos N dias,
    só pendente"; o Calendário serve "o mês inteiro, todo status" (ver
    `CentralFinanceiraService.calendario_financeiro`).

    `categoria` (`CategoriaEventoCalendario`) decide a COR do indicador
    (dot) no calendário. `origem_tipo`/`origem_id` (`TipoEntidadeReferenciavel`,
    o mesmo enum de `EventoAgenda`) decidem para ONDE navegar ao clicar -
    são dois discriminadores independentes de propósito (ver docstring de
    `CategoriaEventoCalendario` em `models/enums.py`).

    `status`/`horario` são só apresentação no Drawer do dia (ex.: "PAGO",
    "PENDENTE", "FECHADA", "ATIVA", "CANCELADA") - texto livre porque cada
    entidade de origem tem seu próprio enum de status (`StatusTransacao`,
    `StatusFatura`, etc.); o Service já lê `.value` antes de devolver, então
    aqui é sempre `str`, nunca um enum específico de uma entidade só.
    """

    data: date
    descricao: str
    valor: Decimal
    categoria: CategoriaEventoCalendario
    origem_tipo: TipoEntidadeReferenciavel
    origem_id: int
    status: str | None = None
    # Expansão de Contas Recorrentes (2026-07-20): True só para
    # ocorrências FUTURAS projetadas de um template ATIVO (horizonte de 90
    # dias, nunca persistidas - ver
    # `ContaRecorrenteService.projetar_ocorrencias`). Default False =
    # mudança aditiva, nenhum evento/consumidor existente muda.
    previsto: bool = False


class CalendarioFinanceiroRead(OrmBaseModel):
    ano: int
    mes: int
    eventos: list[EventoCalendario]


class AtividadeRecente(OrmBaseModel):
    """Um item da Central de Atividades (`GET /central-financeira/atividades`,
    Sprint de Refinamento Premium, item 17) - feed cronológico de "o que
    aconteceu recentemente", combinando Transação/Transferência/Meta
    concluída (ver `CentralFinanceiraService.atividades_recentes`).
    `data_hora` é sempre um `datetime` (mesmo para Meta, cujo
    `concluida_em` é só `date` - o Service normaliza para meia-noite ao
    montar isto), único jeito de ordenar as 3 fontes de forma consistente.
    `origem_tipo`/`origem_id` reaproveitam o mesmo discriminador de
    `EventoCalendario`/`EventoAgenda` (`TipoEntidadeReferenciavel`) - zero
    tipo novo, mesmo mapa de ícone/rota do frontend serve aqui também."""

    data_hora: datetime
    descricao: str
    valor: Decimal | None = None
    origem_tipo: TipoEntidadeReferenciavel
    origem_id: int


class CentralAtividadesRead(OrmBaseModel):
    atividades: list[AtividadeRecente]


class PontoTendenciaMensal(OrmBaseModel):
    """Um mês da série de `GET /central-financeira/graficos/tendencias`
    (docs/analise-arquitetural-graficos.md). `saldo_total` é ACUMULADO
    (saldo de todas as contas ao FINAL deste mês); `entradas`/`saidas` são
    só deste mês (não acumuladas) - ver
    `CentralFinanceiraService.graficos_tendencias`."""

    ano: int
    mes: int
    saldo_total: Decimal
    entradas: Decimal
    saidas: Decimal


class GraficosTendenciasRead(OrmBaseModel):
    meses: list[PontoTendenciaMensal]


class GastoPorCategoria(OrmBaseModel):
    """`categoria_id` pode ser `None` (lançamento sem categoria) -
    `categoria_nome` já vem resolvido como "Sem categoria" nesse caso,
    nunca omitido do gráfico."""

    categoria_id: int | None
    categoria_nome: str
    categoria_cor: str | None
    categoria_icone: str | None
    total: Decimal


class GastoPorCartao(OrmBaseModel):
    cartao_id: int
    cartao_nome: str
    total: Decimal


class GraficosPeriodoRead(OrmBaseModel):
    ano: int
    mes: int
    gastos_por_categoria: list[GastoPorCategoria]
    gastos_por_cartao: list[GastoPorCartao]
