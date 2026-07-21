"""Testes unitários de ParcelamentoService - isolado com repositories e um
TransacaoService FALSOS (em memória, sem banco). Cobre exatamente o que é
próprio de ParcelamentoService (divisão de valor, geração de datas com
clamping/rollover de mês, cancelamento parcial preservando histórico,
posse do usuário) - a validação de posse/ativo de Conta ou Cartão,
compatibilidade de categoria, resolução de fatura etc. NÃO é reexercitada
aqui: já está exaustivamente coberta em test_transacao_service.py, e
ParcelamentoService nunca duplica essa lógica, apenas delega para
TransacaoService (ver docs/analise-arquitetural-parcelamento.md).
"""
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.schemas.parcelamento import ParcelamentoCreate
from app.services.parcelamento_service import ParcelamentoService


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
        self.parcelamento_id = dados.parcelamento_id
        self.numero_parcela = dados.numero_parcela


class FakeTransacaoRepository:
    """Compartilhado com FakeTransacaoService (mesma instância) - assim
    `ParcelamentoService.cancelar` consegue listar, via
    `transacao_repo.listar_do_usuario`, as parcelas que
    `transacao_service.criar` gerou."""

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

    def delete(self, transacao):
        del self._transacoes[transacao.id]

    def listar_do_usuario(self, usuario_id, *, parcelamento_id=None, limit=100, **_ignorado):
        resultado = [t for t in self._transacoes.values() if t.usuario_id == usuario_id]
        if parcelamento_id is not None:
            resultado = [t for t in resultado if t.parcelamento_id == parcelamento_id]
        resultado.sort(key=lambda t: t.numero_parcela)
        return resultado[:limit]


class FakeTransacaoService:
    """Substitui TransacaoService de verdade - ParcelamentoService nunca
    deveria precisar saber COMO uma transação é validada/criada (isso já é
    responsabilidade de TransacaoService, testada à exaustão em
    test_transacao_service.py). Aqui só registramos as chamadas, para
    confirmar que ParcelamentoService de fato DELEGA em vez de duplicar
    lógica, e permitimos simular uma parcela "travada" (fatura já
    fechada) via `ids_que_falham_ao_excluir`.

    `cancelar_parcelas_do_parcelamento` espelha o método de verdade (ver
    TransacaoService): bug real de 2026-07-20 fez o loop de cancelamento
    (excluir as parcelas destravadas + marcar Parcelamento.ativo=False)
    migrar de dentro de `ParcelamentoService.cancelar` para dentro de
    `TransacaoService` - agora é o ÚNICO lugar que faz isso, também
    chamado por `TransacaoService.excluir()` quando qualquer parcela
    isolada é apagada pelo endpoint genérico de Transação."""

    def __init__(self, transacao_repo, parcelamento_repo=None):
        self.transacao_repo = transacao_repo
        self.parcelamento_repo = parcelamento_repo
        self.chamadas_criar = []
        self.chamadas_excluir = []
        self.chamadas_cancelar_parcelamento = []
        self.ids_que_falham_ao_excluir: set[int] = set()

    def criar(self, dados, usuario_id):
        self.chamadas_criar.append((dados, usuario_id))
        return self.transacao_repo.create(_TransacaoFalsa(dados, usuario_id))

    def excluir(self, transacao_id, usuario_id):
        self.chamadas_excluir.append((transacao_id, usuario_id))
        if transacao_id in self.ids_que_falham_ao_excluir:
            raise BusinessRuleError("Transação de cartão com fatura já fechada não pode ser excluída.")
        self.transacao_repo.delete(self.transacao_repo.get(transacao_id))

    def cancelar_parcelas_do_parcelamento(self, parcelamento_id, usuario_id):
        self.chamadas_cancelar_parcelamento.append((parcelamento_id, usuario_id))
        parcelas = self.transacao_repo.listar_do_usuario(usuario_id, parcelamento_id=parcelamento_id)
        for parcela in parcelas:
            if parcela.id in self.ids_que_falham_ao_excluir:
                continue
            self.transacao_repo.delete(parcela)
        parcelamento = self.parcelamento_repo.get(parcelamento_id)
        if parcelamento is not None and parcelamento.ativo:
            parcelamento.ativo = False
            self.parcelamento_repo.update(parcelamento)


class FakeParcelamentoRepository:
    def __init__(self):
        self._parcelamentos = {}
        self._proximo_id = 1

    def create(self, parcelamento):
        parcelamento.id = self._proximo_id
        self._proximo_id += 1
        self._parcelamentos[parcelamento.id] = parcelamento
        return parcelamento

    def get(self, id):
        return self._parcelamentos.get(id)

    def update(self, parcelamento):
        return parcelamento

    def listar_do_usuario(self, usuario_id, *, apenas_ativos=True, skip=0, limit=100):
        resultado = [p for p in self._parcelamentos.values() if p.usuario_id == usuario_id]
        if apenas_ativos:
            resultado = [p for p in resultado if p.ativo]
        resultado.sort(key=lambda p: p.data_inicio, reverse=True)
        return resultado[skip : skip + limit]


@pytest.fixture()
def transacao_repo():
    return FakeTransacaoRepository()


@pytest.fixture()
def parcelamento_repo():
    return FakeParcelamentoRepository()


@pytest.fixture()
def transacao_service(transacao_repo, parcelamento_repo):
    return FakeTransacaoService(transacao_repo, parcelamento_repo)


@pytest.fixture()
def service(parcelamento_repo, transacao_repo, transacao_service):
    return ParcelamentoService(parcelamento_repo, transacao_repo, transacao_service)


def _criar(
    service,
    usuario_id=1,
    descricao="Notebook",
    valor_total=Decimal("1000.00"),
    num_parcelas=10,
    taxa_juros=None,
    data_inicio=date(2026, 7, 15),
    categoria_id=None,
    cartao_id=10,
    conta_id=None,
    valor_parcela=None,
):
    dados = ParcelamentoCreate(
        descricao=descricao,
        valor_total=valor_total,
        num_parcelas=num_parcelas,
        taxa_juros=taxa_juros,
        data_inicio=data_inicio,
        categoria_id=categoria_id,
        cartao_id=cartao_id,
        conta_id=conta_id,
        valor_parcela=valor_parcela,
    )
    return service.criar(dados, usuario_id)


# --- criar: estrutura (cartao XOR conta) ------------------------------------

def test_criar_sem_cartao_e_sem_conta_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, cartao_id=None, conta_id=None)


def test_criar_com_cartao_e_conta_ao_mesmo_tempo_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, cartao_id=10, conta_id=100)


def test_criar_com_estrutura_invalida_nao_gera_nenhuma_parcela(service, transacao_service):
    with pytest.raises(BusinessRuleError):
        _criar(service, cartao_id=None, conta_id=None)
    assert transacao_service.chamadas_criar == []


# --- criar: delegação para TransacaoService (nao duplica logica) -----------

def test_criar_gera_uma_transacao_por_parcela_via_transacao_service(service, transacao_service):
    _criar(service, num_parcelas=10)
    assert len(transacao_service.chamadas_criar) == 10


def test_criar_repassa_cartao_id_para_cada_parcela(service, transacao_service):
    _criar(service, cartao_id=10, conta_id=None, num_parcelas=3)
    for dados, _usuario_id in transacao_service.chamadas_criar:
        assert dados.cartao_id == 10
        assert dados.conta_id is None


def test_criar_repassa_conta_id_para_cada_parcela(service, transacao_service):
    _criar(service, cartao_id=None, conta_id=100, num_parcelas=3)
    for dados, _usuario_id in transacao_service.chamadas_criar:
        assert dados.conta_id == 100
        assert dados.cartao_id is None


def test_criar_gera_parcelas_como_despesa_vinculadas_ao_parcelamento(service, transacao_service):
    from app.models.enums import TipoTransacao

    parcelamento = _criar(service, num_parcelas=3)
    for dados, usuario_id in transacao_service.chamadas_criar:
        assert dados.tipo == TipoTransacao.DESPESA
        assert dados.parcelamento_id == parcelamento.id
        assert usuario_id == 1


def test_criar_numera_parcelas_de_1_ate_num_parcelas_em_ordem(service, transacao_service):
    _criar(service, num_parcelas=4)
    numeros = [dados.numero_parcela for dados, _ in transacao_service.chamadas_criar]
    assert numeros == [1, 2, 3, 4]


def test_criar_repassa_categoria_para_cada_parcela(service, transacao_service):
    _criar(service, categoria_id=7, num_parcelas=2)
    for dados, _ in transacao_service.chamadas_criar:
        assert dados.categoria_id == 7


# --- criar: divisão de valores -----------------------------------------------

def test_criar_divide_valor_total_em_partes_iguais_quando_exato(service, transacao_service):
    _criar(service, valor_total=Decimal("1000.00"), num_parcelas=10)
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar]
    assert valores == [Decimal("100.00")] * 10
    assert sum(valores) == Decimal("1000.00")


def test_criar_divide_valor_total_com_resto_absorvido_pela_ultima_parcela(service, transacao_service):
    # 100 / 3 = 33.333... -> 33.33 arredondado; 2 primeiras = 33.33,
    # ultima absorve o resto para a soma bater exatamente com 100.00.
    _criar(service, valor_total=Decimal("100.00"), num_parcelas=3)
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar]
    assert valores[:2] == [Decimal("33.33"), Decimal("33.33")]
    assert valores[2] == Decimal("33.34")
    assert sum(valores) == Decimal("100.00")


def test_criar_divide_valor_total_com_resto_negativo_absorvido_pela_ultima_parcela(service, transacao_service):
    # 100 / 3 arredondaria para 33.33 * 3 = 99.99 (falta 1 centavo) SE nao
    # fosse pela regra oposta acontecendo aqui: 10.01 / 3 = 3.336... ->
    # 3.34 * 2 = 6.68, sobra so 3.33 pra ultima - cobre o caso em que a
    # ultima parcela fica MENOR que as demais, nao so maior.
    _criar(service, valor_total=Decimal("10.01"), num_parcelas=3)
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar]
    assert sum(valores) == Decimal("10.01")
    assert valores[2] == Decimal("10.01") - valores[0] - valores[1]


# --- criar: valor_parcela customizado (juros embutidos pela loja) ----------

def test_criar_com_valor_parcela_usa_o_mesmo_valor_em_todas_as_parcelas(service, transacao_service):
    """Compra de R$1000 em 10x, mas a loja cobra R$105/mês (embute juros) -
    valor_parcela informado prevalece sobre a divisão de valor_total."""
    _criar(service, valor_total=Decimal("1000.00"), num_parcelas=10, valor_parcela=Decimal("105.00"))
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar]
    assert valores == [Decimal("105.00")] * 10


def test_criar_com_valor_parcela_nao_absorve_resto_na_ultima(service, transacao_service):
    """Diferente da divisão padrão: aqui a última parcela NÃO vira um plug
    de arredondamento - todas são idênticas, mesmo que a soma não feche
    exatamente com valor_total (esperado, é o preço do juro embutido)."""
    _criar(service, valor_total=Decimal("100.00"), num_parcelas=3, valor_parcela=Decimal("35.00"))
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar]
    assert valores == [Decimal("35.00")] * 3
    assert sum(valores) != Decimal("100.00")


def test_criar_sem_valor_parcela_mantem_divisao_padrao_de_valor_total(service, transacao_service):
    _criar(service, valor_total=Decimal("1000.00"), num_parcelas=10, valor_parcela=None)
    valores = [dados.valor for dados, _ in transacao_service.chamadas_criar]
    assert valores == [Decimal("100.00")] * 10


# --- criar: geração de datas (clamping e rollover de mês) ------------------

def test_criar_primeira_parcela_usa_a_propria_data_inicio(service, transacao_service):
    _criar(service, data_inicio=date(2026, 7, 15), num_parcelas=2)
    primeira_data = transacao_service.chamadas_criar[0][0].data
    assert primeira_data == date(2026, 7, 15)


def test_criar_parcelas_seguintes_somam_um_mes_por_vez(service, transacao_service):
    _criar(service, data_inicio=date(2026, 7, 15), num_parcelas=3)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2026, 7, 15), date(2026, 8, 15), date(2026, 9, 15)]


def test_criar_datas_fazem_rollover_de_ano_ao_passar_de_dezembro(service, transacao_service):
    _criar(service, data_inicio=date(2026, 11, 30), num_parcelas=3)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    # nov/2026 (dia 30) -> dez/2026 (dia 30) -> jan/2027 (dia 30)
    assert datas == [date(2026, 11, 30), date(2026, 12, 30), date(2027, 1, 30)]


def test_criar_datas_fazem_clamping_de_dia_em_mes_mais_curto(service, transacao_service):
    # dia 31 nao existe em fevereiro (2027 nao e bissexto) - cai pro
    # ultimo dia do mes, mesmo raciocinio ja usado por FaturaService.
    _criar(service, data_inicio=date(2027, 1, 31), num_parcelas=2)
    datas = [dados.data for dados, _ in transacao_service.chamadas_criar]
    assert datas == [date(2027, 1, 31), date(2027, 2, 28)]


# --- obter / listar -----------------------------------------------------------

def test_obter_parcelamento_proprio(service):
    parcelamento = _criar(service)
    assert service.obter(parcelamento.id, usuario_id=1).id == parcelamento.id


def test_obter_parcelamento_de_outro_usuario_levanta_not_found(service):
    parcelamento = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(parcelamento.id, usuario_id=2)


def test_obter_parcelamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_parcelamentos_do_usuario(service):
    _criar(service, usuario_id=1, cartao_id=10, conta_id=None, descricao="Meu")
    _criar(service, usuario_id=2, cartao_id=None, conta_id=100, descricao="Do outro")
    resultado = service.listar(usuario_id=1)
    assert [p.descricao for p in resultado] == ["Meu"]


def test_listar_por_padrao_oculta_parcelamentos_cancelados(service):
    parcelamento = _criar(service, usuario_id=1)
    service.cancelar(parcelamento.id, usuario_id=1)
    assert service.listar(usuario_id=1) == []
    assert service.listar(usuario_id=1, apenas_ativos=False) == [parcelamento]


# --- cancelar -------------------------------------------------------------

def test_cancelar_marca_ativo_como_false(service):
    parcelamento = _criar(service)
    cancelado = service.cancelar(parcelamento.id, usuario_id=1)
    assert cancelado.ativo is False


def test_cancelar_exclui_todas_as_parcelas_quando_nenhuma_esta_travada(
    service, transacao_service, transacao_repo
):
    # Bug real de 2026-07-20: o loop de cancelamento migrou de
    # ParcelamentoService (chamando excluir() por parcela) para um único
    # método em TransacaoService (cancelar_parcelas_do_parcelamento),
    # chamado tanto daqui quanto de TransacaoService.excluir() - ver
    # docstring de ambos.
    parcelamento = _criar(service, num_parcelas=3)
    service.cancelar(parcelamento.id, usuario_id=1)
    assert transacao_service.chamadas_cancelar_parcelamento == [(parcelamento.id, 1)]
    assert transacao_repo.listar_do_usuario(1, parcelamento_id=parcelamento.id) == []


def test_cancelar_preserva_parcelas_com_fatura_ja_fechada(service, transacao_service, transacao_repo):
    parcelamento = _criar(service, num_parcelas=3)
    parcelas = transacao_repo.listar_do_usuario(1, parcelamento_id=parcelamento.id)
    parcela_travada = parcelas[0].id
    transacao_service.ids_que_falham_ao_excluir.add(parcela_travada)

    service.cancelar(parcelamento.id, usuario_id=1)

    restantes = transacao_repo.listar_do_usuario(1, parcelamento_id=parcelamento.id)
    assert [p.id for p in restantes] == [parcela_travada]  # so a travada sobrou


def test_cancelar_parcelamento_ja_cancelado_levanta_business_rule_error(service):
    parcelamento = _criar(service)
    service.cancelar(parcelamento.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.cancelar(parcelamento.id, usuario_id=1)


def test_cancelar_parcelamento_de_outro_usuario_levanta_not_found(service):
    parcelamento = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.cancelar(parcelamento.id, usuario_id=2)


def test_cancelar_parcelamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.cancelar(999, usuario_id=1)
