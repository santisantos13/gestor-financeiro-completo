"""Testes unitários de AlertaService - isolado com um repository FALSO (em
memória) e Services de domínio FALSOS (mesmo nível de isolamento de
`test_central_financeira_service.py`, que também fakeia Services em vez de
Repository: `AlertaService` só orquestra `obter()` de outros Services,
nunca acessa Repository de outra entidade). Cobre: derivação de
`entidade_tipo` a partir de `tipo`, validação/normalização de `condicao`
por tipo, e a avaliação em tempo real (`disparado`/`mensagem`) dos 5 tipos
de gatilho.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import StatusFatura, StatusRecorrencia, TipoAlerta
from app.schemas.alerta import AlertaCreate, AlertaRead, AlertaUpdate
from app.services.alerta_service import AlertaService

HOJE = date.today()


class FakeAlertaRepository:
    def __init__(self):
        self._alertas = {}
        self._proximo_id = 1

    def get(self, id):
        return self._alertas.get(id)

    def create(self, alerta):
        alerta.id = self._proximo_id
        self._proximo_id += 1
        if getattr(alerta, "criado_em", None) is None:
            alerta.criado_em = datetime.now()
        self._alertas[alerta.id] = alerta
        return alerta

    def update(self, alerta):
        return alerta

    def delete(self, alerta):
        self._alertas.pop(alerta.id, None)

    def listar_do_usuario(self, usuario_id, *, apenas_ativos=False):
        resultado = [
            a for a in self._alertas.values() if a.usuario_id == usuario_id and (not apenas_ativos or a.ativo)
        ]
        resultado.sort(key=lambda a: a.id)
        return resultado


class _FakeServiceComObter:
    """Base comum aos 4 fakes abaixo - todos só precisam de `obter(id,
    usuario_id)`, levantando `NotFoundError` para id desconhecido ou de
    outro usuário (mesmo contrato dos Services reais)."""

    def __init__(self, entidades: dict[int, SimpleNamespace]):
        self._entidades = entidades

    def obter(self, entidade_id, usuario_id):
        entidade = self._entidades.get(entidade_id)
        if entidade is None or entidade.usuario_id != usuario_id:
            raise NotFoundError("Não encontrado.")
        return entidade


class FakeCartaoService(_FakeServiceComObter):
    pass


class FakeContaRecorrenteService(_FakeServiceComObter):
    pass


class FakeMetaService(_FakeServiceComObter):
    pass


class FakeContaService(_FakeServiceComObter):
    pass


class FakeFaturaService:
    def __init__(self, faturas_por_cartao: dict[int, list[SimpleNamespace]]):
        self._faturas_por_cartao = faturas_por_cartao

    def listar_recentes(self, cartao_id, usuario_id, *, limit=12):
        return list(self._faturas_por_cartao.get(cartao_id, []))[:limit]


def _service(
    *, cartoes=(), faturas_por_cartao=None, contas_recorrentes=(), metas=(), contas=()
) -> AlertaService:
    return AlertaService(
        FakeAlertaRepository(),
        FakeCartaoService({c.id: c for c in cartoes}),
        FakeFaturaService(faturas_por_cartao or {}),
        FakeContaRecorrenteService({r.id: r for r in contas_recorrentes}),
        FakeMetaService({m.id: m for m in metas}),
        FakeContaService({c.id: c for c in contas}),
    )


def _cartao(id=1, usuario_id=1, nome="Nubank", limite=Decimal("1000"), limite_disponivel=Decimal("500")):
    return SimpleNamespace(id=id, usuario_id=usuario_id, nome=nome, limite=limite, limite_disponivel=limite_disponivel)


def _conta_recorrente(id=1, usuario_id=1, descricao="Netflix", status=StatusRecorrencia.ATIVA, proxima_execucao=HOJE):
    return SimpleNamespace(id=id, usuario_id=usuario_id, descricao=descricao, status=status, proxima_execucao=proxima_execucao)


def _meta(id=1, usuario_id=1, descricao="Viagem", concluida_em=None):
    return SimpleNamespace(id=id, usuario_id=usuario_id, descricao=descricao, concluida_em=concluida_em)


def _conta(id=1, usuario_id=1, nome="Conta Corrente", saldo_atual=Decimal("100")):
    return SimpleNamespace(id=id, usuario_id=usuario_id, nome=nome, saldo_atual=saldo_atual)


# --- criar(): derivação de entidade_tipo + validação de posse + condicao ----

def test_criar_deriva_entidade_tipo_do_tipo_e_nunca_aceita_do_cliente():
    cartao = _cartao()
    service = _service(cartoes=[cartao])

    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )

    assert alerta.entidade_tipo.value == "CARTAO"
    assert alerta.ativo is True


def test_criar_levanta_not_found_quando_entidade_e_de_outro_usuario():
    cartao = _cartao(usuario_id=2)
    service = _service(cartoes=[cartao])

    with pytest.raises(NotFoundError):
        service.criar(
            AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
            usuario_id=1,
        )


def test_criar_limite_cartao_exige_limite_percentual():
    cartao = _cartao()
    service = _service(cartoes=[cartao])

    with pytest.raises(BusinessRuleError):
        service.criar(AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={}), usuario_id=1)


def test_criar_vencimento_fatura_usa_dias_antes_padrao_quando_omitido():
    cartao = _cartao()
    service = _service(cartoes=[cartao])

    alerta = service.criar(AlertaCreate(tipo=TipoAlerta.VENCIMENTO_FATURA, entidade_id=cartao.id), usuario_id=1)

    import json

    assert json.loads(alerta.condicao) == {"dias_antes": 3}


def test_criar_meta_atingida_nunca_tem_condicao():
    meta = _meta()
    service = _service(metas=[meta])

    alerta = service.criar(AlertaCreate(tipo=TipoAlerta.META_ATINGIDA, entidade_id=meta.id), usuario_id=1)

    assert alerta.condicao is None


def test_criar_saldo_baixo_exige_valor_minimo():
    conta = _conta()
    service = _service(contas=[conta])

    with pytest.raises(BusinessRuleError):
        service.criar(AlertaCreate(tipo=TipoAlerta.SALDO_BAIXO, entidade_id=conta.id, condicao={}), usuario_id=1)


# --- avaliação: LIMITE_CARTAO ------------------------------------------------

def test_avaliar_limite_cartao_dispara_quando_uso_ultrapassa_o_percentual():
    cartao = _cartao(limite=Decimal("1000"), limite_disponivel=Decimal("50"))  # 95% usado
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is True
    assert "95%" in resultado.mensagem


def test_avaliar_limite_cartao_nao_dispara_abaixo_do_percentual():
    cartao = _cartao(limite=Decimal("1000"), limite_disponivel=Decimal("800"))  # 20% usado
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is False
    assert resultado.mensagem is None


# --- avaliação: VENCIMENTO_FATURA -------------------------------------------

def test_avaliar_vencimento_fatura_dispara_dentro_da_janela_de_dias_antes():
    cartao = _cartao()
    fatura = SimpleNamespace(status_calculado=StatusFatura.ABERTA, data_vencimento=HOJE + timedelta(days=2))
    service = _service(cartoes=[cartao], faturas_por_cartao={cartao.id: [fatura]})
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.VENCIMENTO_FATURA, entidade_id=cartao.id, condicao={"dias_antes": 3}),
        usuario_id=1,
    )

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is True


def test_avaliar_vencimento_fatura_ignora_fatura_ja_paga():
    cartao = _cartao()
    fatura = SimpleNamespace(status_calculado=StatusFatura.PAGA, data_vencimento=HOJE + timedelta(days=1))
    service = _service(cartoes=[cartao], faturas_por_cartao={cartao.id: [fatura]})
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.VENCIMENTO_FATURA, entidade_id=cartao.id, condicao={"dias_antes": 3}),
        usuario_id=1,
    )

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is False


# --- avaliação: VENCIMENTO_CONTA_RECORRENTE ---------------------------------

def test_avaliar_vencimento_conta_recorrente_nao_dispara_se_pausada():
    recorrente = _conta_recorrente(status=StatusRecorrencia.PAUSADA, proxima_execucao=HOJE)
    service = _service(contas_recorrentes=[recorrente])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.VENCIMENTO_CONTA_RECORRENTE, entidade_id=recorrente.id, condicao={"dias_antes": 3}),
        usuario_id=1,
    )

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is False


# --- avaliação: META_ATINGIDA ------------------------------------------------

def test_avaliar_meta_atingida_dispara_quando_meta_tem_concluida_em():
    meta = _meta(concluida_em=datetime.now())
    service = _service(metas=[meta])
    alerta = service.criar(AlertaCreate(tipo=TipoAlerta.META_ATINGIDA, entidade_id=meta.id), usuario_id=1)

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is True
    assert "Viagem" in resultado.mensagem


# --- avaliação: SALDO_BAIXO --------------------------------------------------

def test_avaliar_saldo_baixo_dispara_abaixo_do_minimo():
    conta = _conta(saldo_atual=Decimal("50"))
    service = _service(contas=[conta])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.SALDO_BAIXO, entidade_id=conta.id, condicao={"valor_minimo": 100}), usuario_id=1
    )

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is True


# --- alerta desativado nunca é avaliado -------------------------------------

def test_alerta_desativado_nao_e_avaliado():
    cartao = _cartao(limite=Decimal("1000"), limite_disponivel=Decimal("0"))  # 100% usado
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )
    service.atualizar(alerta.id, AlertaUpdate(ativo=False), usuario_id=1)

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is None
    assert resultado.mensagem is None


def test_alerta_com_entidade_excluida_nao_quebra_nao_dispara():
    """Cartão foi excluído depois do alerta criado (CASCADE apagaria o
    Alerta na prática, mas o teste unitário simula o gap defensivo do
    Service - ver docstring de `_com_avaliacao`)."""
    cartao = _cartao()
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )
    service.cartao_service._entidades.clear()  # simula exclusão do cartão

    resultado = service.obter(alerta.id, usuario_id=1)

    assert resultado.disparado is False


# --- listar / atualizar / excluir -------------------------------------------

def test_listar_filtra_por_usuario_e_apenas_ativos():
    cartao_a = _cartao(id=1, usuario_id=1)
    cartao_b = _cartao(id=2, usuario_id=1)
    service = _service(cartoes=[cartao_a, cartao_b])
    a1 = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=1, condicao={"limite_percentual": 90}), usuario_id=1
    )
    service.criar(AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=2, condicao={"limite_percentual": 90}), usuario_id=1)
    service.atualizar(a1.id, AlertaUpdate(ativo=False), usuario_id=1)

    todos = service.listar(usuario_id=1)
    ativos = service.listar(usuario_id=1, apenas_ativos=True)

    assert len(todos) == 2
    assert len(ativos) == 1


def test_atualizar_nao_permite_mudar_tipo_ou_entidade_id():
    cartao = _cartao()
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )

    atualizado = service.atualizar(alerta.id, AlertaUpdate(condicao={"limite_percentual": 80}), usuario_id=1)

    assert atualizado.tipo == TipoAlerta.LIMITE_CARTAO
    assert atualizado.entidade_id == cartao.id


def test_excluir_remove_o_alerta():
    cartao = _cartao()
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )

    service.excluir(alerta.id, usuario_id=1)

    with pytest.raises(NotFoundError):
        service.obter(alerta.id, usuario_id=1)


# --- AlertaRead: condicao desserializa de string JSON para dict ------------

def test_alerta_read_desserializa_condicao_de_string_json_para_dict():
    """`Alerta.condicao` é uma coluna String - `AlertaRead.model_validate`
    precisa devolver `dict`, nunca a string crua (ver field_validator em
    schemas/alerta.py)."""
    cartao = _cartao()
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )
    assert isinstance(alerta.condicao, str)  # confirma a premissa: o objeto ORM guarda string.

    lido = AlertaRead.model_validate(alerta)

    assert lido.condicao == {"limite_percentual": 90.0}


def test_obter_ou_atualizar_ou_excluir_de_outro_usuario_levanta_not_found():
    cartao = _cartao()
    service = _service(cartoes=[cartao])
    alerta = service.criar(
        AlertaCreate(tipo=TipoAlerta.LIMITE_CARTAO, entidade_id=cartao.id, condicao={"limite_percentual": 90}),
        usuario_id=1,
    )

    with pytest.raises(NotFoundError):
        service.obter(alerta.id, usuario_id=2)
    with pytest.raises(NotFoundError):
        service.atualizar(alerta.id, AlertaUpdate(ativo=False), usuario_id=2)
    with pytest.raises(NotFoundError):
        service.excluir(alerta.id, usuario_id=2)
