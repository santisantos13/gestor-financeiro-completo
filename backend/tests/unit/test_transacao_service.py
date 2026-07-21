"""Testes unitários de TransacaoService - isolado com repositories FALSOS
(em memória, sem banco). Cobre validação estrutural (conta XOR cartão, no
máximo um contrato, numero_parcela condizente - mesma família dos
CheckConstraints do model), posse cruzada de Conta/Cartão/Categoria/Tag/
Parcelamento/Financiamento/Empréstimo/Meta, resolução de fatura via um
FaturaService falso, `status` forçado para transação de cartão OU de
contrato de crédito, bloqueio de edição de `status` para parcela de
contrato de crédito, e imutabilidade de transações vinculadas a fatura
fechada. Ver docs/analise-arquitetural-transacao.md,
docs/analise-arquitetural-financiamento.md,
docs/analise-arquitetural-emprestimo.md e docs/analise-arquitetural-meta.md.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Tag, Transacao
from app.models.enums import StatusFatura, StatusTransacao, TipoCategoria, TipoTransacao
from app.schemas.transacao import TransacaoCreate, TransacaoUpdate
from app.services.transacao_service import EscopoOperacaoParcela, TransacaoService


class FakeTransacaoRepository:
    def __init__(self):
        self._transacoes = {}
        self._proximo_id = 1

    def get(self, id):
        return self._transacoes.get(id)

    def create(self, transacao):
        transacao.id = self._proximo_id
        self._proximo_id += 1
        self._transacoes[transacao.id] = transacao
        return transacao

    def update(self, transacao):
        return transacao

    def delete(self, transacao):
        del self._transacoes[transacao.id]

    def listar_do_usuario(
        self,
        usuario_id,
        *,
        conta_id=None,
        cartao_id=None,
        fatura_id=None,
        categoria_id=None,
        parcelamento_id=None,
        financiamento_id=None,
        emprestimo_id=None,
        origem_recorrente_id=None,
        meta_id=None,
        tipo=None,
        status=None,
        data_inicio=None,
        data_fim=None,
        apenas_conta=False,
        skip=0,
        limit=100,
    ):
        resultado = [t for t in self._transacoes.values() if t.usuario_id == usuario_id]
        if conta_id is not None:
            resultado = [t for t in resultado if t.conta_id == conta_id]
        if cartao_id is not None:
            resultado = [t for t in resultado if t.cartao_id == cartao_id]
        if fatura_id is not None:
            resultado = [t for t in resultado if getattr(t, "fatura_id", None) == fatura_id]
        if apenas_conta:
            resultado = [t for t in resultado if t.cartao_id is None]
        if categoria_id is not None:
            resultado = [t for t in resultado if t.categoria_id == categoria_id]
        if parcelamento_id is not None:
            resultado = [t for t in resultado if t.parcelamento_id == parcelamento_id]
        if financiamento_id is not None:
            resultado = [t for t in resultado if t.financiamento_id == financiamento_id]
        if emprestimo_id is not None:
            resultado = [t for t in resultado if t.emprestimo_id == emprestimo_id]
        if origem_recorrente_id is not None:
            resultado = [t for t in resultado if t.origem_recorrente_id == origem_recorrente_id]
        if meta_id is not None:
            resultado = [t for t in resultado if t.meta_id == meta_id]
        if tipo is not None:
            resultado = [t for t in resultado if t.tipo == tipo]
        if status is not None:
            resultado = [t for t in resultado if t.status == status]
        if data_inicio is not None:
            resultado = [t for t in resultado if t.data >= data_inicio]
        if data_fim is not None:
            resultado = [t for t in resultado if t.data <= data_fim]
        resultado.sort(key=lambda t: (t.data, t.id), reverse=True)
        return resultado[skip : skip + limit]


class _ContaFalsa:
    def __init__(self, id, usuario_id, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.ativo = ativo


class FakeContaRepository:
    def __init__(self):
        self._contas = {}

    def adicionar(self, conta_id, usuario_id, ativo=True):
        self._contas[conta_id] = _ContaFalsa(conta_id, usuario_id, ativo)

    def get(self, id):
        return self._contas.get(id)


class _CartaoFalso:
    def __init__(self, id, usuario_id, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.ativo = ativo


class FakeCartaoRepository:
    def __init__(self):
        self._cartoes = {}

    def adicionar(self, cartao_id, usuario_id, ativo=True):
        self._cartoes[cartao_id] = _CartaoFalso(cartao_id, usuario_id, ativo)

    def get(self, id):
        return self._cartoes.get(id)


class _CategoriaFalsa:
    def __init__(self, id, usuario_id, tipo=TipoCategoria.AMBOS, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.tipo = tipo
        self.ativo = ativo


class FakeCategoriaRepository:
    def __init__(self):
        self._categorias = {}

    def adicionar(self, categoria_id, usuario_id=None, tipo=TipoCategoria.AMBOS, ativo=True):
        self._categorias[categoria_id] = _CategoriaFalsa(categoria_id, usuario_id, tipo, ativo)

    def get(self, id):
        return self._categorias.get(id)


class FakeTagRepository:
    """Usa o model Tag DE VERDADE (nao um objeto falso qualquer) - Tag
    participa de um relationship N-N real em Transacao.tags, e o SQLAlchemy
    dispara eventos de ORM (bulk_replace/fire_append_event) ao atribuir a
    lista que exigem instancias de verdade mapeadas pelo ORM."""

    def __init__(self):
        self._tags = {}

    def adicionar(self, tag_id, usuario_id, ativo=True):
        self._tags[tag_id] = Tag(id=tag_id, usuario_id=usuario_id, nome=f"tag{tag_id}", ativo=ativo)

    def get(self, id):
        return self._tags.get(id)


class _FaturaFalsa:
    def __init__(self, id, status):
        self.id = id
        self.status = status


class FakeFaturaRepository:
    def __init__(self):
        self._faturas = {}

    def adicionar(self, fatura_id, status=StatusFatura.ABERTA):
        self._faturas[fatura_id] = _FaturaFalsa(fatura_id, status)

    def get(self, id):
        return self._faturas.get(id)


class FakeFaturaService:
    """Substitui FaturaService de verdade nestes testes - devolve faturas
    de um FakeFaturaRepository COMPARTILHADO com o TransacaoService sendo
    testado, para os testes de imutabilidade poderem alterar o status da
    fatura depois de criada."""

    def __init__(self, fatura_repo):
        self.fatura_repo = fatura_repo
        self._proximo_id = 1
        self.chamadas = []
        self.excecao: Exception | None = None

    def resolver_fatura_aberta(self, cartao_id, data, usuario_id):
        self.chamadas.append((cartao_id, data, usuario_id))
        if self.excecao is not None:
            raise self.excecao
        fatura_id = self._proximo_id
        self._proximo_id += 1
        self.fatura_repo.adicionar(fatura_id, status=StatusFatura.ABERTA)
        return self.fatura_repo.get(fatura_id)


class _ParcelamentoFalso:
    def __init__(self, id, usuario_id, num_parcelas, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.num_parcelas = num_parcelas
        self.ativo = ativo


class FakeParcelamentoRepository:
    def __init__(self):
        self._parcelamentos = {}

    def adicionar(self, parcelamento_id, usuario_id, num_parcelas=10, ativo=True):
        self._parcelamentos[parcelamento_id] = _ParcelamentoFalso(parcelamento_id, usuario_id, num_parcelas, ativo)

    def get(self, id):
        return self._parcelamentos.get(id)

    def update(self, parcelamento):
        return parcelamento


class _FinanciamentoFalso:
    def __init__(self, id, usuario_id, num_parcelas):
        self.id = id
        self.usuario_id = usuario_id
        self.num_parcelas = num_parcelas


class FakeFinanciamentoRepository:
    def __init__(self):
        self._financiamentos = {}

    def adicionar(self, financiamento_id, usuario_id, num_parcelas=6):
        self._financiamentos[financiamento_id] = _FinanciamentoFalso(financiamento_id, usuario_id, num_parcelas)

    def get(self, id):
        return self._financiamentos.get(id)


class _EmprestimoFalso:
    def __init__(self, id, usuario_id, num_parcelas):
        self.id = id
        self.usuario_id = usuario_id
        self.num_parcelas = num_parcelas


class FakeEmprestimoRepository:
    def __init__(self):
        self._emprestimos = {}

    def adicionar(self, emprestimo_id, usuario_id, num_parcelas=5):
        self._emprestimos[emprestimo_id] = _EmprestimoFalso(emprestimo_id, usuario_id, num_parcelas)

    def get(self, id):
        return self._emprestimos.get(id)


class _ContaRecorrenteFalsa:
    def __init__(self, id, usuario_id, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.ativo = ativo


class FakeContaRecorrenteRepository:
    def __init__(self):
        self._contas_recorrentes = {}

    def adicionar(self, conta_recorrente_id, usuario_id, ativo=True):
        self._contas_recorrentes[conta_recorrente_id] = _ContaRecorrenteFalsa(
            conta_recorrente_id, usuario_id, ativo
        )

    def get(self, id):
        return self._contas_recorrentes.get(id)


class _MetaFalsa:
    def __init__(self, id, usuario_id, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.ativo = ativo


class FakeMetaRepository:
    def __init__(self):
        self._metas = {}

    def adicionar(self, meta_id, usuario_id, ativo=True):
        self._metas[meta_id] = _MetaFalsa(meta_id, usuario_id, ativo)

    def get(self, id):
        return self._metas.get(id)


@pytest.fixture()
def transacao_repo():
    return FakeTransacaoRepository()


@pytest.fixture()
def conta_repo():
    repo = FakeContaRepository()
    repo.adicionar(conta_id=100, usuario_id=1)
    repo.adicionar(conta_id=200, usuario_id=2)
    repo.adicionar(conta_id=101, usuario_id=1, ativo=False)
    return repo


@pytest.fixture()
def cartao_repo():
    repo = FakeCartaoRepository()
    repo.adicionar(cartao_id=10, usuario_id=1)
    repo.adicionar(cartao_id=20, usuario_id=2)
    repo.adicionar(cartao_id=11, usuario_id=1, ativo=False)
    return repo


@pytest.fixture()
def categoria_repo():
    repo = FakeCategoriaRepository()
    repo.adicionar(categoria_id=1, usuario_id=1, tipo=TipoCategoria.AMBOS)
    repo.adicionar(categoria_id=2, usuario_id=1, tipo=TipoCategoria.DESPESA)
    repo.adicionar(categoria_id=3, usuario_id=1, tipo=TipoCategoria.RECEITA)
    repo.adicionar(categoria_id=4, usuario_id=2, tipo=TipoCategoria.AMBOS)
    repo.adicionar(categoria_id=5, usuario_id=None, tipo=TipoCategoria.AMBOS)
    repo.adicionar(categoria_id=6, usuario_id=1, tipo=TipoCategoria.AMBOS, ativo=False)
    return repo


@pytest.fixture()
def tag_repo():
    repo = FakeTagRepository()
    repo.adicionar(tag_id=1, usuario_id=1)
    repo.adicionar(tag_id=2, usuario_id=2)
    repo.adicionar(tag_id=3, usuario_id=1, ativo=False)
    return repo


@pytest.fixture()
def fatura_repo():
    return FakeFaturaRepository()


@pytest.fixture()
def fatura_service(fatura_repo):
    return FakeFaturaService(fatura_repo)


@pytest.fixture()
def parcelamento_repo():
    repo = FakeParcelamentoRepository()
    repo.adicionar(parcelamento_id=1, usuario_id=1, num_parcelas=10)
    repo.adicionar(parcelamento_id=2, usuario_id=2, num_parcelas=5)
    return repo


@pytest.fixture()
def financiamento_repo():
    repo = FakeFinanciamentoRepository()
    repo.adicionar(financiamento_id=1, usuario_id=1, num_parcelas=6)
    repo.adicionar(financiamento_id=2, usuario_id=2, num_parcelas=5)
    return repo


@pytest.fixture()
def emprestimo_repo():
    repo = FakeEmprestimoRepository()
    repo.adicionar(emprestimo_id=1, usuario_id=1, num_parcelas=5)
    repo.adicionar(emprestimo_id=2, usuario_id=2, num_parcelas=4)
    return repo


@pytest.fixture()
def conta_recorrente_repo():
    repo = FakeContaRecorrenteRepository()
    repo.adicionar(conta_recorrente_id=1, usuario_id=1)
    repo.adicionar(conta_recorrente_id=2, usuario_id=2)
    return repo


@pytest.fixture()
def meta_repo():
    repo = FakeMetaRepository()
    repo.adicionar(meta_id=1, usuario_id=1)
    repo.adicionar(meta_id=2, usuario_id=2)
    repo.adicionar(meta_id=3, usuario_id=1, ativo=False)
    return repo


@pytest.fixture()
def service(
    transacao_repo,
    conta_repo,
    cartao_repo,
    categoria_repo,
    tag_repo,
    parcelamento_repo,
    financiamento_repo,
    emprestimo_repo,
    conta_recorrente_repo,
    meta_repo,
    fatura_repo,
    fatura_service,
):
    return TransacaoService(
        transacao_repo,
        conta_repo,
        cartao_repo,
        categoria_repo,
        tag_repo,
        parcelamento_repo,
        financiamento_repo,
        emprestimo_repo,
        conta_recorrente_repo,
        meta_repo,
        fatura_repo,
        fatura_service,
    )


def _criar(
    service,
    usuario_id=1,
    tipo=TipoTransacao.DESPESA,
    valor=Decimal("100.00"),
    data=date(2026, 7, 3),
    descricao="Compra",
    status=None,
    categoria_id=None,
    conta_id=100,
    cartao_id=None,
    parcelamento_id=None,
    financiamento_id=None,
    emprestimo_id=None,
    numero_parcela=None,
    origem_recorrente_id=None,
    meta_id=None,
    tag_ids=None,
):
    dados = TransacaoCreate(
        tipo=tipo,
        valor=valor,
        data=data,
        descricao=descricao,
        status=status,
        categoria_id=categoria_id,
        conta_id=conta_id,
        cartao_id=cartao_id,
        parcelamento_id=parcelamento_id,
        financiamento_id=financiamento_id,
        emprestimo_id=emprestimo_id,
        numero_parcela=numero_parcela,
        origem_recorrente_id=origem_recorrente_id,
        meta_id=meta_id,
        tag_ids=tag_ids or [],
    )
    return service.criar(dados, usuario_id)


# --- criar: estrutura (conta XOR cartão, contrato, numero_parcela) --------

def test_criar_sem_conta_e_sem_cartao_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None, cartao_id=None)


def test_criar_com_conta_e_cartao_ao_mesmo_tempo_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=100, cartao_id=10)


def test_criar_com_mais_de_um_contrato_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, parcelamento_id=1, financiamento_id=1, numero_parcela=1)


def test_criar_com_contrato_sem_numero_parcela_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, parcelamento_id=1, numero_parcela=None)


def test_criar_com_numero_parcela_sem_contrato_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, numero_parcela=3)


# --- criar: posse e faixa de parcelamento_id --------------------------------

def test_criar_com_parcelamento_proprio_e_numero_parcela_valido_e_aceito(service):
    transacao = _criar(service, parcelamento_id=1, numero_parcela=3)
    assert transacao.parcelamento_id == 1
    assert transacao.numero_parcela == 3


def test_criar_com_parcelamento_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, parcelamento_id=2, numero_parcela=1)  # parcelamento 2 e do usuario 2


def test_criar_com_parcelamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, parcelamento_id=999, numero_parcela=1)


def test_criar_com_numero_parcela_acima_do_num_parcelas_levanta_business_rule_error(service):
    # parcelamento 1 (fixture) tem num_parcelas=10; numero_parcela=0 nunca
    # chega ate aqui - ja e rejeitado por TransacaoCreate (Field(ge=1)).
    with pytest.raises(BusinessRuleError):
        _criar(service, parcelamento_id=1, numero_parcela=11)


def test_criar_com_numero_parcela_ja_usada_no_mesmo_parcelamento_levanta_conflict_error(service):
    # achado da revisao tecnica final: sem essa checagem, essa duplicata so
    # seria barrada pelo UniqueConstraint do banco - um IntegrityError cru,
    # nunca traduzido em resposta HTTP (ver _validar_parcelamento).
    _criar(service, parcelamento_id=1, numero_parcela=1)
    with pytest.raises(ConflictError):
        _criar(service, parcelamento_id=1, numero_parcela=1)


# --- criar: posse e faixa de financiamento_id -------------------------------

def test_criar_com_financiamento_proprio_e_numero_parcela_valido_e_aceito(service):
    transacao = _criar(service, financiamento_id=1, numero_parcela=3)
    assert transacao.financiamento_id == 1
    assert transacao.numero_parcela == 3


def test_criar_com_financiamento_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, financiamento_id=2, numero_parcela=1)  # financiamento 2 e do usuario 2


def test_criar_com_financiamento_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, financiamento_id=999, numero_parcela=1)


def test_criar_com_numero_parcela_acima_do_num_parcelas_do_financiamento_levanta_business_rule_error(service):
    # financiamento 1 (fixture) tem num_parcelas=6.
    with pytest.raises(BusinessRuleError):
        _criar(service, financiamento_id=1, numero_parcela=7)


def test_criar_com_numero_parcela_ja_usada_no_mesmo_financiamento_levanta_conflict_error(service):
    _criar(service, financiamento_id=1, numero_parcela=1)
    with pytest.raises(ConflictError):
        _criar(service, financiamento_id=1, numero_parcela=1)


def test_criar_transacao_de_financiamento_forca_status_pendente_ignorando_payload(service):
    # protege saldo_devedor: mesmo que o cliente mande PAGO explicitamente,
    # so marcar_parcela_de_contrato_paga() (chamada exclusivamente pela
    # acao dedicada de FinanciamentoService.pagar_parcela) pode mudar isso.
    transacao = _criar(
        service, financiamento_id=1, numero_parcela=1, status=StatusTransacao.PAGO
    )
    assert transacao.status == StatusTransacao.PENDENTE


# --- criar: posse e faixa de emprestimo_id ----------------------------------

def test_criar_com_emprestimo_proprio_e_numero_parcela_valido_e_aceito(service):
    transacao = _criar(service, emprestimo_id=1, numero_parcela=3)
    assert transacao.emprestimo_id == 1
    assert transacao.numero_parcela == 3


def test_criar_com_emprestimo_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, emprestimo_id=2, numero_parcela=1)  # emprestimo 2 e do usuario 2


def test_criar_com_emprestimo_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, emprestimo_id=999, numero_parcela=1)


def test_criar_com_numero_parcela_acima_do_num_parcelas_do_emprestimo_levanta_business_rule_error(service):
    # emprestimo 1 (fixture) tem num_parcelas=5.
    with pytest.raises(BusinessRuleError):
        _criar(service, emprestimo_id=1, numero_parcela=6)


def test_criar_com_numero_parcela_ja_usada_no_mesmo_emprestimo_levanta_conflict_error(service):
    _criar(service, emprestimo_id=1, numero_parcela=1)
    with pytest.raises(ConflictError):
        _criar(service, emprestimo_id=1, numero_parcela=1)


def test_criar_transacao_de_emprestimo_forca_status_pendente_ignorando_payload(service):
    transacao = _criar(
        service, emprestimo_id=1, numero_parcela=1, status=StatusTransacao.PAGO
    )
    assert transacao.status == StatusTransacao.PENDENTE


# --- criar/atualizar: meta_id (refatoramento aportes/resgates=Transferencia) -
#
# `meta_id` foi removido de TransacaoCreate/TransacaoUpdate (ver
# docs/analise-arquitetural-metas-transferencias.md, secao 6): nenhuma
# Transacao NOVA pode mais ser vinculada a uma Meta - aportes/resgates agora
# sao Transferencia para o "cofrinho" da Meta. Os testes de posse/validacao
# de meta_id em criar()/atualizar() que existiam aqui foram removidos porque
# testavam um caminho de escrita que nao existe mais (TransacaoCreate/Update
# ignoram silenciosamente um `meta_id` no payload - comportamento padrao do
# Pydantic v2 para campo desconhecido). O campo de LEITURA
# (`TransacaoRead.meta_id`) continua existindo para sustentar o historico
# legado congelado - ver test_listar_filtra_por_meta_id abaixo, que constroi
# a Transacao diretamente no repository falso (nao via TransacaoCreate) para
# continuar cobrindo o filtro `GET /transacoes?meta_id=`.


# --- atualizar: posse e faixa de financiamento_id ---------------------------

def test_atualizar_financiamento_para_financiamento_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, financiamento_id=1, numero_parcela=1)
    with pytest.raises(NotFoundError):
        service.atualizar(transacao.id, TransacaoUpdate(financiamento_id=2), usuario_id=1)


def test_atualizar_numero_parcela_do_financiamento_para_uma_ja_usada_levanta_conflict_error(service):
    _criar(service, financiamento_id=1, numero_parcela=1)
    outra = _criar(service, financiamento_id=1, numero_parcela=2)
    with pytest.raises(ConflictError):
        service.atualizar(outra.id, TransacaoUpdate(numero_parcela=1), usuario_id=1)


# --- atualizar: posse e faixa de emprestimo_id ------------------------------

def test_atualizar_emprestimo_para_emprestimo_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, emprestimo_id=1, numero_parcela=1)
    with pytest.raises(NotFoundError):
        service.atualizar(transacao.id, TransacaoUpdate(emprestimo_id=2), usuario_id=1)


def test_atualizar_numero_parcela_do_emprestimo_para_uma_ja_usada_levanta_conflict_error(service):
    _criar(service, emprestimo_id=1, numero_parcela=1)
    outra = _criar(service, emprestimo_id=1, numero_parcela=2)
    with pytest.raises(ConflictError):
        service.atualizar(outra.id, TransacaoUpdate(numero_parcela=1), usuario_id=1)


# --- atualizar/criar: bloqueio de status em contrato de crédito ------------

def test_criar_com_financiamento_e_status_pago_no_payload_nao_e_aplicado(service):
    transacao = _criar(service, financiamento_id=1, numero_parcela=1, status=StatusTransacao.PAGO)
    assert transacao.status != StatusTransacao.PAGO


def test_atualizar_status_em_transacao_de_financiamento_levanta_business_rule_error(service):
    transacao = _criar(service, financiamento_id=1, numero_parcela=1)
    with pytest.raises(BusinessRuleError):
        service.atualizar(transacao.id, TransacaoUpdate(status=StatusTransacao.PAGO), usuario_id=1)


def test_atualizar_status_em_transacao_de_emprestimo_levanta_business_rule_error(service):
    transacao = _criar(service, emprestimo_id=1, numero_parcela=1)
    with pytest.raises(BusinessRuleError):
        service.atualizar(transacao.id, TransacaoUpdate(status=StatusTransacao.PAGO), usuario_id=1)


def test_atualizar_outros_campos_em_transacao_de_financiamento_continua_permitido(service):
    # so `status` e bloqueado - descricao/valor continuam editaveis
    # livremente (o bloqueio protege especificamente saldo_devedor).
    transacao = _criar(service, financiamento_id=1, numero_parcela=1, descricao="Original")
    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(descricao="Renomeada"), usuario_id=1
    )
    assert atualizada.descricao == "Renomeada"


def test_atualizar_vinculando_financiamento_e_status_pago_na_mesma_chamada_levanta_business_rule_error(
    service,
):
    # achado da revisao critica final: a checagem original olhava so
    # transacao.financiamento_id ANTES do merge - um unico PATCH que
    # vincula financiamento_id e manda status=PAGO ao mesmo tempo
    # conseguia burlar a protecao, porque o valor antigo (None) ainda
    # passava na checagem. A checagem correta usa o estado MESCLADO
    # (financiamento_id que vai de fato ser gravado), nao o anterior.
    transacao = _criar(service, conta_id=100, status=StatusTransacao.PENDENTE)
    with pytest.raises(BusinessRuleError):
        service.atualizar(
            transacao.id,
            TransacaoUpdate(financiamento_id=1, numero_parcela=1, status=StatusTransacao.PAGO),
            usuario_id=1,
        )


def test_atualizar_vinculando_emprestimo_e_status_pago_na_mesma_chamada_levanta_business_rule_error(
    service,
):
    # mesma regressao aplicada a emprestimo_id - a checagem de status deve
    # olhar o estado MESCLADO tanto para financiamento_id quanto para
    # emprestimo_id (ver atualizar() em TransacaoService).
    transacao = _criar(service, conta_id=100, status=StatusTransacao.PENDENTE)
    with pytest.raises(BusinessRuleError):
        service.atualizar(
            transacao.id,
            TransacaoUpdate(emprestimo_id=1, numero_parcela=1, status=StatusTransacao.PAGO),
            usuario_id=1,
        )


# --- marcar_parcela_de_contrato_paga ----------------------------------------

def test_marcar_parcela_de_contrato_paga_transiciona_pendente_para_pago(service):
    transacao = _criar(service, financiamento_id=1, numero_parcela=1)
    assert transacao.status == StatusTransacao.PENDENTE

    atualizada = service.marcar_parcela_de_contrato_paga(transacao.id, usuario_id=1)
    assert atualizada.status == StatusTransacao.PAGO


def test_marcar_parcela_de_contrato_paga_funciona_para_emprestimo_tambem(service):
    transacao = _criar(service, emprestimo_id=1, numero_parcela=1)
    atualizada = service.marcar_parcela_de_contrato_paga(transacao.id, usuario_id=1)
    assert atualizada.status == StatusTransacao.PAGO


def test_marcar_parcela_ja_paga_levanta_business_rule_error(service):
    transacao = _criar(service, financiamento_id=1, numero_parcela=1)
    service.marcar_parcela_de_contrato_paga(transacao.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.marcar_parcela_de_contrato_paga(transacao.id, usuario_id=1)


def test_marcar_parcela_de_transacao_sem_contrato_levanta_business_rule_error(service):
    transacao = _criar(service, conta_id=100)
    with pytest.raises(BusinessRuleError):
        service.marcar_parcela_de_contrato_paga(transacao.id, usuario_id=1)


def test_marcar_parcela_de_contrato_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, usuario_id=1, financiamento_id=1, numero_parcela=1)
    with pytest.raises(NotFoundError):
        service.marcar_parcela_de_contrato_paga(transacao.id, usuario_id=2)


# --- criar: posse e duplicidade de origem_recorrente_id --------------------

def test_criar_com_origem_recorrente_propria_e_aceito(service):
    transacao = _criar(service, origem_recorrente_id=1, data=date(2026, 7, 5))
    assert transacao.origem_recorrente_id == 1


def test_criar_com_origem_recorrente_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, origem_recorrente_id=2, data=date(2026, 7, 5))


def test_criar_com_origem_recorrente_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, origem_recorrente_id=999, data=date(2026, 7, 5))


def test_criar_com_origem_recorrente_e_data_ja_usada_levanta_conflict_error(service):
    # mesma licao da duplicidade de numero_parcela: sem essa checagem, a
    # UniqueConstraint(origem_recorrente_id, data) do banco seria a unica
    # barreira - um IntegrityError cru (ver _validar_conta_recorrente).
    _criar(service, origem_recorrente_id=1, data=date(2026, 7, 5))
    with pytest.raises(ConflictError):
        _criar(service, origem_recorrente_id=1, data=date(2026, 7, 5))


def test_criar_com_origem_recorrente_em_data_diferente_e_aceito(service):
    _criar(service, origem_recorrente_id=1, data=date(2026, 7, 5))
    transacao = _criar(service, origem_recorrente_id=1, data=date(2026, 8, 5))
    assert transacao.data == date(2026, 8, 5)


# --- atualizar: posse e duplicidade de origem_recorrente_id ----------------

def test_atualizar_data_para_uma_ja_usada_pela_mesma_recorrencia_levanta_conflict_error(service):
    _criar(service, origem_recorrente_id=1, data=date(2026, 7, 5))
    outra = _criar(service, origem_recorrente_id=1, data=date(2026, 8, 5))
    with pytest.raises(ConflictError):
        service.atualizar(outra.id, TransacaoUpdate(data=date(2026, 7, 5)), usuario_id=1)


def test_atualizar_mantendo_a_mesma_data_nao_conflita_consigo_mesma(service):
    transacao = _criar(service, origem_recorrente_id=1, data=date(2026, 7, 5))
    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(descricao="Renomeada", data=date(2026, 7, 5)), usuario_id=1
    )
    assert atualizada.data == date(2026, 7, 5)


# --- criar: transação de conta ---------------------------------------------

def test_criar_transacao_de_conta_associa_ao_usuario(service):
    transacao = _criar(service, usuario_id=1, conta_id=100)
    assert transacao.id is not None
    assert transacao.usuario_id == 1
    assert transacao.conta_id == 100
    assert transacao.cartao_id is None


def test_criar_transacao_com_conta_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, conta_id=200)


def test_criar_transacao_com_conta_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, conta_id=999)


def test_criar_transacao_com_conta_inativa_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, usuario_id=1, conta_id=101)


def test_criar_transacao_de_conta_usa_pendente_como_status_padrao(service):
    transacao = _criar(service, conta_id=100, status=None)
    assert transacao.status == StatusTransacao.PENDENTE


def test_criar_transacao_de_conta_aceita_status_explicito(service):
    transacao = _criar(service, conta_id=100, status=StatusTransacao.PAGO)
    assert transacao.status == StatusTransacao.PAGO


# --- criar: transação de cartão --------------------------------------------

def test_criar_transacao_de_cartao_resolve_fatura_via_fatura_service(service, fatura_service):
    transacao = _criar(service, conta_id=None, cartao_id=10, data=date(2026, 7, 3))
    assert transacao.fatura_id is not None
    assert transacao.cartao_id == 10
    assert fatura_service.chamadas == [(10, date(2026, 7, 3), 1)]


def test_criar_transacao_de_cartao_forca_status_pago_ignorando_payload(service):
    transacao = _criar(service, conta_id=None, cartao_id=10, status=StatusTransacao.PENDENTE)
    assert transacao.status == StatusTransacao.PAGO


def test_criar_transacao_com_cartao_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, conta_id=None, cartao_id=20)


def test_criar_transacao_com_cartao_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, conta_id=None, cartao_id=999)


def test_criar_transacao_com_cartao_inativo_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, usuario_id=1, conta_id=None, cartao_id=11)


def test_criar_transacao_de_cartao_propaga_erro_quando_ciclo_ja_fechado(service, fatura_service):
    fatura_service.excecao = BusinessRuleError("ciclo já fechado")
    with pytest.raises(BusinessRuleError):
        _criar(service, conta_id=None, cartao_id=10)


# --- criar: categoria --------------------------------------------------------

def test_criar_transacao_com_categoria_do_sistema_e_aceita(service):
    transacao = _criar(service, categoria_id=5)
    assert transacao.categoria_id == 5


def test_criar_transacao_com_categoria_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, categoria_id=4)


def test_criar_transacao_com_categoria_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, categoria_id=999)


def test_criar_transacao_com_categoria_inativa_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, categoria_id=6)


def test_criar_transacao_com_categoria_de_tipo_incompativel_levanta_business_rule_error(service):
    # categoria 2 e so-DESPESA; transacao de tipo RECEITA nao pode usa-la.
    with pytest.raises(BusinessRuleError):
        _criar(service, tipo=TipoTransacao.RECEITA, categoria_id=2)


def test_criar_transacao_com_categoria_tipo_ambos_aceita_qualquer_tipo_de_transacao(service):
    transacao = _criar(service, tipo=TipoTransacao.RECEITA, categoria_id=1)
    assert transacao.categoria_id == 1


def test_criar_transacao_com_categoria_de_tipo_compativel_e_aceita(service):
    transacao = _criar(service, tipo=TipoTransacao.DESPESA, categoria_id=2)
    assert transacao.categoria_id == 2


# --- criar: tags --------------------------------------------------------------

def test_criar_transacao_com_tags_do_usuario_e_aceita(service):
    transacao = _criar(service, tag_ids=[1])
    assert [tag.id for tag in transacao.tags] == [1]


def test_criar_transacao_com_tag_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, tag_ids=[2])


def test_criar_transacao_com_tag_inativa_levanta_business_rule_error(service):
    with pytest.raises(BusinessRuleError):
        _criar(service, tag_ids=[3])


# --- obter / listar ------------------------------------------------------

def test_obter_transacao_propria(service):
    transacao = _criar(service, usuario_id=1)
    assert service.obter(transacao.id, usuario_id=1).id == transacao.id


def test_obter_transacao_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(transacao.id, usuario_id=2)


def test_obter_transacao_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_transacoes_do_usuario(service):
    _criar(service, usuario_id=1, conta_id=100, descricao="Minha")
    _criar(service, usuario_id=2, conta_id=200, descricao="Do outro")
    resultado = service.listar(usuario_id=1)
    assert [t.descricao for t in resultado] == ["Minha"]


def test_listar_filtra_por_conta_id(service):
    _criar(service, usuario_id=1, conta_id=100, descricao="Conta 100")
    resultado = service.listar(usuario_id=1, conta_id=100)
    assert len(resultado) == 1


def test_listar_filtra_por_tipo(service):
    _criar(service, usuario_id=1, tipo=TipoTransacao.DESPESA)
    _criar(service, usuario_id=1, tipo=TipoTransacao.RECEITA)
    resultado = service.listar(usuario_id=1, tipo=TipoTransacao.RECEITA)
    assert len(resultado) == 1
    assert resultado[0].tipo == TipoTransacao.RECEITA


def test_listar_filtra_por_origem_recorrente_id(service):
    _criar(service, usuario_id=1, origem_recorrente_id=1, data=date(2026, 7, 5))
    _criar(service, usuario_id=1, conta_id=100, descricao="Avulsa")
    resultado = service.listar(usuario_id=1, origem_recorrente_id=1)
    assert len(resultado) == 1
    assert resultado[0].origem_recorrente_id == 1


def test_listar_filtra_por_financiamento_id(service):
    _criar(service, usuario_id=1, financiamento_id=1, numero_parcela=1)
    _criar(service, usuario_id=1, conta_id=100, descricao="Avulsa")
    resultado = service.listar(usuario_id=1, financiamento_id=1)
    assert len(resultado) == 1
    assert resultado[0].financiamento_id == 1


def test_listar_filtra_por_emprestimo_id(service):
    _criar(service, usuario_id=1, emprestimo_id=1, numero_parcela=1)
    _criar(service, usuario_id=1, conta_id=100, descricao="Avulsa")
    resultado = service.listar(usuario_id=1, emprestimo_id=1)
    assert len(resultado) == 1
    assert resultado[0].emprestimo_id == 1


def test_listar_filtra_por_meta_id(service, transacao_repo):
    # meta_id nao e mais atribuivel via TransacaoCreate (ver bloco de
    # comentario acima de "criar/atualizar: meta_id") - construimos a
    # Transacao diretamente no repository falso para simular um registro
    # LEGADO (congelado) que ja existia antes do refatoramento.
    legada = Transacao(
        usuario_id=1,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("100.00"),
        data=date(2026, 7, 3),
        descricao="Aporte legado",
        conta_id=100,
        meta_id=1,
    )
    transacao_repo.create(legada)
    _criar(service, usuario_id=1, conta_id=100, descricao="Avulsa")

    resultado = service.listar(usuario_id=1, meta_id=1)
    assert len(resultado) == 1
    assert resultado[0].meta_id == 1


# --- atualizar -------------------------------------------------------------

def test_atualizar_aplica_apenas_campos_enviados(service):
    transacao = _criar(service, descricao="Original", valor=Decimal("50.00"))
    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(valor=Decimal("70.00")), usuario_id=1
    )
    assert atualizada.descricao == "Original"
    assert atualizada.valor == Decimal("70.00")


def test_atualizar_transacao_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.atualizar(transacao.id, TransacaoUpdate(descricao="Hackeado"), usuario_id=2)


def test_atualizar_categoria_revalida_compatibilidade_de_tipo(service):
    transacao = _criar(service, tipo=TipoTransacao.RECEITA)
    with pytest.raises(BusinessRuleError):
        # categoria 2 e so-DESPESA
        service.atualizar(transacao.id, TransacaoUpdate(categoria_id=2), usuario_id=1)


def test_atualizar_tipo_revalida_categoria_ja_atribuida(service):
    transacao = _criar(service, tipo=TipoTransacao.DESPESA, categoria_id=2)
    with pytest.raises(BusinessRuleError):
        service.atualizar(transacao.id, TransacaoUpdate(tipo=TipoTransacao.RECEITA), usuario_id=1)


def test_atualizar_tags_substitui_conjunto_inteiro(service):
    transacao = _criar(service, tag_ids=[1])
    atualizada = service.atualizar(transacao.id, TransacaoUpdate(tag_ids=[]), usuario_id=1)
    assert atualizada.tags == []


def test_atualizar_status_em_transacao_de_conta_e_aplicado(service):
    transacao = _criar(service, conta_id=100, status=StatusTransacao.PENDENTE)
    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(status=StatusTransacao.PAGO), usuario_id=1
    )
    assert atualizada.status == StatusTransacao.PAGO


def test_atualizar_status_em_transacao_de_cartao_e_ignorado(service):
    transacao = _criar(service, conta_id=None, cartao_id=10)
    assert transacao.status == StatusTransacao.PAGO

    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(status=StatusTransacao.PENDENTE), usuario_id=1
    )
    assert atualizada.status == StatusTransacao.PAGO  # nao mudou


def test_atualizar_numero_parcela_inconsistente_levanta_business_rule_error(service):
    transacao = _criar(service, parcelamento_id=1, numero_parcela=1)
    with pytest.raises(BusinessRuleError):
        # remove o contrato sem limpar numero_parcela -> estado inconsistente
        service.atualizar(transacao.id, TransacaoUpdate(parcelamento_id=None), usuario_id=1)


def test_atualizar_numero_parcela_para_fora_da_faixa_do_parcelamento_levanta_business_rule_error(service):
    transacao = _criar(service, parcelamento_id=1, numero_parcela=1)
    with pytest.raises(BusinessRuleError):
        service.atualizar(transacao.id, TransacaoUpdate(numero_parcela=99), usuario_id=1)


def test_atualizar_numero_parcela_para_uma_ja_usada_por_outra_transacao_levanta_conflict_error(service):
    _criar(service, parcelamento_id=1, numero_parcela=1)
    outra = _criar(service, parcelamento_id=1, numero_parcela=2)
    with pytest.raises(ConflictError):
        service.atualizar(outra.id, TransacaoUpdate(numero_parcela=1), usuario_id=1)


def test_atualizar_numero_parcela_mantendo_o_mesmo_valor_nao_conflita_consigo_mesma(service):
    # transacao_id_excluir garante que a propria transacao sendo editada
    # nao conta como colisao consigo mesma.
    transacao = _criar(service, parcelamento_id=1, numero_parcela=1)
    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(descricao="Renomeada", numero_parcela=1), usuario_id=1
    )
    assert atualizada.numero_parcela == 1


def test_atualizar_parcelamento_para_parcelamento_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, parcelamento_id=1, numero_parcela=1)
    with pytest.raises(NotFoundError):
        service.atualizar(transacao.id, TransacaoUpdate(parcelamento_id=2), usuario_id=1)


def test_atualizar_valor_em_transacao_de_cartao_com_fatura_aberta_e_permitido(service):
    transacao = _criar(service, conta_id=None, cartao_id=10)
    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(valor=Decimal("999.00")), usuario_id=1
    )
    assert atualizada.valor == Decimal("999.00")


def test_atualizar_valor_em_transacao_de_cartao_com_fatura_fechada_levanta_business_rule_error(
    service, fatura_repo
):
    transacao = _criar(service, conta_id=None, cartao_id=10)
    fatura_repo.get(transacao.fatura_id).status = StatusFatura.FECHADA

    with pytest.raises(BusinessRuleError):
        service.atualizar(transacao.id, TransacaoUpdate(valor=Decimal("999.00")), usuario_id=1)


def test_atualizar_descricao_em_transacao_de_cartao_com_fatura_fechada_e_permitido(
    service, fatura_repo
):
    # campos descritivos continuam livres mesmo com a fatura fechada - ver
    # docs/analise-arquitetural-fatura.md.
    transacao = _criar(service, conta_id=None, cartao_id=10)
    fatura_repo.get(transacao.fatura_id).status = StatusFatura.FECHADA

    atualizada = service.atualizar(
        transacao.id, TransacaoUpdate(descricao="Recategorizada"), usuario_id=1
    )
    assert atualizada.descricao == "Recategorizada"


# --- excluir -------------------------------------------------------------

def test_excluir_transacao_propria(service, transacao_repo):
    transacao = _criar(service, usuario_id=1)
    service.excluir(transacao.id, usuario_id=1)
    assert transacao_repo.get(transacao.id) is None


def test_excluir_transacao_de_outro_usuario_levanta_not_found(service):
    transacao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(transacao.id, usuario_id=2)


def test_excluir_transacao_de_compra_com_fatura_fechada_levanta_business_rule_error(
    service, fatura_repo
):
    transacao = _criar(service, conta_id=None, cartao_id=10)
    fatura_repo.get(transacao.fatura_id).status = StatusFatura.FECHADA

    with pytest.raises(BusinessRuleError):
        service.excluir(transacao.id, usuario_id=1)


def test_excluir_transacao_de_pagamento_e_sempre_permitido_mesmo_com_fatura_fechada(
    service, transacao_repo, fatura_repo
):
    # transacao de PAGAMENTO (fatura_paga_id) - nunca criada via
    # TransacaoService.criar (so pelo fluxo de FaturaService.registrar_pagamento);
    # inserida diretamente no repository falso para simular esse cenario.
    fatura_repo.adicionar(1, status=StatusFatura.FECHADA)
    pagamento = Transacao(
        usuario_id=1,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("100.00"),
        data=date(2026, 7, 20),
        descricao="Pagamento de fatura",
        status=StatusTransacao.PAGO,
        conta_id=100,
        fatura_paga_id=1,
    )
    transacao_repo.create(pagamento)

    service.excluir(pagamento.id, usuario_id=1)
    assert transacao_repo.get(pagamento.id) is None


# --- excluir: cascata de Parcelamento (bug real de 2026-07-20) -----------
# Achado do usuário: excluir UMA parcela de uma compra parcelada no cartão
# pelo endpoint genérico de Transação atualizava a fatura atual (SUM ao
# vivo, correto) mas deixava as outras parcelas - inclusive as de faturas
# futuras já resolvidas na criação - completamente intocadas, e
# `Parcelamento.ativo` continuava True. Ver docstring de
# `TransacaoService.excluir`/`cancelar_parcelas_do_parcelamento`.

def test_excluir_uma_parcela_cancela_as_demais_do_mesmo_parcelamento(
    service, transacao_repo, parcelamento_repo, cartao_repo
):
    cartao_repo.adicionar(cartao_id=10, usuario_id=1)
    parcela1 = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=1, descricao="Compra (1/3)"
    )
    parcela2 = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=2, descricao="Compra (2/3)"
    )
    parcela3 = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=3, descricao="Compra (3/3)"
    )

    service.excluir(parcela2.id, usuario_id=1)

    assert transacao_repo.get(parcela1.id) is None
    assert transacao_repo.get(parcela2.id) is None
    assert transacao_repo.get(parcela3.id) is None
    assert parcelamento_repo.get(1).ativo is False


def test_excluir_uma_parcela_preserva_a_que_ja_esta_em_fatura_fechada(
    service, transacao_repo, parcelamento_repo, cartao_repo, fatura_repo
):
    cartao_repo.adicionar(cartao_id=10, usuario_id=1)
    parcela_paga = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=1, descricao="Compra (1/2)"
    )
    fatura_repo.get(parcela_paga.fatura_id).status = StatusFatura.FECHADA
    parcela_futura = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=2, descricao="Compra (2/2)"
    )

    service.excluir(parcela_futura.id, usuario_id=1)

    # a parcela cuja fatura ja fechou e passado - preservada intacta, mesma
    # regra de qualquer outra transacao de fatura fechada.
    assert transacao_repo.get(parcela_paga.id) is not None
    assert transacao_repo.get(parcela_futura.id) is None
    assert parcelamento_repo.get(1).ativo is False


def test_excluir_a_parcela_clicada_com_fatura_fechada_ainda_levanta_business_rule_error(
    service, cartao_repo, fatura_repo
):
    # a trava de "nao mexe em fatura fechada" continua valendo para a
    # transacao efetivamente clicada - so as OUTRAS parcelas (irmas) tem o
    # BusinessRuleError silenciosamente ignorado dentro da cascata.
    cartao_repo.adicionar(cartao_id=10, usuario_id=1)
    parcela = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=1, descricao="Compra (1/2)"
    )
    fatura_repo.get(parcela.fatura_id).status = StatusFatura.FECHADA

    with pytest.raises(BusinessRuleError):
        service.excluir(parcela.id, usuario_id=1)


def test_aplicar_exclusao_de_parcela_com_escopo_esta_parcela_levanta_not_implemented(
    service, cartao_repo
):
    """Trava do ponto de extensão centralizado (ver docstring de
    `EscopoOperacaoParcela` em transacao_service.py): hoje só
    `TODO_PARCELAMENTO` é suportado - `ESTA_PARCELA` é só o nome reservado
    para uma funcionalidade futura (renegociação/edição avançada), NUNCA
    implementado nesta etapa. `NotImplementedError` explícito (em vez de
    silenciosamente cair para outro comportamento) garante que, se algum
    dia um caller chamar isto por engano antes da funcionalidade existir de
    verdade, o erro é óbvio e imediato."""
    cartao_repo.adicionar(cartao_id=10, usuario_id=1)
    parcela = _criar(
        service, conta_id=None, cartao_id=10, parcelamento_id=1, numero_parcela=1, descricao="Compra (1/2)"
    )

    with pytest.raises(NotImplementedError):
        service._aplicar_exclusao_de_parcela(
            parcela, usuario_id=1, escopo=EscopoOperacaoParcela.ESTA_PARCELA
        )
