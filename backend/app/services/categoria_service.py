"""Service de Categoria.

Regras de negócio concentradas aqui: visibilidade (sistema vs. própria vs.
de outro usuário), validação de categoria pai (existe? é utilizável por
este usuário? não cria ciclo?) e bloqueio de exclusão com subcategoria
ativa.
"""
from app.core.exceptions import AcessoNegadoError, BusinessRuleError, NotFoundError
from app.models import Categoria
from app.repositories.categoria_repository import CategoriaRepository
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate


class CategoriaService:
    def __init__(self, categoria_repo: CategoriaRepository) -> None:
        self.categoria_repo = categoria_repo

    def criar(self, dados: CategoriaCreate, usuario_id: int) -> Categoria:
        if dados.categoria_pai_id is not None:
            self._resolver_pai(dados.categoria_pai_id, usuario_id)
        # ativo=True explicito - mesmo motivo de ContaService.criar: o
        # default da coluna so e aplicado num flush de verdade, e nao
        # queremos depender disso (ex: testes unitarios com repository falso).
        categoria = Categoria(**dados.model_dump(), usuario_id=usuario_id, ativo=True)
        categoria = self.categoria_repo.create(categoria)
        # oculta_para_mim explicito (nunca True numa categoria recem-criada
        # pelo proprio usuario - o conceito nem existe pra categoria propria).
        categoria.oculta_para_mim = False
        return categoria

    def obter(self, categoria_id: int, usuario_id: int) -> Categoria:
        categoria = self._buscar_visivel(categoria_id, usuario_id)
        self._anexar_oculta_para_mim(categoria, usuario_id)
        return categoria

    def listar(
        self,
        usuario_id: int,
        *,
        apenas_ativas: bool = True,
        incluir_ocultas: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Categoria]:
        categorias = list(
            self.categoria_repo.listar_visiveis_do_usuario(
                usuario_id,
                apenas_ativas=apenas_ativas,
                incluir_ocultas=incluir_ocultas,
                skip=skip,
                limit=limit,
            )
        )
        for categoria in categorias:
            self._anexar_oculta_para_mim(categoria, usuario_id)
        return categorias

    def atualizar(self, categoria_id: int, dados: CategoriaUpdate, usuario_id: int) -> Categoria:
        """Edição livre de categorias (Tarefa #111): categoria de sistema
        agora é editável nos seus campos de conteúdo (nome/tipo/cor/icone/
        categoria_pai_id) - antes qualquer escrita levava 403 via
        `_buscar_editavel`. Achado real que motivou a decisão de manter uma
        exceção aqui: `usuario_id is None` é UMA ÚNICA LINHA compartilhada
        por TODOS os usuários (não uma cópia por usuário) - por isso
        `ativo: False` numa categoria de sistema continua bloqueado abaixo,
        mesmo dentro deste método: desativar/excluir uma categoria de
        sistema tiraria ela de TODO MUNDO, não só de quem editou, e isso
        nunca foi pedido - segue sendo feito só via `desativar()`/
        `excluir()`, que continuam usando `_buscar_editavel` e bloqueando
        categoria de sistema por inteiro."""
        categoria = self._buscar_visivel(categoria_id, usuario_id)
        alteracoes = dados.model_dump(exclude_unset=True)

        if alteracoes.get("ativo") is False and categoria.usuario_id is None:
            raise AcessoNegadoError(
                "Categorias do sistema são compartilhadas por todos os usuários e não podem ser desativadas."
            )

        # so valida pai/ciclo se o cliente de fato mandou trocar o pai (e
        # para um valor nao-nulo - remover o pai, setando null, nunca cria
        # ciclo, entao nao precisa de checagem).
        if "categoria_pai_id" in alteracoes and alteracoes["categoria_pai_id"] is not None:
            novo_pai_id = alteracoes["categoria_pai_id"]
            if novo_pai_id == categoria_id:
                raise BusinessRuleError("Uma categoria não pode ser pai dela mesma.")
            self._resolver_pai(novo_pai_id, usuario_id)
            if self._cria_ciclo(categoria_id, novo_pai_id):
                raise BusinessRuleError("Essa alteração criaria um ciclo na hierarquia de categorias.")

        # PATCH e DELETE sao dois caminhos pro MESMO efeito (ativo:
        # True -> False) - a regra "nao desativar com subcategoria ativa"
        # tem que valer nos dois, senao um cliente contornaria a regra so
        # usando PATCH {"ativo": false} em vez de DELETE. So dispara quando
        # a alteracao de fato desliga (nao incomoda reenviar ativo=true, e
        # nao incomoda reenviar ativo=false numa categoria ja inativa).
        if alteracoes.get("ativo") is False and categoria.ativo is True:
            self._impedir_desativacao_com_subcategoria_ativa(categoria_id)

        for campo, valor in alteracoes.items():
            setattr(categoria, campo, valor)
        categoria = self.categoria_repo.update(categoria)
        self._anexar_oculta_para_mim(categoria, usuario_id)
        return categoria

    def desativar(self, categoria_id: int, usuario_id: int) -> None:
        """"Exclui" uma categoria sem apagar a linha - so marca ativo=False,
        mesmo padrao de Conta.desativar (preserva o rotulo em transacoes
        historicas mesmo apos a categoria sair das listas de escolha).

        Revisitado na Etapa de Refinamento de UX/Dashboard/Cartoes
        (docs/analise-arquitetural-refinamento-ux-dashboard-cartoes.md,
        secao 10): havia aqui um `TODO(categoria-em-uso)` escrito antes do
        CRUD de Transacao existir, propondo bloquear a desativacao se
        houver transacao vinculada. Agora que Transacao existe
        (`existe_transacao_vinculada`, usado por `excluir()` abaixo),
        a conclusao ao revisitar e que esse bloqueio NAO deveria ser
        adicionado aqui: `ContaService.desativar()` (mesmo padrao, citado
        acima) tambem nunca bloqueia por transacao vinculada - e o proprio
        objetivo do soft delete e permitir que uma categoria/conta em uso
        historico saia das listas de escolha sem apagar o rotulo de nada
        (`Transacao.categoria_id` e `ondelete=SET NULL`, nao CASCADE, por
        isso o dado antigo continua integro mesmo com a categoria
        inativa). Adicionar um bloqueio aqui criaria uma regra de negocio
        nova, inconsistente com o padrao ja estabelecido, sem necessidade
        real - por isso o TODO e removido, nao implementado."""
        categoria = self._buscar_editavel(categoria_id, usuario_id)
        self._impedir_desativacao_com_subcategoria_ativa(categoria_id)
        categoria.ativo = False
        self.categoria_repo.update(categoria)

    def excluir(self, categoria_id: int, usuario_id: int) -> None:
        """Exclusão DEFINITIVA (hard delete) - Etapa F10,
        `docs/analise-arquitetural-exclusao.md`, seção 1: uma AÇÃO NOVA,
        nunca substitui `desativar()` acima. `_buscar_editavel` já barra
        categoria de sistema (`AcessoNegadoError`) e categoria privada de
        outro usuário (`NotFoundError`) - nenhuma checagem nova precisa
        disso aqui. Bloqueia se houver qualquer transação vinculada OU
        qualquer subcategoria (ativa ou inativa, seção 2.2) - mais rígido
        que a checagem de desativação porque o auto-FK
        `categoria_pai_id` tem `ondelete=CASCADE`."""
        categoria = self._buscar_editavel(categoria_id, usuario_id)
        if self.categoria_repo.existe_transacao_vinculada(categoria_id):
            raise BusinessRuleError(
                "Esta categoria possui transações vinculadas e não pode ser excluída definitivamente. "
                "Desative-a em vez disso."
            )
        if self.categoria_repo.existe_subcategoria(categoria_id):
            raise BusinessRuleError(
                "Esta categoria possui subcategorias e não pode ser excluída definitivamente."
            )
        self.categoria_repo.delete(categoria)

    def ocultar_para_usuario(self, categoria_id: int, usuario_id: int) -> None:
        """"Excluir" uma categoria de sistema DO PONTO DE VISTA DESTE
        USUÁRIO (Sprint de Refinamento Premium, item 4) - nunca toca a
        linha de `Categoria`, que continua existindo e visível para todos
        os outros usuários. Diferente de `desativar()`/`excluir()`
        (bloqueados para sistema via `_buscar_editavel`, e isso continua
        valendo): esta é uma operação nova e distinta, que só grava/apaga
        uma entrada em `CategoriaOcultaUsuario`.

        Só faz sentido para categoria de sistema - categoria própria do
        usuário já tem `desativar()`/`excluir()` normais para isso."""
        categoria = self._buscar_visivel(categoria_id, usuario_id)
        if categoria.usuario_id is not None:
            raise BusinessRuleError(
                "Esta categoria já é sua - use desativar ou excluir em vez de ocultar."
            )
        if self.categoria_repo.existe_transacao_vinculada_do_usuario(categoria_id, usuario_id):
            raise BusinessRuleError(
                "Você possui transações usando esta categoria e não pode ocultá-la. "
                "Troque a categoria dessas transações antes, ou mantenha-a visível."
            )
        self.categoria_repo.ocultar_para_usuario(categoria_id, usuario_id)

    def reexibir_para_usuario(self, categoria_id: int, usuario_id: int) -> None:
        """Reverte `ocultar_para_usuario` - sempre idempotente, sem
        restrição (reexibir nunca pode falhar por regra de negócio)."""
        self._buscar_visivel(categoria_id, usuario_id)
        self.categoria_repo.reexibir_para_usuario(categoria_id, usuario_id)

    def _anexar_oculta_para_mim(self, categoria: Categoria, usuario_id: int) -> None:
        """`oculta_para_mim` não é uma coluna de `Categoria` (é por-usuário,
        não pode viver na linha compartilhada) - mesmo padrão de
        `Conta.saldo_atual`: computado pelo Service e anexado como atributo
        transiente no objeto ORM antes de `CategoriaRead.model_validate`
        (ver docstring de `app/schemas/categoria.py`). Só verifica para
        categoria de sistema - categoria própria nunca pode estar "oculta"
        (o conceito não existe pra ela)."""
        categoria.oculta_para_mim = (
            categoria.usuario_id is None
            and self.categoria_repo.esta_oculta_para_usuario(categoria.id, usuario_id)
        )

    def _impedir_desativacao_com_subcategoria_ativa(self, categoria_id: int) -> None:
        if self.categoria_repo.existe_subcategoria_ativa(categoria_id):
            raise BusinessRuleError(
                "Não é possível excluir uma categoria que possui subcategorias ativas."
            )

    def _buscar_visivel(self, categoria_id: int, usuario_id: int) -> Categoria:
        """Uma categoria e "visivel" se for do sistema (usuario_id nulo,
        publica pra qualquer usuario autenticado) OU do proprio usuario.
        Categoria privada de OUTRO usuario recebe o mesmo tratamento de
        "nao existe" (NotFoundError) - mesmo raciocinio anti-enumeracao ja
        usado em ContaService/AuthService: nao da pra descobrir, testando
        IDs, quais categorias privadas outros usuarios tem."""
        categoria = self.categoria_repo.get(categoria_id)
        if categoria is None or (categoria.usuario_id is not None and categoria.usuario_id != usuario_id):
            raise NotFoundError("Categoria não encontrada.")
        return categoria

    def _buscar_editavel(self, categoria_id: int, usuario_id: int) -> Categoria:
        """Usado só por `desativar()`/`excluir()` (não mais por
        `atualizar()`, que desde a Tarefa #111 usa `_buscar_visivel` para
        permitir edição de conteúdo em categoria de sistema). Aqui a
        categoria de sistema continua totalmente bloqueada: desativar ou
        excluir uma linha compartilhada por todos os usuários não é a mesma
        operação que editar seu nome/cor/ícone, e nunca foi pedido. Diferente
        do caso "privada de outro usuario" (que deve parecer inexistente,
        404), aqui o usuario ja enxerga a categoria - recusar a escrita com
        um 403 claro e mais correto e menos confuso do que fingir que ela
        nao existe."""
        categoria = self._buscar_visivel(categoria_id, usuario_id)
        if categoria.usuario_id is None:
            raise AcessoNegadoError("Categorias do sistema são somente leitura.")
        return categoria

    def _resolver_pai(self, categoria_pai_id: int, usuario_id: int) -> Categoria:
        """Valida que a categoria pai proposta existe e e utilizavel por
        este usuario (do sistema OU do proprio usuario) - nunca permite
        apontar para uma categoria privada de outro usuario (o que
        vazaria/vincularia dado entre usuarios). Mesmo tratamento
        (NotFoundError) para "nao existe" e "existe mas e privada de outro
        usuario", pelo mesmo motivo anti-enumeracao de sempre."""
        return self._buscar_visivel(categoria_pai_id, usuario_id)

    def _cria_ciclo(self, categoria_id: int, novo_pai_id: int) -> bool:
        """Sobe a cadeia de ancestrais a partir de novo_pai_id; se em algum
        momento encontrar categoria_id, definir esse pai criaria um ciclo
        (categoria_id acabaria sendo ancestral de si mesma)."""
        atual_id: int | None = novo_pai_id
        visitados: set[int] = set()
        while atual_id is not None:
            if atual_id == categoria_id:
                return True
            if atual_id in visitados:
                break  # protecao contra ciclo pre-existente corrompido no banco
            visitados.add(atual_id)
            pai = self.categoria_repo.get(atual_id)
            atual_id = pai.categoria_pai_id if pai is not None else None
        return False
