"""Testes unitários de CartaoService - isolado com repositories FALSOS (em
memória, sem banco). Cobre o que mais diferencia Cartao de Conta/Categoria/
Tag: validação cruzada de posse (conta_pagamento_id precisa ser de uma
Conta do MESMO usuário) e o cálculo de limite_disponivel.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.enums import Bandeira
from app.schemas.cartao import CartaoCreate, CartaoUpdate
from app.services.cartao_service import CartaoService


class FakeCartaoRepository:
    def __init__(self):
        self._cartoes = {}
        self._proximo_id = 1
        self.gastos_nao_pagos: dict[int, Decimal] = {}
        self._cartoes_com_fatura_vinculada: set[int] = set()

    def get(self, id):
        return self._cartoes.get(id)

    def create(self, cartao):
        cartao.id = self._proximo_id
        self._proximo_id += 1
        self._cartoes[cartao.id] = cartao
        return cartao

    def update(self, cartao):
        return cartao

    def delete(self, cartao):
        self._cartoes.pop(cartao.id, None)

    def listar_do_usuario(self, usuario_id, *, apenas_ativos=True, skip=0, limit=100):
        resultado = [
            c
            for c in self._cartoes.values()
            if c.usuario_id == usuario_id and (not apenas_ativos or c.ativo)
        ]
        resultado.sort(key=lambda c: c.nome)
        return resultado[skip : skip + limit]

    def buscar_por_nome(self, usuario_id, nome):
        return next(
            (c for c in self._cartoes.values() if c.usuario_id == usuario_id and c.nome == nome), None
        )

    def somar_gastos_nao_pagos(self, cartao_id, ids_faturas_pagas=None):
        return self.gastos_nao_pagos.get(cartao_id, Decimal("0"))

    def existe_fatura_vinculada(self, cartao_id):
        return cartao_id in self._cartoes_com_fatura_vinculada

    def marcar_fatura_vinculada(self, cartao_id):
        """Helper de teste - não existe no CartaoRepository real. Simula o
        estado que `existe_fatura_vinculada` leria de verdade do banco."""
        self._cartoes_com_fatura_vinculada.add(cartao_id)


class FakeFaturaService:
    """Fake mínimo - só os métodos que CartaoService consome:
    `ids_faturas_pagas` (cálculo de limite_disponivel, controlado nos
    testes deste arquivo via `FakeCartaoRepository.gastos_nao_pagos`) e
    `listar`/`excluir` (cascata de `_apagar_faturas_e_transacoes`, cobertos
    nos testes de exclusão abaixo)."""

    def __init__(self):
        self._faturas: dict[int, object] = {}
        self._proximo_id = 1
        self.ids_excluidas: list[int] = []

    def ids_faturas_pagas(self, cartao_id):
        return set()

    def adicionar_fatura_falsa(self, cartao_id):
        """Helper de teste - não existe no FaturaService real. Registra uma
        fatura falsa vinculada a `cartao_id` para os testes de exclusão
        simularem `existe_fatura_vinculada` e a cascata `listar`/`excluir`."""
        fatura = SimpleNamespace(id=self._proximo_id, cartao_id=cartao_id)
        self._faturas[fatura.id] = fatura
        self._proximo_id += 1
        return fatura

    def listar(self, cartao_id, usuario_id, skip=0, limit=100):
        return [f for f in self._faturas.values() if f.cartao_id == cartao_id][skip : skip + limit]

    def excluir(self, fatura_id, usuario_id):
        self.ids_excluidas.append(fatura_id)
        self._faturas.pop(fatura_id, None)


class FakeTransacaoService:
    """Fake mínimo - só os métodos que a cascata de
    `CartaoService._apagar_faturas_e_transacoes` consome (`listar` filtrado
    por `cartao_id`, `excluir`). Não modela `NotFoundError` em cascata de
    Parcelamento (não é preciso para cobrir o comportamento de
    CartaoService - isso é testado em test_transacao_service.py)."""

    def __init__(self):
        self._transacoes: dict[int, object] = {}
        self._proximo_id = 1
        self.ids_excluidas: list[int] = []

    def adicionar_transacao_falsa(self, cartao_id):
        transacao = SimpleNamespace(id=self._proximo_id, cartao_id=cartao_id)
        self._transacoes[transacao.id] = transacao
        self._proximo_id += 1
        return transacao

    def listar(self, usuario_id, *, cartao_id=None, limit=100, **kwargs):
        resultado = [t for t in self._transacoes.values() if cartao_id is None or t.cartao_id == cartao_id]
        return resultado[:limit]

    def excluir(self, transacao_id, usuario_id):
        if transacao_id not in self._transacoes:
            raise NotFoundError("Transação não encontrada.")
        self.ids_excluidas.append(transacao_id)
        self._transacoes.pop(transacao_id, None)


class FakeParcelamentoService:
    """Fake mínimo - só os métodos que a cascata de
    `CartaoService._apagar_faturas_e_transacoes` consome (`listar`
    filtrado em Python por `cartao_id` no próprio Service, `excluir`).
    Cobre a correção do bug "excluir cartão falha com Falha de conexão com
    o servidor" (2026-07-21): cabeçalho de Parcelamento tem que ser
    apagado junto, nunca só desvinculado (`cartao_id`/`conta_id` são XOR e
    NOT NULL em conjunto no model real)."""

    def __init__(self):
        self._parcelamentos: dict[int, object] = {}
        self._proximo_id = 1
        self.ids_excluidos: list[int] = []

    def adicionar_parcelamento_falso(self, cartao_id):
        parcelamento = SimpleNamespace(id=self._proximo_id, cartao_id=cartao_id, conta_id=None)
        self._parcelamentos[parcelamento.id] = parcelamento
        self._proximo_id += 1
        return parcelamento

    def listar(self, usuario_id, *, apenas_ativos=True, limit=100):
        return list(self._parcelamentos.values())[:limit]

    def excluir(self, parcelamento_id, usuario_id):
        self.ids_excluidos.append(parcelamento_id)
        self._parcelamentos.pop(parcelamento_id, None)


class FakeContaRecorrenteService:
    """Fake mínimo - mesmo papel de `FakeParcelamentoService`, para a
    correção do mesmo bug aplicada a `ContaRecorrente`
    (`ck_conta_recorrente_cartao_xor_conta`)."""

    def __init__(self):
        self._recorrentes: dict[int, object] = {}
        self._proximo_id = 1
        self.ids_excluidos: list[int] = []

    def adicionar_recorrente_falsa(self, cartao_id):
        recorrente = SimpleNamespace(id=self._proximo_id, cartao_id=cartao_id, conta_id=None)
        self._recorrentes[recorrente.id] = recorrente
        self._proximo_id += 1
        return recorrente

    def listar(self, usuario_id, *, status=None, limit=100):
        return list(self._recorrentes.values())[:limit]

    def excluir(self, recorrente_id, usuario_id):
        self.ids_excluidos.append(recorrente_id)
        self._recorrentes.pop(recorrente_id, None)


class _ContaFalsa:
    def __init__(self, id, usuario_id):
        self.id = id
        self.usuario_id = usuario_id


class FakeContaRepository:
    def __init__(self):
        self._contas = {}

    def adicionar(self, conta_id, usuario_id):
        self._contas[conta_id] = _ContaFalsa(conta_id, usuario_id)

    def get(self, id):
        return self._contas.get(id)


@pytest.fixture()
def cartao_repo():
    return FakeCartaoRepository()


@pytest.fixture()
def conta_repo():
    repo = FakeContaRepository()
    repo.adicionar(conta_id=100, usuario_id=1)
    repo.adicionar(conta_id=200, usuario_id=2)
    return repo


@pytest.fixture()
def fatura_service():
    return FakeFaturaService()


@pytest.fixture()
def transacao_service():
    return FakeTransacaoService()


@pytest.fixture()
def parcelamento_service():
    return FakeParcelamentoService()


@pytest.fixture()
def conta_recorrente_service():
    return FakeContaRecorrenteService()


@pytest.fixture()
def service(cartao_repo, conta_repo, fatura_service, transacao_service, parcelamento_service, conta_recorrente_service):
    return CartaoService(
        cartao_repo, conta_repo, fatura_service, transacao_service, parcelamento_service, conta_recorrente_service
    )


def _criar(
    service,
    usuario_id=1,
    nome="Nubank",
    conta_pagamento_id=100,
    instituicao="Nubank",
    bandeira=Bandeira.MASTERCARD,
    ultimos_quatro_digitos="1234",
    limite=Decimal("5000"),
    dia_fechamento=10,
    dia_vencimento=17,
):
    dados = CartaoCreate(
        nome=nome,
        conta_pagamento_id=conta_pagamento_id,
        instituicao=instituicao,
        bandeira=bandeira,
        ultimos_quatro_digitos=ultimos_quatro_digitos,
        limite=limite,
        dia_fechamento=dia_fechamento,
        dia_vencimento=dia_vencimento,
    )
    return service.criar(dados, usuario_id)


# --- criar -------------------------------------------------------------

def test_criar_cartao_associa_ao_usuario(service):
    cartao = _criar(service, usuario_id=1)
    assert cartao.id is not None
    assert cartao.usuario_id == 1
    assert cartao.ativo is True


def test_criar_cartao_com_conta_de_outro_usuario_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, conta_pagamento_id=200)  # conta 200 e do usuario 2


def test_criar_cartao_com_conta_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        _criar(service, usuario_id=1, conta_pagamento_id=999)


def test_criar_cartao_com_nome_duplicado_no_mesmo_usuario_levanta_conflict_error(service):
    _criar(service, usuario_id=1, nome="Nubank")
    with pytest.raises(ConflictError):
        _criar(service, usuario_id=1, nome="Nubank")


def test_criar_cartao_com_mesmo_nome_em_usuarios_diferentes_e_permitido(service, conta_repo):
    cartao_a = _criar(service, usuario_id=1, nome="Cartao", conta_pagamento_id=100)
    cartao_b = _criar(service, usuario_id=2, nome="Cartao", conta_pagamento_id=200)
    assert cartao_a.id != cartao_b.id


def test_criar_cartao_com_nome_de_cartao_desativado_reativa_em_vez_de_duplicar(service, cartao_repo):
    original = _criar(service, usuario_id=1, nome="Nubank", limite=Decimal("5000"))
    service.desativar(original.id, usuario_id=1)

    recriado = _criar(service, usuario_id=1, nome="Nubank", limite=Decimal("8000"))

    assert recriado.id == original.id  # mesma linha, reativada
    assert recriado.ativo is True
    assert recriado.limite == Decimal("8000")
    assert len(cartao_repo._cartoes) == 1  # nao criou uma segunda linha


# --- obter / listar ------------------------------------------------------

def test_obter_cartao_proprio(service):
    cartao = _criar(service, usuario_id=1)
    assert service.obter(cartao.id, usuario_id=1).id == cartao.id


def test_obter_cartao_de_outro_usuario_levanta_not_found(service):
    cartao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(cartao.id, usuario_id=2)


def test_obter_cartao_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_cartoes_do_usuario(service):
    _criar(service, usuario_id=1, nome="Meu", conta_pagamento_id=100)
    _criar(service, usuario_id=2, nome="Do outro", conta_pagamento_id=200)
    resultado = service.listar(usuario_id=1)
    assert [c.nome for c in resultado] == ["Meu"]


def test_listar_filtra_apenas_ativos_por_padrao(service):
    ativo = _criar(service, usuario_id=1, nome="Ativo")
    inativo = _criar(service, usuario_id=1, nome="Inativo")
    service.desativar(inativo.id, usuario_id=1)

    assert [c.nome for c in service.listar(usuario_id=1)] == ["Ativo"]
    assert {c.nome for c in service.listar(usuario_id=1, apenas_ativos=False)} == {"Ativo", "Inativo"}


# --- limite_disponivel ---------------------------------------------------

def test_limite_disponivel_sem_gastos_e_igual_ao_limite(service):
    cartao = _criar(service, usuario_id=1, limite=Decimal("5000"))
    assert cartao.limite_disponivel == Decimal("5000")


def test_limite_disponivel_subtrai_gastos_nao_pagos(service, cartao_repo):
    cartao = _criar(service, usuario_id=1, limite=Decimal("5000"))
    cartao_repo.gastos_nao_pagos[cartao.id] = Decimal("1200")

    atualizado = service.obter(cartao.id, usuario_id=1)
    assert atualizado.limite_disponivel == Decimal("3800")


def test_limite_disponivel_pode_ficar_negativo_se_cartao_estourado(service, cartao_repo):
    cartao = _criar(service, usuario_id=1, limite=Decimal("1000"))
    cartao_repo.gastos_nao_pagos[cartao.id] = Decimal("1500")

    atualizado = service.obter(cartao.id, usuario_id=1)
    assert atualizado.limite_disponivel == Decimal("-500")


# --- atualizar -------------------------------------------------------------

def test_atualizar_cartao_proprio_aplica_apenas_campos_enviados(service):
    cartao = _criar(service, usuario_id=1, nome="Original", limite=Decimal("5000"))
    atualizado = service.atualizar(cartao.id, CartaoUpdate(limite=Decimal("9000")), usuario_id=1)
    assert atualizado.nome == "Original"
    assert atualizado.limite == Decimal("9000")


def test_atualizar_cartao_de_outro_usuario_levanta_not_found(service):
    cartao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.atualizar(cartao.id, CartaoUpdate(nome="Hackeado"), usuario_id=2)


def test_atualizar_conta_pagamento_para_conta_de_outro_usuario_levanta_not_found(service):
    cartao = _criar(service, usuario_id=1, conta_pagamento_id=100)
    with pytest.raises(NotFoundError):
        service.atualizar(cartao.id, CartaoUpdate(conta_pagamento_id=200), usuario_id=1)


def test_atualizar_nome_para_nome_ja_usado_por_outro_cartao_levanta_conflict_error(service):
    _criar(service, usuario_id=1, nome="Nubank")
    outro = _criar(service, usuario_id=1, nome="Inter")

    with pytest.raises(ConflictError):
        service.atualizar(outro.id, CartaoUpdate(nome="Nubank"), usuario_id=1)


def test_atualizar_reenviando_o_mesmo_nome_nao_levanta_conflict_error(service):
    cartao = _criar(service, usuario_id=1, nome="Nubank")
    atualizado = service.atualizar(
        cartao.id, CartaoUpdate(nome="Nubank", limite=Decimal("7000")), usuario_id=1
    )
    assert atualizado.limite == Decimal("7000")


def test_atualizar_renomeando_para_nome_de_cartao_inativo_levanta_conflict_error(service):
    """Mesma decisão de TagService: renomear NÃO reativa/mescla
    automaticamente com um cartão inativo de mesmo nome."""
    inativo = _criar(service, usuario_id=1, nome="Nubank")
    service.desativar(inativo.id, usuario_id=1)
    outro = _criar(service, usuario_id=1, nome="Inter")

    with pytest.raises(ConflictError):
        service.atualizar(outro.id, CartaoUpdate(nome="Nubank"), usuario_id=1)


def test_atualizar_ativo_true_reativa_cartao_diretamente(service, cartao_repo):
    cartao = _criar(service, usuario_id=1)
    service.desativar(cartao.id, usuario_id=1)

    reativado = service.atualizar(cartao.id, CartaoUpdate(ativo=True), usuario_id=1)

    assert reativado.ativo is True
    assert cartao_repo.get(cartao.id).ativo is True


# --- desativar ---------------------------------------------------------

def test_desativar_cartao_proprio(service, cartao_repo):
    cartao = _criar(service, usuario_id=1)
    service.desativar(cartao.id, usuario_id=1)
    assert cartao_repo.get(cartao.id).ativo is False


def test_desativar_cartao_de_outro_usuario_levanta_not_found(service):
    cartao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.desativar(cartao.id, usuario_id=2)


# --- excluir (hard delete) - Etapa F10 -----------------------------------

def test_excluir_cartao_sem_fatura_apaga_a_linha(service, cartao_repo):
    cartao = _criar(service, usuario_id=1)
    service.excluir(cartao.id, usuario_id=1)
    assert cartao_repo.get(cartao.id) is None


def test_excluir_cartao_de_outro_usuario_levanta_not_found(service):
    cartao = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(cartao.id, usuario_id=2)


def test_excluir_cartao_com_fatura_vinculada_sem_apagar_transacoes_levanta_business_rule_error(
    service, cartao_repo
):
    """Comportamento original (default `apagar_transacoes=False`)
    inalterado: continua bloqueando, sem apagar nada."""
    cartao = _criar(service, usuario_id=1)
    cartao_repo.marcar_fatura_vinculada(cartao.id)

    with pytest.raises(BusinessRuleError):
        service.excluir(cartao.id, usuario_id=1)

    assert cartao_repo.get(cartao.id) is not None


def test_excluir_cartao_com_fatura_vinculada_e_apagar_transacoes_true_remove_tudo(
    service, cartao_repo, fatura_service, transacao_service
):
    """Pedido explícito do usuário (ver
    docs/analise-arquitetural-exclusao-cartao-com-historico.md): com
    `apagar_transacoes=True`, em vez de bloquear, apaga as faturas e as
    transações do cartão via os Services já existentes, e só então apaga o
    cartão."""
    cartao = _criar(service, usuario_id=1)
    cartao_repo.marcar_fatura_vinculada(cartao.id)
    fatura = fatura_service.adicionar_fatura_falsa(cartao.id)
    transacao_a = transacao_service.adicionar_transacao_falsa(cartao.id)
    transacao_b = transacao_service.adicionar_transacao_falsa(cartao.id)

    service.excluir(cartao.id, usuario_id=1, apagar_transacoes=True)

    assert cartao_repo.get(cartao.id) is None
    assert fatura_service.ids_excluidas == [fatura.id]
    assert set(transacao_service.ids_excluidas) == {transacao_a.id, transacao_b.id}


def test_excluir_cartao_com_apagar_transacoes_true_tolera_transacao_ja_removida_em_cascata(
    service, cartao_repo, fatura_service, transacao_service
):
    """Simula o caso de uma transação parcelada: uma chamada a
    `TransacaoService.excluir()` pode cascatear e já remover outra parcela
    do mesmo Parcelamento antes do loop da cascata chegar nela -
    `NotFoundError` precisa ser tolerado, não propagado."""
    cartao = _criar(service, usuario_id=1)
    cartao_repo.marcar_fatura_vinculada(cartao.id)
    transacao = transacao_service.adicionar_transacao_falsa(cartao.id)
    # Remove a transação "por baixo" antes da cascata chegar nela - simula
    # outra parcela do mesmo parcelamento já ter apagado esta.
    transacao_service._transacoes.pop(transacao.id)

    service.excluir(cartao.id, usuario_id=1, apagar_transacoes=True)

    assert cartao_repo.get(cartao.id) is None
    assert transacao_service.ids_excluidas == []


def test_excluir_cartao_com_parcelamento_vinculado_sem_fatura_e_sem_apagar_transacoes_bloqueia(
    service, cartao_repo, parcelamento_service
):
    """Gap corrigido em 2026-07-21 junto do bug de exclusão: antes desta
    correção, `excluir()` só checava `existe_fatura_vinculada` - um cartão
    com uma compra parcelada MAS SEM nenhuma Fatura ainda criada (fatura é
    resolvida/criada à parte) passava direto para
    `self.cartao_repo.delete(cartao)`, sem bloquear nem cascatear nada."""
    cartao = _criar(service, usuario_id=1)
    parcelamento_service.adicionar_parcelamento_falso(cartao.id)

    with pytest.raises(BusinessRuleError):
        service.excluir(cartao.id, usuario_id=1)

    assert cartao_repo.get(cartao.id) is not None


def test_excluir_cartao_com_apagar_transacoes_true_apaga_parcelamento_vinculado(
    service, cartao_repo, parcelamento_service
):
    """Bug real corrigido em 2026-07-21 ("excluir cartão falha com Falha
    de conexão com o servidor"): o cabeçalho de Parcelamento tem que ser
    apagado junto com o cartão - `cartao_id`/`conta_id` são XOR e NOT NULL
    em conjunto no model real (`ck_parcelamento_cartao_xor_conta`), então
    não existe "desvincular" um Parcelamento do Cartão que está sendo
    apagado. No SQLite de desenvolvimento isso nunca dava erro (sem
    `PRAGMA foreign_keys=ON`); no Postgres de produção a FK é enforced e
    bloqueava a exclusão do cartão."""
    cartao = _criar(service, usuario_id=1)
    parcelamento = parcelamento_service.adicionar_parcelamento_falso(cartao.id)

    service.excluir(cartao.id, usuario_id=1, apagar_transacoes=True)

    assert cartao_repo.get(cartao.id) is None
    assert parcelamento_service.ids_excluidos == [parcelamento.id]


def test_excluir_cartao_com_apagar_transacoes_true_apaga_recorrente_vinculada(
    service, cartao_repo, conta_recorrente_service
):
    """Mesmo bug do teste acima, para `ContaRecorrente`
    (`ck_conta_recorrente_cartao_xor_conta`)."""
    cartao = _criar(service, usuario_id=1)
    recorrente = conta_recorrente_service.adicionar_recorrente_falsa(cartao.id)

    service.excluir(cartao.id, usuario_id=1, apagar_transacoes=True)

    assert cartao_repo.get(cartao.id) is None
    assert conta_recorrente_service.ids_excluidos == [recorrente.id]
