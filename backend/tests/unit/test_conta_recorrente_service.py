"""Testes unitários de ContaRecorrenteService - isolado com repositories e
um TransacaoService FALSOS (em memória, sem banco). Cobre exatamente o que é
próprio de ContaRecorrenteService (validação estrutural conta XOR cartão,
dia_vencimento × família de frequência, geração lazy sobre o cursor
`proxima_execucao` com clamping/rollover, idempotência, ciclo de vida
ATIVA/PAUSADA/ENCERRADA, sincronização global, projeção virtual) - a
validação de posse/ativo de Conta ou Cartão, compatibilidade de categoria,
resolução de fatura etc. NÃO é reexercitada aqui: já está exaustivamente
coberta em test_transacao_service.py, e ContaRecorrenteService nunca
duplica essa lógica, apenas delega para TransacaoService. Ver
docs/analise-arquitetural-conta-recorrente-expansao.md.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import ContaRecorrente
from app.models.enums import FrequenciaRecorrencia, StatusRecorrencia, TipoTransacao
from app.schemas.conta_recorrente import ContaRecorrenteCreate, ContaRecorrenteUpdate
from app.services.conta_recorrente_service import ContaRecorrenteService


class _TransacaoFalsa:
    def __init__(self, dados, usuario_id):
        self.usuario_id = usuario_id
        self.tipo = dados.tipo
        self.valor = dados.valor
        self.data = dados.data
        self.descricao = dados.descricao
        self.categoria_id = dados.categoria_id
        self.conta_id = dados.conta_id
        self.cartao_id = dados.cartao_id
        self.origem_recorrente_id = dados.origem_recorrente_id


class FakeTransacaoRepository:
    def __init__(self):
        self._transacoes = {}
        self._proximo_id = 1

    def create(self, transacao):
        transacao.id = self._proximo_id
        self._proximo_id += 1
        self._transacoes[transacao.id] = transacao
        return transacao

    def get(self, id):
        return self._transacoes.get(id)

    def listar_do_usuario(
        self,
        usuario_id,
        *,
        origem_recorrente_id=None,
        data_inicio=None,
        data_fim=None,
        limit=100,
        **_ignorado,
    ):
        resultado = [t for t in self._transacoes.values() if t.usuario_id == usuario_id]
        if origem_recorrente_id is not None:
            resultado = [t for t in resultado if t.origem_recorrente_id == origem_recorrente_id]
        if data_inicio is not None:
            resultado = [t for t in resultado if t.data >= data_inicio]
        if data_fim is not None:
            resultado = [t for t in resultado if t.data <= data_fim]
        resultado.sort(key=lambda t: (t.data, t.id), reverse=True)
        return resultado[:limit]


class FakeTransacaoService:
    """Substitui TransacaoService de verdade - só registra as chamadas,
    para confirmar que ContaRecorrenteService DELEGA em vez de duplicar."""

    def __init__(self, transacao_repo):
        self.transacao_repo = transacao_repo
        self.chamadas_criar = []

    def criar(self, dados, usuario_id):
        self.chamadas_criar.append((dados, usuario_id))
        return self.transacao_repo.create(_TransacaoFalsa(dados, usuario_id))


class FakeContaRecorrenteRepository:
    def __init__(self):
        self._contas_recorrentes = {}
        self._proximo_id = 1

    def create(self, conta_recorrente):
        conta_recorrente.id = self._proximo_id
        self._proximo_id += 1
        self._contas_recorrentes[conta_recorrente.id] = conta_recorrente
        return conta_recorrente

    def get(self, id):
        return self._contas_recorrentes.get(id)

    def update(self, conta_recorrente):
        return conta_recorrente

    def delete(self, conta_recorrente):
        self._contas_recorrentes.pop(conta_recorrente.id, None)

    def listar_do_usuario(self, usuario_id, *, status=None, skip=0, limit=100):
        resultado = [cr for cr in self._contas_recorrentes.values() if cr.usuario_id == usuario_id]
        if status is not None:
            resultado = [cr for cr in resultado if cr.status == status]
        resultado.sort(key=lambda cr: cr.data_inicio, reverse=True)
        return resultado[skip : skip + limit]


@pytest.fixture()
def transacao_repo():
    return FakeTransacaoRepository()


@pytest.fixture()
def transacao_service(transacao_repo):
    return FakeTransacaoService(transacao_repo)


@pytest.fixture()
def conta_recorrente_repo():
    return FakeContaRecorrenteRepository()


@pytest.fixture()
def service(conta_recorrente_repo, transacao_repo, transacao_service):
    return ContaRecorrenteService(conta_recorrente_repo, transacao_repo, transacao_service)


def _primeiro_dia_meses_atras(referencia: date, meses: int) -> date:
    ano, mes = referencia.year, referencia.month
    for _ in range(meses):
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
    return date(ano, mes, 1)


def _primeiro_dia_proximo_mes(referencia: date) -> date:
    ano, mes = referencia.year, referencia.month
    mes += 1
    if mes == 13:
        mes = 1
        ano += 1
    return date(ano, mes, 1)


def _criar(
    service,
    usuario_id=1,
    descricao="Aluguel",
    valor=Decimal("1500.00"),
    tipo=TipoTransacao.DESPESA,
    frequencia=FrequenciaRecorrencia.MENSAL,
    dia_vencimento=1,
    categoria_id=None,
    conta_id=100,
    cartao_id=None,
    data_inicio=date(2026, 1, 1),
    data_fim=None,
):
    dados = ContaRecorrenteCreate(
        descricao=descricao,
        valor=valor,
        tipo=tipo,
        frequencia=frequencia,
        dia_vencimento=dia_vencimento,
        categoria_id=categoria_id,
        conta_id=conta_id,
        cartao_id=cartao_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    return service.criar(dados, usuario_id)


def _obj_conta_recorrente(
    id=1,
    usuario_id=1,
    descricao="Aluguel",
    valor=Decimal("1500.00"),
    tipo=TipoTransacao.DESPESA,
    frequencia=FrequenciaRecorrencia.MENSAL,
    dia_vencimento=31,
    categoria_id=None,
    conta_id=100,
    cartao_id=None,
    data_inicio=date(2026, 1, 31),
    data_fim=None,
    proxima_execucao=None,
    status=StatusRecorrencia.ATIVA,
):
    """Constrói uma instância diretamente (sem Repository/banco) - usada
    nos testes que chamam `_gerar_ocorrencias_pendentes` diretamente, a
    única forma de controlar deterministicamente "hoje" sem mocking. O
    cursor `proxima_execucao` default é a própria primeira data do
    template (mesma conta de `_primeira_execucao`)."""
    conta_recorrente = ContaRecorrente(
        usuario_id=usuario_id,
        descricao=descricao,
        valor=valor,
        tipo=tipo,
        frequencia=frequencia,
        dia_vencimento=dia_vencimento,
        categoria_id=categoria_id,
        conta_id=conta_id,
        cartao_id=cartao_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        proxima_execucao=proxima_execucao
        or ContaRecorrenteService._primeira_execucao(frequencia, dia_vencimento, data_inicio),
        status=status,
    )
    conta_recorrente.id = id
    return conta_recorrente


# --- criar: estrutura (conta XOR cartão) ------------------------------------

def test_criar_sem_conta_e_sem_cartao_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None, cartao_id=None)


def test_criar_com_conta_e_cartao_ao_mesmo_tempo_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=100, cartao_id=10)


def test_criar_com_estrutura_invalida_nao_gera_nenhuma_ocorrencia(service, transacao_service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None, cartao_id=None)
    assert transacao_service.chamadas_criar == []


# --- criar/atualizar: data_fim não pode ser anterior a data_inicio ---------

def test_criar_com_data_fim_anterior_a_data_inicio_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, data_inicio=date(2026, 6, 1), data_fim=date(2026, 1, 1))


def test_criar_com_data_fim_igual_a_data_inicio_e_aceito(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 6, 1), data_fim=date(2026, 6, 1))
    assert conta_recorrente.data_fim == date(2026, 6, 1)


def test_atualizar_data_fim_para_antes_de_data_inicio_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 6, 1))
    with pytest.raises(BusinessRuleError):
        service.atualizar(conta_recorrente.id, ContaRecorrenteUpdate(data_fim=date(2026, 1, 1)), usuario_id=1)


# --- criar: dia_vencimento × família de frequência --------------------------
# Expansão 2026-07-20: substitui o antigo bloqueio de frequências não-MENSAL.

def test_criar_frequencia_baseada_em_dias_com_dia_vencimento_levanta_erro(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, frequencia=FrequenciaRecorrencia.SEMANAL, dia_vencimento=10)


def test_criar_frequencia_baseada_em_meses_sem_dia_vencimento_levanta_erro(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, frequencia=FrequenciaRecorrencia.ANUAL, dia_vencimento=None)


def test_criar_com_frequencia_semanal_sem_dia_vencimento_e_aceito(service):
    conta_recorrente = _criar(
        service, frequencia=FrequenciaRecorrencia.SEMANAL, dia_vencimento=None,
        data_inicio=_primeiro_dia_proximo_mes(date.today()),
    )
    assert conta_recorrente.frequencia == FrequenciaRecorrencia.SEMANAL


def test_criar_com_frequencia_anual_com_dia_vencimento_e_aceito(service):
    conta_recorrente = _criar(
        service, frequencia=FrequenciaRecorrencia.ANUAL, dia_vencimento=15,
        data_inicio=_primeiro_dia_proximo_mes(date.today()),
    )
    assert conta_recorrente.frequencia == FrequenciaRecorrencia.ANUAL


def test_criar_sem_frequencia_usa_mensal_como_padrao(service):
    dados = ContaRecorrenteCreate(
        descricao="Salário",
        valor=Decimal("5000.00"),
        tipo=TipoTransacao.RECEITA,
        dia_vencimento=5,
        conta_id=100,
        data_inicio=date(2026, 1, 5),
    )
    conta_recorrente = service.criar(dados, usuario_id=1)
    assert conta_recorrente.frequencia == FrequenciaRecorrencia.MENSAL


# --- criar: geração lazy até "hoje", cursor inicial -------------------------

def test_criar_com_data_inicio_no_passado_gera_ocorrencias_ate_hoje(service, transacao_service):
    hoje = date.today()
    data_inicio = _primeiro_dia_meses_atras(hoje, 3)
    _criar(service, dia_vencimento=1, data_inicio=data_inicio)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert len(datas) == 4  # mes de data_inicio + 3 seguintes, ate o mes atual
    assert datas[0] == data_inicio
    assert datas[-1].year == hoje.year and datas[-1].month == hoje.month


def test_criar_com_data_inicio_no_futuro_nao_gera_e_deixa_cursor_na_primeira_data(
    service, transacao_service
):
    data_inicio = _primeiro_dia_proximo_mes(date.today())
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=data_inicio)
    assert transacao_service.chamadas_criar == []
    assert conta_recorrente.proxima_execucao == data_inicio


def test_criar_avanca_cursor_para_alem_da_ultima_gerada(service, transacao_service):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 1))
    assert len(transacao_service.chamadas_criar) > 0
    assert conta_recorrente.proxima_execucao > hoje


def test_criar_repassa_campos_do_template_para_cada_ocorrencia(service, transacao_service):
    hoje = date.today()
    _criar(
        service,
        descricao="Netflix",
        valor=Decimal("55.90"),
        tipo=TipoTransacao.DESPESA,
        categoria_id=7,
        conta_id=100,
        cartao_id=None,
        dia_vencimento=1,
        data_inicio=_primeiro_dia_meses_atras(hoje, 1),
    )
    for dados, usuario_id in transacao_service.chamadas_criar:
        assert dados.descricao == "Netflix"
        assert dados.valor == Decimal("55.90")
        assert dados.tipo == TipoTransacao.DESPESA
        assert dados.categoria_id == 7
        assert dados.conta_id == 100
        assert dados.cartao_id is None
        assert usuario_id == 1


def test_criar_marca_origem_recorrente_id_em_cada_ocorrencia(service, transacao_service):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 1))
    for dados, _ in transacao_service.chamadas_criar:
        assert dados.origem_recorrente_id == conta_recorrente.id


# --- gerar_ocorrencias_pendentes: idempotência ------------------------------

def test_gerar_ocorrencias_pendentes_e_idempotente(service, transacao_service):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 2))
    total_apos_criar = len(transacao_service.chamadas_criar)
    assert total_apos_criar > 0

    novas = service.gerar_ocorrencias_pendentes(conta_recorrente.id, usuario_id=1)

    assert novas == []
    assert len(transacao_service.chamadas_criar) == total_apos_criar


def test_gerar_ocorrencias_pendentes_em_recorrencia_pausada_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    service.pausar(conta_recorrente.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.gerar_ocorrencias_pendentes(conta_recorrente.id, usuario_id=1)


def test_gerar_ocorrencias_pendentes_de_outro_usuario_levanta_not_found(service):
    conta_recorrente = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.gerar_ocorrencias_pendentes(conta_recorrente.id, usuario_id=2)


def test_gerar_ocorrencias_pendentes_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.gerar_ocorrencias_pendentes(999, usuario_id=1)


# --- geração sobre o cursor: rollover, clamping e frequências ---------------
# (via método privado - única forma de controlar "hoje" deterministicamente)

def test_gerar_ocorrencias_avanca_mes_a_mes_ate_o_limite(service, transacao_service):
    conta_recorrente = _obj_conta_recorrente(dia_vencimento=15, data_inicio=date(2026, 1, 15))
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 4, 30))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15), date(2026, 4, 15)]


def test_gerar_ocorrencias_faz_clamping_de_dia_em_mes_mais_curto(service, transacao_service):
    # dia 31 nao existe em fevereiro (2026 nao e bissexto) - cai pro ultimo
    # dia, e VOLTA a ser 31 em marco (o clamp nunca "gruda": cada avanco
    # parte do dia_vencimento desejado, nao do dia da data anterior).
    conta_recorrente = _obj_conta_recorrente(dia_vencimento=31, data_inicio=date(2026, 1, 31))
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 3, 31))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_gerar_ocorrencias_faz_rollover_de_ano_ao_passar_de_dezembro(service, transacao_service):
    conta_recorrente = _obj_conta_recorrente(dia_vencimento=10, data_inicio=date(2026, 11, 10))
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2027, 1, 10))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 11, 10), date(2026, 12, 10), date(2027, 1, 10)]


def test_gerar_ocorrencias_respeita_data_fim_e_encerra(service, transacao_service):
    conta_recorrente = _obj_conta_recorrente(
        dia_vencimento=1, data_inicio=date(2026, 1, 1), data_fim=date(2026, 3, 1)
    )
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 6, 1))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    # apesar de "hoje" ja estar em junho, nada alem de data_fim e gerado -
    # e a recorrencia transiciona automaticamente para ENCERRADA (cumpriu
    # seu periodo, sai de "ativas" sem acao manual).
    assert datas == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
    assert conta_recorrente.status == StatusRecorrencia.ENCERRADA


def test_gerar_ocorrencias_diaria_avanca_um_dia_por_vez(service, transacao_service):
    conta_recorrente = _obj_conta_recorrente(
        frequencia=FrequenciaRecorrencia.DIARIA, dia_vencimento=None, data_inicio=date(2026, 3, 1)
    )
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 3, 4))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4)]


def test_gerar_ocorrencias_semanal_ancora_no_dia_da_semana_de_data_inicio(service, transacao_service):
    # 2026-03-06 e uma sexta - toda ocorrencia cai em sextas seguintes.
    conta_recorrente = _obj_conta_recorrente(
        frequencia=FrequenciaRecorrencia.SEMANAL, dia_vencimento=None, data_inicio=date(2026, 3, 6)
    )
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 3, 21))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 3, 6), date(2026, 3, 13), date(2026, 3, 20)]


def test_gerar_ocorrencias_quinzenal_avanca_14_dias(service, transacao_service):
    # QUINZENAL = intervalo fixo de 14 dias (decisao do usuario, 2026-07-20).
    conta_recorrente = _obj_conta_recorrente(
        frequencia=FrequenciaRecorrencia.QUINZENAL, dia_vencimento=None, data_inicio=date(2026, 3, 1)
    )
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 3, 30))
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 3, 1), date(2026, 3, 15), date(2026, 3, 29)]


def test_gerar_ocorrencias_bimestral_trimestral_semestral_anual(service, transacao_service):
    casos = {
        FrequenciaRecorrencia.BIMESTRAL: [date(2026, 1, 10), date(2026, 3, 10), date(2026, 5, 10)],
        FrequenciaRecorrencia.TRIMESTRAL: [date(2026, 1, 10), date(2026, 4, 10)],
        FrequenciaRecorrencia.SEMESTRAL: [date(2026, 1, 10)],
        FrequenciaRecorrencia.ANUAL: [date(2026, 1, 10)],
    }
    for frequencia, esperadas in casos.items():
        transacao_service.chamadas_criar.clear()
        conta_recorrente = _obj_conta_recorrente(
            frequencia=frequencia, dia_vencimento=10, data_inicio=date(2026, 1, 10)
        )
        service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 6, 30))
        datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
        assert datas == esperadas, frequencia


def test_cursor_nao_regenera_ocorrencia_excluida(service, transacao_service, transacao_repo):
    """O cursor so anda para frente: excluir a ultima Transacao gerada NAO
    faz a proxima sincronizacao recria-la (bug latente do desenho antigo,
    que derivava a proxima data da ultima ocorrencia existente - ver
    analise, secao 2, gap 4)."""
    conta_recorrente = _obj_conta_recorrente(dia_vencimento=1, data_inicio=date(2026, 1, 1))
    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 3, 1))
    assert len(transacao_service.chamadas_criar) == 3

    # usuario exclui a ocorrencia de marco pela tela de Transacoes
    ultima = max(transacao_repo._transacoes.values(), key=lambda t: t.data)
    del transacao_repo._transacoes[ultima.id]

    service._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id=1, hoje=date(2026, 3, 1))
    assert len(transacao_service.chamadas_criar) == 3  # nada recriado


# --- ciclo de vida: pausar / reativar / encerrar ----------------------------

def test_pausar_muda_status_sem_afetar_ocorrencias(service, transacao_service):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 2))
    total_antes = len(transacao_service.chamadas_criar)
    pausada = service.pausar(conta_recorrente.id, usuario_id=1)
    assert pausada.status == StatusRecorrencia.PAUSADA
    assert len(transacao_service.chamadas_criar) == total_antes


def test_pausar_nao_ativa_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    service.pausar(conta_recorrente.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.pausar(conta_recorrente.id, usuario_id=1)


def test_reativar_nunca_gera_retroativos(service, transacao_service):
    """Decisao do usuario (2026-07-20): reativar pula o periodo pausado -
    o cursor avanca para a primeira data futura e NENHUMA ocorrencia do
    periodo pausado e gerada."""
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 3))
    service.pausar(conta_recorrente.id, usuario_id=1)
    # simula o tempo parado: cursor ficou meses no passado
    conta_recorrente.proxima_execucao = _primeiro_dia_meses_atras(hoje, 2)
    total_antes = len(transacao_service.chamadas_criar)

    reativada = service.reativar(conta_recorrente.id, usuario_id=1)

    assert reativada.status == StatusRecorrencia.ATIVA
    assert reativada.proxima_execucao > hoje
    assert len(transacao_service.chamadas_criar) == total_antes  # zero retroativos

    novas = service.gerar_ocorrencias_pendentes(conta_recorrente.id, usuario_id=1)
    assert novas == []  # nem a sincronizacao gera nada do periodo pausado


def test_reativar_alem_de_data_fim_encerra_em_vez_de_reativar(service):
    hoje = date.today()
    conta_recorrente = _criar(
        service,
        dia_vencimento=1,
        data_inicio=_primeiro_dia_meses_atras(hoje, 3),
        data_fim=hoje,
    )
    # ainda ATIVA se sobrou execucao? forca o estado: pausa e simula cursor preso no passado
    if conta_recorrente.status == StatusRecorrencia.ATIVA:
        service.pausar(conta_recorrente.id, usuario_id=1)
    else:
        conta_recorrente.status = StatusRecorrencia.PAUSADA
    conta_recorrente.proxima_execucao = _primeiro_dia_meses_atras(hoje, 1)

    reativada = service.reativar(conta_recorrente.id, usuario_id=1)
    # o proximo cursor valido ja passa de data_fim=hoje - nao ha mais nada
    # a executar, entao encerra em vez de reativar.
    assert reativada.status == StatusRecorrencia.ENCERRADA


def test_reativar_nao_pausada_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    with pytest.raises(BusinessRuleError):
        service.reativar(conta_recorrente.id, usuario_id=1)


def test_encerrar_preserva_template_e_ocorrencias(service, conta_recorrente_repo, transacao_repo):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 2))
    total_transacoes = len(transacao_repo._transacoes)

    encerrada = service.encerrar(conta_recorrente.id, usuario_id=1)

    assert encerrada.status == StatusRecorrencia.ENCERRADA
    assert encerrada.data_fim == hoje
    assert conta_recorrente_repo.get(conta_recorrente.id) is not None  # nunca apagada
    assert len(transacao_repo._transacoes) == total_transacoes  # ocorrencias intactas


def test_encerrar_ja_encerrada_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    service.encerrar(conta_recorrente.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.encerrar(conta_recorrente.id, usuario_id=1)


def test_encerrar_nao_antecipa_data_fim_ja_passada(service):
    hoje = date.today()
    data_fim_passada = hoje - timedelta(days=30)
    conta_recorrente = _obj_conta_recorrente(
        dia_vencimento=1,
        data_inicio=date(2024, 1, 1),
        data_fim=data_fim_passada,
        status=StatusRecorrencia.PAUSADA,
    )
    service.conta_recorrente_repo.create(conta_recorrente)
    encerrada = service.encerrar(conta_recorrente.id, usuario_id=1)
    assert encerrada.data_fim == data_fim_passada  # historia real preservada


def test_atualizar_encerrada_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    service.encerrar(conta_recorrente.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.atualizar(conta_recorrente.id, ContaRecorrenteUpdate(descricao="Nova"), usuario_id=1)


# --- excluir (hard delete) - só para a cascata de exclusão de Conta ---------

def test_excluir_apaga_o_template_de_verdade(service, conta_recorrente_repo):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    service.excluir(conta_recorrente.id, usuario_id=1)
    assert conta_recorrente_repo.get(conta_recorrente.id) is None


def test_excluir_nao_apaga_ocorrencias_ja_geradas(service, transacao_repo):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 2))
    total_antes = len(transacao_repo._transacoes)
    service.excluir(conta_recorrente.id, usuario_id=1)
    assert len(transacao_repo._transacoes) == total_antes


def test_excluir_de_outro_usuario_levanta_not_found(service):
    conta_recorrente = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(conta_recorrente.id, usuario_id=2)


# --- sincronizar (global) ---------------------------------------------------

def test_sincronizar_gera_pendentes_de_todos_os_templates_ativos(service, transacao_service):
    hoje = date.today()
    a = _criar(service, descricao="A", dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))
    b = _criar(service, descricao="B", dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))
    # forca pendencia: cursores no passado (simula tempo passando)
    a.proxima_execucao = _primeiro_dia_meses_atras(hoje, 2)
    b.proxima_execucao = _primeiro_dia_meses_atras(hoje, 1)

    resultado = service.sincronizar(usuario_id=1)

    assert resultado["geradas"] == 5  # A: 3 meses (n-2, n-1, n), B: 2 meses
    assert resultado["encerradas"] == 0


def test_sincronizar_ignora_pausadas_e_encerradas(service, transacao_service):
    hoje = date.today()
    pausada = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))
    service.pausar(pausada.id, usuario_id=1)
    pausada.proxima_execucao = _primeiro_dia_meses_atras(hoje, 2)

    resultado = service.sincronizar(usuario_id=1)
    assert resultado["geradas"] == 0


def test_sincronizar_e_idempotente(service):
    hoje = date.today()
    template = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))
    template.proxima_execucao = _primeiro_dia_meses_atras(hoje, 1)

    primeiro = service.sincronizar(usuario_id=1)
    segundo = service.sincronizar(usuario_id=1)

    assert primeiro["geradas"] > 0
    assert segundo["geradas"] == 0


# --- projetar_ocorrencias (virtual, nunca persiste) -------------------------

def test_projetar_ocorrencias_projeta_futuro_sem_criar_transacao(service, transacao_service):
    hoje = date.today()
    template = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))
    total_antes = len(transacao_service.chamadas_criar)

    projecoes = service.projetar_ocorrencias(1, hoje, hoje + timedelta(days=60))

    assert len(projecoes) >= 1
    assert all(p["data"] > hoje for p in projecoes)
    assert all(p["origem_id"] == template.id for p in projecoes)
    assert len(transacao_service.chamadas_criar) == total_antes  # nada persistido


def test_projetar_ocorrencias_respeita_horizonte_de_90_dias(service):
    hoje = date.today()
    _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))

    projecoes = service.projetar_ocorrencias(1, hoje, hoje + timedelta(days=365))

    assert all(p["data"] <= hoje + timedelta(days=90) for p in projecoes)


def test_projetar_ocorrencias_ignora_pausadas(service):
    hoje = date.today()
    template = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_proximo_mes(hoje))
    service.pausar(template.id, usuario_id=1)

    projecoes = service.projetar_ocorrencias(1, hoje, hoje + timedelta(days=60))
    assert projecoes == []


def test_projetar_ocorrencias_respeita_data_fim_do_template(service):
    hoje = date.today()
    inicio = _primeiro_dia_proximo_mes(hoje)
    _criar(service, dia_vencimento=1, data_inicio=inicio, data_fim=inicio)

    projecoes = service.projetar_ocorrencias(1, hoje, hoje + timedelta(days=90))
    assert [p["data"] for p in projecoes] == [inicio]


# --- obter / listar ------------------------------------------------------

def test_obter_conta_recorrente_propria(service):
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    assert service.obter(conta_recorrente.id, usuario_id=1).id == conta_recorrente.id


def test_obter_conta_recorrente_de_outro_usuario_levanta_not_found(service):
    conta_recorrente = _criar(service, usuario_id=1, data_inicio=date(2026, 1, 1))
    with pytest.raises(NotFoundError):
        service.obter(conta_recorrente.id, usuario_id=2)


def test_listar_retorna_apenas_contas_recorrentes_do_usuario(service):
    _criar(service, usuario_id=1, conta_id=100, descricao="Minha", data_inicio=date(2026, 1, 1))
    _criar(service, usuario_id=2, conta_id=200, descricao="Do outro", data_inicio=date(2026, 1, 1))
    resultado = service.listar(usuario_id=1)
    assert [cr.descricao for cr in resultado] == ["Minha"]


def test_listar_filtra_por_status(service):
    ativa = _criar(service, descricao="Ativa", data_inicio=date(2026, 1, 1))
    pausada = _criar(service, descricao="Pausada", data_inicio=date(2026, 1, 1))
    service.pausar(pausada.id, usuario_id=1)

    assert {cr.descricao for cr in service.listar(usuario_id=1)} == {"Ativa", "Pausada"}
    assert [cr.descricao for cr in service.listar(usuario_id=1, status=StatusRecorrencia.ATIVA)] == ["Ativa"]
    assert [cr.descricao for cr in service.listar(usuario_id=1, status=StatusRecorrencia.PAUSADA)] == [
        "Pausada"
    ]
    assert ativa.status == StatusRecorrencia.ATIVA


# --- atualizar (PATCH) - seguro, afeta so ocorrencias futuras --------------

def test_atualizar_aplica_apenas_campos_enviados(service):
    conta_recorrente = _criar(service, descricao="Original", valor=Decimal("100.00"), data_inicio=date(2026, 1, 1))
    atualizada = service.atualizar(
        conta_recorrente.id, ContaRecorrenteUpdate(valor=Decimal("150.00")), usuario_id=1
    )
    assert atualizada.descricao == "Original"
    assert atualizada.valor == Decimal("150.00")


def test_atualizar_conta_recorrente_de_outro_usuario_levanta_not_found(service):
    conta_recorrente = _criar(service, usuario_id=1, data_inicio=date(2026, 1, 1))
    with pytest.raises(NotFoundError):
        service.atualizar(conta_recorrente.id, ContaRecorrenteUpdate(descricao="Hackeado"), usuario_id=2)


def test_atualizar_frequencia_sem_ajustar_dia_vencimento_levanta_erro(service):
    # MENSAL (com dia_vencimento) -> SEMANAL exige limpar dia_vencimento
    # junto - o PATCH que so troca a frequencia deixa o par invalido.
    conta_recorrente = _criar(service, data_inicio=date(2026, 1, 1))
    with pytest.raises(BusinessRuleError):
        service.atualizar(
            conta_recorrente.id,
            ContaRecorrenteUpdate(frequencia=FrequenciaRecorrencia.SEMANAL),
            usuario_id=1,
        )


def test_atualizar_frequencia_e_dia_vencimento_juntos_e_aceito(service):
    conta_recorrente = _criar(
        service, data_inicio=_primeiro_dia_proximo_mes(date.today())
    )
    atualizada = service.atualizar(
        conta_recorrente.id,
        ContaRecorrenteUpdate(frequencia=FrequenciaRecorrencia.SEMANAL, dia_vencimento=None),
        usuario_id=1,
    )
    assert atualizada.frequencia == FrequenciaRecorrencia.SEMANAL
    assert atualizada.dia_vencimento is None


def test_atualizar_estrutura_para_conta_e_cartao_ao_mesmo_tempo_levanta_business_rule_error(service):
    conta_recorrente = _criar(service, conta_id=100, cartao_id=None, data_inicio=date(2026, 1, 1))
    with pytest.raises(BusinessRuleError):
        service.atualizar(conta_recorrente.id, ContaRecorrenteUpdate(cartao_id=10), usuario_id=1)


def test_atualizar_permite_trocar_de_conta_para_cartao_explicitamente(service):
    conta_recorrente = _criar(service, conta_id=100, cartao_id=None, data_inicio=date(2026, 1, 1))
    atualizada = service.atualizar(
        conta_recorrente.id,
        ContaRecorrenteUpdate(conta_id=None, cartao_id=10),
        usuario_id=1,
    )
    assert atualizada.conta_id is None
    assert atualizada.cartao_id == 10


def test_atualizar_data_inicio_sem_ocorrencias_reancora_o_cursor(service):
    inicio_original = _primeiro_dia_proximo_mes(date.today())
    inicio_novo = _primeiro_dia_proximo_mes(inicio_original)
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=inicio_original)
    assert conta_recorrente.proxima_execucao == inicio_original

    atualizada = service.atualizar(
        conta_recorrente.id, ContaRecorrenteUpdate(data_inicio=inicio_novo), usuario_id=1
    )
    assert atualizada.proxima_execucao == inicio_novo


def test_atualizar_nao_gera_nenhuma_ocorrencia_nova(service, transacao_service):
    hoje = date.today()
    conta_recorrente = _criar(service, dia_vencimento=1, data_inicio=_primeiro_dia_meses_atras(hoje, 2))
    total_antes = len(transacao_service.chamadas_criar)
    service.atualizar(conta_recorrente.id, ContaRecorrenteUpdate(valor=Decimal("999.00")), usuario_id=1)
    assert len(transacao_service.chamadas_criar) == total_antes
