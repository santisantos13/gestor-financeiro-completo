"""Service de Conta.

Toda regra de negócio de Conta mora aqui: cálculo de saldo_atual,
verificação de posse (uma conta só pode ser lida/alterada pelo usuário
dono dela) e a decisão de quando isso vira NotFoundError.

Depende de `TransacaoService`/`TransferenciaService`/`CartaoService`/
`FinanciamentoService`/`EmprestimoService`/`ContaRecorrenteService` (não só
do próprio `ContaRepository`) desde a exclusão em cascata de Conta
(`excluir(..., apagar_vinculos=True)`, ver
docs/analise-arquitetural-exclusao-conta-com-historico.md) - mesmo padrão
"Service depende de Service, nunca acessa Repository de outro domínio
diretamente" já usado em `CartaoService`/`TransacaoService`.
"""
import calendar
from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Conta, Transacao
from app.models.enums import CategoriaMovimentacaoConta, StatusTransacao, TipoEntidadeReferenciavel, TipoTransacao
from app.repositories.conta_repository import ContaRepository
from app.schemas.conta import (
    ContaCreate,
    ContaExtratoResumo,
    ContaExtratoRead,
    ContaResumoMesAtual,
    ContaUpdate,
    MaiorMovimentacaoRead,
    MovimentacaoContaRead,
)
from app.services.cartao_service import CartaoService
from app.services.conta_recorrente_service import ContaRecorrenteService
from app.services.emprestimo_service import EmprestimoService
from app.services.financiamento_service import FinanciamentoService
from app.services.transacao_service import TransacaoService
from app.services.transferencia_service import TransferenciaService

# Alto o suficiente pra cobrir qualquer conta real NUM UNICO MES (mesma
# familia de _LIMITE_TRANSACOES_CALENDARIO em CentralFinanceiraService) -
# usado por ContaService.extrato().
_LIMITE_EXTRATO_MENSAL = 2_000

# Limite alto o suficiente pra cobrir qualquer conta real (mesmo raciocínio
# de "big limit pra loop de limpeza" já usado em
# CartaoService._LIMITE_CASCATA_EXCLUSAO/CentralFinanceiraService).
_LIMITE_CASCATA_EXCLUSAO = 10_000


class ContaService:
    def __init__(
        self,
        conta_repo: ContaRepository,
        transacao_service: TransacaoService,
        transferencia_service: TransferenciaService,
        cartao_service: CartaoService,
        financiamento_service: FinanciamentoService,
        emprestimo_service: EmprestimoService,
        conta_recorrente_service: ContaRecorrenteService,
    ) -> None:
        self.conta_repo = conta_repo
        self.transacao_service = transacao_service
        self.transferencia_service = transferencia_service
        self.cartao_service = cartao_service
        self.financiamento_service = financiamento_service
        self.emprestimo_service = emprestimo_service
        self.conta_recorrente_service = conta_recorrente_service

    def criar(self, dados: ContaCreate, usuario_id: int) -> Conta:
        # ativo=True e passado explicitamente (em vez de depender do default
        # da coluna, que so e aplicado pelo SQLAlchemy durante um flush de
        # verdade) - mesmo motivo documentado em AuthService.registrar:
        # mantem o Service correto mesmo fora do caminho feliz com banco
        # real, ex: testes unitarios com repository falso, que nunca fazem
        # flush.
        conta = Conta(**dados.model_dump(), usuario_id=usuario_id, ativo=True)
        conta = self.conta_repo.create(conta)
        return self._com_saldo(conta)

    def obter(self, conta_id: int, usuario_id: int) -> Conta:
        conta = self._buscar_da_propriedade_do_usuario(conta_id, usuario_id)
        return self._com_saldo(conta)

    def listar(
        self,
        usuario_id: int,
        *,
        apenas_ativas: bool = True,
        apenas_visiveis: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Conta]:
        contas = self.conta_repo.listar_do_usuario(
            usuario_id, apenas_ativas=apenas_ativas, apenas_visiveis=apenas_visiveis, skip=skip, limit=limit
        )
        return [self._com_saldo(conta) for conta in contas]

    def atualizar(self, conta_id: int, dados: ContaUpdate, usuario_id: int) -> Conta:
        conta = self._buscar_da_propriedade_do_usuario(conta_id, usuario_id)
        # exclude_unset=True: so os campos que o cliente de fato enviou no
        # payload sao alterados (semantica de PATCH) - um campo omitido
        # nunca e sobrescrito com None.
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(conta, campo, valor)
        conta = self.conta_repo.update(conta)
        return self._com_saldo(conta)

    def desativar(self, conta_id: int, usuario_id: int) -> None:
        """"Exclui" uma conta sem apagar a linha do banco: so marca
        ativo=False. Transacao.conta_id tem ondelete=CASCADE - um DELETE
        de verdade apagaria junto todo o historico financeiro ligado a
        essa conta, o que nao e o comportamento esperado de um sistema
        financeiro (o usuario pode ter fechado a conta no banco, mas o
        historico de gastos continua relevante)."""
        conta = self._buscar_da_propriedade_do_usuario(conta_id, usuario_id)
        conta.ativo = False
        self.conta_repo.update(conta)

    def excluir(self, conta_id: int, usuario_id: int, apagar_vinculos: bool = False) -> None:
        """Exclusão DEFINITIVA (hard delete) - Etapa F10,
        `docs/analise-arquitetural-exclusao.md`, seção 1: uma AÇÃO NOVA,
        nunca substitui `desativar()` acima. Bloqueia se houver qualquer
        vínculo real (mesmo inativo/cancelado) - decisão deliberadamente
        NÃO estendida para `desativar()` nesta etapa (fora do pedido
        original).

        Conta oculta (o "cofrinho" automático de uma Meta) SEMPRE bloqueia,
        independente de `apagar_vinculos` - a relação aqui é invertida (a
        Meta é dona da Conta, nunca o contrário); apagar o cofrinho por
        aqui corromperia o estado da Meta. `MetaService.excluir` já tem seu
        próprio fluxo para decidir o destino correto do cofrinho.

        `apagar_vinculos=True` (pedido explícito do usuário, ver
        docs/analise-arquitetural-exclusao-conta-com-historico.md): em vez
        de bloquear, apaga tudo que está vinculado a esta conta antes de
        apagar a conta - ver `_apagar_vinculos` para o detalhe da cascata.
        Default `False` preserva o comportamento original."""
        conta = self._buscar_da_propriedade_do_usuario(conta_id, usuario_id)
        if conta.oculta:
            raise BusinessRuleError(
                "Esta conta é o cofrinho de uma Meta e não pode ser excluída diretamente. "
                "Exclua a Meta em vez disso."
            )
        if self.conta_repo.existe_vinculo(conta_id):
            if not apagar_vinculos:
                raise BusinessRuleError(
                    "Esta conta possui transações, transferências, cartões ou contratos vinculados e não "
                    "pode ser excluída definitivamente. Desative-a em vez disso, ou confirme a exclusão "
                    "junto com todo o histórico vinculado."
                )
            self._apagar_vinculos(conta_id, usuario_id)
        self.conta_repo.delete(conta)

    def _apagar_vinculos(self, conta_id: int, usuario_id: int) -> None:
        """Cascata explícita (Python, não `ondelete` do banco - este
        projeto nunca liga `PRAGMA foreign_keys=ON`, ver
        `fatura_repository.py::desvincular_transacoes`), 100% reaproveitando
        Services já existentes:

        1. `FinanciamentoService.excluir()`/`EmprestimoService.excluir()`
           por contrato vinculado a esta conta - já existentes, já
           desvinculam `financiamento_id`/`emprestimo_id`+`numero_parcela`
           de cada parcela antes de apagar o contrato, preservando as
           parcelas como Transacao avulsa (ainda com `conta_id` apontando
           para esta conta - recolhidas no passo 5).
        2. `ContaRecorrenteService.excluir()` por template vinculado a esta
           conta - método novo (não existia hard delete nenhum para este
           model), sempre permitido.
        3. `CartaoService.excluir(..., apagar_transacoes=True)` por cartão
           cuja conta de pagamento é esta conta - reaproveita a cascata
           inteira já implementada para Cartão (apaga faturas e transações
           do cartão junto). Não existe "trocar a conta de pagamento de um
           cartão" no sistema.
        4. `TransferenciaService.excluir()` por transferência em que esta
           conta é origem OU destino - método novo (só existia `cancelar`,
           soft delete); `conta_origem_id`/`conta_destino_id` são NOT NULL,
           não há "desvincular".
        5. `TransacaoService.excluir()` por transação desta conta - reúne
           tanto as transações nativas da conta quanto as parcelas de
           Financiamento/Empréstimo que o passo 1 desvinculou. Delega
           automaticamente para `cancelar_parcelas_do_parcelamento` quando a
           transação pertence a um Parcelamento (mesmo comportamento já
           usado na cascata de Cartão) - cobre parcelamento de conta e de
           cartão. `NotFoundError` é ignorado (mesma tolerância a corrida de
           cascata já usada na exclusão de Cartão)."""
        financiamentos = self.financiamento_service.listar(
            usuario_id, apenas_ativos=False, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for financiamento in financiamentos:
            if financiamento.conta_id == conta_id:
                self.financiamento_service.excluir(financiamento.id, usuario_id)

        emprestimos = self.emprestimo_service.listar(
            usuario_id, apenas_ativos=False, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for emprestimo in emprestimos:
            if emprestimo.conta_id == conta_id:
                self.emprestimo_service.excluir(emprestimo.id, usuario_id)

        # `status=None` lista TODAS (ativas, pausadas e encerradas) - a
        # cascata precisa apagar qualquer template vinculado à conta,
        # independente do ciclo de vida (expansão 2026-07-20: `ativo` ->
        # `status`).
        recorrentes = self.conta_recorrente_service.listar(
            usuario_id, status=None, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for recorrente in recorrentes:
            if recorrente.conta_id == conta_id:
                self.conta_recorrente_service.excluir(recorrente.id, usuario_id)

        cartoes = self.cartao_service.listar(
            usuario_id, apenas_ativos=False, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for cartao in cartoes:
            if cartao.conta_pagamento_id == conta_id:
                self.cartao_service.excluir(cartao.id, usuario_id, apagar_transacoes=True)

        transferencias = self.transferencia_service.listar(
            usuario_id, apenas_ativas=False, conta_id=conta_id, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for transferencia in transferencias:
            self.transferencia_service.excluir(transferencia.id, usuario_id)

        transacoes = self.transacao_service.listar(
            usuario_id, conta_id=conta_id, limit=_LIMITE_CASCATA_EXCLUSAO
        )
        for transacao in transacoes:
            try:
                self.transacao_service.excluir(transacao.id, usuario_id)
            except NotFoundError:
                continue

    def _buscar_da_propriedade_do_usuario(self, conta_id: int, usuario_id: int) -> Conta:
        conta = self.conta_repo.get(conta_id)
        if conta is None or conta.usuario_id != usuario_id:
            # Mesmo tratamento para "nao existe" e "existe mas e de outro
            # usuario" - de proposito. Se distinguissemos os dois casos (ex:
            # 404 vs 403), um usuario autenticado poderia descobrir, so
            # testando IDs sequenciais, quantas contas outros usuarios tem e
            # quais IDs sao validos (Broken Object Level Authorization -
            # OWASP API Security Top 10). Mesmo raciocinio ja aplicado em
            # AuthService.autenticar (mensagem identica p/ email inexistente
            # e senha errada).
            raise NotFoundError("Conta não encontrada.")
        return conta

    def _com_saldo(self, conta: Conta) -> Conta:
        """Anexa saldo_atual (calculado, nunca armazenado) ao objeto Conta
        antes de devolve-lo. Atributo transiente: nao e uma coluna mapeada,
        nunca e persistido, existe só para o Router/Schema lerem."""
        liquido_transacoes = self.conta_repo.somar_transacoes_pagas(conta.id)
        liquido_transferencias = self.conta_repo.somar_transferencias(conta.id)
        conta.saldo_atual = conta.saldo_inicial + liquido_transacoes + liquido_transferencias
        return conta

    # --- extrato (histórico expansível, pedido explícito do usuário) --------

    def extrato(
        self, conta_id: int, usuario_id: int, *, ano: int | None = None, mes: int | None = None
    ) -> ContaExtratoRead:
        """Painel "extrato bancário" de uma Conta -
        docs/analise-arquitetural-extrato-conta.md. `ano`/`mes` (opcionais,
        default = mês atual) definem o PERÍODO navegado - `saldo_atual`
        continua sempre o valor real de agora, independente do período.

        Nenhuma soma nova é feita via SQL `SUM`: as mesmas linhas de
        `Transacao`/`Transferencia` do período já são buscadas para montar
        a lista de histórico, e entradas/saídas/saldo líquido/última
        movimentação/maior entrada/maior saída são só aritmética Python
        sobre essa mesma lista (já pequena e limitada - uma conta, um mês -
        mesmo raciocínio de `CentralFinanceiraService.calendario_financeiro`,
        ver docstring do módulo dela e a seção correspondente da análise
        arquitetural deste extrato)."""
        conta = self._com_saldo(self._buscar_da_propriedade_do_usuario(conta_id, usuario_id))

        hoje = date.today()
        ano = ano or hoje.year
        mes = mes or hoje.month
        data_inicio, data_fim = self._limites_do_mes(ano, mes)
        movimentacoes = self._movimentacoes_do_periodo(conta_id, usuario_id, data_inicio, data_fim)

        if (ano, mes) == (hoje.year, hoje.month):
            movimentacoes_mes_atual = movimentacoes
        else:
            data_inicio_mes, data_fim_mes = self._limites_do_mes(hoje.year, hoje.month)
            movimentacoes_mes_atual = self._movimentacoes_do_periodo(
                conta_id, usuario_id, data_inicio_mes, data_fim_mes
            )

        entradas_periodo = self._somar(movimentacoes, positivo=True)
        saidas_periodo = self._somar(movimentacoes, positivo=False)

        resumo = ContaExtratoResumo(
            saldo_atual=conta.saldo_atual,
            saldo_inicial=conta.saldo_inicial,
            entradas_periodo=entradas_periodo,
            saidas_periodo=saidas_periodo,
            saldo_liquido_periodo=entradas_periodo - saidas_periodo,
            ultima_movimentacao=movimentacoes[0].data if movimentacoes else None,
            quantidade_movimentacoes=len(movimentacoes),
        )

        entradas_mes = self._somar(movimentacoes_mes_atual, positivo=True)
        saidas_mes = self._somar(movimentacoes_mes_atual, positivo=False)
        maior_entrada = max(
            (m for m in movimentacoes_mes_atual if m.positivo), key=lambda m: m.valor, default=None
        )
        maior_saida = max(
            (m for m in movimentacoes_mes_atual if not m.positivo), key=lambda m: m.valor, default=None
        )
        resumo_mes_atual = ContaResumoMesAtual(
            entradas_mes=entradas_mes,
            saidas_mes=saidas_mes,
            saldo_mes=entradas_mes - saidas_mes,
            maior_entrada=self._como_maior_movimentacao(maior_entrada),
            maior_saida=self._como_maior_movimentacao(maior_saida),
        )

        return ContaExtratoRead(resumo=resumo, resumo_mes_atual=resumo_mes_atual, movimentacoes=movimentacoes)

    def _movimentacoes_do_periodo(
        self, conta_id: int, usuario_id: int, data_inicio: date, data_fim: date
    ) -> list[MovimentacaoContaRead]:
        """Reaproveita `TransacaoService.listar`/`TransferenciaService.listar`
        (já injetados aqui desde a exclusão em cascata) - nenhum acesso a
        Repository de outro domínio. `conta_id=X` já exclui compra de
        cartão sozinho (sempre `cartao_id` preenchido, nunca `conta_id`) -
        nenhum filtro extra precisou ser escrito para isso."""
        transacoes = self.transacao_service.listar(
            usuario_id,
            conta_id=conta_id,
            status=StatusTransacao.PAGO,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=_LIMITE_EXTRATO_MENSAL,
        )
        transferencias = self.transferencia_service.listar(
            usuario_id,
            conta_id=conta_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=_LIMITE_EXTRATO_MENSAL,
        )

        movimentacoes: list[MovimentacaoContaRead] = []
        for transacao in transacoes:
            if transacao.importada:
                # parcela de Financiamento/Empréstimo do onboarding
                # ("parcelas_ja_pagas") - nunca alterou o saldo desta conta
                # de verdade (mesmo critério de
                # ContaRepository.somar_transacoes_pagas), então não entra
                # no histórico. Ver docstring de Transacao.importada.
                continue
            categoria, positivo = self._categoria_da_transacao(transacao)
            origem_tipo, origem_id = self._origem_da_transacao(transacao)
            movimentacoes.append(
                MovimentacaoContaRead(
                    data=transacao.data,
                    descricao=transacao.descricao,
                    valor=transacao.valor,
                    positivo=positivo,
                    categoria=categoria,
                    origem_tipo=origem_tipo,
                    origem_id=origem_id,
                )
            )
        for transferencia in transferencias:
            recebida = transferencia.conta_destino_id == conta_id
            movimentacoes.append(
                MovimentacaoContaRead(
                    data=transferencia.data,
                    descricao=transferencia.descricao
                    or ("Transferência recebida" if recebida else "Transferência enviada"),
                    valor=transferencia.valor,
                    positivo=recebida,
                    categoria=(
                        CategoriaMovimentacaoConta.TRANSFERENCIA_RECEBIDA
                        if recebida
                        else CategoriaMovimentacaoConta.TRANSFERENCIA_ENVIADA
                    ),
                    origem_tipo=TipoEntidadeReferenciavel.TRANSFERENCIA,
                    origem_id=transferencia.id,
                )
            )

        movimentacoes.sort(key=lambda m: m.data, reverse=True)
        return movimentacoes

    @staticmethod
    def _categoria_da_transacao(transacao: Transacao) -> tuple[CategoriaMovimentacaoConta, bool]:
        if transacao.fatura_paga_id is not None:
            return CategoriaMovimentacaoConta.PAGAMENTO_FATURA, False
        if transacao.financiamento_id is not None:
            return CategoriaMovimentacaoConta.PAGAMENTO_FINANCIAMENTO, False
        if transacao.emprestimo_id is not None:
            return CategoriaMovimentacaoConta.PAGAMENTO_EMPRESTIMO, False
        if transacao.tipo == TipoTransacao.RECEITA:
            return CategoriaMovimentacaoConta.RECEITA, True
        return CategoriaMovimentacaoConta.DESPESA, False

    @staticmethod
    def _origem_da_transacao(transacao: Transacao) -> tuple[TipoEntidadeReferenciavel, int]:
        if transacao.financiamento_id is not None:
            return TipoEntidadeReferenciavel.FINANCIAMENTO, transacao.financiamento_id
        if transacao.emprestimo_id is not None:
            return TipoEntidadeReferenciavel.EMPRESTIMO, transacao.emprestimo_id
        if transacao.fatura_paga_id is not None:
            return TipoEntidadeReferenciavel.FATURA, transacao.fatura_paga_id
        return TipoEntidadeReferenciavel.TRANSACAO, transacao.id

    @staticmethod
    def _somar(movimentacoes: list[MovimentacaoContaRead], *, positivo: bool) -> Decimal:
        # Decimal("0.00"), nao Decimal("0") - mesma casa decimal das colunas
        # Numeric(12,2) do banco, para o schema sempre serializar "0.00" em
        # vez de "0" quando a lista esta vazia (consistencia com todo outro
        # valor monetario da API).
        return sum((m.valor for m in movimentacoes if m.positivo == positivo), Decimal("0.00"))

    @staticmethod
    def _como_maior_movimentacao(movimentacao: MovimentacaoContaRead | None) -> MaiorMovimentacaoRead | None:
        if movimentacao is None:
            return None
        return MaiorMovimentacaoRead(
            data=movimentacao.data, descricao=movimentacao.descricao, valor=movimentacao.valor
        )

    @staticmethod
    def _limites_do_mes(ano: int, mes: int) -> tuple[date, date]:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return date(ano, mes, 1), date(ano, mes, ultimo_dia)
