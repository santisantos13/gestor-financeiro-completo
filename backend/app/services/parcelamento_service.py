"""Service de Parcelamento.

Regra de negócio central: dividir `valor_total` em N parcelas datadas e
GERAR cada uma delas como uma Transacao real, no momento da criação
(eager, não lazy - todas as datas/valores já são determinísticos de
imediato, diferente da resolução lazy de Fatura). Ver
docs/analise-arquitetural-parcelamento.md para o desenho completo.

Este Service NUNCA constrói uma Transacao nem fala com TransacaoRepository
para escrever - toda parcela nasce (`criar`) e morre (`cancelar`) através
de `TransacaoService`, reaproveitando de graça toda a validação que já
existe lá (posse/ativo de Conta ou Cartão, resolução de fatura,
compatibilidade de categoria, estrutura). A única coisa que
`TransacaoService` estruturalmente não pode saber - porque opera numa
transação por vez - é como dividir um valor total em N parcelas datadas, e
é só isso que mora aqui.

`ParcelamentoCreate.valor_parcela` (opcional, Pydantic-only, sem coluna
nova): quando o usuário já sabe o valor real cobrado por parcela (ex:
compra parcelada com juros embutidos pela loja/operadora, onde a parcela
não é `valor_total / num_parcelas`), esse valor é usado diretamente para
TODAS as N parcelas em vez do sistema calcular a divisão - ver
`_gerar_parcelas`.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.core.datas import dia_valido, proximo_mes
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Parcelamento
from app.models.enums import TipoTransacao
from app.repositories.parcelamento_repository import ParcelamentoRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.schemas.parcelamento import ParcelamentoCreate
from app.schemas.transacao import TransacaoCreate
from app.services.transacao_service import TransacaoService


class ParcelamentoService:
    def __init__(
        self,
        parcelamento_repo: ParcelamentoRepository,
        transacao_repo: TransacaoRepository,
        transacao_service: TransacaoService,
    ) -> None:
        self.parcelamento_repo = parcelamento_repo
        self.transacao_repo = transacao_repo
        self.transacao_service = transacao_service

    def criar(self, dados: ParcelamentoCreate, usuario_id: int) -> Parcelamento:
        self._validar_estrutura(dados.cartao_id, dados.conta_id)

        parcelamento = Parcelamento(
            usuario_id=usuario_id,
            descricao=dados.descricao,
            valor_total=dados.valor_total,
            num_parcelas=dados.num_parcelas,
            taxa_juros=dados.taxa_juros,
            data_inicio=dados.data_inicio,
            categoria_id=dados.categoria_id,
            cartao_id=dados.cartao_id,
            conta_id=dados.conta_id,
            ativo=True,
        )
        parcelamento = self.parcelamento_repo.create(parcelamento)

        self._gerar_parcelas(parcelamento, usuario_id, dados.valor_parcela)
        return parcelamento

    def obter(self, parcelamento_id: int, usuario_id: int) -> Parcelamento:
        return self._buscar_da_propriedade_do_usuario(parcelamento_id, usuario_id)

    def listar(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Parcelamento]:
        return list(
            self.parcelamento_repo.listar_do_usuario(
                usuario_id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
            )
        )

    def cancelar(self, parcelamento_id: int, usuario_id: int) -> Parcelamento:
        """Cancelamento é PARCIAL, por design: marca o cabeçalho
        `ativo=False` e remove só as parcelas ainda não travadas - nunca
        reescreve histórico. Diferente do "tudo ou nada" de
        `FaturaService.excluir`, porque um Parcelamento naturalmente
        acumula histórico ao longo de vários ciclos (algumas parcelas já
        pagas, outras ainda por vir) - "cancelar o que falta" é a única
        semântica que faz sentido aqui.

        Delega o loop de verdade para `TransacaoService.cancelar_parcelas_
        do_parcelamento` (bug real corrigido em 2026-07-20: excluir uma
        parcela pelo endpoint genérico de Transação também precisa cancelar
        o parcelamento inteiro, não só aquela linha - ver docstring de
        `TransacaoService.excluir`). Ter as duas entradas (esta ação
        dedicada E o delete genérico de uma parcela) chamando o MESMO
        método evita duas implementações divergentes do mesmo
        "cancelar o que falta"."""
        parcelamento = self._buscar_da_propriedade_do_usuario(parcelamento_id, usuario_id)
        if not parcelamento.ativo:
            raise BusinessRuleError("Este parcelamento já está cancelado.")

        self.transacao_service.cancelar_parcelas_do_parcelamento(parcelamento_id, usuario_id)
        return self._buscar_da_propriedade_do_usuario(parcelamento_id, usuario_id)

    def _gerar_parcelas(
        self, parcelamento: Parcelamento, usuario_id: int, valor_parcela: Decimal | None = None
    ) -> None:
        """Uma chamada a `TransacaoService.criar()` por parcela, todas na
        mesma sessão de request - se uma falhar no meio (ex: cartão
        inativo, categoria incompatível), a Unit of Work implícita do
        projeto (commit só no fim de `get_db()`) já garante rollback
        atômico de tudo, sem tratamento especial de erro parcial aqui.

        `valor_parcela` (opcional, vindo de `ParcelamentoCreate.valor_parcela`)
        despacha para `_valores_fixos` em vez de `_dividir_valor` - todas as
        N parcelas nascem com o MESMO valor informado (sem a última
        absorver resto), porque aqui o valor de cada parcela já é um dado
        conhecido e fixo (ex: juros embutidos pela loja/operadora), não algo
        para o sistema calcular dividindo `valor_total`."""
        valores = (
            [valor_parcela] * parcelamento.num_parcelas
            if valor_parcela is not None
            else self._dividir_valor(parcelamento.valor_total, parcelamento.num_parcelas)
        )
        ano, mes = parcelamento.data_inicio.year, parcelamento.data_inicio.month

        for indice, valor_parcela in enumerate(valores):
            if indice == 0:
                # parcela 1/N acontece na própria data da compra.
                data_parcela = parcelamento.data_inicio
            else:
                ano, mes = proximo_mes(ano, mes)
                data_parcela = dia_valido(ano, mes, parcelamento.data_inicio.day)

            dados_transacao = TransacaoCreate(
                tipo=TipoTransacao.DESPESA,
                valor=valor_parcela,
                data=data_parcela,
                descricao=f"{parcelamento.descricao} ({indice + 1}/{parcelamento.num_parcelas})",
                categoria_id=parcelamento.categoria_id,
                conta_id=parcelamento.conta_id,
                cartao_id=parcelamento.cartao_id,
                parcelamento_id=parcelamento.id,
                numero_parcela=indice + 1,
            )
            self.transacao_service.criar(dados_transacao, usuario_id)

    @staticmethod
    def _dividir_valor(valor_total: Decimal, num_parcelas: int) -> list[Decimal]:
        """Divide `valor_total` em `num_parcelas` partes de 2 casas
        decimais: as primeiras (N-1) recebem o valor base arredondado; a
        ÚLTIMA absorve o resto - garante que a soma das parcelas bate
        exatamente com `valor_total`, nunca perde nem sobra centavo por
        arredondamento (ver docs/analise-arquitetural-parcelamento.md)."""
        valor_base = (valor_total / num_parcelas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valores = [valor_base] * (num_parcelas - 1)
        valores.append(valor_total - valor_base * (num_parcelas - 1))
        return valores

    @staticmethod
    def _validar_estrutura(cartao_id: int | None, conta_id: int | None) -> None:
        """Mesma família do `ck_parcelamento_cartao_xor_conta` do banco -
        validado aqui antes para devolver um erro de negócio claro em vez
        de um IntegrityError cru, mesmo raciocínio já usado em
        `TransacaoService._validar_estrutura`."""
        if (cartao_id is None) == (conta_id is None):
            raise BusinessRuleError("Informe exatamente um entre cartao_id e conta_id.")

    def _buscar_da_propriedade_do_usuario(self, parcelamento_id: int, usuario_id: int) -> Parcelamento:
        parcelamento = self.parcelamento_repo.get(parcelamento_id)
        if parcelamento is None or parcelamento.usuario_id != usuario_id:
            raise NotFoundError("Parcelamento não encontrado.")
        return parcelamento
