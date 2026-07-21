"""Service de Cartao.

Regras de negócio concentradas aqui: nome único por usuário (mesma tensão
com soft delete já resolvida em TagService - ver criar()), garantia de que
`conta_pagamento_id` aponta para uma Conta do MESMO usuário (nunca uma FK
sozinha consegue expressar isso), e cálculo de limite_disponivel.

Depende de `FaturaService` (não só do próprio `CartaoRepository`) desde a
correção do bug "limite disponível não volta ao pagar fatura" (2026-07):
`FaturaService.ids_faturas_pagas()` é a única fonte de verdade sobre "o que
conta como pago" - `_com_limite_disponivel` reusa esse cálculo em vez de
duplicar a regra. Também depende de `ParcelamentoService`/
`ContaRecorrenteService` desde a correção do bug "excluir cartão falha com
Falha de conexão com o servidor" (2026-07-21, ver
`_apagar_faturas_e_transacoes`)."""
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Cartao
from app.repositories.cartao_repository import CartaoRepository
from app.repositories.conta_repository import ContaRepository
from app.schemas.cartao import CartaoCreate, CartaoUpdate
from app.services.conta_recorrente_service import ContaRecorrenteService
from app.services.fatura_service import FaturaService
from app.services.parcelamento_service import ParcelamentoService
from app.services.transacao_service import TransacaoService

# Limite alto o suficiente pra cobrir qualquer cartão real (nenhum usuário
# tem centenas de faturas/transações num único cartão) - mesmo raciocínio de
# "big limit pra loop de limpeza" já usado em CentralFinanceiraService.
_LIMITE_CASCATA_EXCLUSAO = 10_000


class CartaoService:
    def __init__(
        self,
        cartao_repo: CartaoRepository,
        conta_repo: ContaRepository,
        fatura_service: FaturaService,
        transacao_service: TransacaoService,
        parcelamento_service: ParcelamentoService,
        conta_recorrente_service: ContaRecorrenteService,
    ) -> None:
        self.cartao_repo = cartao_repo
        self.conta_repo = conta_repo
        self.fatura_service = fatura_service
        self.transacao_service = transacao_service
        self.parcelamento_service = parcelamento_service
        self.conta_recorrente_service = conta_recorrente_service

    def criar(self, dados: CartaoCreate, usuario_id: int) -> Cartao:
        """Cria um cartão novo - ou REATIVA um existente, se o nome colidir
        com um cartão desativado do mesmo usuário. Mesmo raciocínio de
        TagService.criar(): a UniqueConstraint(usuario_id, nome) não
        distingue cartão ativo de desativado, então reativar em vez de
        inserir evita "queimar" o nome permanentemente quando um cartão é
        cancelado (soft delete) e o usuário quer reusar o nome depois."""
        self._validar_conta_do_usuario(dados.conta_pagamento_id, usuario_id)

        existente = self.cartao_repo.buscar_por_nome(usuario_id, dados.nome)
        if existente is not None:
            if existente.ativo:
                raise ConflictError("Já existe um cartão com este nome.")
            # Semântica de CRIAÇÃO, não de "restaurar como estava" - mesmo
            # raciocínio de TagService.criar(): o payload é aplicado por
            # completo (o cartão "novo" pode ter limite, bandeira, últimos
            # dígitos etc. diferentes do cartão antigo que só emprestou o
            # nome), nunca uma mistura implícita do estado antigo com o novo.
            for campo, valor in dados.model_dump().items():
                setattr(existente, campo, valor)
            existente.ativo = True
            cartao = self.cartao_repo.update(existente)
            return self._com_limite_disponivel(cartao)

        # ativo=True explícito - mesmo motivo de Conta/Categoria/TagService.criar:
        # o default da coluna só é aplicado num flush de verdade.
        cartao = Cartao(**dados.model_dump(), usuario_id=usuario_id, ativo=True)
        cartao = self.cartao_repo.create(cartao)
        return self._com_limite_disponivel(cartao)

    def obter(self, cartao_id: int, usuario_id: int) -> Cartao:
        cartao = self._buscar_da_propriedade_do_usuario(cartao_id, usuario_id)
        return self._com_limite_disponivel(cartao)

    def listar(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Cartao]:
        cartoes = self.cartao_repo.listar_do_usuario(
            usuario_id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
        )
        return [self._com_limite_disponivel(cartao) for cartao in cartoes]

    def atualizar(self, cartao_id: int, dados: CartaoUpdate, usuario_id: int) -> Cartao:
        cartao = self._buscar_da_propriedade_do_usuario(cartao_id, usuario_id)
        alteracoes = dados.model_dump(exclude_unset=True)

        if "conta_pagamento_id" in alteracoes:
            self._validar_conta_do_usuario(alteracoes["conta_pagamento_id"], usuario_id)

        novo_nome = alteracoes.get("nome")
        if novo_nome is not None and novo_nome != cartao.nome:
            # Renomear NÃO reativa/mescla com um cartão inativo de mesmo
            # nome - mesma decisão (e mesmo motivo) de TagService.atualizar:
            # fundir identidades implicitamente ao renomear seria arriscado
            # demais para ser automático. Bloqueia com 409, igual a
            # qualquer outra colisão de nome.
            colisao = self.cartao_repo.buscar_por_nome(usuario_id, novo_nome)
            if colisao is not None and colisao.id != cartao.id:
                raise ConflictError("Já existe um cartão com este nome.")

        for campo, valor in alteracoes.items():
            setattr(cartao, campo, valor)
        cartao = self.cartao_repo.update(cartao)
        return self._com_limite_disponivel(cartao)

    def desativar(self, cartao_id: int, usuario_id: int) -> None:
        """"Exclui" um cartão sem apagar a linha - só marca ativo=False,
        mesmo padrão de Conta/Categoria/Tag. Faturas e transações antigas
        do cartão continuam intactas (Fatura.cartao_id não tem soft delete
        em cascata) - só some das listas de novos lançamentos."""
        cartao = self._buscar_da_propriedade_do_usuario(cartao_id, usuario_id)
        cartao.ativo = False
        self.cartao_repo.update(cartao)

    def excluir(self, cartao_id: int, usuario_id: int, apagar_transacoes: bool = False) -> None:
        """Exclusão DEFINITIVA (hard delete) - Etapa F10,
        `docs/analise-arquitetural-exclusao.md`, seção 1: uma AÇÃO NOVA,
        nunca substitui `desativar()` acima. Bloqueia se houver qualquer
        fatura, parcelamento ou recorrência vinculados (seção 2.4 +
        correção 2026-07-21) - decisão deliberadamente NÃO estendida para
        `desativar()` nesta etapa (fora do pedido original).

        `apagar_transacoes=True` (pedido explícito do usuário, ver
        docs/analise-arquitetural-exclusao-cartao-com-historico.md): em vez
        de bloquear, apaga faturas, transações, parcelamentos e
        recorrências deste cartão antes de apagar o cartão - ver
        `_apagar_faturas_e_transacoes` para o detalhe da cascata. Default
        `False` preserva o comportamento original (nunca apaga histórico
        sem confirmação explícita).

        `_possui_vinculo_bloqueante` checa faturas E parcelamentos/
        recorrências (não só faturas, como antes da correção de
        2026-07-21): um cartão pode ter uma compra parcelada ou uma
        recorrência SEM nenhuma Fatura ainda existir (fatura é resolvida/
        criada à parte) - checar só `existe_fatura_vinculada` deixava esses
        dois casos passarem direto para `self.cartao_repo.delete(cartao)`
        sem cascata nem bloqueio nenhum, o que no Postgres de produção
        batia direto no `IntegrityError` da FK de Parcelamento/
        ContaRecorrente (`cartao_id` sem `ondelete`, ao contrário de
        Fatura/Transacao que já têm `ondelete=CASCADE`) - bug relatado
        pelo usuário como "Falha de conexão com o servidor" ao excluir
        cartão."""
        cartao = self._buscar_da_propriedade_do_usuario(cartao_id, usuario_id)
        if self._possui_vinculo_bloqueante(cartao_id, usuario_id):
            if not apagar_transacoes:
                raise BusinessRuleError(
                    "Este cartão possui faturas, compras parceladas ou recorrências vinculadas e não "
                    "pode ser excluído definitivamente. Desative-o em vez disso, ou confirme a exclusão "
                    "junto com o histórico de transações."
                )
            self._apagar_faturas_e_transacoes(cartao_id, usuario_id)
        self.cartao_repo.delete(cartao)

    def _possui_vinculo_bloqueante(self, cartao_id: int, usuario_id: int) -> bool:
        if self.cartao_repo.existe_fatura_vinculada(cartao_id):
            return True
        parcelamentos = self.parcelamento_service.listar(
            usuario_id, apenas_ativos=False, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        if any(parcelamento.cartao_id == cartao_id for parcelamento in parcelamentos):
            return True
        recorrentes = self.conta_recorrente_service.listar(usuario_id, status=None, limit=_LIMITE_CASCATA_EXCLUSAO)
        return any(recorrente.cartao_id == cartao_id for recorrente in recorrentes)

    def _apagar_faturas_e_transacoes(self, cartao_id: int, usuario_id: int) -> None:
        """Cascata explícita (Python, não `ondelete` do banco - este
        projeto nunca liga `PRAGMA foreign_keys=ON`, ver
        `fatura_repository.py::desvincular_transacoes`), 100% reaproveitando
        Services já existentes:

        1. `FaturaService.excluir()` por fatura - já desvincula toda
           transação ligada a ela (compra E pagamento) antes de apagar a
           fatura. A transação de PAGAMENTO (`fatura_paga_id`, sempre uma
           transação de Conta) nunca é apagada aqui, só perde a referência -
           dinheiro real que já saiu do banco não desaparece.
        2. `TransacaoService.excluir()` por transação de COMPRA deste
           cartão (`cartao_id`) - como o passo 1 já zerou `fatura_id` de
           todas elas, a trava de "fatura fechada" nunca dispara. Delega
           automaticamente para `cancelar_parcelas_do_parcelamento` quando a
           transação pertence a um Parcelamento (mesmo método que
           `ParcelamentoService.cancelar()` usa). Uma chamada pode
           cascatear e já remover outras parcelas do mesmo Parcelamento
           antes do loop chegar nelas - `NotFoundError` é ignorado por
           esse motivo.
        3. `ParcelamentoService.excluir()` por parcelamento cujo `cartao_id`
           é este cartão - ao contrário da cascata de Transação/Fatura, o
           cabeçalho do Parcelamento NÃO pode só ficar `ativo=False`:
           `cartao_id`/`conta_id` são XOR e NOT NULL em conjunto
           (`ck_parcelamento_cartao_xor_conta`), não existe "desvincular"
           um Parcelamento do Cartão que está sendo apagado. Bug real
           (relatado pelo usuário, 2026-07-21): esse cabeçalho ficava
           orfão silenciosamente no SQLite (sem `PRAGMA foreign_keys=ON`),
           mas no Postgres de produção a FK é enforced e bloqueava a
           exclusão do cartão com `IntegrityError` não tratado -
           aparecendo no frontend como "Falha de conexão com o servidor".
        4. `ContaRecorrenteService.excluir()` por recorrência cujo
           `cartao_id` é este cartão - mesmo raciocínio do item 3
           (`ck_conta_recorrente_cartao_xor_conta` também é XOR/NOT NULL
           em conjunto)."""
        faturas = self.fatura_service.listar(cartao_id, usuario_id, limit=_LIMITE_CASCATA_EXCLUSAO)
        for fatura in faturas:
            self.fatura_service.excluir(fatura.id, usuario_id)

        transacoes = self.transacao_service.listar(
            usuario_id, cartao_id=cartao_id, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for transacao in transacoes:
            try:
                self.transacao_service.excluir(transacao.id, usuario_id)
            except NotFoundError:
                continue

        # `apenas_ativos=False`/`status=None`: um Parcelamento cancelado ou
        # uma recorrência encerrada continuam com `cartao_id` preenchido -
        # a cascata precisa apagar/desvincular independente do ciclo de
        # vida (mesmo raciocínio já usado para Fatura/Transação acima).
        parcelamentos = self.parcelamento_service.listar(
            usuario_id, apenas_ativos=False, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for parcelamento in parcelamentos:
            if parcelamento.cartao_id == cartao_id:
                self.parcelamento_service.excluir(parcelamento.id, usuario_id)

        recorrentes = self.conta_recorrente_service.listar(
            usuario_id, status=None, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for recorrente in recorrentes:
            if recorrente.cartao_id == cartao_id:
                self.conta_recorrente_service.excluir(recorrente.id, usuario_id)

    def _validar_conta_do_usuario(self, conta_id: int, usuario_id: int) -> None:
        """Garante que `conta_pagamento_id` aponta para uma Conta que
        existe E pertence ao mesmo usuário do cartão - nunca uma conta de
        outro usuário. Mesmo tratamento (404) para "não existe" e "é de
        outro usuário", mesmo raciocínio anti-enumeração já usado em
        CategoriaService._resolver_pai: um usuário não pode descobrir,
        testando IDs, quais contas outros usuários têm."""
        conta = self.conta_repo.get(conta_id)
        if conta is None or conta.usuario_id != usuario_id:
            raise NotFoundError("Conta não encontrada.")

    def _buscar_da_propriedade_do_usuario(self, cartao_id: int, usuario_id: int) -> Cartao:
        cartao = self.cartao_repo.get(cartao_id)
        if cartao is None or cartao.usuario_id != usuario_id:
            # Mesmo tratamento (404) para "não existe" e "é de outro
            # usuário" - mesmo raciocínio anti-enumeração de sempre (BOLA,
            # OWASP API Security Top 10).
            raise NotFoundError("Cartão não encontrado.")
        return cartao

    def _com_limite_disponivel(self, cartao: Cartao) -> Cartao:
        """Anexa limite_disponivel (calculado, nunca armazenado) ao objeto
        Cartao antes de devolvê-lo. Atributo transiente: não é uma coluna
        mapeada, nunca é persistido, existe só para o Router/Schema lerem.
        Pode ficar negativo (cartão estourado) - de propósito, não é
        limitado (clamp) em zero: esconder um estouro real seria menos
        correto do que mostrá-lo.

        `saldo_inicial_utilizado` ("Estado Inicial do Cartão") também
        consome limite permanentemente até o usuário editá-lo - é o valor
        que já estava em uso quando o cartão foi cadastrado no sistema,
        independente de qualquer Fatura/Transacao (ver
        docs/analise-arquitetural-sprint-refinamento-premium.md, seção 1)."""
        ids_faturas_pagas = self.fatura_service.ids_faturas_pagas(cartao.id)
        gastos_nao_pagos = self.cartao_repo.somar_gastos_nao_pagos(cartao.id, ids_faturas_pagas)
        cartao.limite_disponivel = cartao.limite - gastos_nao_pagos - cartao.saldo_inicial_utilizado
        return cartao
