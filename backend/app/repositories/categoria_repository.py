"""Repository de Categoria.

Além do CRUD genérico, expõe as buscas específicas de Categoria: listar as
categorias VISÍVEIS a um usuário (do sistema + próprias, nunca as privadas
de outro usuário) e checar existência de subcategoria ativa (usado por
CategoriaService para bloquear exclusão de categoria com filhos ativos).
"""
from typing import Sequence

from sqlalchemy import delete, exists, insert, or_, select

from app.models import Categoria, CategoriaOcultaUsuario, Transacao
from app.repositories.base import SQLAlchemyRepository


class CategoriaRepository(SQLAlchemyRepository[Categoria]):
    model = Categoria

    def listar_visiveis_do_usuario(
        self,
        usuario_id: int,
        *,
        apenas_ativas: bool = True,
        incluir_ocultas: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Categoria]:
        """Categorias do sistema (usuario_id nulo) + as do próprio usuário -
        nunca as privadas de outro usuário.

        `incluir_ocultas=False` (padrão): exclui, via NOT EXISTS, as
        categorias de sistema que ESTE usuário ocultou para si
        (`CategoriaOcultaUsuario` - Sprint de Refinamento Premium, item 4).
        `incluir_ocultas=True` devolve tudo, inclusive as ocultas - usado
        pela visão "Categorias ocultas" do frontend, para o usuário
        encontrar e reexibir o que ocultou."""
        condicoes = [or_(Categoria.usuario_id.is_(None), Categoria.usuario_id == usuario_id)]
        if apenas_ativas:
            condicoes.append(Categoria.ativo.is_(True))
        if not incluir_ocultas:
            oculta = (
                select(CategoriaOcultaUsuario.id)
                .where(
                    CategoriaOcultaUsuario.categoria_id == Categoria.id,
                    CategoriaOcultaUsuario.usuario_id == usuario_id,
                )
                .exists()
            )
            condicoes.append(~oculta)
        stmt = select(Categoria).where(*condicoes).order_by(Categoria.nome).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def esta_oculta_para_usuario(self, categoria_id: int, usuario_id: int) -> bool:
        stmt = select(
            exists().where(
                CategoriaOcultaUsuario.categoria_id == categoria_id,
                CategoriaOcultaUsuario.usuario_id == usuario_id,
            )
        )
        return self.db.execute(stmt).scalar_one()

    def ocultar_para_usuario(self, categoria_id: int, usuario_id: int) -> None:
        """Idempotente: se já estiver oculta para este usuário, não faz
        nada (evita erro de UniqueConstraint num duplo clique/retry)."""
        if self.esta_oculta_para_usuario(categoria_id, usuario_id):
            return
        self.db.execute(
            insert(CategoriaOcultaUsuario).values(categoria_id=categoria_id, usuario_id=usuario_id)
        )
        self.db.flush()

    def reexibir_para_usuario(self, categoria_id: int, usuario_id: int) -> None:
        """Idempotente: reexibir uma categoria que não estava oculta não é
        erro, só não faz nada."""
        self.db.execute(
            delete(CategoriaOcultaUsuario).where(
                CategoriaOcultaUsuario.categoria_id == categoria_id,
                CategoriaOcultaUsuario.usuario_id == usuario_id,
            )
        )
        self.db.flush()

    def existe_subcategoria_ativa(self, categoria_id: int) -> bool:
        stmt = select(
            exists().where(Categoria.categoria_pai_id == categoria_id, Categoria.ativo.is_(True))
        )
        return self.db.execute(stmt).scalar_one()

    def existe_subcategoria(self, categoria_id: int) -> bool:
        """Usado só pela exclusão definitiva (hard delete,
        `docs/analise-arquitetural-exclusao.md`, seção 2.2) - mais rígido
        que `existe_subcategoria_ativa` acima (que só bloqueia
        DESATIVAÇÃO, e por isso só se importa com filha ATIVA): aqui
        qualquer subcategoria, ativa OU inativa, já bloqueia, porque
        `Categoria.categoria_pai_id` tem `ondelete=CASCADE` - um DELETE
        físico apagaria a subárvore inteira, mesmo as subcategorias já
        desativadas."""
        stmt = select(exists().where(Categoria.categoria_pai_id == categoria_id))
        return self.db.execute(stmt).scalar_one()

    def existe_transacao_vinculada(self, categoria_id: int) -> bool:
        """Resolve formalmente o `# TODO(categoria-em-uso)` de
        `CategoriaService.desativar()` - escrito exatamente para este
        momento (exclusão definitiva). `Transacao.categoria_id` usa
        `ondelete=SET NULL`, então um DELETE físico não quebraria
        integridade referencial - mas ainda assim apagaria o rótulo de
        transações históricas reais, o que não deveria acontecer
        silenciosamente."""
        stmt = select(exists().where(Transacao.categoria_id == categoria_id))
        return self.db.execute(stmt).scalar_one()

    def existe_transacao_vinculada_do_usuario(self, categoria_id: int, usuario_id: int) -> bool:
        """Mesmo espírito de `existe_transacao_vinculada` acima, mas
        escopado a um único usuário - usado por
        `CategoriaService.ocultar_para_usuario` (Sprint de Refinamento
        Premium, item 4): ocultar uma categoria de sistema que o próprio
        usuário já usa em transações apagaria o rótulo delas das suas
        listas de escolha silenciosamente, então é bloqueado (mesmo
        racional do hard delete, mas por-usuário, já que aqui a ação
        também é por-usuário)."""
        stmt = select(
            exists().where(Transacao.categoria_id == categoria_id, Transacao.usuario_id == usuario_id)
        )
        return self.db.execute(stmt).scalar_one()
