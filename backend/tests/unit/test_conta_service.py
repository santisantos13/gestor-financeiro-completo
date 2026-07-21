"""Testes unitários de ContaService - isolado com um repository FALSO (em
memória, sem banco). As somas de transações/transferências também são
falsas aqui: a correção da QUERY de agregação (SQL) é responsabilidade dos
testes de integração; aqui testamos só a fórmula e as regras de negócio
(posse, saldo = inicial + somas, soft delete, PATCH parcial).
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import CategoriaMovimentacaoConta, TipoConta, TipoEntidadeReferenciavel, TipoTransacao
from app.schemas.conta import ContaCreate, ContaUpdate, MovimentacaoContaRead
from app.services.conta_service import ContaService


class FakeContaRepository:
    """Substitui ContaRepository nos testes: mesma interface, guardando
    tudo em um dict em memória. `somas_transacoes`/`somas_transferencias`
    permitem o teste controlar o resultado das agregações sem precisar de
    um banco real. `contas_com_vinculo` permite simular `existe_vinculo`
    sem precisar de um banco real por trás (mesmo padrão de
    `FakeCartaoRepository.marcar_fatura_vinculada` em
    test_cartao_service.py)."""

    def __init__(self):
        self._contas = {}
        self._proximo_id = 1
        self.somas_transacoes: dict[int, Decimal] = {}
        self.somas_transferencias: dict[int, Decimal] = {}
        self._contas_com_vinculo: set[int] = set()

    def get(self, id):
        return self._contas.get(id)

    def create(self, conta):
        conta.id = self._proximo_id
        self._proximo_id += 1
        self._contas[conta.id] = conta
        return conta

    def update(self, conta):
        return conta

    def delete(self, conta):
        self._contas.pop(conta.id, None)

    def listar_do_usuario(self, usuario_id, *, apenas_ativas=True, apenas_visiveis=True, skip=0, limit=100):
        resultado = [
            c
            for c in self._contas.values()
            if c.usuario_id == usuario_id
            and (not apenas_ativas or c.ativo)
            and (not apenas_visiveis or not getattr(c, "oculta", False))
        ]
        return resultado[skip : skip + limit]

    def somar_transacoes_pagas(self, conta_id):
        return self.somas_transacoes.get(conta_id, Decimal("0"))

    def somar_transferencias(self, conta_id):
        return self.somas_transferencias.get(conta_id, Decimal("0"))

    def existe_vinculo(self, conta_id):
        return conta_id in self._contas_com_vinculo

    def marcar_vinculo(self, conta_id):
        """Helper de teste - não existe no ContaRepository real."""
        self._contas_com_vinculo.add(conta_id)


class _FakeServiceComLista:
    """Base compartilhada pelos fakes de Financiamento/Empréstimo/
    ContaRecorrente/Cartão abaixo - todos seguem o mesmo formato mínimo que
    `ContaService._apagar_vinculos` consome: `listar(usuario_id, ...)`
    devolvendo objetos com `.id`/o campo de vínculo, e `excluir(id,
    usuario_id)` removendo-o."""

    def __init__(self):
        self._itens: dict[int, object] = {}
        self._proximo_id = 1
        self.ids_excluidos: list[int] = []

    def _adicionar(self, **campos):
        item = SimpleNamespace(id=self._proximo_id, **campos)
        self._itens[item.id] = item
        self._proximo_id += 1
        return item

    def excluir(self, item_id, usuario_id):
        if item_id not in self._itens:
            raise NotFoundError("Não encontrado.")
        self.ids_excluidos.append(item_id)
        self._itens.pop(item_id, None)


class FakeFinanciamentoService(_FakeServiceComLista):
    def adicionar_financiamento_falso(self, conta_id):
        return self._adicionar(conta_id=conta_id)

    def listar(self, usuario_id, *, apenas_ativos=True, limit=100):
        return list(self._itens.values())[:limit]


class FakeEmprestimoService(_FakeServiceComLista):
    def adicionar_emprestimo_falso(self, conta_id):
        return self._adicionar(conta_id=conta_id)

    def listar(self, usuario_id, *, apenas_ativos=True, limit=100):
        return list(self._itens.values())[:limit]


class FakeContaRecorrenteService(_FakeServiceComLista):
    def adicionar_recorrente_falso(self, conta_id):
        return self._adicionar(conta_id=conta_id)

    # `status=None` espelha a assinatura real pós-expansão de Contas
    # Recorrentes (2026-07-20, `ativo` -> `status`) - a cascata de
    # exclusão de Conta chama com status=None (todas).
    def listar(self, usuario_id, *, status=None, limit=100):
        return list(self._itens.values())[:limit]


class FakeCartaoService(_FakeServiceComLista):
    def adicionar_cartao_falso(self, conta_pagamento_id):
        return self._adicionar(conta_pagamento_id=conta_pagamento_id)

    def listar(self, usuario_id, *, apenas_ativos=True, limit=100):
        return list(self._itens.values())[:limit]

    def excluir(self, item_id, usuario_id, apagar_transacoes=False):
        # assinatura própria (aceita apagar_transacoes) - assertado nos
        # testes de cascata que ele é sempre chamado com True.
        self.chamadas_apagar_transacoes = getattr(self, "chamadas_apagar_transacoes", [])
        self.chamadas_apagar_transacoes.append(apagar_transacoes)
        super().excluir(item_id, usuario_id)


class FakeParcelamentoService(_FakeServiceComLista):
    """Fake mínimo - correção do bug "excluir cartão/conta falha com Falha
    de conexão com o servidor" (2026-07-21): cabeçalho de Parcelamento tem
    que ser apagado junto, nunca só desvinculado (`cartao_id`/`conta_id`
    são XOR e NOT NULL em conjunto no model real,
    `ck_parcelamento_cartao_xor_conta`)."""

    def adicionar_parcelamento_falso(self, conta_id):
        return self._adicionar(conta_id=conta_id, cartao_id=None)

    def listar(self, usuario_id, *, apenas_ativos=True, limit=100):
        return list(self._itens.values())[:limit]


class FakeTransferenciaService(_FakeServiceComLista):
    def adicionar_transferencia_falsa(self, conta_id):
        return self._adicionar(conta_id=conta_id)

    def listar(self, usuario_id, *, apenas_ativas=True, conta_id=None, limit=100):
        resultado = [t for t in self._itens.values() if conta_id is None or t.conta_id == conta_id]
        return resultado[:limit]


class FakeTransacaoServiceConta(_FakeServiceComLista):
    """Nome diferente de `FakeTransacaoService` (test_cartao_service.py)
    para não colidir se algum dia os dois arquivos compartilharem um
    conftest - filtra por `conta_id` em vez de `cartao_id`."""

    def adicionar_transacao_falsa(self, conta_id):
        return self._adicionar(conta_id=conta_id)

    def listar(self, usuario_id, *, conta_id=None, limit=100, **kwargs):
        resultado = [t for t in self._itens.values() if conta_id is None or t.conta_id == conta_id]
        return resultado[:limit]


@pytest.fixture()
def repo():
    return FakeContaRepository()


@pytest.fixture()
def transacao_service():
    return FakeTransacaoServiceConta()


@pytest.fixture()
def transferencia_service():
    return FakeTransferenciaService()


@pytest.fixture()
def cartao_service():
    return FakeCartaoService()


@pytest.fixture()
def financiamento_service():
    return FakeFinanciamentoService()


@pytest.fixture()
def emprestimo_service():
    return FakeEmprestimoService()


@pytest.fixture()
def conta_recorrente_service():
    return FakeContaRecorrenteService()


@pytest.fixture()
def parcelamento_service():
    return FakeParcelamentoService()


@pytest.fixture()
def service(
    repo,
    transacao_service,
    transferencia_service,
    cartao_service,
    financiamento_service,
    emprestimo_service,
    conta_recorrente_service,
    parcelamento_service,
):
    return ContaService(
        repo,
        transacao_service,
        transferencia_service,
        cartao_service,
        financiamento_service,
        emprestimo_service,
        conta_recorrente_service,
        parcelamento_service,
    )


def _criar(service, usuario_id=1, nome="Conta Corrente", saldo_inicial=Decimal("100")):
    dados = ContaCreate(nome=nome, saldo_inicial=saldo_inicial)
    return service.criar(dados, usuario_id)


def test_criar_conta_associa_ao_usuario(service):
    conta = _criar(service, usuario_id=42)
    assert conta.id is not None
    assert conta.usuario_id == 42
    assert conta.ativo is True
    assert conta.tipo == TipoConta.CORRENTE


def test_criar_conta_sem_movimentacao_saldo_atual_igual_ao_inicial(service):
    conta = _criar(service, saldo_inicial=Decimal("250.50"))
    assert conta.saldo_atual == Decimal("250.50")


def test_obter_conta_soma_saldo_inicial_e_movimentacoes(service, repo):
    conta = _criar(service, saldo_inicial=Decimal("100"))
    repo.somas_transacoes[conta.id] = Decimal("50")
    repo.somas_transferencias[conta.id] = Decimal("-20")

    resultado = service.obter(conta.id, conta.usuario_id)

    assert resultado.saldo_atual == Decimal("130")


def test_obter_conta_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_obter_conta_de_outro_usuario_levanta_not_found(service):
    conta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(conta.id, usuario_id=2)


def test_listar_contas_retorna_apenas_do_usuario(service):
    _criar(service, usuario_id=1, nome="Conta A")
    _criar(service, usuario_id=2, nome="Conta B")

    contas = service.listar(usuario_id=1)

    assert len(contas) == 1
    assert contas[0].nome == "Conta A"


def test_listar_contas_filtra_apenas_ativas_por_padrao(service):
    ativa = _criar(service, usuario_id=1, nome="Ativa")
    inativa = _criar(service, usuario_id=1, nome="Inativa")
    service.desativar(inativa.id, usuario_id=1)

    contas = service.listar(usuario_id=1)
    assert [c.nome for c in contas] == ["Ativa"]

    todas = service.listar(usuario_id=1, apenas_ativas=False)
    assert {c.nome for c in todas} == {"Ativa", "Inativa"}


def test_atualizar_conta_aplica_apenas_campos_enviados(service):
    conta = _criar(service, nome="Nome Original", saldo_inicial=Decimal("100"))

    atualizado = service.atualizar(conta.id, ContaUpdate(nome="Nome Novo"), conta.usuario_id)

    assert atualizado.nome == "Nome Novo"
    assert atualizado.saldo_inicial == Decimal("100")  # nao enviado, nao mudou


def test_atualizar_conta_de_outro_usuario_levanta_not_found(service):
    conta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.atualizar(conta.id, ContaUpdate(nome="Hackeado"), usuario_id=2)


def test_desativar_conta_marca_ativo_false_sem_remover(service, repo):
    conta = _criar(service, usuario_id=1)

    service.desativar(conta.id, usuario_id=1)

    assert repo.get(conta.id) is not None  # continua no banco
    assert repo.get(conta.id).ativo is False


def test_desativar_conta_de_outro_usuario_levanta_not_found(service):
    conta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.desativar(conta.id, usuario_id=2)


# --- excluir (hard delete) - Etapa F10 -----------------------------------

def test_excluir_conta_sem_vinculo_apaga_a_linha(service, repo):
    conta = _criar(service, usuario_id=1)
    service.excluir(conta.id, usuario_id=1)
    assert repo.get(conta.id) is None


def test_excluir_conta_de_outro_usuario_levanta_not_found(service):
    conta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(conta.id, usuario_id=2)


def test_excluir_conta_com_vinculo_sem_apagar_vinculos_levanta_business_rule_error(service, repo):
    conta = _criar(service, usuario_id=1)
    repo.marcar_vinculo(conta.id)

    with pytest.raises(BusinessRuleError):
        service.excluir(conta.id, usuario_id=1)

    assert repo.get(conta.id) is not None


def test_excluir_conta_oculta_sempre_bloqueia_mesmo_com_apagar_vinculos(service, repo):
    """Conta oculta = cofrinho de uma Meta - a relação é invertida (a Meta
    é dona da conta, não o contrário). Nunca deve ser apagável por aqui,
    nem com apagar_vinculos=True - `MetaService.excluir` é quem decide o
    destino do cofrinho."""
    conta = _criar(service, usuario_id=1)
    repo.get(conta.id).oculta = True

    with pytest.raises(BusinessRuleError):
        service.excluir(conta.id, usuario_id=1, apagar_vinculos=True)

    assert repo.get(conta.id) is not None


def test_excluir_conta_com_apagar_vinculos_true_remove_tudo(
    service,
    repo,
    transacao_service,
    transferencia_service,
    cartao_service,
    financiamento_service,
    emprestimo_service,
    conta_recorrente_service,
    parcelamento_service,
):
    """Pedido explícito do usuário (ver
    docs/analise-arquitetural-exclusao-conta-com-historico.md): com
    `apagar_vinculos=True`, em vez de bloquear, apaga tudo vinculado à
    conta via os Services já existentes, e só então apaga a conta."""
    conta = _criar(service, usuario_id=1)
    repo.marcar_vinculo(conta.id)

    financiamento = financiamento_service.adicionar_financiamento_falso(conta.id)
    # financiamento de OUTRA conta - não deve ser tocado.
    financiamento_service.adicionar_financiamento_falso(conta.id + 999)

    emprestimo = emprestimo_service.adicionar_emprestimo_falso(conta.id)
    recorrente = conta_recorrente_service.adicionar_recorrente_falso(conta.id)
    cartao = cartao_service.adicionar_cartao_falso(conta.id)
    transferencia = transferencia_service.adicionar_transferencia_falsa(conta.id)
    transacao_a = transacao_service.adicionar_transacao_falsa(conta.id)
    transacao_b = transacao_service.adicionar_transacao_falsa(conta.id)
    # bug real corrigido em 2026-07-21 ("excluir cartão/conta falha com
    # Falha de conexão com o servidor"): cabeçalho de Parcelamento também
    # tem que ser apagado, nunca só desvinculado.
    parcelamento = parcelamento_service.adicionar_parcelamento_falso(conta.id)

    service.excluir(conta.id, usuario_id=1, apagar_vinculos=True)

    assert repo.get(conta.id) is None
    assert financiamento_service.ids_excluidos == [financiamento.id]
    assert emprestimo_service.ids_excluidos == [emprestimo.id]
    assert conta_recorrente_service.ids_excluidos == [recorrente.id]
    assert cartao_service.ids_excluidos == [cartao.id]
    assert cartao_service.chamadas_apagar_transacoes == [True]
    assert transferencia_service.ids_excluidos == [transferencia.id]
    assert set(transacao_service.ids_excluidos) == {transacao_a.id, transacao_b.id}
    assert parcelamento_service.ids_excluidos == [parcelamento.id]


def test_excluir_conta_com_apagar_vinculos_true_tolera_transacao_ja_removida_em_cascata(
    service, repo, transacao_service
):
    """Mesma tolerância a corrida de cascata já usada na exclusão de
    Cartão: uma chamada a `TransacaoService.excluir()` pode cascatear e já
    remover outra parcela do mesmo Parcelamento antes do loop chegar
    nela."""
    conta = _criar(service, usuario_id=1)
    repo.marcar_vinculo(conta.id)
    transacao = transacao_service.adicionar_transacao_falsa(conta.id)
    transacao_service._itens.pop(transacao.id)

    service.excluir(conta.id, usuario_id=1, apagar_vinculos=True)

    assert repo.get(conta.id) is None
    assert transacao_service.ids_excluidos == []


# --- extrato (histórico expansível) - helpers estáticos --------------------
# Testados isoladamente (sem precisar de fixture/DB) - a correção da
# QUERY/combinação de listas é responsabilidade dos testes de integração em
# test_conta_flow.py; aqui só a regra de categorização/sinal, que é a parte
# com mais lógica condicional (e mais fácil de acertar errado).


def _transacao_falsa(**campos):
    base = dict(
        tipo=TipoTransacao.DESPESA,
        fatura_paga_id=None,
        financiamento_id=None,
        emprestimo_id=None,
        id=1,
    )
    base.update(campos)
    return SimpleNamespace(**base)


def test_categoria_da_transacao_receita_e_positiva():
    categoria, positivo = ContaService._categoria_da_transacao(_transacao_falsa(tipo=TipoTransacao.RECEITA))
    assert categoria == CategoriaMovimentacaoConta.RECEITA
    assert positivo is True


def test_categoria_da_transacao_despesa_e_negativa():
    categoria, positivo = ContaService._categoria_da_transacao(_transacao_falsa(tipo=TipoTransacao.DESPESA))
    assert categoria == CategoriaMovimentacaoConta.DESPESA
    assert positivo is False


def test_categoria_da_transacao_pagamento_de_fatura():
    categoria, positivo = ContaService._categoria_da_transacao(_transacao_falsa(fatura_paga_id=42))
    assert categoria == CategoriaMovimentacaoConta.PAGAMENTO_FATURA
    assert positivo is False


def test_categoria_da_transacao_pagamento_de_financiamento():
    categoria, positivo = ContaService._categoria_da_transacao(_transacao_falsa(financiamento_id=7))
    assert categoria == CategoriaMovimentacaoConta.PAGAMENTO_FINANCIAMENTO
    assert positivo is False


def test_categoria_da_transacao_pagamento_de_emprestimo():
    categoria, positivo = ContaService._categoria_da_transacao(_transacao_falsa(emprestimo_id=9))
    assert categoria == CategoriaMovimentacaoConta.PAGAMENTO_EMPRESTIMO
    assert positivo is False


def test_categoria_da_transacao_prioriza_contrato_sobre_tipo():
    """Uma parcela de financiamento é sempre DESPESA no campo `tipo`, mas a
    categoria de exibição deve ser PAGAMENTO_FINANCIAMENTO, não DESPESA
    genérica - `financiamento_id` sempre vence."""
    categoria, _ = ContaService._categoria_da_transacao(
        _transacao_falsa(tipo=TipoTransacao.DESPESA, financiamento_id=7)
    )
    assert categoria == CategoriaMovimentacaoConta.PAGAMENTO_FINANCIAMENTO


def test_origem_da_transacao_sem_contrato_aponta_para_a_propria_transacao():
    origem_tipo, origem_id = ContaService._origem_da_transacao(_transacao_falsa(id=123))
    assert (origem_tipo, origem_id) == (TipoEntidadeReferenciavel.TRANSACAO, 123)


def test_origem_da_transacao_com_fatura_paga_aponta_para_a_fatura():
    origem_tipo, origem_id = ContaService._origem_da_transacao(_transacao_falsa(fatura_paga_id=42))
    assert (origem_tipo, origem_id) == (TipoEntidadeReferenciavel.FATURA, 42)


def test_somar_movimentacoes_filtra_por_sinal():
    movimentacoes = [
        MovimentacaoContaRead(
            data=date(2026, 7, 1),
            descricao="Salário",
            valor=Decimal("1000"),
            positivo=True,
            categoria=CategoriaMovimentacaoConta.RECEITA,
            origem_tipo=TipoEntidadeReferenciavel.TRANSACAO,
            origem_id=1,
        ),
        MovimentacaoContaRead(
            data=date(2026, 7, 2),
            descricao="Mercado",
            valor=Decimal("300"),
            positivo=False,
            categoria=CategoriaMovimentacaoConta.DESPESA,
            origem_tipo=TipoEntidadeReferenciavel.TRANSACAO,
            origem_id=2,
        ),
    ]
    assert ContaService._somar(movimentacoes, positivo=True) == Decimal("1000")
    assert ContaService._somar(movimentacoes, positivo=False) == Decimal("300")


def test_limites_do_mes_cobre_do_primeiro_ao_ultimo_dia():
    inicio, fim = ContaService._limites_do_mes(2026, 2)
    assert inicio == date(2026, 2, 1)
    assert fim == date(2026, 2, 28)
