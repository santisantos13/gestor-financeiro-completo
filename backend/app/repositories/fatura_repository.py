"""Repository de Fatura.

Além do CRUD genérico, expõe as buscas/agregações específicas de Fatura:
listar os ciclos de um cartão, buscar por (cartão, mês) - unicidade -,
somar as compras vinculadas ao ciclo (`fatura_id`) e somar os pagamentos
já registrados (`fatura_paga_id`). As duas somas são matéria-prima que
`FaturaService` usa para calcular `valor_total`/`valor_pago` (a fórmula em
si - o que é "valor emitido", o que conta como "pago" - é regra de
negócio e mora no Service; aqui só a query).
"""
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import case, func, select, update

from app.models import Fatura, Transacao
from app.models.enums import TipoTransacao
from app.repositories.base import SQLAlchemyRepository


class FaturaRepository(SQLAlchemyRepository[Fatura]):
    model = Fatura

    def listar_do_cartao(
        self, cartao_id: int, *, skip: int = 0, limit: int = 100
    ) -> Sequence[Fatura]:
        # mais antiga primeiro - pedido do usuario (2026-07-20): historico de
        # faturas le melhor em ordem cronologica ascendente. O desempate por
        # status (paga -> fechada -> aberta) so faz sentido quando duas
        # faturas do MESMO mes_referencia existem, o que a constraint de
        # unicidade (cartao_id, mes_referencia) nunca permite - por isso o
        # desempate mora inteiramente no frontend (utils/fatura.ts,
        # ordenarFaturasParaListagem), que ja tem o status_calculado pronto
        # sem precisar duplicar a formula de derivacao aqui em SQL.
        stmt = (
            select(Fatura)
            .where(Fatura.cartao_id == cartao_id)
            .order_by(Fatura.mes_referencia.asc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def listar_recentes_do_cartao(self, cartao_id: int, *, limit: int = 100) -> Sequence[Fatura]:
        """Mesmas linhas de `listar_do_cartao`, ordem OPOSTA (mais recente
        primeiro) - usado só por `CentralFinanceiraService.
        calendario_financeiro`/`agenda_financeira`, que buscam com
        `limit=3` esperando "o ciclo atual + uma folga de ciclos
        próximos". Bug real corrigido em 2026-07-21 ("calendário não
        exibe fechamento/vencimento de fatura"): os dois chamavam
        `listar_do_cartao` (ordem ASCENDENTE desde 2026-07-20, pedido do
        usuário para a tela de listagem de faturas) com esse mesmo
        `limit=3` - qualquer cartão com mais de 3 meses de uso passou a
        nunca mais mostrar o ciclo atual, só os 3 mais antigos do
        histórico. Método separado (em vez de um parâmetro `ordem=` em
        `listar_do_cartao`) porque os dois usos têm requisitos opostos e
        nenhuma relação entre si - misturar os dois num parâmetro só
        esconderia essa diferença de propósito."""
        stmt = (
            select(Fatura)
            .where(Fatura.cartao_id == cartao_id)
            .order_by(Fatura.mes_referencia.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def listar_no_periodo(self, cartao_id: int, data_inicio: date, data_fim: date) -> Sequence[Fatura]:
        """Toda fatura deste cartão cujo `data_fechamento` OU `data_vencimento`
        caia dentro de `[data_inicio, data_fim]` - usada só por
        `CentralFinanceiraService.calendario_financeiro`, que precisa saber
        exatamente quais eventos de Fatura pertencem ao MÊS consultado.

        Substitui a antiga abordagem de `listar_recentes_do_cartao(limit=3)`
        (bug real relatado pelo usuário em 2026-07-22: "vencimento de
        fatura não aparece" - reproduzido em
        `test_calendario_financeiro_fatura_vencimento_aparece_mesmo_com_3_faturas_mais_recentes`).
        `limit=3` era um palpite de "ciclo atual + folga de ciclos
        próximos" que quebrava sempre que o cartão já tinha 3+ faturas mais
        recentes que a do mês consultado (comum ao navegar para um mês
        passado, ou com múltiplos cartões cada um gerando fatura todo mês) -
        qualquer número fixo teria o mesmo problema. Filtrar direto pela
        janela de data que o chamador já conhece elimina a classe inteira
        do bug, sem precisar adivinhar quantos ciclos "bastam"."""
        stmt = select(Fatura).where(
            Fatura.cartao_id == cartao_id,
            (Fatura.data_fechamento.between(data_inicio, data_fim))
            | (Fatura.data_vencimento.between(data_inicio, data_fim)),
        )
        return self.db.execute(stmt).scalars().all()

    def buscar_por_cartao_e_mes(self, cartao_id: int, mes_referencia: date) -> Fatura | None:
        stmt = select(Fatura).where(
            Fatura.cartao_id == cartao_id, Fatura.mes_referencia == mes_referencia
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def somar_transacoes(self, fatura_id: int) -> Decimal:
        """Soma líquida (DESPESA soma, RECEITA/estorno subtrai) das
        transações vinculadas a este ciclo via `fatura_id` - as compras
        (e eventuais estornos) em si. Enquanto a fatura está ABERTA, este
        é o "valor em aberto" ao vivo; depois de FECHADA, deveria sempre
        coincidir com o snapshot congelado em `Fatura.valor_total`,
        protegido pela imutabilidade das transações de fatura fechada."""
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (Transacao.tipo == TipoTransacao.DESPESA, Transacao.valor),
                        else_=-Transacao.valor,
                    )
                ),
                0,
            )
        ).where(Transacao.fatura_id == fatura_id)
        return Decimal(self.db.execute(stmt).scalar_one())

    def somar_pagamentos(self, fatura_id: int) -> Decimal:
        """Soma das transações de pagamento vinculadas via `fatura_paga_id`
        - pode ser mais de uma (pagamento parcial/múltiplo)."""
        stmt = select(func.coalesce(func.sum(Transacao.valor), 0)).where(
            Transacao.fatura_paga_id == fatura_id
        )
        return Decimal(self.db.execute(stmt).scalar_one())

    def desvincular_transacoes(self, fatura_id: int) -> None:
        """Zera `fatura_id`/`fatura_paga_id` de toda transação vinculada a
        este ciclo - chamado por `FaturaService.excluir()` logo antes de
        apagar a fatura, nunca isoladamente.

        Mudança de regra (2026-07-24, pedido do usuário): excluir uma
        fatura já não é mais bloqueado por ter histórico vinculado (compra
        ou pagamento) - o usuário precisa poder desfazer/corrigir uma
        fatura cadastrada errada mesmo depois de já ter registrado um
        pagamento nela. O que NUNCA acontece é apagar a transação em si -
        ela continua existindo, com o mesmo valor/data, só sem fatura
        associada (mesmo dinheiro real, sem mais vínculo com um ciclo que
        deixou de existir). Se o usuário também quiser remover a
        transação, isso é uma ação separada e explícita (exclusão de
        Transacao), nunca implícita na exclusão da fatura.

        Esta é a versão em código do que a FK já declara (`ondelete="SET
        NULL"` em `Transacao.fatura_id`/`fatura_paga_id`) mas que o SQLite
        deste projeto não executa sozinho - a conexão nunca liga `PRAGMA
        foreign_keys=ON` (ver `app/db/session.py`), então a constraint é só
        documentação de schema, nunca é de fato disparada pelo banco no
        DELETE. Sem este método, apagar a fatura deixaria `fatura_id`/
        `fatura_paga_id` "pendurados", apontando para uma linha que não
        existe mais."""
        self.db.execute(update(Transacao).where(Transacao.fatura_id == fatura_id).values(fatura_id=None))
        self.db.execute(
            update(Transacao).where(Transacao.fatura_paga_id == fatura_id).values(fatura_paga_id=None)
        )
