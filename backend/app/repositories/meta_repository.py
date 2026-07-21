"""Repository de Meta.

Além do CRUD genérico, expõe a listagem por usuário, a busca por descrição
(usada por `MetaService` para validar unicidade e para reativar uma meta
soft-deletada em vez de tentar criar uma linha duplicada - mesmo padrão de
`TagRepository`/`CartaoRepository`) e a soma dos aportes já pagos - a
MATÉRIA-PRIMA que `MetaService` usa para calcular `valor_acumulado`/
`percentual` (a fórmula em si é regra de negócio e mora no Service; aqui só
existe a query). Mesmo raciocínio de `ContaRepository.somar_transacoes_pagas`:
a agregação consulta a tabela `Transacao`, mas a responsabilidade
conceitual ("progresso de uma Meta") pertence ao Repository da entidade que
está calculando o valor derivado.
"""
from decimal import Decimal
from typing import Sequence

from sqlalchemy import case, func, select, update

from app.models import Meta, Transacao
from app.models.enums import StatusTransacao, TipoTransacao
from app.repositories.base import SQLAlchemyRepository


class MetaRepository(SQLAlchemyRepository[Meta]):
    model = Meta

    def listar_do_usuario(
        self, usuario_id: int, *, apenas_ativas: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Meta]:
        condicoes = [Meta.usuario_id == usuario_id]
        if apenas_ativas:
            condicoes.append(Meta.ativo.is_(True))
        stmt = select(Meta).where(*condicoes).order_by(Meta.descricao).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def buscar_por_descricao(self, usuario_id: int, descricao: str) -> Meta | None:
        """Busca INDEPENDENTE de `ativo` (ativa ou desativada) - e exatamente
        por isso que serve tanto para checar unicidade quanto para achar a
        meta a reativar quando a descrição colide com uma já desativada."""
        stmt = select(Meta).where(Meta.usuario_id == usuario_id, Meta.descricao == descricao)
        return self.db.execute(stmt).scalar_one_or_none()

    def somar_transacoes_pagas(self, meta_id: int) -> Decimal:
        """Soma líquida (aportes - retiradas) das transações PAGAS marcadas
        com `meta_id` = esta Meta. RECEITA soma (aporte), DESPESA subtrai
        (retirada) - mesma fórmula de `ContaRepository.somar_transacoes_pagas`.
        Transação PENDENTE ainda não moveu dinheiro de verdade (ver
        StatusTransacao), então não entra na soma."""
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
            Transacao.meta_id == meta_id,
            Transacao.status == StatusTransacao.PAGO,
        )
        return Decimal(self.db.execute(stmt).scalar_one())

    def desvincular_transacoes(self, meta_id: int) -> None:
        """Zera `meta_id` de toda transação vinculada a esta meta - chamado
        por `MetaService.excluir()` logo antes de apagar a meta, nunca
        isoladamente. Mesmo padrão (e mesmo motivo) de
        `FaturaRepository.desvincular_transacoes`: excluir a Meta nunca
        precisou apagar a Transacao - o aporte continua existindo, com o
        mesmo valor/data, só sem meta associada (o usuário pode inclusive
        vincular esse lançamento a outra meta depois, editando a
        transação). Também é a versão em código do que a FK já declara
        (`ondelete="SET NULL"` em `Transacao.meta_id`) mas que o SQLite
        deste projeto não executa sozinho - a conexão nunca liga `PRAGMA
        foreign_keys=ON` (ver `app/db/session.py`), então sem este método
        a exclusão deixaria `meta_id` "pendurado", apontando para uma
        linha que não existe mais."""
        self.db.execute(update(Transacao).where(Transacao.meta_id == meta_id).values(meta_id=None))
