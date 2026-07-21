"""Service de Tag.

Regra de negócio central: nome único por usuário, inclusive coexistindo
com soft delete - ver `criar()` para como isso é resolvido sem violar
`UniqueConstraint(usuario_id, nome)`.
"""
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Tag
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagUpdate


class TagService:
    def __init__(self, tag_repo: TagRepository) -> None:
        self.tag_repo = tag_repo

    def criar(self, dados: TagCreate, usuario_id: int) -> Tag:
        """Cria uma tag nova - ou REATIVA uma existente, se o nome colidir
        com uma tag desativada do mesmo usuário.

        `UniqueConstraint(usuario_id, nome)` não sabe distinguir tag ativa
        de desativada: se simplesmente tentássemos inserir uma linha nova
        com um nome que já pertenceu a uma tag soft-deletada, o banco
        rejeitaria por violação de unicidade - o usuário nunca conseguiria
        "recriar" uma tag que ele mesmo apagou. Reativar em vez de inserir
        resolve isso sem enfraquecer a constraint nem exigir um índice
        parcial (que só faria sentido em bancos que suportam isso bem, e
        criaria um caminho fora do padrão do resto do projeto).
        """
        existente = self.tag_repo.buscar_por_nome(usuario_id, dados.nome)
        if existente is not None:
            if existente.ativo:
                raise ConflictError("Já existe uma tag com este nome.")
            # Semantica de CRIACAO, nao de "restaurar como estava": o
            # payload e aplicado por completo, entao se `cor` nao for
            # enviado (fica None, default de TagCreate), a cor antiga E
            # SOBRESCRITA - de proposito. TagCreate nao tem o exclude_unset
            # de TagUpdate pra saber "o cliente nao mencionou esse campo",
            # entao tratar isso como uma criacao normal (o que foi enviado
            # e o estado final) e mais previsivel do que magicamente
            # preservar atributos de uma tag que, do ponto de vista do
            # usuario, ele acabou de "criar de novo".
            existente.cor = dados.cor
            existente.ativo = True
            return self.tag_repo.update(existente)

        # ativo=True explicito - mesmo motivo de Conta/CategoriaService.criar:
        # o default da coluna so e aplicado num flush de verdade.
        tag = Tag(**dados.model_dump(), usuario_id=usuario_id, ativo=True)
        return self.tag_repo.create(tag)

    def obter(self, tag_id: int, usuario_id: int) -> Tag:
        return self._buscar_da_propriedade_do_usuario(tag_id, usuario_id)

    def listar(
        self, usuario_id: int, *, apenas_ativas: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Tag]:
        return list(
            self.tag_repo.listar_do_usuario(usuario_id, apenas_ativas=apenas_ativas, skip=skip, limit=limit)
        )

    def atualizar(self, tag_id: int, dados: TagUpdate, usuario_id: int) -> Tag:
        tag = self._buscar_da_propriedade_do_usuario(tag_id, usuario_id)
        alteracoes = dados.model_dump(exclude_unset=True)

        novo_nome = alteracoes.get("nome")
        if novo_nome is not None and novo_nome != tag.nome:
            colisao = self.tag_repo.buscar_por_nome(usuario_id, novo_nome)
            if colisao is not None and colisao.id != tag.id:
                raise ConflictError("Já existe uma tag com este nome.")

        for campo, valor in alteracoes.items():
            setattr(tag, campo, valor)
        return self.tag_repo.update(tag)

    def desativar(self, tag_id: int, usuario_id: int) -> None:
        """"Exclui" uma tag sem apagar a linha - so marca ativo=False,
        mesmo padrao de Conta/Categoria. Nao ha checagem de "em uso":
        diferente da hierarquia de Categoria (onde apagar um pai com filhos
        ativos quebraria a arvore), o vinculo N-N com Transacao nao e afetado
        por soft delete - a tag so some das listas de novas selecoes,
        transacoes que ja a usam continuam com o vinculo intacto."""
        tag = self._buscar_da_propriedade_do_usuario(tag_id, usuario_id)
        tag.ativo = False
        self.tag_repo.update(tag)

    def excluir(self, tag_id: int, usuario_id: int) -> None:
        """Exclusão DEFINITIVA (hard delete) - Etapa F10,
        `docs/analise-arquitetural-exclusao.md`, seção 1: uma AÇÃO NOVA,
        nunca substitui `desativar()` acima. Diferente de
        Conta/Categoria/Cartão, Tag NÃO bloqueia por uso (seção 2.3): o
        vínculo N-N com Transacao é só removido da tabela de associação
        (`ondelete=CASCADE` só ali), nenhuma transação é apagada - sempre
        permitido, sem checagem de negócio nenhuma."""
        tag = self._buscar_da_propriedade_do_usuario(tag_id, usuario_id)
        self.tag_repo.delete(tag)

    def contar_uso(self, tag_id: int, usuario_id: int) -> int:
        """Só informativo, consultado pelo frontend antes de confirmar a
        exclusão definitiva, para avisar quantas transações perdem o
        rótulo (sem bloquear nada - seção 2.3)."""
        self._buscar_da_propriedade_do_usuario(tag_id, usuario_id)
        return self.tag_repo.contar_transacoes_vinculadas(tag_id)

    def _buscar_da_propriedade_do_usuario(self, tag_id: int, usuario_id: int) -> Tag:
        tag = self.tag_repo.get(tag_id)
        if tag is None or tag.usuario_id != usuario_id:
            # Mesmo tratamento (404) para "nao existe" e "e de outro
            # usuario" - mesmo raciocinio anti-enumeracao ja usado em
            # ContaService/CategoriaService (nao ha conceito de "tag do
            # sistema" aqui, entao e sempre binario: e sua, ou nao existe).
            raise NotFoundError("Tag não encontrada.")
        return tag
