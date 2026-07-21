"""Repository de Transferencia.

Além do CRUD genérico, expõe `listar_do_usuario` - mesmo padrão de
`ContaRepository`/`CartaoRepository`/`ParcelamentoRepository`
(`apenas_ativas` por padrão `true`, já que Transferencia agora tem soft
delete via `ativo` - ver docstring do model).
"""
from datetime import date
from typing import Sequence

from sqlalchemy import or_, select

from app.models import Transferencia
from app.repositories.base import SQLAlchemyRepository


class TransferenciaRepository(SQLAlchemyRepository[Transferencia]):
    model = Transferencia

    def listar_do_usuario(
        self,
        usuario_id: int,
        *,
        apenas_ativas: bool = True,
        conta_id: int | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Transferencia]:
        """`conta_id` (opcional) filtra transferências em que a conta
        informada é origem OU destino - o "extrato" de uma conta
        específica. Usado pelo Refatoramento de Metas/Transferências para
        buscar o histórico de aportes/resgates de um cofrinho
        (`conta_id = meta.conta_id`), mas é um filtro genérico, não
        específico de Meta - mesmo raciocínio de filtros opcionais já
        existentes em `TransacaoRepository.listar_do_usuario`.

        `data_inicio`/`data_fim` (opcionais, mesmo par de
        `TransacaoRepository.listar_do_usuario`) - adicionados para o
        extrato de Conta (`ContaService.extrato`,
        docs/analise-arquitetural-extrato-conta.md) buscar só as
        transferências de um mês específico, sem carregar o histórico
        inteiro da conta a cada consulta."""
        condicoes = [Transferencia.usuario_id == usuario_id]
        if apenas_ativas:
            condicoes.append(Transferencia.ativo.is_(True))
        if conta_id is not None:
            condicoes.append(
                or_(Transferencia.conta_origem_id == conta_id, Transferencia.conta_destino_id == conta_id)
            )
        if data_inicio is not None:
            condicoes.append(Transferencia.data >= data_inicio)
        if data_fim is not None:
            condicoes.append(Transferencia.data <= data_fim)
        stmt = (
            select(Transferencia)
            .where(*condicoes)
            .order_by(Transferencia.data.desc(), Transferencia.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
