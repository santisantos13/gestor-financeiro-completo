"""Service de Emprestimo.

Espelha `FinanciamentoService` quase inteiramente - mesmo `ContratoCreditoMixin`,
mesmo cronograma de amortização (delegado a `app/core/amortizacao.py`,
compartilhado com Financiamento em vez de duplicado), mesmo mecanismo de
`saldo_devedor` (armazenado, atualizado transacionalmente em
`pagar_parcela`), mesma ação dedicada de pagamento, mesma composição de
TransacaoService (nunca constrói uma Transacao nem fala com
TransacaoRepository para escrever). Ver
docs/analise-arquitetural-emprestimo.md para o desenho completo e a única
diferença real de domínio.

A diferença: o valor liberado (`valor_liberado`, sempre obrigatório - não
existe "entrada" em empréstimo) SEMPRE entra na conta do usuário no
desembolso - `criar()` sempre gera uma Transacao de RECEITA avulsa (sem
`emprestimo_id`/`numero_parcela`, mesmo raciocínio da entrada de
Financiamento: vincular corromperia a contagem de "parcelas restantes"),
além das parcelas de amortização (DESPESA). O principal do cronograma é o
próprio `valor_liberado` inteiro - não há nada a descontar dele.

Pagamento de parcela é ação dedicada (`pagar_parcela`), nunca um
`PATCH /transacoes/{id}` genérico - `TransacaoService.atualizar` já
bloqueia edição de `status` quando `emprestimo_id` está preenchido (mesmo
guard usado para `financiamento_id`, nenhuma mudança necessária lá).
"""
from decimal import Decimal

from app.core.amortizacao import gerar_cronograma
from app.core.datas import dia_valido, proximo_mes
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Emprestimo, Transacao
from app.models.enums import StatusContratoCredito, TipoTransacao
from app.repositories.emprestimo_repository import EmprestimoRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.schemas.emprestimo import EmprestimoCreate
from app.schemas.transacao import TransacaoCreate
from app.services.transacao_service import TransacaoService


class EmprestimoService:
    def __init__(
        self,
        emprestimo_repo: EmprestimoRepository,
        transacao_repo: TransacaoRepository,
        transacao_service: TransacaoService,
    ) -> None:
        self.emprestimo_repo = emprestimo_repo
        self.transacao_repo = transacao_repo
        self.transacao_service = transacao_service

    def criar(self, dados: EmprestimoCreate, usuario_id: int) -> Emprestimo:
        self._validar_conta_obrigatoria(dados.conta_id)
        self._validar_parcelas_ja_pagas(dados.parcelas_ja_pagas, dados.num_parcelas)
        principal = dados.valor_liberado

        emprestimo = Emprestimo(
            usuario_id=usuario_id,
            descricao=dados.descricao,
            instituicao_financeira=dados.instituicao_financeira,
            numero_contrato=dados.numero_contrato,
            valor_liberado=dados.valor_liberado,
            finalidade=dados.finalidade,
            taxa_juros=dados.taxa_juros,
            sistema_amortizacao=dados.sistema_amortizacao,
            num_parcelas=dados.num_parcelas,
            cet=dados.cet,
            data_inicio=dados.data_inicio,
            saldo_devedor=principal,
            permite_quitacao_antecipada=dados.permite_quitacao_antecipada,
            status=StatusContratoCredito.ATIVO,
            conta_id=dados.conta_id,
            categoria_id=dados.categoria_id,
        )
        emprestimo = self.emprestimo_repo.create(emprestimo)

        # desembolso e SEMPRE gerado (diferente da entrada opcional de
        # Financiamento) - e uma Transacao AVULSA, sem emprestimo_id/
        # numero_parcela, mesmo raciocinio ja usado para a entrada de
        # Financiamento. Ver docs/analise-arquitetural-emprestimo.md.
        self._gerar_transacao_de_desembolso(emprestimo, usuario_id)

        self._gerar_parcelas(emprestimo, principal, usuario_id)

        # Etapa de Onboarding: mesmo raciocínio de `FinanciamentoService.criar`
        # - reaproveita `pagar_parcela` em loop, nunca duplica o decremento
        # de `saldo_devedor`/transição para QUITADO. Depois de pagar, marca
        # a parcela como `importada=True` (dinheiro que já tinha saído
        # ANTES do usuário usar o app) para nunca entrar em
        # `ContaRepository.somar_transacoes_pagas` - ver docstring espelhada
        # em `FinanciamentoService.criar`.
        for numero_parcela in range(1, dados.parcelas_ja_pagas + 1):
            emprestimo = self.pagar_parcela(emprestimo.id, numero_parcela, usuario_id)
            parcela = self._buscar_parcela(emprestimo, numero_parcela, usuario_id)
            parcela.importada = True
            self.transacao_repo.update(parcela)

        return emprestimo

    def obter(self, emprestimo_id: int, usuario_id: int) -> Emprestimo:
        return self._buscar_da_propriedade_do_usuario(emprestimo_id, usuario_id)

    def excluir(self, emprestimo_id: int, usuario_id: int) -> None:
        """Espelha `FinanciamentoService.excluir` - exclusão sempre
        permitida, com o mesmo achado real: `ondelete=SET NULL` sozinho não
        basta (zera só `emprestimo_id`, deixando `numero_parcela` órfão e
        violando `ck_transacao_numero_parcela_condiz_com_contrato`), então o
        desvínculo de `emprestimo_id`+`numero_parcela` é feito aqui
        explicitamente antes de excluir o contrato. O desembolso (Transacao
        avulsa, sem `emprestimo_id`/`numero_parcela`) nunca precisa disso."""
        emprestimo = self._buscar_da_propriedade_do_usuario(emprestimo_id, usuario_id)
        parcelas = self.transacao_repo.listar_do_usuario(
            usuario_id, emprestimo_id=emprestimo_id, limit=emprestimo.num_parcelas + 1
        )
        for parcela in parcelas:
            parcela.emprestimo_id = None
            parcela.numero_parcela = None
            self.transacao_repo.update(parcela)
        self.emprestimo_repo.delete(emprestimo)

    def listar(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Emprestimo]:
        return list(
            self.emprestimo_repo.listar_do_usuario(
                usuario_id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
            )
        )

    def pagar_parcela(self, emprestimo_id: int, numero_parcela: int, usuario_id: int) -> Emprestimo:
        """Única forma permitida de pagar uma parcela de empréstimo.
        Recalcula a decomposição juros/amortização daquele número de
        parcela a partir do cronograma determinístico, transiciona a
        Transacao correspondente para PAGO através de
        `TransacaoService.marcar_parcela_de_contrato_paga` (idempotente),
        decrementa `saldo_devedor` pela amortização daquela parcela, e
        transiciona o contrato para QUITADO quando a última parcela é
        paga."""
        emprestimo = self._buscar_da_propriedade_do_usuario(emprestimo_id, usuario_id)
        if not (1 <= numero_parcela <= emprestimo.num_parcelas):
            raise BusinessRuleError(
                f"numero_parcela deve estar entre 1 e {emprestimo.num_parcelas} para este empréstimo."
            )

        parcela = self._buscar_parcela(emprestimo, numero_parcela, usuario_id)

        cronograma = gerar_cronograma(
            emprestimo.valor_liberado, emprestimo.taxa_juros, emprestimo.num_parcelas, emprestimo.sistema_amortizacao
        )
        _valor_parcela, amortizacao = cronograma[numero_parcela - 1]

        self.transacao_service.marcar_parcela_de_contrato_paga(parcela.id, usuario_id)

        emprestimo.saldo_devedor = max(emprestimo.saldo_devedor - amortizacao, Decimal("0.00"))
        if numero_parcela == emprestimo.num_parcelas or emprestimo.saldo_devedor == Decimal("0.00"):
            emprestimo.status = StatusContratoCredito.QUITADO
        return self.emprestimo_repo.update(emprestimo)

    # --- geração de parcelas e desembolso (eager, na criação) -------------------

    def _gerar_parcelas(self, emprestimo: Emprestimo, principal: Decimal, usuario_id: int) -> None:
        cronograma = gerar_cronograma(
            principal, emprestimo.taxa_juros, emprestimo.num_parcelas, emprestimo.sistema_amortizacao
        )
        ano, mes = emprestimo.data_inicio.year, emprestimo.data_inicio.month

        for indice, (valor_parcela, _amortizacao) in enumerate(cronograma):
            if indice == 0:
                data_parcela = emprestimo.data_inicio
            else:
                ano, mes = proximo_mes(ano, mes)
                data_parcela = dia_valido(ano, mes, emprestimo.data_inicio.day)

            dados_transacao = TransacaoCreate(
                tipo=TipoTransacao.DESPESA,
                valor=valor_parcela,
                data=data_parcela,
                descricao=f"{emprestimo.descricao} ({indice + 1}/{emprestimo.num_parcelas})",
                categoria_id=emprestimo.categoria_id,
                conta_id=emprestimo.conta_id,
                emprestimo_id=emprestimo.id,
                numero_parcela=indice + 1,
            )
            self.transacao_service.criar(dados_transacao, usuario_id)

    def _gerar_transacao_de_desembolso(self, emprestimo: Emprestimo, usuario_id: int) -> None:
        dados_transacao = TransacaoCreate(
            tipo=TipoTransacao.RECEITA,
            valor=emprestimo.valor_liberado,
            data=emprestimo.data_inicio,
            descricao=f"Desembolso - {emprestimo.descricao}",
            categoria_id=emprestimo.categoria_id,
            conta_id=emprestimo.conta_id,
        )
        self.transacao_service.criar(dados_transacao, usuario_id)

    # --- validações estruturais --------------------------------------------------

    @staticmethod
    def _validar_conta_obrigatoria(conta_id: int | None) -> None:
        """`ContratoCreditoMixin.conta_id` é `nullable=True` no banco
        (compartilhado com Financiamento), mas um Empréstimo sem conta é
        estruturalmente inútil aqui - é de onde o desembolso entra e de
        onde as parcelas saem. Validado no Service em vez do banco, mesma
        decisão já aplicada a Financiamento - ver
        docs/analise-arquitetural-emprestimo.md."""
        if conta_id is None:
            raise BusinessRuleError(
                "conta_id é obrigatório para um empréstimo - é para onde o valor liberado entra e de "
                "onde as parcelas são debitadas."
            )

    @staticmethod
    def _validar_parcelas_ja_pagas(parcelas_ja_pagas: int, num_parcelas: int) -> None:
        if parcelas_ja_pagas > num_parcelas:
            raise BusinessRuleError(
                f"parcelas_ja_pagas não pode ser maior que num_parcelas ({num_parcelas})."
            )

    def _buscar_parcela(self, emprestimo: Emprestimo, numero_parcela: int, usuario_id: int) -> Transacao:
        parcelas = self.transacao_repo.listar_do_usuario(
            usuario_id, emprestimo_id=emprestimo.id, limit=emprestimo.num_parcelas + 1
        )
        for parcela in parcelas:
            if parcela.numero_parcela == numero_parcela:
                return parcela
        raise NotFoundError(f"Parcela {numero_parcela} não encontrada para este empréstimo.")

    def _buscar_da_propriedade_do_usuario(self, emprestimo_id: int, usuario_id: int) -> Emprestimo:
        emprestimo = self.emprestimo_repo.get(emprestimo_id)
        if emprestimo is None or emprestimo.usuario_id != usuario_id:
            raise NotFoundError("Empréstimo não encontrado.")
        return emprestimo
