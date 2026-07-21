"""Service de Financiamento.

Regra de negócio central: dado um contrato de crédito tradicional (valor
financiado, taxa de juros mensal, sistema de amortização PRICE ou SAC,
número de parcelas), gerar o cronograma de amortização e CADA parcela como
uma Transacao real, no momento da criação (eager, mesmo raciocínio já
usado em ParcelamentoService - todas as datas/valores são determinísticos
de imediato). Ver docs/analise-arquitetural-financiamento.md para o
desenho completo.

Este Service NUNCA constrói uma Transacao nem fala com TransacaoRepository
para escrever - toda parcela nasce (`criar`) e é paga (`pagar_parcela`)
através de TransacaoService, reaproveitando de graça toda a validação que
já existe lá (posse/ativo de Conta, compatibilidade de categoria,
estrutura, e agora também posse/faixa/duplicidade de `numero_parcela` via
`_validar_financiamento`). A única coisa que TransacaoService
estruturalmente não pode saber - porque opera numa transação por vez - é
como decompor um contrato de crédito num cronograma de amortização
PRICE/SAC, e é só isso que mora aqui.

`saldo_devedor` é a exceção já documentada ao princípio "calculado, nunca
armazenado" deste projeto (ver docstring de `ContratoCreditoMixin`) - é
atualizado transacionalmente aqui, dentro de `pagar_parcela`, nunca em
`criar` (na criação ele começa igual ao principal financiado, nenhuma
parcela foi paga ainda).

Pagamento de parcela é ação dedicada (`pagar_parcela`), nunca um
`PATCH /transacoes/{id}` genérico - `TransacaoService.atualizar` bloqueia
edição de `status` quando `financiamento_id`/`emprestimo_id` está
preenchido, justamente para `saldo_devedor` nunca desincronizar de uma
parcela marcada paga por fora deste Service (Conflito 1 de
docs/analise-arquitetural-financiamento.md).
"""
from decimal import Decimal

from app.core.amortizacao import gerar_cronograma
from app.core.datas import dia_valido, proximo_mes
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Financiamento, Transacao
from app.models.enums import SistemaAmortizacao, StatusContratoCredito, TipoTransacao
from app.repositories.financiamento_repository import FinanciamentoRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.schemas.financiamento import FinanciamentoCreate
from app.schemas.transacao import TransacaoCreate
from app.services.transacao_service import TransacaoService


class FinanciamentoService:
    def __init__(
        self,
        financiamento_repo: FinanciamentoRepository,
        transacao_repo: TransacaoRepository,
        transacao_service: TransacaoService,
    ) -> None:
        self.financiamento_repo = financiamento_repo
        self.transacao_repo = transacao_repo
        self.transacao_service = transacao_service

    def criar(self, dados: FinanciamentoCreate, usuario_id: int) -> Financiamento:
        self._validar_conta_obrigatoria(dados.conta_id)
        principal = self._validar_principal(dados.valor_financiado, dados.valor_entrada)
        self._validar_parcelas_ja_pagas(dados.parcelas_ja_pagas, dados.num_parcelas)

        financiamento = Financiamento(
            usuario_id=usuario_id,
            descricao=dados.descricao,
            instituicao_financeira=dados.instituicao_financeira,
            numero_contrato=dados.numero_contrato,
            valor_financiado=dados.valor_financiado,
            valor_entrada=dados.valor_entrada,
            bem_financiado=dados.bem_financiado,
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
        financiamento = self.financiamento_repo.create(financiamento)

        # entrada (se houver) e uma Transacao AVULSA, sem financiamento_id/
        # numero_parcela - se carregasse financiamento_id corromperia a
        # conta "parcelas restantes = num_parcelas - pagas" que a Central
        # Financeira ja espera. Ver docs/analise-arquitetural-financiamento.md.
        if dados.valor_entrada is not None:
            self._gerar_transacao_de_entrada(financiamento, usuario_id)

        self._gerar_parcelas(financiamento, principal, usuario_id)

        # Etapa de Onboarding: "importa" o progresso de um contrato que já
        # existia antes do usuário usar o app, chamando `pagar_parcela` uma
        # vez por parcela já paga (1, 2, 3, ... em ordem) - reaproveita
        # 100% do mesmo caminho usado por um pagamento feito manualmente
        # pela UI depois da criação, então `saldo_devedor`/status QUITADO
        # nunca podem desincronizar por causa de um caminho alternativo
        # aqui. `financiamento` é reatribuído a cada chamada porque
        # `pagar_parcela` retorna a instância já atualizada.
        #
        # Depois de pagar, marca a parcela como `importada=True`: ela
        # representa dinheiro que já tinha saído da vida financeira do
        # usuário ANTES dele começar a usar o app - por isso nunca deve
        # entrar em `ContaRepository.somar_transacoes_pagas` (ver docstring
        # lá). Instrução explícita do usuário: "deixe por conta do usuário
        # decidir se ele tá com saldo negativo ou não, evite deduções com
        # base em informações resgatadas do passado financeiro antes do uso
        # do app". Isso não afeta `saldo_devedor` do contrato nem as
        # métricas de progresso (parcelas pagas/total pago) - só o saldo
        # da Conta.
        for numero_parcela in range(1, dados.parcelas_ja_pagas + 1):
            financiamento = self.pagar_parcela(financiamento.id, numero_parcela, usuario_id)
            parcela = self._buscar_parcela(financiamento, numero_parcela, usuario_id)
            parcela.importada = True
            self.transacao_repo.update(parcela)

        return financiamento

    def obter(self, financiamento_id: int, usuario_id: int) -> Financiamento:
        return self._buscar_da_propriedade_do_usuario(financiamento_id, usuario_id)

    def excluir(self, financiamento_id: int, usuario_id: int) -> None:
        """Exclusão sempre permitida (decisão do usuário ao investigar esta
        tarefa): diferente de Fatura, Financiamento gera TODAS as N
        parcelas (Transacao) de uma vez já na criação - a regra "só exclui
        sem nenhuma transação vinculada" nunca seria satisfeita aqui, então
        não faz sentido reaproveitá-la. As parcelas (pagas ou não) NÃO são
        apagadas, só perdem o vínculo e viram despesas avulsas comuns,
        preservando o histórico de saldo da conta sem mais rastreio de qual
        contrato as gerou.

        Achado real ao implementar: `Transacao.financiamento_id` tem
        `ondelete=SET NULL` no banco, mas isso sozinho NÃO bastava -
        `ck_transacao_numero_parcela_condiz_com_contrato` exige que
        `numero_parcela` só exista SE `financiamento_id` (ou
        parcelamento_id/emprestimo_id) também existir; o cascade do banco
        zera só `financiamento_id`, deixando `numero_parcela` órfão e
        violando a CHECK. Por isso o desvínculo é feito aqui explicitamente,
        nos dois campos ao mesmo tempo, ANTES de excluir o contrato - o
        `ondelete=SET NULL` do banco vira só uma rede de segurança redundante
        para esses mesmos registros, nunca a única linha de defesa."""
        financiamento = self._buscar_da_propriedade_do_usuario(financiamento_id, usuario_id)
        parcelas = self.transacao_repo.listar_do_usuario(
            usuario_id, financiamento_id=financiamento_id, limit=financiamento.num_parcelas + 1
        )
        for parcela in parcelas:
            parcela.financiamento_id = None
            parcela.numero_parcela = None
            self.transacao_repo.update(parcela)
        self.financiamento_repo.delete(financiamento)

    def listar(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Financiamento]:
        return list(
            self.financiamento_repo.listar_do_usuario(
                usuario_id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
            )
        )

    def pagar_parcela(self, financiamento_id: int, numero_parcela: int, usuario_id: int) -> Financiamento:
        """Única forma permitida de pagar uma parcela de financiamento.
        Recalcula a decomposição juros/amortização daquele número de
        parcela a partir do cronograma determinístico (função pura dos
        campos do contrato - nenhuma coluna nova precisa existir),
        transiciona a Transacao correspondente para PAGO através de
        `TransacaoService.marcar_parcela_de_contrato_paga` (idempotente -
        levanta erro se a parcela já estava paga, evitando decrementar
        `saldo_devedor` duas vezes), decrementa `saldo_devedor` pela
        amortização daquela parcela, e transiciona o contrato para QUITADO
        quando a última parcela é paga."""
        financiamento = self._buscar_da_propriedade_do_usuario(financiamento_id, usuario_id)
        if not (1 <= numero_parcela <= financiamento.num_parcelas):
            raise BusinessRuleError(
                f"numero_parcela deve estar entre 1 e {financiamento.num_parcelas} para este financiamento."
            )

        parcela = self._buscar_parcela(financiamento, numero_parcela, usuario_id)

        principal = financiamento.valor_financiado - (financiamento.valor_entrada or Decimal("0"))
        cronograma = self._gerar_cronograma(
            principal, financiamento.taxa_juros, financiamento.num_parcelas, financiamento.sistema_amortizacao
        )
        _valor_parcela, amortizacao = cronograma[numero_parcela - 1]

        self.transacao_service.marcar_parcela_de_contrato_paga(parcela.id, usuario_id)

        financiamento.saldo_devedor = max(financiamento.saldo_devedor - amortizacao, Decimal("0.00"))
        if numero_parcela == financiamento.num_parcelas or financiamento.saldo_devedor == Decimal("0.00"):
            financiamento.status = StatusContratoCredito.QUITADO
        return self.financiamento_repo.update(financiamento)

    # --- geração de parcelas (eager, na criação) --------------------------------

    def _gerar_parcelas(self, financiamento: Financiamento, principal: Decimal, usuario_id: int) -> None:
        cronograma = self._gerar_cronograma(
            principal, financiamento.taxa_juros, financiamento.num_parcelas, financiamento.sistema_amortizacao
        )
        ano, mes = financiamento.data_inicio.year, financiamento.data_inicio.month

        for indice, (valor_parcela, _amortizacao) in enumerate(cronograma):
            if indice == 0:
                # parcela 1/N vence no proprio mes da contratacao - mesma
                # convencao ja usada por ParcelamentoService.
                data_parcela = financiamento.data_inicio
            else:
                ano, mes = proximo_mes(ano, mes)
                data_parcela = dia_valido(ano, mes, financiamento.data_inicio.day)

            dados_transacao = TransacaoCreate(
                tipo=TipoTransacao.DESPESA,
                valor=valor_parcela,
                data=data_parcela,
                descricao=f"{financiamento.descricao} ({indice + 1}/{financiamento.num_parcelas})",
                categoria_id=financiamento.categoria_id,
                conta_id=financiamento.conta_id,
                financiamento_id=financiamento.id,
                numero_parcela=indice + 1,
            )
            self.transacao_service.criar(dados_transacao, usuario_id)

    def _gerar_transacao_de_entrada(self, financiamento: Financiamento, usuario_id: int) -> None:
        dados_transacao = TransacaoCreate(
            tipo=TipoTransacao.DESPESA,
            valor=financiamento.valor_entrada,
            data=financiamento.data_inicio,
            descricao=f"Entrada - {financiamento.descricao}",
            categoria_id=financiamento.categoria_id,
            conta_id=financiamento.conta_id,
        )
        self.transacao_service.criar(dados_transacao, usuario_id)

    # --- cronograma de amortização: função pura, sem estado --------------------

    @staticmethod
    def _gerar_cronograma(
        principal: Decimal, taxa_juros: Decimal, num_parcelas: int, sistema: SistemaAmortizacao
    ) -> list[tuple[Decimal, Decimal]]:
        """Delega para `app/core/amortizacao.py` (extraído durante a
        implementação de Emprestimo para as duas entidades compartilharem
        a mesma matemática PRICE/SAC em vez de duplicá-la - ver
        docs/analise-arquitetural-emprestimo.md). Mantido como staticmethod
        aqui só para preservar a assinatura já usada pelos testes
        existentes (`FinanciamentoService._gerar_cronograma(...)`)."""
        return gerar_cronograma(principal, taxa_juros, num_parcelas, sistema)

    # --- validações estruturais --------------------------------------------------

    @staticmethod
    def _validar_conta_obrigatoria(conta_id: int | None) -> None:
        """`ContratoCreditoMixin.conta_id` é `nullable=True` no banco (por
        ser compartilhado com Empréstimo, que ainda não teve sua própria
        análise arquitetural), mas um Financiamento sem conta é
        estruturalmente inútil aqui - nenhuma parcela pode ser gerada
        sem uma conta de origem (`Transacao` exige `conta_id XOR
        cartao_id`, e um financiamento nunca é pago no cartão). Validado
        no Service em vez do banco por decisão explícita - ver Conflito 2
        de docs/analise-arquitetural-financiamento.md."""
        if conta_id is None:
            raise BusinessRuleError(
                "conta_id é obrigatório para um financiamento - é de onde as parcelas são debitadas."
            )

    @staticmethod
    def _validar_principal(valor_financiado: Decimal, valor_entrada: Decimal | None) -> Decimal:
        principal = valor_financiado - (valor_entrada or Decimal("0"))
        if principal <= 0:
            raise BusinessRuleError("valor_entrada não pode ser maior ou igual a valor_financiado.")
        return principal

    @staticmethod
    def _validar_parcelas_ja_pagas(parcelas_ja_pagas: int, num_parcelas: int) -> None:
        if parcelas_ja_pagas > num_parcelas:
            raise BusinessRuleError(
                f"parcelas_ja_pagas não pode ser maior que num_parcelas ({num_parcelas})."
            )

    def _buscar_parcela(self, financiamento: Financiamento, numero_parcela: int, usuario_id: int) -> Transacao:
        parcelas = self.transacao_repo.listar_do_usuario(
            usuario_id, financiamento_id=financiamento.id, limit=financiamento.num_parcelas + 1
        )
        for parcela in parcelas:
            if parcela.numero_parcela == numero_parcela:
                return parcela
        raise NotFoundError(f"Parcela {numero_parcela} não encontrada para este financiamento.")

    def _buscar_da_propriedade_do_usuario(self, financiamento_id: int, usuario_id: int) -> Financiamento:
        financiamento = self.financiamento_repo.get(financiamento_id)
        if financiamento is None or financiamento.usuario_id != usuario_id:
            raise NotFoundError("Financiamento não encontrado.")
        return financiamento
