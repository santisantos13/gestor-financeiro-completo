"""Testes unitários de MetaService - isolado com repositories FALSOS (em
memória, sem banco). Cobre o que mais diferencia Meta de Tag/Cartão: o
"cofrinho" automático (Conta dedicada e oculta, criada por `MetaService.
criar` - Refatoramento de Metas/Transferências, ver
docs/analise-arquitetural-metas-transferencias.md) e o cálculo de
`valor_acumulado`/`percentual`, que soma DUAS fontes - o histórico legado
(`Transacao.meta_id`, CONGELADO) e o saldo do cofrinho (`Transferencia`,
simulado aqui por `FakeContaRepository.transferencias`).
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import FrequenciaContribuicao, SituacaoPlanejamentoMeta
from app.schemas.meta import MetaCreate, MetaUpdate
from app.services.meta_service import MetaService


class FakeMetaRepository:
    def __init__(self):
        self._metas = {}
        self._proximo_id = 1
        self.aportes_pagos: dict[int, Decimal] = {}
        self.transacoes_vinculadas: set[int] = set()
        self.desvinculadas: list[int] = []

    def get(self, id):
        return self._metas.get(id)

    def create(self, meta):
        meta.id = self._proximo_id
        self._proximo_id += 1
        # Mesmo comportamento de `TimestampMixin.criado_em` num banco real
        # (`server_default=func.now()`, só aplicado numa insercao de
        # verdade) - sem isso, `MetaService._com_progresso` (que agora lê
        # `meta.criado_em.date()`) quebraria em todo teste unitário.
        if getattr(meta, "criado_em", None) is None:
            meta.criado_em = datetime.now()
        self._metas[meta.id] = meta
        return meta

    def update(self, meta):
        return meta

    def delete(self, meta):
        self._metas.pop(meta.id, None)

    def desvincular_transacoes(self, meta_id):
        self.desvinculadas.append(meta_id)

    def listar_do_usuario(self, usuario_id, *, apenas_ativas=True, skip=0, limit=100):
        resultado = [
            m
            for m in self._metas.values()
            if m.usuario_id == usuario_id and (not apenas_ativas or m.ativo)
        ]
        resultado.sort(key=lambda m: m.descricao)
        return resultado[skip : skip + limit]

    def buscar_por_descricao(self, usuario_id, descricao):
        return next(
            (m for m in self._metas.values() if m.usuario_id == usuario_id and m.descricao == descricao),
            None,
        )

    def somar_transacoes_pagas(self, meta_id):
        return self.aportes_pagos.get(meta_id, Decimal("0"))


class _ContaFalsa:
    def __init__(self, id, usuario_id, oculta=False, ativo=True):
        self.id = id
        self.usuario_id = usuario_id
        self.oculta = oculta
        self.ativo = ativo


class FakeContaRepository:
    """`somar_transferencias` simula o saldo do cofrinho (aportes -
    resgates, seção 3 da análise) - por padrão 0 para toda conta não
    explicitamente configurada em `self.transferencias`. `existe_vinculo`
    simula se o cofrinho já recebeu alguma Transferencia real (seção 2.1 -
    decide se `MetaService.excluir` apaga o cofrinho de verdade ou só
    desoculta/desativa)."""

    def __init__(self):
        self._contas = {}
        self._proximo_id = 100
        self.transferencias: dict[int, Decimal] = {}
        self.vinculos: set[int] = set()
        self.deletadas: list[int] = []

    def adicionar(self, conta_id, usuario_id, oculta=False):
        self._contas[conta_id] = _ContaFalsa(conta_id, usuario_id, oculta=oculta)
        return self._contas[conta_id]

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
        self.deletadas.append(conta.id)

    def somar_transferencias(self, conta_id):
        return self.transferencias.get(conta_id, Decimal("0"))

    def existe_vinculo(self, conta_id):
        return conta_id in self.vinculos


@pytest.fixture()
def meta_repo():
    return FakeMetaRepository()


@pytest.fixture()
def conta_repo():
    return FakeContaRepository()


@pytest.fixture()
def service(meta_repo, conta_repo):
    return MetaService(meta_repo, conta_repo)


def _criar(
    service,
    usuario_id=1,
    descricao="Viagem para o Japão",
    valor_alvo=Decimal("15000"),
    data_alvo=None,
    frequencia_contribuicao=None,
):
    dados = MetaCreate(
        descricao=descricao,
        valor_alvo=valor_alvo,
        data_alvo=data_alvo,
        frequencia_contribuicao=frequencia_contribuicao,
    )
    return service.criar(dados, usuario_id)


# --- criar -------------------------------------------------------------

def test_criar_meta_associa_ao_usuario(service):
    meta = _criar(service, usuario_id=1)
    assert meta.id is not None
    assert meta.usuario_id == 1
    assert meta.ativo is True


def test_criar_meta_cria_cofrinho_automatico(service, conta_repo):
    """Toda Meta nova ganha, automaticamente, uma Conta dedicada e oculta
    - o usuário nunca escolhe/vê essa conta (seção 2 da análise)."""
    meta = _criar(service, usuario_id=1)
    assert meta.conta_id is not None

    cofrinho = conta_repo.get(meta.conta_id)
    assert cofrinho is not None
    assert cofrinho.usuario_id == 1
    assert cofrinho.oculta is True
    assert cofrinho.ativo is True


def test_criar_meta_com_descricao_duplicada_no_mesmo_usuario_levanta_conflict_error(service):
    _criar(service, usuario_id=1, descricao="Viagem")
    with pytest.raises(ConflictError):
        _criar(service, usuario_id=1, descricao="Viagem")


def test_criar_meta_com_mesma_descricao_em_usuarios_diferentes_e_permitido(service):
    meta_a = _criar(service, usuario_id=1, descricao="Viagem")
    meta_b = _criar(service, usuario_id=2, descricao="Viagem")
    assert meta_a.id != meta_b.id
    assert meta_a.conta_id != meta_b.conta_id  # cofrinhos independentes


def test_criar_meta_com_descricao_de_meta_desativada_reativa_em_vez_de_duplicar(service, meta_repo):
    original = _criar(service, usuario_id=1, descricao="Viagem", valor_alvo=Decimal("10000"))
    service.desativar(original.id, usuario_id=1)

    recriada = _criar(service, usuario_id=1, descricao="Viagem", valor_alvo=Decimal("20000"))

    assert recriada.id == original.id  # mesma linha, reativada
    assert recriada.ativo is True
    assert recriada.valor_alvo == Decimal("20000")
    assert len(meta_repo._metas) == 1  # nao criou uma segunda linha


def test_criar_meta_reativando_preserva_cofrinho_existente(service, conta_repo):
    """Reativar NÃO cria um segundo cofrinho - preserva o que a meta já
    tinha, com todo o saldo já acumulado nele."""
    original = _criar(service, usuario_id=1, descricao="Viagem")
    cofrinho_original_id = original.conta_id
    service.desativar(original.id, usuario_id=1)

    recriada = _criar(service, usuario_id=1, descricao="Viagem")

    assert recriada.conta_id == cofrinho_original_id
    assert len(conta_repo._contas) == 1  # nao criou um segundo cofrinho


def test_criar_meta_normaliza_espacos_na_descricao(service):
    meta = _criar(service, usuario_id=1, descricao="  Viagem  ")
    assert meta.descricao == "Viagem"


# --- obter / listar ------------------------------------------------------

def test_obter_meta_propria(service):
    meta = _criar(service, usuario_id=1)
    assert service.obter(meta.id, usuario_id=1).id == meta.id


def test_obter_meta_de_outro_usuario_levanta_not_found(service):
    meta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.obter(meta.id, usuario_id=2)


def test_obter_meta_inexistente_levanta_not_found(service):
    with pytest.raises(NotFoundError):
        service.obter(999, usuario_id=1)


def test_listar_retorna_apenas_metas_do_usuario(service):
    _criar(service, usuario_id=1, descricao="Minha")
    _criar(service, usuario_id=2, descricao="Do outro")
    resultado = service.listar(usuario_id=1)
    assert [m.descricao for m in resultado] == ["Minha"]


def test_listar_filtra_apenas_ativas_por_padrao(service):
    ativa = _criar(service, usuario_id=1, descricao="Ativa")
    inativa = _criar(service, usuario_id=1, descricao="Inativa")
    service.desativar(inativa.id, usuario_id=1)

    assert [m.descricao for m in service.listar(usuario_id=1)] == ["Ativa"]
    assert {m.descricao for m in service.listar(usuario_id=1, apenas_ativas=False)} == {"Ativa", "Inativa"}


# --- valor_acumulado / percentual ----------------------------------------

def test_valor_acumulado_sem_aportes_e_zero(service):
    meta = _criar(service, usuario_id=1, valor_alvo=Decimal("1000"))
    assert meta.valor_acumulado == Decimal("0")
    assert meta.percentual == Decimal("0.00")


def test_valor_acumulado_reflete_soma_de_aportes_pagos_legado(service, meta_repo):
    meta = _criar(service, usuario_id=1, valor_alvo=Decimal("1000"))
    meta_repo.aportes_pagos[meta.id] = Decimal("250")

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.valor_acumulado == Decimal("250")
    assert atualizada.percentual == Decimal("25.00")


def test_valor_acumulado_reflete_saldo_do_cofrinho_novo(service, conta_repo):
    """Aportes/resgates novos (Transferencia) somam via o saldo do
    cofrinho - nenhum aporte legado (Transacao) necessário."""
    meta = _criar(service, usuario_id=1, valor_alvo=Decimal("1000"))
    conta_repo.transferencias[meta.conta_id] = Decimal("400")

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.valor_acumulado == Decimal("400")
    assert atualizada.percentual == Decimal("40.00")


def test_valor_acumulado_soma_legado_e_cofrinho(service, meta_repo, conta_repo):
    """As duas fontes somam juntas - histórico congelado + aportes/
    resgates novos (seção 3 da análise)."""
    meta = _criar(service, usuario_id=1, valor_alvo=Decimal("1000"))
    meta_repo.aportes_pagos[meta.id] = Decimal("300")  # legado
    conta_repo.transferencias[meta.conta_id] = Decimal("150")  # novo

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.valor_acumulado == Decimal("450")


def test_percentual_pode_passar_de_100_se_meta_superada(service, meta_repo):
    """Sem teto artificial - mesma filosofia de CartaoService não clampar
    limite_disponivel negativo: mostra a realidade."""
    meta = _criar(service, usuario_id=1, valor_alvo=Decimal("1000"))
    meta_repo.aportes_pagos[meta.id] = Decimal("1500")

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.percentual == Decimal("150.00")


def test_listar_calcula_progresso_de_cada_meta(service, meta_repo):
    meta_a = _criar(service, usuario_id=1, descricao="A", valor_alvo=Decimal("100"))
    meta_b = _criar(service, usuario_id=1, descricao="B", valor_alvo=Decimal("200"))
    meta_repo.aportes_pagos[meta_a.id] = Decimal("50")
    meta_repo.aportes_pagos[meta_b.id] = Decimal("100")

    resultado = {m.descricao: m.percentual for m in service.listar(usuario_id=1)}
    assert resultado == {"A": Decimal("50.00"), "B": Decimal("50.00")}


# --- atualizar -------------------------------------------------------------

def test_atualizar_meta_propria_aplica_apenas_campos_enviados(service):
    meta = _criar(service, usuario_id=1, descricao="Original", valor_alvo=Decimal("1000"))
    atualizada = service.atualizar(meta.id, MetaUpdate(valor_alvo=Decimal("2000")), usuario_id=1)
    assert atualizada.descricao == "Original"
    assert atualizada.valor_alvo == Decimal("2000")


def test_atualizar_meta_de_outro_usuario_levanta_not_found(service):
    meta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.atualizar(meta.id, MetaUpdate(descricao="Hackeada"), usuario_id=2)


def test_atualizar_nao_altera_o_cofrinho(service):
    """`conta_id` não existe em `MetaUpdate` - não há como o cliente
    trocar o cofrinho de uma Meta via PATCH."""
    meta = _criar(service, usuario_id=1)
    cofrinho_original = meta.conta_id
    atualizada = service.atualizar(meta.id, MetaUpdate(valor_alvo=Decimal("999")), usuario_id=1)
    assert atualizada.conta_id == cofrinho_original


def test_atualizar_descricao_para_descricao_ja_usada_por_outra_meta_levanta_conflict_error(service):
    _criar(service, usuario_id=1, descricao="Viagem")
    outra = _criar(service, usuario_id=1, descricao="Carro")

    with pytest.raises(ConflictError):
        service.atualizar(outra.id, MetaUpdate(descricao="Viagem"), usuario_id=1)


def test_atualizar_reenviando_a_mesma_descricao_nao_levanta_conflict_error(service):
    meta = _criar(service, usuario_id=1, descricao="Viagem")
    atualizada = service.atualizar(
        meta.id, MetaUpdate(descricao="Viagem", valor_alvo=Decimal("5000")), usuario_id=1
    )
    assert atualizada.valor_alvo == Decimal("5000")


def test_atualizar_renomeando_para_descricao_de_meta_inativa_levanta_conflict_error(service):
    """Mesma decisão de TagService/CartaoService: renomear NÃO reativa/
    mescla automaticamente com uma meta inativa de mesma descrição."""
    inativa = _criar(service, usuario_id=1, descricao="Viagem")
    service.desativar(inativa.id, usuario_id=1)
    outra = _criar(service, usuario_id=1, descricao="Carro")

    with pytest.raises(ConflictError):
        service.atualizar(outra.id, MetaUpdate(descricao="Viagem"), usuario_id=1)


def test_atualizar_ativo_true_reativa_meta_diretamente(service, meta_repo):
    meta = _criar(service, usuario_id=1)
    service.desativar(meta.id, usuario_id=1)

    reativada = service.atualizar(meta.id, MetaUpdate(ativo=True), usuario_id=1)

    assert reativada.ativo is True
    assert meta_repo.get(meta.id).ativo is True


# --- desativar ---------------------------------------------------------

def test_desativar_meta_propria(service, meta_repo):
    meta = _criar(service, usuario_id=1)
    service.desativar(meta.id, usuario_id=1)
    assert meta_repo.get(meta.id).ativo is False


def test_desativar_meta_nao_afeta_o_cofrinho(service, conta_repo):
    meta = _criar(service, usuario_id=1)
    service.desativar(meta.id, usuario_id=1)
    cofrinho = conta_repo.get(meta.conta_id)
    assert cofrinho.ativo is True
    assert cofrinho.oculta is True


def test_desativar_meta_de_outro_usuario_levanta_not_found(service):
    meta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.desativar(meta.id, usuario_id=2)


# --- excluir (hard delete) -----------------------------------------------

def test_excluir_meta_sem_aportes(service, meta_repo):
    meta = _criar(service, usuario_id=1)
    service.excluir(meta.id, usuario_id=1)
    assert meta_repo.get(meta.id) is None


def test_excluir_meta_com_aporte_vinculado_desvincula_e_remove(service, meta_repo):
    """Mesma regra de FaturaService.excluir (2026-07-24): ter uma
    transação (aporte legado) vinculada não bloqueia mais a exclusão -
    `desvincular_transacoes` é chamado antes do delete (o aporte em si
    nunca é apagado, só perde o vínculo com a meta)."""
    meta = _criar(service, usuario_id=1)
    meta_repo.transacoes_vinculadas.add(meta.id)

    service.excluir(meta.id, usuario_id=1)

    assert meta_repo.get(meta.id) is None
    assert meta.id in meta_repo.desvinculadas


def test_excluir_meta_de_outro_usuario_levanta_not_found(service, meta_repo):
    meta = _criar(service, usuario_id=1)
    with pytest.raises(NotFoundError):
        service.excluir(meta.id, usuario_id=2)
    assert meta_repo.get(meta.id) is not None


def test_excluir_meta_sem_vinculo_apaga_cofrinho_de_verdade(service, conta_repo):
    """Cofrinho que nunca recebeu nenhuma Transferencia é apagado junto -
    nada a preservar nele (seção 2.1 da análise)."""
    meta = _criar(service, usuario_id=1)
    cofrinho_id = meta.conta_id

    service.excluir(meta.id, usuario_id=1)

    assert conta_repo.get(cofrinho_id) is None
    assert cofrinho_id in conta_repo.deletadas


def test_excluir_meta_com_vinculo_desoculta_e_desativa_cofrinho(service, conta_repo):
    """Cofrinho que já tem alguma Transferencia real NUNCA é apagado com
    dinheiro dentro - vira uma Conta comum, visível e desativada, para o
    usuário não perder acesso ao saldo."""
    meta = _criar(service, usuario_id=1)
    cofrinho_id = meta.conta_id
    conta_repo.vinculos.add(cofrinho_id)

    service.excluir(meta.id, usuario_id=1)

    cofrinho = conta_repo.get(cofrinho_id)
    assert cofrinho is not None
    assert cofrinho.oculta is False
    assert cofrinho.ativo is False


# --- Refinamento de Metas: contribuicao_sugerida_por_periodo -------------

def test_contribuicao_sugerida_mensal(service):
    """Meta R$12.000, prazo 300 dias (10 períodos de 30 dias), mensal ->
    R$1.200/período - mesmo espírito do exemplo do pedido do usuário."""
    hoje = date.today()
    meta = _criar(
        service,
        valor_alvo=Decimal("12000"),
        data_alvo=hoje + timedelta(days=300),
        frequencia_contribuicao=FrequenciaContribuicao.MENSAL,
    )
    assert meta.contribuicao_sugerida_por_periodo == Decimal("1200.00")


def test_contribuicao_sugerida_semanal(service):
    hoje = date.today()
    meta = _criar(
        service,
        valor_alvo=Decimal("2300"),
        data_alvo=hoje + timedelta(days=70),  # 10 periodos de 7 dias
        frequencia_contribuicao=FrequenciaContribuicao.SEMANAL,
    )
    assert meta.contribuicao_sugerida_por_periodo == Decimal("230.00")


def test_contribuicao_sugerida_none_sem_frequencia(service):
    meta = _criar(service, data_alvo=date.today() + timedelta(days=300))
    assert meta.contribuicao_sugerida_por_periodo is None


def test_contribuicao_sugerida_none_sem_data_alvo(service):
    meta = _criar(service, frequencia_contribuicao=FrequenciaContribuicao.MENSAL)
    assert meta.contribuicao_sugerida_por_periodo is None


def test_contribuicao_sugerida_none_com_prazo_vencido(service):
    meta = _criar(
        service,
        data_alvo=date.today() - timedelta(days=5),
        frequencia_contribuicao=FrequenciaContribuicao.MENSAL,
    )
    assert meta.contribuicao_sugerida_por_periodo is None


def test_contribuicao_sugerida_none_meta_ja_concluida(service, meta_repo):
    hoje = date.today()
    meta = _criar(
        service,
        valor_alvo=Decimal("1000"),
        data_alvo=hoje + timedelta(days=300),
        frequencia_contribuicao=FrequenciaContribuicao.MENSAL,
    )
    meta_repo.aportes_pagos[meta.id] = Decimal("1000")
    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.contribuicao_sugerida_por_periodo is None


# --- Refinamento de Metas: planejado x realizado -------------------------

def _definir_criado_em(meta_repo, meta_id, quando):
    meta_repo._metas[meta_id].criado_em = quando


def test_valor_planejado_ate_hoje_na_metade_do_prazo(service, meta_repo):
    hoje = date.today()
    criado_em = hoje - timedelta(days=100)
    meta = _criar(service, valor_alvo=Decimal("1000"), data_alvo=criado_em + timedelta(days=200))
    _definir_criado_em(meta_repo, meta.id, datetime.combine(criado_em, datetime.min.time()))

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.valor_planejado_ate_hoje == Decimal("500.00")


def test_valor_planejado_ate_hoje_none_sem_data_alvo(service):
    meta = _criar(service)
    assert meta.valor_planejado_ate_hoje is None


def test_diferenca_planejado_realizado_adiantado(service, meta_repo):
    hoje = date.today()
    criado_em = hoje - timedelta(days=100)
    meta = _criar(service, valor_alvo=Decimal("1000"), data_alvo=criado_em + timedelta(days=200))
    _definir_criado_em(meta_repo, meta.id, datetime.combine(criado_em, datetime.min.time()))
    meta_repo.aportes_pagos[meta.id] = Decimal("850")  # planejado seria 500

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.diferenca_planejado_realizado == Decimal("350.00")
    assert atualizada.situacao_planejamento == SituacaoPlanejamentoMeta.ADIANTADO


def test_diferenca_planejado_realizado_atrasado(service, meta_repo):
    hoje = date.today()
    criado_em = hoje - timedelta(days=100)
    meta = _criar(service, valor_alvo=Decimal("1000"), data_alvo=criado_em + timedelta(days=200))
    _definir_criado_em(meta_repo, meta.id, datetime.combine(criado_em, datetime.min.time()))
    meta_repo.aportes_pagos[meta.id] = Decimal("320")  # planejado seria 500

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.diferenca_planejado_realizado == Decimal("-180.00")
    assert atualizada.situacao_planejamento == SituacaoPlanejamentoMeta.ATRASADO


def test_situacao_dentro_do_planejado_com_pequena_diferenca(service, meta_repo):
    """Banda de tolerância de 2% do valor_alvo - pequenas flutuações não
    viram ADIANTADO/ATRASADO."""
    hoje = date.today()
    criado_em = hoje - timedelta(days=100)
    meta = _criar(service, valor_alvo=Decimal("1000"), data_alvo=criado_em + timedelta(days=200))
    _definir_criado_em(meta_repo, meta.id, datetime.combine(criado_em, datetime.min.time()))
    meta_repo.aportes_pagos[meta.id] = Decimal("510")  # planejado 500, diferenca 10 (1% < 2%)

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.situacao_planejamento == SituacaoPlanejamentoMeta.DENTRO_DO_PLANEJADO


def test_situacao_planejamento_none_sem_data_alvo(service):
    meta = _criar(service)
    assert meta.situacao_planejamento is None


def test_situacao_planejamento_none_meta_ja_concluida(service, meta_repo):
    hoje = date.today()
    meta = _criar(service, valor_alvo=Decimal("1000"), data_alvo=hoje + timedelta(days=200))
    meta_repo.aportes_pagos[meta.id] = Decimal("1000")
    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.situacao_planejamento is None


# --- Refinamento de Metas: previsão de conclusão -------------------------

def test_data_prevista_conclusao_no_ritmo_atual(service, meta_repo):
    hoje = date.today()
    criado_em = hoje - timedelta(days=100)
    meta = _criar(service, valor_alvo=Decimal("1000"))
    _definir_criado_em(meta_repo, meta.id, datetime.combine(criado_em, datetime.min.time()))
    meta_repo.aportes_pagos[meta.id] = Decimal("500")  # ritmo = 5/dia, restam 500 -> 100 dias

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.data_prevista_conclusao == hoje + timedelta(days=100)


def test_data_prevista_conclusao_none_sem_nenhum_progresso(service):
    meta = _criar(service, valor_alvo=Decimal("1000"))
    assert meta.data_prevista_conclusao is None


def test_data_prevista_conclusao_none_meta_ja_concluida(service, meta_repo):
    meta = _criar(service, valor_alvo=Decimal("1000"))
    meta_repo.aportes_pagos[meta.id] = Decimal("1000")
    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.data_prevista_conclusao is None


def test_data_prevista_conclusao_none_ritmo_baixo_demais_para_ser_confiavel(service, meta_repo):
    hoje = date.today()
    criado_em = hoje - timedelta(days=1000)
    meta = _criar(service, valor_alvo=Decimal("100000"))
    _definir_criado_em(meta_repo, meta.id, datetime.combine(criado_em, datetime.min.time()))
    meta_repo.aportes_pagos[meta.id] = Decimal("0.01")  # ritmo irrisorio

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.data_prevista_conclusao is None


# --- Refinamento de Metas: concluida_em (lazy, uma unica vez) ------------

def test_concluida_em_e_gravada_na_primeira_vez_que_percentual_atinge_100(service, meta_repo):
    meta = _criar(service, valor_alvo=Decimal("1000"))
    assert meta.concluida_em is None

    meta_repo.aportes_pagos[meta.id] = Decimal("1000")
    atualizada = service.obter(meta.id, usuario_id=1)

    assert atualizada.concluida_em == date.today()
    assert meta_repo.get(meta.id).concluida_em == date.today()


def test_concluida_em_nao_e_sobrescrita_se_percentual_cair_depois(service, meta_repo):
    """Uma vez concluída, o "recorde" é histórico - uma retirada que
    derruba o percentual de volta não apaga `concluida_em`."""
    meta = _criar(service, valor_alvo=Decimal("1000"))
    meta_repo.aportes_pagos[meta.id] = Decimal("1000")
    primeira_leitura = service.obter(meta.id, usuario_id=1)
    data_conclusao_original = primeira_leitura.concluida_em

    meta_repo.aportes_pagos[meta.id] = Decimal("400")  # retirada parcial depois
    segunda_leitura = service.obter(meta.id, usuario_id=1)

    assert segunda_leitura.percentual == Decimal("40.00")
    assert segunda_leitura.concluida_em == data_conclusao_original


def test_concluida_em_nao_muda_se_ja_setada_e_meta_continua_concluida(service, meta_repo):
    meta = _criar(service, valor_alvo=Decimal("1000"))
    data_antiga = date.today() - timedelta(days=30)
    meta_repo._metas[meta.id].concluida_em = data_antiga
    meta_repo.aportes_pagos[meta.id] = Decimal("1500")

    atualizada = service.obter(meta.id, usuario_id=1)
    assert atualizada.concluida_em == data_antiga


# --- Refinamento de Metas: frequencia_contribuicao (campo persistido) ---

def test_criar_meta_com_frequencia_contribuicao(service):
    meta = _criar(service, frequencia_contribuicao=FrequenciaContribuicao.SEMANAL)
    assert meta.frequencia_contribuicao == FrequenciaContribuicao.SEMANAL


def test_criar_meta_sem_frequencia_contribuicao_e_permitido(service):
    meta = _criar(service)
    assert meta.frequencia_contribuicao is None


def test_atualizar_frequencia_contribuicao(service):
    meta = _criar(service, frequencia_contribuicao=FrequenciaContribuicao.MENSAL)
    atualizada = service.atualizar(
        meta.id, MetaUpdate(frequencia_contribuicao=FrequenciaContribuicao.DIARIA), usuario_id=1
    )
    assert atualizada.frequencia_contribuicao == FrequenciaContribuicao.DIARIA
