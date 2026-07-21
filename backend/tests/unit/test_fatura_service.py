"""Testes unitários de FaturaService - isolado com repositories FALSOS (em
memória, sem banco). Cobre o que é específico de Fatura: derivação de
datas do ciclo a partir do Cartão, posse transitiva (via Cartão, já que
Fatura não tem usuario_id próprio), valor_total/status sempre derivados
(nunca lidos direto de uma coluna persistida) e as ações de negócio
explícitas (fechar, registrar pagamento, excluir).
"""
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.enums import StatusFatura
from app.schemas.fatura import (
    FaturaAjusteManualUpdate,
    FaturaAjustePosFechamentoCreate,
    FaturaCreate,
    FaturaImportarCreate,
    FaturaPagamentoCreate,
)
from app.services.fatura_service import FaturaService


class FakeFaturaRepository:
    def __init__(self):
        self._faturas = {}
        self._proximo_id = 1
        # "ledgers" falsos usados pelos testes pra controlar o resultado
        # das agregações sem precisar de um banco real.
        self.compras: dict[int, Decimal] = {}
        self.pagamentos: dict[int, Decimal] = {}
        self.transacoes_vinculadas: set[int] = set()
        # ids de fatura para os quais `desvincular_transacoes` foi chamado -
        # usado pelos testes de `excluir()` pra confirmar que a transação é
        # desvinculada (nunca apagada) antes da fatura ser removida.
        self.desvinculadas: list[int] = []

    def get(self, id):
        return self._faturas.get(id)

    def create(self, fatura):
        fatura.id = self._proximo_id
        self._proximo_id += 1
        self._faturas[fatura.id] = fatura
        return fatura

    def update(self, fatura):
        return fatura

    def delete(self, fatura):
        del self._faturas[fatura.id]

    def listar_do_cartao(self, cartao_id, *, skip=0, limit=100):
        resultado = [f for f in self._faturas.values() if f.cartao_id == cartao_id]
        resultado.sort(key=lambda f: f.mes_referencia, reverse=True)
        return resultado[skip : skip + limit]

    def buscar_por_cartao_e_mes(self, cartao_id, mes_referencia):
        return next(
            (
                f
                for f in self._faturas.values()
                if f.cartao_id == cartao_id and f.mes_referencia == mes_referencia
            ),
            None,
        )

    def somar_transacoes(self, fatura_id):
        return self.compras.get(fatura_id, Decimal("0"))

    def somar_pagamentos(self, fatura_id):
        return self.pagamentos.get(fatura_id, Decimal("0"))

    def desvincular_transacoes(self, fatura_id):
        self.desvinculadas.append(fatura_id)


class _CartaoFalso:
    def __init__(self, id, usuario_id, dia_fechamento=10, dia_vencimento=17,
                 nome="Nubank", conta_pagamento_id=100):
        self.id = id
        self.usuario_id = usuario_id
        self.dia_fechamento = dia_fechamento
        self.dia_vencimento = dia_vencimento
        self.nome = nome
        self.conta_pagamento_id = conta_pagamento_id


class FakeCartaoRepository:
    def __init__(self):
        self._cartoes = {}

    def adicionar(self, cartao_id, usuario_id, **kwargs):
        self._cartoes[cartao_id] = _CartaoFalso(cartao_id, usuario_id, **kwargs)

    def get(self, id):
        return self._cartoes.get(id)


class FakeTransacaoRepository:
    def __init__(self):
        self.criadas = []

    def create(self, transacao):
        transacao.id = len(self.criadas) + 1
        self.criadas.append(transacao)
        return transacao


@pytest.fixture()
def fatura_repo():
    return FakeFaturaRepository()


@pytest.fixture()
def cartao_repo():
    repo = FakeCartaoRepository()
    repo.adicionar(cartao_id=1, usuario_id=1, dia_fechamento=10, dia_vencimento=17)
    repo.adicionar(cartao_id=2, usuario_id=2, dia_fechamento=10, dia_vencimento=17)
    return repo


@pytest.fixture()
def transacao_repo():
    return FakeTransacaoRepository()


@pytest.fixture()
def service(fatura_repo, cartao_repo, transacao_repo):
    return FaturaService(fatura_repo, cartao_repo, transacao_repo)


def _criar(service, usuario_id=1, cartao_id=1, mes_referencia=date(2026, 7, 1)):
    return service.criar(FaturaCreate(cartao_id=cartao_id, mes_referencia=mes_referencia), usuario_id)


def _mes_referencia_com_vencimento_futuro() -> date:
    """Bug real encontrado na varredura de 2026-07: `test_status_fechada_
    sem_pagamento`/`test_status_parcialmente_paga` usavam `mes_referencia=
    date(2026, 7, 1)` fixo, o que dava `data_vencimento == date(2026, 7,
    17)` (dia_vencimento=17 do cartão fake). `_derivar_status` (fatura_
    service.py) compara isso com `date.today()` pra decidir ATRASADA -
    então esses testes eram uma bomba-relógio, quebrando sozinhos assim
    que o relógio real passasse de 17/07/2026, mesmo sem nenhuma mudança
    de código. Usar sempre o mês seguinte ao atual garante vencimento no
    futuro pra sempre, sem depender de mockar `date.today()`."""
    hoje = date.today()
    if hoje.month == 12:
        return date(hoje.year + 1, 1, 1)
    return date(hoje.year, hoje.month + 1, 1)


# --- criar: derivação de datas -------------------------------------------

def test_criar_fatura_deriva_datas_do_cartao(service):
    fatura = _criar(service, mes_referencia=date(2026, 7, 1))
    assert fatura.data_fechamento == date(2026, 7, 10)
    assert fatura.data_vencimento == date(2026, 7, 17)
    assert fatura.status == StatusFatura.ABERTA


def test_criar_fatura_com_vencimento_menor_que_fechamento_vira_mes_seguinte(service, cartao_repo):
    cartao_repo.adicionar(cartao_id=1, usuario_id=1, dia_fechamento=28, dia_vencimento=5)
    fatura = _criar(service, mes_referencia=date(2026, 7, 1))
    assert fatura.data_fechamento == date(2026, 7, 28)
    assert fatura.data_vencimento == date(2026, 8, 5)  # mes seguinte


def test_criar_fatura_com_dia_configurado_maior_que_dias_do_mes_usa_ultimo_dia_valido(service, cartao_repo):
    cartao_repo.adicionar(cartao_id=1, usuario_id=1, dia_fechamento=31, dia_vencimento=31)
    fatura = _criar(service, mes_referencia=date(2026, 2, 1))  # fevereiro/2026 tem 28 dias
    assert fatura.data_fechamento == date(2026, 2, 28)


def test_criar_fatura_com_cartao_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, cartao_id=2)  # cartao 2 e do usuario 2


def test_criar_fatura_com_cartao_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, cartao_id=999)


def test_criar_fatura_duplicada_mesmo_cartao_mesmo_mes_levanta_conflict_error(service):
    _criar(service, mes_referencia=date(2026, 7, 1))
    with pytest.raises(ConflictError):
        _criar(service, mes_referencia=date(2026, 7, 1))


def test_criar_fatura_mesmo_mes_em_cartoes_diferentes_e_permitido(service, cartao_repo):
    cartao_repo.adicionar(cartao_id=3, usuario_id=1, dia_fechamento=10, dia_vencimento=17)
    fatura_a = _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    fatura_b = _criar(service, cartao_id=3, mes_referencia=date(2026, 7, 1))
    assert fatura_a.id != fatura_b.id


# --- importar (fatura histórica) -------------------------------------------

def _importar(service, usuario_id=1, cartao_id=1, mes_referencia=date(2026, 5, 1), valor_total=Decimal("450.00")):
    return service.importar(
        FaturaImportarCreate(cartao_id=cartao_id, mes_referencia=mes_referencia, valor_total=valor_total),
        usuario_id,
    )


def test_importar_fatura_nasce_fechada_com_valor_informado(service):
    fatura = _importar(service, valor_total=Decimal("450.00"))
    assert fatura.status == StatusFatura.FECHADA
    assert fatura.importada is True

    atualizada = service.obter(fatura.id, usuario_id=1)
    assert atualizada.valor_total_calculado == Decimal("450.00")


def test_importar_fatura_deriva_datas_do_cartao_normalmente(service):
    fatura = _importar(service, mes_referencia=date(2026, 5, 1))
    assert fatura.data_fechamento == date(2026, 5, 10)
    assert fatura.data_vencimento == date(2026, 5, 17)


def test_importar_fatura_sem_pagamento_fica_com_status_calculado_fechada_ou_atrasada(service):
    # sem nenhum pagamento registrado ainda, o status derivado depende só
    # de valor_pago (0) vs. data_vencimento - nunca "PAGA" sem transacao.
    fatura = _importar(service, mes_referencia=date(2020, 1, 1), valor_total=Decimal("100.00"))
    atualizada = service.obter(fatura.id, usuario_id=1)
    assert atualizada.status_calculado in (StatusFatura.FECHADA, StatusFatura.ATRASADA)


def test_importar_fatura_ja_existente_no_mes_levanta_conflict_error(service):
    _criar(service, mes_referencia=date(2026, 5, 1))
    with pytest.raises(ConflictError):
        _importar(service, mes_referencia=date(2026, 5, 1))


def test_importar_fatura_de_cartao_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _importar(service, usuario_id=1, cartao_id=2)


def test_importar_fatura_pode_receber_pagamento_normalmente_depois(service, transacao_repo):
    # status já FECHADA (não ABERTA) na importação - registrar_pagamento
    # aceita normalmente, sem nenhuma mudança no fluxo existente.
    fatura = _importar(service, valor_total=Decimal("200.00"))
    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("200.00"), data=date(2020, 6, 1)), usuario_id=1
    )
    assert len(transacao_repo.criadas) == 1
    assert transacao_repo.criadas[0].fatura_paga_id == fatura.id


# --- obter / listar --------------------------------------------------------

def test_obter_fatura_propria(service):
    fatura = _criar(service)
    assert service.obter(fatura.id, usuario_id=1).id == fatura.id


def test_obter_fatura_de_cartao_de_outro_usuario_levanta_not_found(service):
    fatura = _criar(service, usuario_id=1, cartao_id=1)
    with pytest.raises(NotFoundError):
        service.obter(fatura.id, usuario_id=2)


def test_obter_fatura_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_faturas_do_cartao(service, cartao_repo):
    cartao_repo.adicionar(cartao_id=3, usuario_id=1, dia_fechamento=10, dia_vencimento=17)
    _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    _criar(service, cartao_id=3, mes_referencia=date(2026, 7, 1))

    resultado = service.listar(cartao_id=1, usuario_id=1)
    assert len(resultado) == 1


def test_listar_faturas_com_cartao_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.listar(cartao_id=2, usuario_id=1)


# --- valor_total / status derivados ---------------------------------------

def test_valor_total_aberta_e_calculado_ao_vivo(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("350.00")

    atualizado = service.obter(fatura.id, usuario_id=1)
    assert atualizado.valor_total_calculado == Decimal("350.00")
    assert atualizado.status_calculado == StatusFatura.ABERTA


def test_valor_total_fechada_e_o_snapshot_congelado_nao_a_soma_atual(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("350.00")
    service.fechar(fatura.id, usuario_id=1)

    # depois de fechar, uma "nova compra" hipotetica nao deveria mudar o total
    fatura_repo.compras[fatura.id] = Decimal("999.00")

    atualizado = service.obter(fatura.id, usuario_id=1)
    assert atualizado.valor_total_calculado == Decimal("350.00")  # snapshot, nao 999


def test_status_fechada_sem_pagamento(service, fatura_repo):
    fatura = _criar(service, mes_referencia=_mes_referencia_com_vencimento_futuro())
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    fatura = service.fechar(fatura.id, usuario_id=1)
    assert fatura.status_calculado == StatusFatura.FECHADA


def test_status_parcialmente_paga(service, fatura_repo):
    fatura = _criar(service, mes_referencia=_mes_referencia_com_vencimento_futuro())
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)
    fatura_repo.pagamentos[fatura.id] = Decimal("40.00")

    atualizado = service.obter(fatura.id, usuario_id=1)
    assert atualizado.status_calculado == StatusFatura.PARCIALMENTE_PAGA


def test_status_paga(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)
    fatura_repo.pagamentos[fatura.id] = Decimal("100.00")

    atualizado = service.obter(fatura.id, usuario_id=1)
    assert atualizado.status_calculado == StatusFatura.PAGA


def test_status_atrasada(service, fatura_repo):
    fatura = _criar(service, mes_referencia=date(2020, 1, 1))  # vencimento bem no passado
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)

    atualizado = service.obter(fatura.id, usuario_id=1)
    assert atualizado.status_calculado == StatusFatura.ATRASADA


def test_status_atrasada_tem_prioridade_sobre_parcialmente_paga(service, fatura_repo):
    """Uma fatura vencida com saldo devedor ainda em aberto e tratada como
    atrasada mesmo tendo recebido pagamento parcial - o risco importa mais
    que o progresso."""
    fatura = _criar(service, mes_referencia=date(2020, 1, 1))
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)
    fatura_repo.pagamentos[fatura.id] = Decimal("40.00")

    atualizado = service.obter(fatura.id, usuario_id=1)
    assert atualizado.status_calculado == StatusFatura.ATRASADA


# --- fechar -----------------------------------------------------------

def test_fechar_fatura_aberta_congela_valor_total_e_muda_status(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("250.00")

    fechada = service.fechar(fatura.id, usuario_id=1)

    assert fechada.status == StatusFatura.FECHADA
    assert fechada.valor_total == Decimal("250.00")


def test_fechar_fatura_ja_fechada_levanta_business_rule_error(service):
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)
    with pytest.raises(BusinessRuleError):
        service.fechar(fatura.id, usuario_id=1)


def test_fechar_fatura_de_cartao_de_outro_usuario_levanta_not_found(service):
    fatura = _criar(service, usuario_id=1, cartao_id=1)
    with pytest.raises(NotFoundError):
        service.fechar(fatura.id, usuario_id=2)


# --- registrar_pagamento -----------------------------------------------

def test_registrar_pagamento_cria_transacao_despesa_vinculada_a_fatura(service, transacao_repo):
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)

    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("100.00"), data=date(2026, 7, 20)), usuario_id=1
    )

    assert len(transacao_repo.criadas) == 1
    pagamento = transacao_repo.criadas[0]
    assert pagamento.valor == Decimal("100.00")
    assert pagamento.conta_id == 100  # conta_pagamento_id do cartao falso
    assert pagamento.cartao_id is None
    assert pagamento.fatura_paga_id == fatura.id
    assert pagamento.fatura_id is None


def test_registrar_pagamento_usa_descricao_padrao_quando_nao_informada(service, transacao_repo):
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)

    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("50.00"), data=date(2026, 7, 20)), usuario_id=1
    )

    assert "Nubank" in transacao_repo.criadas[0].descricao


def test_registrar_pagamento_em_fatura_aberta_levanta_business_rule_error(service):
    fatura = _criar(service)  # ainda ABERTA, nunca fechada
    with pytest.raises(BusinessRuleError):
        service.registrar_pagamento(
            fatura.id, FaturaPagamentoCreate(valor=Decimal("10.00"), data=date(2026, 7, 20)), usuario_id=1
        )


def test_registrar_pagamento_de_fatura_de_outro_usuario_levanta_not_found(service):
    fatura = _criar(service, usuario_id=1, cartao_id=1)
    service.fechar(fatura.id, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.registrar_pagamento(
            fatura.id, FaturaPagamentoCreate(valor=Decimal("10.00"), data=date(2026, 7, 20)), usuario_id=2
        )


def test_registrar_pagamento_permite_multiplos_pagamentos_parciais(service, transacao_repo):
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)

    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("30.00"), data=date(2026, 7, 20)), usuario_id=1
    )
    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("20.00"), data=date(2026, 7, 25)), usuario_id=1
    )

    assert len(transacao_repo.criadas) == 2


# --- excluir -------------------------------------------------------------

def test_excluir_fatura_aberta_sem_transacoes(service, fatura_repo):
    fatura = _criar(service)
    service.excluir(fatura.id, usuario_id=1)
    assert fatura_repo.get(fatura.id) is None


def test_excluir_fatura_fechada_sem_transacoes_e_permitido(service, fatura_repo):
    # Ciclo fechado por engano (ex: "Fechar ciclo" clicado sem nenhuma
    # compra ainda) - sem transação vinculada, não há histórico real a
    # perder, então a exclusão continua permitida mesmo já FECHADA.
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)
    service.excluir(fatura.id, usuario_id=1)
    assert fatura_repo.get(fatura.id) is None


def test_excluir_fatura_aberta_com_transacao_vinculada_desvincula_e_remove(service, fatura_repo):
    """Mudança de regra (2026-07-24, pedido do usuário): ter uma transação
    vinculada não bloqueia mais a exclusão - o usuário precisa poder
    desfazer/corrigir uma fatura errada mesmo depois de já ter uma compra
    ou pagamento registrado nela. `desvincular_transacoes` é chamado antes
    do delete (a transação em si nunca é apagada - ver
    `FaturaRepository.desvincular_transacoes`)."""
    fatura = _criar(service)
    fatura_repo.transacoes_vinculadas.add(fatura.id)

    service.excluir(fatura.id, usuario_id=1)

    assert fatura_repo.get(fatura.id) is None
    assert fatura.id in fatura_repo.desvinculadas


def test_excluir_fatura_fechada_com_transacao_vinculada_desvincula_e_remove(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.transacoes_vinculadas.add(fatura.id)
    service.fechar(fatura.id, usuario_id=1)

    service.excluir(fatura.id, usuario_id=1)

    assert fatura_repo.get(fatura.id) is None
    assert fatura.id in fatura_repo.desvinculadas


# --- ajustar_saldo_inicial (saldo já usado, sem Transacao) ------------------

def test_ajustar_saldo_inicial_em_fatura_aberta_soma_ao_valor_total(service):
    """Pedido explícito do usuário: informar o saldo já usado do cartão
    SEM vincular a nenhuma compra. `ajuste_manual` entra em
    `valor_total_calculado` mesmo sem nenhuma Transacao (`fatura_repo.
    compras` continua vazio aqui)."""
    fatura = _criar(service)

    ajustada = service.ajustar_saldo_inicial(
        fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("800.00")), usuario_id=1
    )

    assert ajustada.ajuste_manual == Decimal("800.00")
    assert ajustada.valor_total_calculado == Decimal("800.00")


def test_ajustar_saldo_inicial_soma_junto_com_transacoes_reais(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("120.00")

    ajustada = service.ajustar_saldo_inicial(
        fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("300.00")), usuario_id=1
    )

    assert ajustada.valor_total_calculado == Decimal("420.00")


def test_ajustar_saldo_inicial_substitui_valor_anterior_em_vez_de_somar(service):
    """Editar sempre define o total, nunca soma em cima do que já estava
    salvo - mesmo padrão de PATCH em qualquer outro cadastro do projeto."""
    fatura = _criar(service)
    service.ajustar_saldo_inicial(
        fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("500.00")), usuario_id=1
    )

    ajustada = service.ajustar_saldo_inicial(
        fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("200.00")), usuario_id=1
    )

    assert ajustada.ajuste_manual == Decimal("200.00")
    assert ajustada.valor_total_calculado == Decimal("200.00")


def test_ajustar_saldo_inicial_em_fatura_fechada_levanta_business_rule_error(service):
    """Uma fatura FECHADA já tem valor_total congelado para sempre -
    ajustar o "ponto de partida" de um ciclo que já aconteceu é o que
    `FaturaImportarCreate` resolve, de outro jeito."""
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)

    with pytest.raises(BusinessRuleError):
        service.ajustar_saldo_inicial(
            fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("100.00")), usuario_id=1
        )


def test_ajustar_saldo_inicial_de_fatura_de_outro_usuario_levanta_not_found(service):
    fatura = _criar(service, usuario_id=1, cartao_id=1)
    with pytest.raises(NotFoundError):
        service.ajustar_saldo_inicial(
            fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("100.00")), usuario_id=2
        )


def test_fechar_fatura_congela_ajuste_manual_dentro_do_valor_total(service, fatura_repo):
    """`ajuste_manual` só entra "ao vivo" enquanto ABERTA - depois de
    fechada, vira parte do número congelado (somado uma única vez em
    `fechar()`). `fechar()` zera o campo nesse momento (ver docstring lá) -
    por isso `ajuste_manual` volta a ser 0 na fatura recém-fechada, e
    `valor_total_calculado` não soma o valor antigo de novo (só somaria uma
    correção pós-fechamento NOVA, feita depois por
    `ajustar_valor_pos_fechamento` - ver testes próprios dele)."""
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.ajustar_saldo_inicial(
        fatura.id, FaturaAjusteManualUpdate(ajuste_manual=Decimal("50.00")), usuario_id=1
    )

    fechada = service.fechar(fatura.id, usuario_id=1)

    assert fechada.valor_total == Decimal("150.00")
    assert fechada.valor_total_calculado == Decimal("150.00")
    assert fechada.ajuste_manual == Decimal("0")

    # depois de fechada, o congelado nunca soma o ajuste antigo de novo
    obtida = service.obter(fatura.id, usuario_id=1)
    assert obtida.valor_total_calculado == Decimal("150.00")


# --- ajustar_valor_pos_fechamento (compra esquecida numa fatura já fechada) -
# Pedido explícito do usuário (2026-07-20): "quero adicionar uma transação em
# uma fatura que já foi fechada e paga, porém tinha esquecido dela antes" -
# entre as opções oferecidas, o usuário escolheu só ajustar o número (sem
# criar Transacao).

def test_ajustar_valor_pos_fechamento_soma_ao_valor_total_calculado(service, fatura_repo):
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)

    ajustada = service.ajustar_valor_pos_fechamento(
        fatura.id, FaturaAjustePosFechamentoCreate(valor=Decimal("50.00")), usuario_id=1
    )

    assert ajustada.valor_total == Decimal("100.00")  # coluna congelada nunca é reescrita
    assert ajustada.valor_total_calculado == Decimal("150.00")
    assert ajustada.ajuste_manual == Decimal("50.00")


def test_ajustar_valor_pos_fechamento_acumula_em_chamadas_sucessivas(service, fatura_repo):
    """Diferente de `ajustar_saldo_inicial` (substitui), aqui cada chamada
    SOMA - o usuário pode lembrar de uma segunda compra esquecida depois."""
    fatura = _criar(service)
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)

    service.ajustar_valor_pos_fechamento(
        fatura.id, FaturaAjustePosFechamentoCreate(valor=Decimal("50.00")), usuario_id=1
    )
    ajustada = service.ajustar_valor_pos_fechamento(
        fatura.id, FaturaAjustePosFechamentoCreate(valor=Decimal("30.00")), usuario_id=1
    )

    assert ajustada.ajuste_manual == Decimal("80.00")
    assert ajustada.valor_total_calculado == Decimal("180.00")


def test_ajustar_valor_pos_fechamento_em_fatura_paga_deixa_de_ser_paga(service, fatura_repo):
    """Efeito colateral esperado: o valor pago não muda, mas o total
    aumenta - a fatura estava PAGA e passa a ter saldo em aberto.
    `mes_referencia` com vencimento futuro (ver
    `_mes_referencia_com_vencimento_futuro`) - senão a fatura já paga
    apareceria como ATRASADA em vez de PAGA quando o vencimento (dia 17)
    já tivesse passado, mascarando a asserção que este teste verifica."""
    fatura = _criar(service, mes_referencia=_mes_referencia_com_vencimento_futuro())
    fatura_repo.compras[fatura.id] = Decimal("100.00")
    service.fechar(fatura.id, usuario_id=1)
    fatura_repo.pagamentos[fatura.id] = Decimal("100.00")
    paga = service.obter(fatura.id, usuario_id=1)
    assert paga.status_calculado == StatusFatura.PAGA

    ajustada = service.ajustar_valor_pos_fechamento(
        fatura.id, FaturaAjustePosFechamentoCreate(valor=Decimal("40.00")), usuario_id=1
    )

    assert ajustada.status_calculado != StatusFatura.PAGA
    assert ajustada.valor_total_calculado == Decimal("140.00")
    assert ajustada.valor_pago == Decimal("100.00")


def test_ajustar_valor_pos_fechamento_em_fatura_aberta_levanta_business_rule_error(service):
    fatura = _criar(service)

    with pytest.raises(BusinessRuleError):
        service.ajustar_valor_pos_fechamento(
            fatura.id, FaturaAjustePosFechamentoCreate(valor=Decimal("10.00")), usuario_id=1
        )


def test_ajustar_valor_pos_fechamento_de_fatura_de_outro_usuario_levanta_not_found(service):
    fatura = _criar(service, usuario_id=1, cartao_id=1)
    service.fechar(fatura.id, usuario_id=1)

    with pytest.raises(NotFoundError):
        service.ajustar_valor_pos_fechamento(
            fatura.id, FaturaAjustePosFechamentoCreate(valor=Decimal("10.00")), usuario_id=2
        )


def test_excluir_fatura_de_cartao_de_outro_usuario_levanta_not_found(service):
    fatura = _criar(service, usuario_id=1, cartao_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(fatura.id, usuario_id=2)


# --- excluir_em_lote -------------------------------------------------------
# Pedido explícito do usuário: "quero poder selecionar várias faturas para
# excluir".

def test_excluir_em_lote_remove_todas_as_faturas_informadas(service, fatura_repo):
    fatura_a = _criar(service, mes_referencia=date(2026, 6, 1))
    fatura_b = _criar(service, mes_referencia=date(2026, 7, 1))
    fatura_c = _criar(service, mes_referencia=date(2026, 8, 1))

    service.excluir_em_lote([fatura_a.id, fatura_b.id], usuario_id=1)

    assert fatura_repo.get(fatura_a.id) is None
    assert fatura_repo.get(fatura_b.id) is None
    assert fatura_repo.get(fatura_c.id) is not None  # não estava na lista - intacta


def test_excluir_em_lote_desvincula_transacoes_de_cada_fatura(service, fatura_repo):
    fatura_a = _criar(service, mes_referencia=date(2026, 6, 1))
    fatura_b = _criar(service, mes_referencia=date(2026, 7, 1))
    fatura_repo.transacoes_vinculadas.add(fatura_a.id)
    fatura_repo.transacoes_vinculadas.add(fatura_b.id)

    service.excluir_em_lote([fatura_a.id, fatura_b.id], usuario_id=1)

    assert set(fatura_repo.desvinculadas) == {fatura_a.id, fatura_b.id}


def test_excluir_em_lote_com_fatura_inexistente_levanta_not_found(service):
    fatura = _criar(service)
    with pytest.raises(NotFoundError):
        service.excluir_em_lote([fatura.id, 999], usuario_id=1)


def test_excluir_em_lote_com_fatura_de_outro_usuario_levanta_not_found(service):
    fatura_do_usuario_2 = _criar(service, usuario_id=2, cartao_id=2)
    with pytest.raises(NotFoundError):
        service.excluir_em_lote([fatura_do_usuario_2.id], usuario_id=1)


# --- pagar_em_lote ---------------------------------------------------------
# Pedido explícito do usuário: "seria interessante poder pagar todas
# selecionadas".

def test_pagar_em_lote_paga_o_restante_de_cada_fatura_fechada(service, fatura_repo, transacao_repo):
    fatura_a = _criar(service, mes_referencia=date(2026, 6, 1))
    fatura_repo.compras[fatura_a.id] = Decimal("100.00")
    service.fechar(fatura_a.id, usuario_id=1)

    fatura_b = _criar(service, mes_referencia=date(2026, 7, 1))
    fatura_repo.compras[fatura_b.id] = Decimal("200.00")
    service.fechar(fatura_b.id, usuario_id=1)

    pagas = service.pagar_em_lote([fatura_a.id, fatura_b.id], date(2026, 7, 20), usuario_id=1)

    assert pagas == 2
    assert len(transacao_repo.criadas) == 2
    valores_pagos = {t.fatura_paga_id: t.valor for t in transacao_repo.criadas}
    assert valores_pagos[fatura_a.id] == Decimal("100.00")
    assert valores_pagos[fatura_b.id] == Decimal("200.00")


def test_pagar_em_lote_pula_fatura_ainda_aberta(service, fatura_repo, transacao_repo):
    fatura_fechada = _criar(service, mes_referencia=date(2026, 6, 1))
    fatura_repo.compras[fatura_fechada.id] = Decimal("100.00")
    service.fechar(fatura_fechada.id, usuario_id=1)

    fatura_aberta = _criar(service, mes_referencia=date(2026, 7, 1))  # nunca fechada

    pagas = service.pagar_em_lote([fatura_fechada.id, fatura_aberta.id], date(2026, 7, 20), usuario_id=1)

    assert pagas == 1
    assert len(transacao_repo.criadas) == 1
    assert transacao_repo.criadas[0].fatura_paga_id == fatura_fechada.id


def test_pagar_em_lote_pula_fatura_ja_totalmente_quitada(service, fatura_repo, transacao_repo):
    fatura_paga = _criar(service, mes_referencia=date(2026, 6, 1))
    fatura_repo.compras[fatura_paga.id] = Decimal("100.00")
    service.fechar(fatura_paga.id, usuario_id=1)
    fatura_repo.pagamentos[fatura_paga.id] = Decimal("100.00")  # já quitada

    fatura_pendente = _criar(service, mes_referencia=date(2026, 7, 1))
    fatura_repo.compras[fatura_pendente.id] = Decimal("50.00")
    service.fechar(fatura_pendente.id, usuario_id=1)

    pagas = service.pagar_em_lote([fatura_paga.id, fatura_pendente.id], date(2026, 7, 20), usuario_id=1)

    assert pagas == 1
    assert len(transacao_repo.criadas) == 1
    assert transacao_repo.criadas[0].fatura_paga_id == fatura_pendente.id


def test_pagar_em_lote_sem_nenhuma_fatura_elegivel_levanta_business_rule_error(service, fatura_repo):
    fatura_aberta = _criar(service, mes_referencia=date(2026, 7, 1))

    with pytest.raises(BusinessRuleError):
        service.pagar_em_lote([fatura_aberta.id], date(2026, 7, 20), usuario_id=1)


def test_pagar_em_lote_com_fatura_de_outro_usuario_levanta_not_found(service):
    fatura_do_usuario_2 = _criar(service, usuario_id=2, cartao_id=2)
    with pytest.raises(NotFoundError):
        service.pagar_em_lote([fatura_do_usuario_2.id], date(2026, 7, 20), usuario_id=1)


def test_pagar_em_lote_com_fatura_inexistente_levanta_not_found(service):
    fatura = _criar(service)
    service.fechar(fatura.id, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.pagar_em_lote([fatura.id, 999], date(2026, 7, 20), usuario_id=1)


# --- resolver_fatura_aberta -------------------------------------------

def test_resolver_fatura_aberta_cria_fatura_quando_nao_existe(service, fatura_repo):
    fatura = service.resolver_fatura_aberta(cartao_id=1, data_transacao=date(2026, 7, 3), usuario_id=1)
    assert fatura.mes_referencia == date(2026, 7, 1)
    assert fatura.status == StatusFatura.ABERTA
    assert fatura_repo.get(fatura.id) is not None


def test_resolver_fatura_aberta_reaproveita_fatura_existente(service):
    primeira = service.resolver_fatura_aberta(cartao_id=1, data_transacao=date(2026, 7, 3), usuario_id=1)
    segunda = service.resolver_fatura_aberta(cartao_id=1, data_transacao=date(2026, 7, 8), usuario_id=1)
    assert primeira.id == segunda.id


def test_resolver_fatura_aberta_data_apos_fechamento_vai_pro_ciclo_seguinte(service, cartao_repo):
    # dia_fechamento=10: uma compra no dia 15 nao pertence mais ao ciclo de
    # julho (ja fechou dia 10) - pertence ao ciclo de agosto.
    fatura = service.resolver_fatura_aberta(cartao_id=1, data_transacao=date(2026, 7, 15), usuario_id=1)
    assert fatura.mes_referencia == date(2026, 8, 1)


def test_resolver_fatura_aberta_data_no_dia_do_fechamento_ainda_pertence_ao_ciclo_atual(service):
    # dia_fechamento=10: uma compra exatamente no dia 10 ainda entra no
    # ciclo que fecha nesse dia (limite inclusivo).
    fatura = service.resolver_fatura_aberta(cartao_id=1, data_transacao=date(2026, 7, 10), usuario_id=1)
    assert fatura.mes_referencia == date(2026, 7, 1)


def test_resolver_fatura_aberta_com_ciclo_ja_fechado_levanta_business_rule_error(service):
    fatura = _criar(service, mes_referencia=date(2026, 7, 1))
    service.fechar(fatura.id, usuario_id=1)

    with pytest.raises(BusinessRuleError):
        service.resolver_fatura_aberta(cartao_id=1, data_transacao=date(2026, 7, 3), usuario_id=1)


def test_resolver_fatura_aberta_com_cartao_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.resolver_fatura_aberta(cartao_id=2, data_transacao=date(2026, 7, 3), usuario_id=1)


# --- ids_faturas_pagas (correção do bug "limite disponível não volta ao
# pagar fatura") -------------------------------------------------------


def test_ids_faturas_pagas_nao_inclui_fatura_aberta(service):
    fatura = _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    assert service.ids_faturas_pagas(cartao_id=1) == set()
    assert fatura.status == StatusFatura.ABERTA


def test_ids_faturas_pagas_nao_inclui_fatura_fechada_sem_pagamento(service, fatura_repo):
    fatura = _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    fatura_repo.compras[fatura.id] = Decimal("350.00")
    service.fechar(fatura.id, usuario_id=1)

    assert service.ids_faturas_pagas(cartao_id=1) == set()


def test_ids_faturas_pagas_inclui_fatura_fechada_e_totalmente_paga(service, fatura_repo):
    """Este é exatamente o cenário do bug real: fecha o ciclo, registra o
    pagamento total via `registrar_pagamento` (nunca setando `status`
    diretamente) - `ids_faturas_pagas` precisa reconhecer isso."""
    fatura = _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    fatura_repo.compras[fatura.id] = Decimal("350.00")
    service.fechar(fatura.id, usuario_id=1)

    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("350.00"), data=date(2026, 7, 18)), usuario_id=1
    )
    fatura_repo.pagamentos[fatura.id] = Decimal("350.00")

    assert service.ids_faturas_pagas(cartao_id=1) == {fatura.id}


def test_ids_faturas_pagas_nao_inclui_fatura_paga_parcialmente(service, fatura_repo):
    fatura = _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    fatura_repo.compras[fatura.id] = Decimal("350.00")
    service.fechar(fatura.id, usuario_id=1)

    service.registrar_pagamento(
        fatura.id, FaturaPagamentoCreate(valor=Decimal("100.00"), data=date(2026, 7, 18)), usuario_id=1
    )
    fatura_repo.pagamentos[fatura.id] = Decimal("100.00")

    assert service.ids_faturas_pagas(cartao_id=1) == set()


def test_ids_faturas_pagas_considera_so_faturas_do_cartao_pedido(service, fatura_repo, cartao_repo):
    fatura_1 = _criar(service, cartao_id=1, mes_referencia=date(2026, 7, 1))
    fatura_repo.compras[fatura_1.id] = Decimal("100.00")
    service.fechar(fatura_1.id, usuario_id=1)
    service.registrar_pagamento(
        fatura_1.id, FaturaPagamentoCreate(valor=Decimal("100.00"), data=date(2026, 7, 18)), usuario_id=1
    )
    fatura_repo.pagamentos[fatura_1.id] = Decimal("100.00")

    fatura_2 = _criar(service, cartao_id=2, mes_referencia=date(2026, 7, 1), usuario_id=2)
    fatura_repo.compras[fatura_2.id] = Decimal("200.00")
    service.fechar(fatura_2.id, usuario_id=2)
    service.registrar_pagamento(
        fatura_2.id, FaturaPagamentoCreate(valor=Decimal("200.00"), data=date(2026, 7, 18)), usuario_id=2
    )
    fatura_repo.pagamentos[fatura_2.id] = Decimal("200.00")

    assert service.ids_faturas_pagas(cartao_id=1) == {fatura_1.id}
    assert service.ids_faturas_pagas(cartao_id=2) == {fatura_2.id}
