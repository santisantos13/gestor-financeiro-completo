"""Repository de Transacao.

Além do CRUD genérico, expõe a listagem filtrada por usuário (conta,
cartão, categoria, tipo, status, parcelamento, intervalo de datas) usada
por `TransacaoService.listar`, e a agregação por período (`somar_por_periodo`)
usada pela Central Financeira. Substitui o Repository mínimo criado durante
o CRUD de Fatura (que só existia para dar suporte a
`FaturaService.registrar_pagamento` - ver docs/revisao-tecnica-fatura.md);
o CRUD genérico herdado de `SQLAlchemyRepository` continua sendo usado por
`FaturaService` normalmente, sem nenhuma mudança de contrato.
"""
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select

from app.models import Transacao
from app.models.enums import StatusTransacao, TipoTransacao
from app.repositories.base import SQLAlchemyRepository


class TransacaoRepository(SQLAlchemyRepository[Transacao]):
    model = Transacao

    def listar_do_usuario(
        self,
        usuario_id: int,
        *,
        conta_id: int | None = None,
        cartao_id: int | None = None,
        fatura_id: int | None = None,
        categoria_id: int | None = None,
        parcelamento_id: int | None = None,
        financiamento_id: int | None = None,
        emprestimo_id: int | None = None,
        origem_recorrente_id: int | None = None,
        meta_id: int | None = None,
        tipo: TipoTransacao | None = None,
        status: StatusTransacao | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        apenas_conta: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Transacao]:
        condicoes = [Transacao.usuario_id == usuario_id]
        if conta_id is not None:
            condicoes.append(Transacao.conta_id == conta_id)
        if cartao_id is not None:
            condicoes.append(Transacao.cartao_id == cartao_id)
        if fatura_id is not None:
            # Compras lançadas NESTE ciclo (Transacao.fatura_id, resolvido
            # automaticamente por FaturaService.resolver_fatura_aberta na
            # criação) - diferente de fatura_paga_id, que marca uma
            # Transacao de PAGAMENTO da fatura (linha separada, na Conta de
            # pagamento do cartão, nunca aparece aqui). Pedido do usuário
            # (2026-07-20): "seria interessante se cada fatura tivesse o
            # histórico de compras dela" - usado por FaturaDrawer.
            condicoes.append(Transacao.fatura_id == fatura_id)
        if apenas_conta:
            # Pedido explícito do usuário (2026-07-20): a tela de Transações
            # não deve listar compras de cartão - só o que sai de uma Conta
            # (lançamento direto ou pagamento de fatura, que também é uma
            # Transacao com conta_id preenchido - ver
            # FaturaService.registrar_pagamento). conta_id/cartao_id são
            # mutuamente exclusivos por CHECK constraint (Transacao.__table_args__),
            # então "cartao_id IS NULL" já basta - não precisa checar
            # conta_id IS NOT NULL de novo. Aditivo e opt-in (default False):
            # todo outro chamador deste método (CentralFinanceiraService,
            # CartaoService, ContaService, etc.) continua vendo compras de
            # cartão normalmente - a regra é só de EXIBIÇÃO na tela de
            # Transações, nunca dos dados/cálculos por trás dela (limite de
            # cartão, faturas, Central Financeira continuam somando compras
            # de cartão como sempre somaram).
            condicoes.append(Transacao.cartao_id.is_(None))
        if categoria_id is not None:
            condicoes.append(Transacao.categoria_id == categoria_id)
        if parcelamento_id is not None:
            condicoes.append(Transacao.parcelamento_id == parcelamento_id)
        if financiamento_id is not None:
            condicoes.append(Transacao.financiamento_id == financiamento_id)
        if emprestimo_id is not None:
            condicoes.append(Transacao.emprestimo_id == emprestimo_id)
        if origem_recorrente_id is not None:
            condicoes.append(Transacao.origem_recorrente_id == origem_recorrente_id)
        if meta_id is not None:
            condicoes.append(Transacao.meta_id == meta_id)
        if tipo is not None:
            condicoes.append(Transacao.tipo == tipo)
        if status is not None:
            condicoes.append(Transacao.status == status)
        if data_inicio is not None:
            condicoes.append(Transacao.data >= data_inicio)
        if data_fim is not None:
            condicoes.append(Transacao.data <= data_fim)

        # mais recente primeiro - mesma convencao ja usada em
        # FaturaRepository.listar_do_cartao para um historico financeiro.
        stmt = (
            select(Transacao)
            .where(*condicoes)
            .order_by(Transacao.data.desc(), Transacao.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def somar_por_periodo(
        self,
        usuario_id: int,
        *,
        tipo: TipoTransacao,
        status: StatusTransacao,
        data_inicio: date,
        data_fim: date,
    ) -> Decimal:
        """Soma `Transacao.valor` (usuário, tipo, status e intervalo de
        datas) via `SUM` no banco - matéria-prima usada pela Central
        Financeira para "entradas do mês"/"saídas do mês" (ver
        docs/analise-arquitetural-central-financeira.md, seção 2.2). Existe
        como método dedicado (em vez de `listar_do_usuario` + soma em
        Python) porque `docs/decisao-performance-saldo.md` já registra a
        diretriz do projeto: toda métrica agregada deve ser uma query SQL
        com `SUM`, nunca carregar as linhas em Python para somar - o mesmo
        padrão de `ContaRepository.somar_transacoes_pagas`/
        `MetaRepository.somar_transacoes_pagas`, só que parametrizado por
        tipo/status/intervalo em vez de fixo."""
        stmt = select(func.coalesce(func.sum(Transacao.valor), 0)).where(
            Transacao.usuario_id == usuario_id,
            Transacao.tipo == tipo,
            Transacao.status == status,
            Transacao.data >= data_inicio,
            Transacao.data <= data_fim,
        )
        return Decimal(self.db.execute(stmt).scalar_one())
