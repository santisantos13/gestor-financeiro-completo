"""Repository de Conta.

Além do CRUD genérico, expõe as buscas/agregações específicas de Conta:
listar as contas de um usuário, e somar o que já se moveu de/para uma
conta em Transacao/Transferencia - a MATÉRIA-PRIMA que ContaService usa
para calcular saldo_atual (a fórmula em si - "soma isso, subtrai aquilo" -
é regra de negócio e mora no Service; aqui só existe a query).

Transacao e Transferencia ainda não têm Repository próprio (não têm CRUD
nesta etapa) - por isso esses dois métodos de soma vivem aqui, dentro do
Repository que efetivamente precisa deles, em vez de criar um
TransacaoRepository/TransferenciaRepository inteiros só para isso agora.
Quando o CRUD de Transacao for implementado, avaliar se vale a pena mover.
"""
from decimal import Decimal
from typing import Sequence

from sqlalchemy import case, exists, func, or_, select

from app.models import Cartao, Conta, ContaRecorrente, Emprestimo, Financiamento, Parcelamento, Transacao, Transferencia
from app.models.enums import StatusTransacao, TipoTransacao
from app.repositories.base import SQLAlchemyRepository


class ContaRepository(SQLAlchemyRepository[Conta]):
    model = Conta

    def listar_do_usuario(
        self,
        usuario_id: int,
        *,
        apenas_ativas: bool = True,
        apenas_visiveis: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Conta]:
        """`apenas_visiveis=True` (padrão) filtra `oculta=False` - esconde
        o "cofrinho" automático de Metas de toda listagem/picker normal
        (ContasPage, AccountSelect, resumo de Contas do Dashboard) sem
        nenhuma delas precisar saber que esse conceito existe. Só
        `CentralFinanceiraService.saldo_consolidado` passa
        `apenas_visiveis=False` explicitamente - o cálculo de patrimônio
        total PRECISA somar o saldo de todo cofrinho (ver
        docs/analise-arquitetural-metas-transferencias.md, seção 1.1)."""
        condicoes = [Conta.usuario_id == usuario_id]
        if apenas_ativas:
            condicoes.append(Conta.ativo.is_(True))
        if apenas_visiveis:
            condicoes.append(Conta.oculta.is_(False))
        stmt = select(Conta).where(*condicoes).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def somar_transacoes_pagas(self, conta_id: int) -> Decimal:
        """Soma líquida (receitas - despesas) das transações PAGAS desta
        conta. Transação PENDENTE ainda não moveu dinheiro de verdade
        (ver StatusTransacao), então não entra na soma.

        `Transacao.importada` também é excluída daqui: são parcelas de
        Financiamento/Empréstimo lançadas pelo onboarding
        "parcelas_ja_pagas" para registrar um contrato que já existia ANTES
        do usuário começar a usar o app - dinheiro que já tinha saído da
        vida financeira dele bem antes de qualquer conta ser cadastrada
        aqui. Se entrasse nesta soma, o saldo_atual da conta ficaria
        artificialmente negativo por causa de um histórico que o próprio
        usuário nunca pediu para o app deduzir (ver
        docs/analise-arquitetural-financiamento.md e a instrução explícita
        do usuário: "deixe por conta do usuário decidir se ele tá com saldo
        negativo ou não, evite deduções com base em informações resgatadas
        do passado financeiro antes do uso do app"). Uma parcela paga
        organicamente pelo botão "Pagar" da UI nunca tem `importada=True`,
        então continua contando normalmente."""
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (Transacao.tipo == TipoTransacao.RECEITA, Transacao.valor),
                        else_=-Transacao.valor,
                    )
                ),
                0,
            )
        ).where(
            Transacao.conta_id == conta_id,
            Transacao.status == StatusTransacao.PAGO,
            Transacao.importada.is_(False),
        )
        return Decimal(self.db.execute(stmt).scalar_one())

    def somar_transferencias(self, conta_id: int) -> Decimal:
        """Soma líquida de Transferencia ATIVA envolvendo esta conta: valores
        recebidos (conta é destino) somam, valores enviados (conta é
        origem) subtraem. Transferencia cancelada (`ativo=False`) é
        excluída - `TransferenciaService.cancelar()` é o "desfazer o efeito
        financeiro preservando o histórico" pedido na análise: a linha
        continua existindo (histórico intacto), só deixa de entrar nesta
        soma (ver docstring de `Transferencia.ativo`)."""
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (Transferencia.conta_destino_id == conta_id, Transferencia.valor),
                        (Transferencia.conta_origem_id == conta_id, -Transferencia.valor),
                        else_=0,
                    )
                ),
                0,
            )
        ).where(
            (Transferencia.conta_destino_id == conta_id) | (Transferencia.conta_origem_id == conta_id),
            Transferencia.ativo.is_(True),
        )
        return Decimal(self.db.execute(stmt).scalar_one())

    def existe_vinculo(self, conta_id: int) -> bool:
        """Usado só pela exclusão definitiva (hard delete,
        `docs/analise-arquitetural-exclusao.md`, seção 2.1) - bem mais
        rígido que `somar_transacoes_pagas`/`somar_transferencias` acima
        (que só olham o que já moveu dinheiro DE VERDADE, para calcular
        saldo): aqui qualquer vínculo, EM QUALQUER STATUS - inclusive
        transação PENDENTE, transferência cancelada, cartão desativado -
        já é suficiente para bloquear, porque `Transacao.conta_id` e
        `Cartao.conta_pagamento_id` têm `ondelete=CASCADE`: um DELETE físico
        apagaria essas linhas junto, mesmo que soft-deletadas.

        Ampliado (2026-07, ver
        docs/analise-arquitetural-exclusao-conta-com-historico.md) para
        cobrir também Financiamento/Empréstimo/ContaRecorrente/Parcelamento
        vinculados diretamente à conta (não ao cartão) - gap encontrado ao
        desenhar a exclusão em cascata: nenhum desses quatro era checado
        antes, então já era possível (bug) excluir definitivamente uma
        conta ainda referenciada por um contrato ou por um template de
        recorrência/parcelamento."""
        stmt = select(
            exists().where(Transacao.conta_id == conta_id)
            | exists().where(
                or_(Transferencia.conta_origem_id == conta_id, Transferencia.conta_destino_id == conta_id)
            )
            | exists().where(Cartao.conta_pagamento_id == conta_id)
            | exists().where(Financiamento.conta_id == conta_id)
            | exists().where(Emprestimo.conta_id == conta_id)
            | exists().where(ContaRecorrente.conta_id == conta_id)
            | exists().where(Parcelamento.conta_id == conta_id)
        )
        return self.db.execute(stmt).scalar_one()
