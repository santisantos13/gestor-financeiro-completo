"""Service de Transacao - o registro central do domínio.

Regras de negócio concentradas aqui: validação estrutural (conta XOR
cartão, no máximo um contrato, numero_parcela condizente - mesma família
dos CheckConstraints de `Transacao`, mas validada antes de chegar no banco
para devolver um erro de negócio claro em vez de um IntegrityError cru),
posse cruzada de Conta/Cartão/Categoria/Tag/Parcelamento/Financiamento,
resolução de `fatura_id` via `FaturaService.resolver_fatura_aberta` (nunca
aceito do payload), `status` forçado para transação de cartão OU de
contrato de crédito (ver `StatusTransacao` em app/models/enums.py) e
imutabilidade de transações vinculadas a fatura fechada.
Ver docs/analise-arquitetural-transacao.md para o desenho completo.

`parcelamento_id`, `origem_recorrente_id`, `financiamento_id` e
`emprestimo_id` já tiveram sua lacuna YAGNI original fechada: desde os
CRUDs de Parcelamento, ContaRecorrente, Financiamento e Empréstimo, os
Repositories respectivos existem e são usados aqui para validar posse (e,
no caso de `origem_recorrente_id`, também duplicidade de data; no de
`financiamento_id`/`emprestimo_id`, também faixa/duplicidade de
`numero_parcela`) - ver docs/analise-arquitetural-parcelamento.md,
docs/analise-arquitetural-conta-recorrente.md,
docs/analise-arquitetural-financiamento.md e
docs/analise-arquitetural-emprestimo.md.

`meta_id` NÃO existe mais em `TransacaoCreate`/`TransacaoUpdate`
(Refatoramento de Metas/Transferências: aportes/resgates passaram a ser
`Transferencia`, nunca mais `Transacao` - ver
docs/analise-arquitetural-metas-transferencias.md, seção 6). A coluna e o
`meta_repo` injetado abaixo permanecem só para o histórico legado (Meta
ainda soma `Transacao.meta_id` antigas em `MetaRepository.
somar_transacoes_pagas`) - `meta_repo` deliberadamente NÃO é removido do
construtor para não precisar reordenar os 12 parâmetros posicionais já
usados por `app/api/deps.py` e por 7 arquivos de teste; fica documentado
aqui como não-usado para validação.

`status` de uma transação vinculada a `financiamento_id`/`emprestimo_id`
nunca é editável via criação/PATCH genérico - só nasce PENDENTE e só
transiciona para PAGO através de `marcar_parcela_de_contrato_paga`,
chamada exclusivamente pela ação dedicada de pagamento do próprio
contrato (`FinanciamentoService.pagar_parcela`, futuramente também
`EmprestimoService`). Isso existe para `saldo_devedor` (campo armazenado
em `ContratoCreditoMixin`) nunca desincronizar de uma parcela marcada paga
por fora do Service que sabe decrementá-lo - ver Conflito 1 de
docs/analise-arquitetural-financiamento.md. Mesmo espírito arquitetural já
usado para `cartao_id` (status sempre forçado/travado), aplicado agora
também a contrato de crédito.
"""
import enum
from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Categoria, Cartao, Tag, Transacao
from app.models.enums import StatusFatura, StatusTransacao, TipoCategoria, TipoTransacao
from app.repositories.cartao_repository import CartaoRepository
from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.conta_recorrente_repository import ContaRecorrenteRepository
from app.repositories.conta_repository import ContaRepository
from app.repositories.emprestimo_repository import EmprestimoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.repositories.financiamento_repository import FinanciamentoRepository
from app.repositories.meta_repository import MetaRepository
from app.repositories.parcelamento_repository import ParcelamentoRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.schemas.transacao import TransacaoCreate, TransacaoUpdate
from app.services.fatura_service import FaturaService

# campos cuja alteração é bloqueada numa transação de COMPRA (fatura_id
# preenchido) vinculada a uma fatura que não está mais ABERTA - ver
# docs/analise-arquitetural-fatura.md ("Imutabilidade de transações
# vinculadas a fatura fechada"). cartao_id não entra aqui porque já é
# estruturalmente imutável (nem aparece em TransacaoUpdate).
_CAMPOS_TRAVADOS_EM_FATURA_FECHADA = {"valor", "data", "parcelamento_id"}


class EscopoOperacaoParcela(str, enum.Enum):
    """Escopo de uma operação (hoje só exclusão) sobre uma parcela que
    pertence a um `Parcelamento` - ponto único de decisão "o que fazer com
    as OUTRAS parcelas quando esta é afetada", centralizado aqui em vez de
    espalhado como um `if transacao.parcelamento_id is not None` inline em
    cada método que precisar dessa regra (ver
    docs/analise-arquitetural-escopo-parcelamento.md).

    Interno ao Service - deliberadamente NÃO é um enum de
    `app/models/enums.py` (que reúne vocabulário exposto via schema/API):
    nenhum destes valores é aceito num payload de cliente ainda, e não deve
    virar um até a funcionalidade abaixo ser implementada de verdade
    (YAGNI - ver docstring de `TransacaoService._aplicar_exclusao_de_parcela`).

    - TODO_PARCELAMENTO: único comportamento suportado hoje e sempre usado,
      independente de o cliente pedir ou não - excluir qualquer parcela
      cancela a compra inteira (`cancelar_parcelas_do_parcelamento`).
      Motivo: uma parcela isolada não é uma despesa própria, é 1/N de uma
      única compra - deixar as outras N-1 "penduradas" corrompe o valor
      real da compra em faturas futuras (bug real corrigido em 2026-07-20).
    - ESTA_PARCELA: reservado para uma futura ação "excluir só esta
      parcela" (ex: renegociação, edição avançada) - NÃO implementado.
      Chamar `_aplicar_exclusao_de_parcela` com este valor levanta
      `NotImplementedError` de propósito, em vez de silenciosamente cair
      para outro comportamento - mais seguro do que fingir suporte que
      não existe."""

    ESTA_PARCELA = "ESTA_PARCELA"
    TODO_PARCELAMENTO = "TODO_PARCELAMENTO"


class TransacaoService:
    def __init__(
        self,
        transacao_repo: TransacaoRepository,
        conta_repo: ContaRepository,
        cartao_repo: CartaoRepository,
        categoria_repo: CategoriaRepository,
        tag_repo: TagRepository,
        parcelamento_repo: ParcelamentoRepository,
        financiamento_repo: FinanciamentoRepository,
        emprestimo_repo: EmprestimoRepository,
        conta_recorrente_repo: ContaRecorrenteRepository,
        meta_repo: MetaRepository,
        fatura_repo: FaturaRepository,
        fatura_service: FaturaService,
    ) -> None:
        self.transacao_repo = transacao_repo
        self.conta_repo = conta_repo
        self.cartao_repo = cartao_repo
        self.categoria_repo = categoria_repo
        self.tag_repo = tag_repo
        self.parcelamento_repo = parcelamento_repo
        self.financiamento_repo = financiamento_repo
        self.emprestimo_repo = emprestimo_repo
        self.conta_recorrente_repo = conta_recorrente_repo
        self.meta_repo = meta_repo
        self.fatura_repo = fatura_repo
        self.fatura_service = fatura_service

    def criar(self, dados: TransacaoCreate, usuario_id: int) -> Transacao:
        self._validar_estrutura(
            conta_id=dados.conta_id,
            cartao_id=dados.cartao_id,
            parcelamento_id=dados.parcelamento_id,
            financiamento_id=dados.financiamento_id,
            emprestimo_id=dados.emprestimo_id,
            numero_parcela=dados.numero_parcela,
        )

        if dados.parcelamento_id is not None:
            self._validar_parcelamento(dados.parcelamento_id, dados.numero_parcela, usuario_id)
        if dados.financiamento_id is not None:
            self._validar_financiamento(dados.financiamento_id, dados.numero_parcela, usuario_id)
        if dados.emprestimo_id is not None:
            self._validar_emprestimo(dados.emprestimo_id, dados.numero_parcela, usuario_id)
        if dados.origem_recorrente_id is not None:
            self._validar_conta_recorrente(dados.origem_recorrente_id, dados.data, usuario_id)
        if dados.categoria_id is not None:
            self._validar_categoria(dados.categoria_id, dados.tipo, usuario_id)
        tags = self._validar_tags(dados.tag_ids, usuario_id)

        fatura_id: int | None = None
        status = dados.status or StatusTransacao.PENDENTE
        if dados.conta_id is not None:
            self._validar_conta_ativa(dados.conta_id, usuario_id)
        else:
            self._validar_cartao_ativo(dados.cartao_id, usuario_id)
            # fatura_id NUNCA vem do payload do cliente - sempre resolvido
            # aqui (find-or-create do ciclo aberto que cobre `data`). status
            # e SEMPRE PAGO numa transacao de cartao, ignorando o que o
            # cliente enviou - ver StatusTransacao.
            fatura = self.fatura_service.resolver_fatura_aberta(dados.cartao_id, dados.data, usuario_id)
            fatura_id = fatura.id
            status = StatusTransacao.PAGO
        if dados.financiamento_id is not None or dados.emprestimo_id is not None:
            # uma parcela de contrato de credito sempre nasce PENDENTE,
            # independente do que o cliente mandar aqui OU do que o ramo
            # conta/cartao acima tenha decidido - esta checagem vem POR
            # ULTIMO de proposito, para sempre vencer (inclusive o caso
            # nao-intencional de financiamento_id+cartao_id no mesmo
            # payload, que forcaria PAGO se checado antes). So
            # marcar_parcela_de_contrato_paga() (chamada exclusivamente
            # pela acao dedicada de pagamento do contrato) pode
            # transicionar para PAGO. Ver docstring do modulo.
            status = StatusTransacao.PENDENTE

        transacao = Transacao(
            usuario_id=usuario_id,
            tipo=dados.tipo,
            valor=dados.valor,
            data=dados.data,
            descricao=dados.descricao,
            status=status,
            categoria_id=dados.categoria_id,
            conta_id=dados.conta_id,
            cartao_id=dados.cartao_id,
            parcelamento_id=dados.parcelamento_id,
            financiamento_id=dados.financiamento_id,
            emprestimo_id=dados.emprestimo_id,
            numero_parcela=dados.numero_parcela,
            origem_recorrente_id=dados.origem_recorrente_id,
            fatura_id=fatura_id,
            tags=tags,
        )
        return self.transacao_repo.create(transacao)

    def obter(self, transacao_id: int, usuario_id: int) -> Transacao:
        return self._buscar_da_propriedade_do_usuario(transacao_id, usuario_id)

    def listar(
        self,
        usuario_id: int,
        *,
        conta_id: int | None = None,
        cartao_id: int | None = None,
        fatura_id: int | None = None,
        categoria_id: int | None = None,
        parcelamento_id: int | None = None,
        financiamento_id: int | None = None,
        emprestimo_id: int | None = None,
        origem_recorrente_id: int | None = None,
        meta_id: int | None = None,
        tipo: TipoTransacao | None = None,
        status: StatusTransacao | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        apenas_conta: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transacao]:
        return list(
            self.transacao_repo.listar_do_usuario(
                usuario_id,
                conta_id=conta_id,
                cartao_id=cartao_id,
                fatura_id=fatura_id,
                categoria_id=categoria_id,
                parcelamento_id=parcelamento_id,
                financiamento_id=financiamento_id,
                emprestimo_id=emprestimo_id,
                origem_recorrente_id=origem_recorrente_id,
                meta_id=meta_id,
                tipo=tipo,
                status=status,
                data_inicio=data_inicio,
                data_fim=data_fim,
                apenas_conta=apenas_conta,
                skip=skip,
                limit=limit,
            )
        )

    def somar_por_periodo(
        self,
        usuario_id: int,
        *,
        tipo: TipoTransacao,
        status: StatusTransacao,
        data_inicio: date,
        data_fim: date,
    ) -> Decimal:
        """Wrapper fino sobre `TransacaoRepository.somar_por_periodo` - sem
        nenhuma regra de negócio própria, só delega. Existe como método
        público de Service (em vez de a Central Financeira acessar
        `TransacaoRepository` diretamente) para manter o princípio já
        estabelecido no projeto: nenhuma camada de orquestração acessa
        Repository - ver docs/analise-arquitetural-central-financeira.md."""
        return self.transacao_repo.somar_por_periodo(
            usuario_id, tipo=tipo, status=status, data_inicio=data_inicio, data_fim=data_fim
        )

    # --- Etapa de Gráficos (docs/analise-arquitetural-graficos.md) - wrappers
    # finos sobre os 4 métodos agregados novos de TransacaoRepository, mesmo
    # motivo do wrapper de somar_por_periodo acima.

    def somar_liquido_por_mes(self, usuario_id: int, *, data_fim: date):
        return self.transacao_repo.somar_liquido_por_mes(usuario_id, data_fim=data_fim)

    def somar_por_mes(
        self, usuario_id: int, *, tipo: TipoTransacao, status: StatusTransacao, data_inicio: date, data_fim: date
    ):
        return self.transacao_repo.somar_por_mes(
            usuario_id, tipo=tipo, status=status, data_inicio=data_inicio, data_fim=data_fim
        )

    def somar_agrupado_por_categoria(
        self, usuario_id: int, *, tipo: TipoTransacao, status: StatusTransacao, data_inicio: date, data_fim: date
    ):
        return self.transacao_repo.somar_agrupado_por_categoria(
            usuario_id, tipo=tipo, status=status, data_inicio=data_inicio, data_fim=data_fim
        )

    def somar_agrupado_por_cartao(self, usuario_id: int, *, status: StatusTransacao, data_inicio: date, data_fim: date):
        return self.transacao_repo.somar_agrupado_por_cartao(
            usuario_id, status=status, data_inicio=data_inicio, data_fim=data_fim
        )

    def atualizar(self, transacao_id: int, dados: TransacaoUpdate, usuario_id: int) -> Transacao:
        """Edita APENAS a linha `transacao_id` - diferente de `excluir()`,
        nunca propaga para as demais parcelas do mesmo `Parcelamento` hoje
        (editar a parcela 3 de 12 não toca as outras 11). Isto não é uma
        omissão: é o mesmo ponto de extensão descrito em
        `EscopoOperacaoParcela` (ver docstring), só que do lado da edição -
        se um dia existir "editar todas as parcelas"/"renegociar", o lugar
        certo para decidir isso é aqui, no início deste método, replicando
        o mesmo `escopo` explícito já usado por `_aplicar_exclusao_de_
        parcela` em vez de inventar uma segunda convenção."""
        transacao = self._buscar_da_propriedade_do_usuario(transacao_id, usuario_id)
        alteracoes = dados.model_dump(exclude_unset=True)
        tag_ids = alteracoes.pop("tag_ids", None)

        if _CAMPOS_TRAVADOS_EM_FATURA_FECHADA & alteracoes.keys():
            self._impedir_escrita_em_fatura_fechada(transacao)

        # conta_id/cartao_id sao imutaveis (nem existem em TransacaoUpdate) -
        # a validacao estrutural roda sobre o par (conta_id, cartao_id) JA
        # existente na transacao, mesclado com os campos de contrato que
        # de fato mudaram nesta chamada.
        parcelamento_id = alteracoes.get("parcelamento_id", transacao.parcelamento_id)
        numero_parcela = alteracoes.get("numero_parcela", transacao.numero_parcela)
        financiamento_id = alteracoes.get("financiamento_id", transacao.financiamento_id)
        emprestimo_id = alteracoes.get("emprestimo_id", transacao.emprestimo_id)

        if "status" in alteracoes and (financiamento_id is not None or emprestimo_id is not None):
            # protege saldo_devedor (campo armazenado, atualizado
            # transacionalmente pelo Service dono do contrato) de
            # desincronizar - ver Conflito 1 de
            # docs/analise-arquitetural-financiamento.md. Checagem
            # deliberadamente contra o estado MESCLADO (nao contra
            # transacao.financiamento_id isolado): achado da revisao
            # critica final - um unico PATCH que vincula financiamento_id
            # E manda status=PAGO na mesma chamada burlaria a protecao se
            # a checagem olhasse so o valor anterior (ainda None) em vez
            # do valor que vai de fato ser gravado.
            raise BusinessRuleError(
                "O status de uma parcela de financiamento ou empréstimo não pode ser alterado "
                "diretamente - use a ação de pagamento dedicada do contrato."
            )

        self._validar_estrutura(
            conta_id=transacao.conta_id,
            cartao_id=transacao.cartao_id,
            parcelamento_id=parcelamento_id,
            financiamento_id=financiamento_id,
            emprestimo_id=emprestimo_id,
            numero_parcela=numero_parcela,
        )

        # so revalida posse/faixa se algo que afeta essa checagem de fato
        # mudou nesta chamada - mesmo raciocinio de custo ja usado abaixo
        # para categoria (evita uma consulta extra num PATCH que so mexeu
        # em descricao, por exemplo).
        if parcelamento_id is not None and ("parcelamento_id" in alteracoes or "numero_parcela" in alteracoes):
            self._validar_parcelamento(
                parcelamento_id, numero_parcela, usuario_id, transacao_id_excluir=transacao.id
            )

        if financiamento_id is not None and ("financiamento_id" in alteracoes or "numero_parcela" in alteracoes):
            self._validar_financiamento(
                financiamento_id, numero_parcela, usuario_id, transacao_id_excluir=transacao.id
            )

        if emprestimo_id is not None and ("emprestimo_id" in alteracoes or "numero_parcela" in alteracoes):
            self._validar_emprestimo(
                emprestimo_id, numero_parcela, usuario_id, transacao_id_excluir=transacao.id
            )

        origem_recorrente_id = alteracoes.get("origem_recorrente_id", transacao.origem_recorrente_id)
        data_transacao = alteracoes.get("data", transacao.data)
        if origem_recorrente_id is not None and ("origem_recorrente_id" in alteracoes or "data" in alteracoes):
            self._validar_conta_recorrente(
                origem_recorrente_id, data_transacao, usuario_id, transacao_id_excluir=transacao.id
            )

        if "categoria_id" in alteracoes or "tipo" in alteracoes:
            nova_categoria_id = alteracoes.get("categoria_id", transacao.categoria_id)
            if nova_categoria_id is not None:
                novo_tipo = alteracoes.get("tipo", transacao.tipo)
                self._validar_categoria(nova_categoria_id, novo_tipo, usuario_id)

        if transacao.cartao_id is not None:
            # status nunca e editavel numa transacao de cartao - sempre
            # PAGO, nunca controlado pelo cliente (ver StatusTransacao).
            alteracoes.pop("status", None)

        if tag_ids is not None:
            transacao.tags = self._validar_tags(tag_ids, usuario_id)

        for campo, valor in alteracoes.items():
            setattr(transacao, campo, valor)
        return self.transacao_repo.update(transacao)

    def excluir(self, transacao_id: int, usuario_id: int) -> None:
        """Sem soft delete: Transacao é lançamento de livro-razão, não
        cadastro - uma transação errada é removida de verdade (ver
        docs/analise-arquitetural-transacao.md). Única restrição: uma
        transação de COMPRA (fatura_id) vinculada a fatura não-ABERTA não
        pode ser excluída - excluir uma linha corromperia o snapshot tanto
        quanto alterar seu valor. Uma transação de PAGAMENTO
        (fatura_paga_id) é sempre excluível: valor_pago é sempre
        recalculado ao vivo, não há snapshot de pagamento a proteger.

        Bug real encontrado em 2026-07-20: uma parcela de `Parcelamento`
        (compra parcelada no cartão) NÃO é uma transação isolada - é uma de
        N linhas geradas ATOMICAMENTE por `ParcelamentoService._gerar_
        parcelas` no momento da compra, todas com `fatura_id` já resolvido
        (inclusive as futuras). Excluir só a linha clicada aqui (ex: a
        parcela do mês corrente) deixava as outras N-1 completamente
        intocadas: as faturas futuras continuavam cobrando o valor cheio de
        uma compra que o usuário já tinha removido, e `Parcelamento.ativo`
        continuava `True` mesmo sem mais nenhuma parcela "atual" fazendo
        sentido. Corrigido delegando para `_aplicar_exclusao_de_parcela`
        sempre que a transação pertence a um parcelamento - ver docstring
        de `EscopoOperacaoParcela` para a regra centralizada."""
        transacao = self._buscar_da_propriedade_do_usuario(transacao_id, usuario_id)
        self._impedir_escrita_em_fatura_fechada(transacao)
        if transacao.parcelamento_id is not None:
            self._aplicar_exclusao_de_parcela(
                transacao, usuario_id, escopo=EscopoOperacaoParcela.TODO_PARCELAMENTO
            )
            return
        self.transacao_repo.delete(transacao)

    def _aplicar_exclusao_de_parcela(
        self, transacao: Transacao, usuario_id: int, *, escopo: EscopoOperacaoParcela
    ) -> None:
        """Ponto único de decisão "o que fazer quando UMA parcela de
        Parcelamento é excluída" - existe como método próprio (em vez de
        inline em `excluir()`) para que a regra de negócio cresça num único
        lugar quando uma segunda opção de `escopo` for implementada de
        verdade (ver docstring de `EscopoOperacaoParcela` e
        docs/analise-arquitetural-escopo-parcelamento.md), sem precisar
        redesenhar `excluir()` nem duplicar a checagem em outro método.

        Hoje só `TODO_PARCELAMENTO` é aceito - qualquer outro valor
        levanta `NotImplementedError` de propósito (nunca cai
        silenciosamente para um comportamento parecido, mas errado)."""
        if escopo is not EscopoOperacaoParcela.TODO_PARCELAMENTO:
            raise NotImplementedError(
                f"Escopo de exclusão de parcela ainda não suportado: {escopo.value}."
            )
        self.cancelar_parcelas_do_parcelamento(transacao.parcelamento_id, usuario_id)

    def cancelar_parcelas_do_parcelamento(self, parcelamento_id: int, usuario_id: int) -> None:
        """Motor real do escopo `EscopoOperacaoParcela.TODO_PARCELAMENTO` -
        chamado tanto por `_aplicar_exclusao_de_parcela` acima (quando o
        usuário apaga qualquer uma das parcelas pelo endpoint genérico de
        Transação) quanto por `ParcelamentoService.cancelar()` (ação
        dedicada ao Parcelamento, sempre com esse mesmo escopo - não há
        ambiguidade a decidir ali), para as duas nunca duplicarem este
        mesmo loop. Remove todas as parcelas ainda destravadas (fatura
        ABERTA, ou parcela em Conta que não tem conceito de fechamento);
        preserva intacta qualquer parcela cuja fatura já fechou - já é
        passado, excluí-la corromperia aquele snapshot tanto quanto excluir
        qualquer outra transação de fatura fechada. Marca
        `Parcelamento.ativo = False` ao final, só se ainda estava `True` -
        idempotente, então chamar duas vezes (ex: duas parcelas da mesma
        compra apagadas em sequência) não faz nada de errado na segunda
        vez."""
        parcelamento = self.parcelamento_repo.get(parcelamento_id)
        if parcelamento is None:
            return
        parcelas = self.transacao_repo.listar_do_usuario(
            usuario_id, parcelamento_id=parcelamento_id, limit=parcelamento.num_parcelas
        )
        for parcela in parcelas:
            try:
                self._impedir_escrita_em_fatura_fechada(parcela)
            except BusinessRuleError:
                continue
            self.transacao_repo.delete(parcela)
        if parcelamento.ativo:
            parcelamento.ativo = False
            self.parcelamento_repo.update(parcelamento)

    def marcar_parcela_de_contrato_paga(self, transacao_id: int, usuario_id: int) -> Transacao:
        """Única forma permitida de transicionar o status de uma parcela
        de Financiamento/Empréstimo para PAGO - chamada exclusivamente por
        `FinanciamentoService.pagar_parcela()` ou
        `EmprestimoService.pagar_parcela()`, nunca pelo cliente via PATCH
        genérico (que
        bloqueia esse campo para transações de contrato de crédito, ver
        `atualizar()`). Só transiciona PENDENTE -> PAGO; chamar duas vezes
        na mesma parcela levanta `BusinessRuleError` - quem decrementa
        `saldo_devedor` é o chamador, então uma dupla chamada dobraria o
        decremento se não fosse bloqueada aqui (idempotência)."""
        transacao = self._buscar_da_propriedade_do_usuario(transacao_id, usuario_id)
        if transacao.financiamento_id is None and transacao.emprestimo_id is None:
            raise BusinessRuleError("Esta transação não pertence a um contrato de crédito.")
        if transacao.status == StatusTransacao.PAGO:
            raise BusinessRuleError("Esta parcela já está paga.")
        transacao.status = StatusTransacao.PAGO
        return self.transacao_repo.update(transacao)

    # --- validações estruturais (mesma família dos CheckConstraints do model) ---

    @staticmethod
    def _validar_estrutura(
        *,
        conta_id: int | None,
        cartao_id: int | None,
        parcelamento_id: int | None,
        financiamento_id: int | None,
        emprestimo_id: int | None,
        numero_parcela: int | None,
    ) -> None:
        if (conta_id is None) == (cartao_id is None):
            raise BusinessRuleError("Informe exatamente um entre conta_id e cartao_id.")

        contratos = (parcelamento_id, financiamento_id, emprestimo_id)
        if sum(c is not None for c in contratos) > 1:
            raise BusinessRuleError(
                "Uma transação pertence a no máximo um contrato "
                "(parcelamento, financiamento ou empréstimo)."
            )

        tem_contrato = any(contratos)
        if tem_contrato and numero_parcela is None:
            raise BusinessRuleError(
                "numero_parcela é obrigatório quando a transação pertence a um "
                "parcelamento, financiamento ou empréstimo."
            )
        if not tem_contrato and numero_parcela is not None:
            raise BusinessRuleError(
                "numero_parcela só é permitido quando a transação pertence a um "
                "parcelamento, financiamento ou empréstimo."
            )

    # --- posse cruzada -------------------------------------------------------

    def _validar_conta_ativa(self, conta_id: int, usuario_id: int) -> None:
        conta = self.conta_repo.get(conta_id)
        if conta is None or conta.usuario_id != usuario_id:
            raise NotFoundError("Conta não encontrada.")
        if not conta.ativo:
            raise BusinessRuleError("Não é possível lançar uma transação em uma conta inativa.")

    def _validar_cartao_ativo(self, cartao_id: int, usuario_id: int) -> Cartao:
        cartao = self.cartao_repo.get(cartao_id)
        if cartao is None or cartao.usuario_id != usuario_id:
            raise NotFoundError("Cartão não encontrado.")
        if not cartao.ativo:
            raise BusinessRuleError("Não é possível lançar uma transação em um cartão inativo.")
        return cartao

    def _validar_categoria(self, categoria_id: int, tipo: TipoTransacao, usuario_id: int) -> Categoria:
        """Mesma visibilidade de CategoriaService._buscar_visivel (sistema
        OU própria do usuário). Categoria inativa é bloqueada para nova
        atribuição (nunca desfeita retroativamente numa transação antiga -
        isso é feito só ao NÃO chamar esta validação em campos que não
        mudaram). `categoria.tipo` incompatível com `tipo` da transação é
        rejeitado - achado da análise arquitetural, ver
        docs/analise-arquitetural-transacao.md."""
        categoria = self.categoria_repo.get(categoria_id)
        if categoria is None or (categoria.usuario_id is not None and categoria.usuario_id != usuario_id):
            raise NotFoundError("Categoria não encontrada.")
        if not categoria.ativo:
            raise BusinessRuleError("Não é possível usar uma categoria inativa.")
        if categoria.tipo != TipoCategoria.AMBOS and categoria.tipo.value != tipo.value:
            raise BusinessRuleError("O tipo da categoria não é compatível com o tipo da transação.")
        return categoria

    def _validar_parcelamento(
        self,
        parcelamento_id: int,
        numero_parcela: int | None,
        usuario_id: int,
        *,
        transacao_id_excluir: int | None = None,
    ) -> None:
        """Garante que o parcelamento existe, pertence ao usuário, que
        `numero_parcela` está dentro da faixa válida (1..num_parcelas), e
        que nenhuma outra transação já reivindica essa mesma parcela deste
        parcelamento. Fecha a lacuna deixada deliberadamente em aberto
        (YAGNI) na primeira versão de TransacaoService - agora que
        `ParcelamentoRepository` existe, esta é a mesma validação cruzada
        já usada para Conta/Cartão/Categoria/Tag. Ver
        docs/analise-arquitetural-parcelamento.md.

        A checagem de duplicidade é feita AQUI (levantando um `ConflictError`
        claro, mesmo raciocínio já usado em `FaturaService.criar` para o par
        cartão+mês) em vez de deixar o `UniqueConstraint` do banco ser o
        único guarda-chuva - achado da revisão técnica final: sem isso, um
        `POST /transacoes` manual reivindicando um `numero_parcela` já usado
        por outra transação do mesmo parcelamento derrubava um
        `IntegrityError` cru (500), já que só `ParcelamentoService` (geração
        eager, sempre com números únicos por construção) respeitava esse
        limite - a rota genérica de Transação não tinha nenhuma barreira
        antes do banco.
        `transacao_id_excluir` existe para o caso de `atualizar()`: a própria
        transação sendo editada não deve contar como "conflito" consigo
        mesma."""
        parcelamento = self.parcelamento_repo.get(parcelamento_id)
        if parcelamento is None or parcelamento.usuario_id != usuario_id:
            raise NotFoundError("Parcelamento não encontrado.")
        if numero_parcela is not None and not (1 <= numero_parcela <= parcelamento.num_parcelas):
            raise BusinessRuleError(
                f"numero_parcela deve estar entre 1 e {parcelamento.num_parcelas} para este parcelamento."
            )
        if numero_parcela is not None:
            parcelas_existentes = self.transacao_repo.listar_do_usuario(
                usuario_id, parcelamento_id=parcelamento_id, limit=parcelamento.num_parcelas
            )
            colisao = any(
                p.numero_parcela == numero_parcela and p.id != transacao_id_excluir
                for p in parcelas_existentes
            )
            if colisao:
                raise ConflictError(
                    f"A parcela {numero_parcela} deste parcelamento já está em uso por outra transação."
                )

    def _validar_financiamento(
        self,
        financiamento_id: int,
        numero_parcela: int | None,
        usuario_id: int,
        *,
        transacao_id_excluir: int | None = None,
    ) -> None:
        """Mesma família de `_validar_parcelamento`: garante que o
        Financiamento existe, pertence ao usuário, que `numero_parcela`
        está dentro da faixa válida (1..num_parcelas), e que nenhuma outra
        transação já reivindica essa mesma parcela deste financiamento.
        Fecha a lacuna YAGNI que o próprio docstring deste módulo já
        previa para este campo, agora que `FinanciamentoRepository`
        existe. Ver docs/analise-arquitetural-financiamento.md.

        A checagem de duplicidade é feita AQUI (levantando `ConflictError`)
        em vez de deixar a `UniqueConstraint(financiamento_id,
        numero_parcela)` do banco ser o único guarda-chuva - mesma lição
        já aplicada duas vezes (Parcelamento e ContaRecorrente): aplicada
        proativamente aqui, sem esperar descobrir o mesmo bug de novo."""
        financiamento = self.financiamento_repo.get(financiamento_id)
        if financiamento is None or financiamento.usuario_id != usuario_id:
            raise NotFoundError("Financiamento não encontrado.")
        if numero_parcela is not None and not (1 <= numero_parcela <= financiamento.num_parcelas):
            raise BusinessRuleError(
                f"numero_parcela deve estar entre 1 e {financiamento.num_parcelas} para este financiamento."
            )
        if numero_parcela is not None:
            parcelas_existentes = self.transacao_repo.listar_do_usuario(
                usuario_id, financiamento_id=financiamento_id, limit=financiamento.num_parcelas
            )
            colisao = any(
                p.numero_parcela == numero_parcela and p.id != transacao_id_excluir
                for p in parcelas_existentes
            )
            if colisao:
                raise ConflictError(
                    f"A parcela {numero_parcela} deste financiamento já está em uso por outra transação."
                )

    def _validar_emprestimo(
        self,
        emprestimo_id: int,
        numero_parcela: int | None,
        usuario_id: int,
        *,
        transacao_id_excluir: int | None = None,
    ) -> None:
        """Mesma família de `_validar_financiamento`: garante que o
        Empréstimo existe, pertence ao usuário, que `numero_parcela` está
        dentro da faixa válida (1..num_parcelas), e que nenhuma outra
        transação já reivindica essa mesma parcela deste empréstimo. Fecha
        a lacuna YAGNI que o próprio docstring deste módulo já previa para
        este campo, agora que `EmprestimoRepository` existe. Ver
        docs/analise-arquitetural-emprestimo.md.

        A checagem de duplicidade é feita AQUI (levantando `ConflictError`)
        em vez de deixar a `UniqueConstraint(emprestimo_id,
        numero_parcela)` do banco ser o único guarda-chuva - mesma lição já
        aplicada três vezes (Parcelamento, ContaRecorrente e Financiamento):
        aplicada proativamente aqui, sem esperar descobrir o mesmo bug de
        novo."""
        emprestimo = self.emprestimo_repo.get(emprestimo_id)
        if emprestimo is None or emprestimo.usuario_id != usuario_id:
            raise NotFoundError("Empréstimo não encontrado.")
        if numero_parcela is not None and not (1 <= numero_parcela <= emprestimo.num_parcelas):
            raise BusinessRuleError(
                f"numero_parcela deve estar entre 1 e {emprestimo.num_parcelas} para este empréstimo."
            )
        if numero_parcela is not None:
            parcelas_existentes = self.transacao_repo.listar_do_usuario(
                usuario_id, emprestimo_id=emprestimo_id, limit=emprestimo.num_parcelas
            )
            colisao = any(
                p.numero_parcela == numero_parcela and p.id != transacao_id_excluir
                for p in parcelas_existentes
            )
            if colisao:
                raise ConflictError(
                    f"A parcela {numero_parcela} deste empréstimo já está em uso por outra transação."
                )

    def _validar_conta_recorrente(
        self,
        origem_recorrente_id: int,
        data_transacao: date,
        usuario_id: int,
        *,
        transacao_id_excluir: int | None = None,
    ) -> None:
        """Garante que a ContaRecorrente existe, pertence ao usuário, e que
        nenhuma outra transação já reivindica essa mesma data para essa
        mesma recorrência - mesma família de validação já usada para
        `parcelamento_id`, fechando a mesma lacuna deixada deliberadamente
        em aberto (YAGNI) enquanto `ContaRecorrenteRepository` não existia.
        Ver docs/analise-arquitetural-conta-recorrente.md.

        A checagem de duplicidade é feita AQUI (levantando um
        `ConflictError` claro) em vez de deixar a
        `UniqueConstraint(origem_recorrente_id, data)` do banco ser o único
        guarda-chuva - mesma lição aprendida com `numero_parcela` na
        revisão técnica de Parcelamento: sem isso, um `POST /transacoes`
        manual reivindicando uma data já usada por outra ocorrência da
        mesma recorrência derrubaria um `IntegrityError` cru (500).
        `transacao_id_excluir` existe para o caso de `atualizar()`: a
        própria transação sendo editada não deve contar como "conflito"
        consigo mesma."""
        conta_recorrente = self.conta_recorrente_repo.get(origem_recorrente_id)
        if conta_recorrente is None or conta_recorrente.usuario_id != usuario_id:
            raise NotFoundError("Conta recorrente não encontrada.")

        ocorrencias_na_data = self.transacao_repo.listar_do_usuario(
            usuario_id,
            origem_recorrente_id=origem_recorrente_id,
            data_inicio=data_transacao,
            data_fim=data_transacao,
        )
        colisao = any(ocorrencia.id != transacao_id_excluir for ocorrencia in ocorrencias_na_data)
        if colisao:
            raise ConflictError("Já existe uma transação gerada para esta recorrência nesta data.")


    def _validar_tags(self, tag_ids: list[int], usuario_id: int) -> list[Tag]:
        tags: list[Tag] = []
        for tag_id in tag_ids:
            tag = self.tag_repo.get(tag_id)
            if tag is None or tag.usuario_id != usuario_id:
                raise NotFoundError("Tag não encontrada.")
            if not tag.ativo:
                raise BusinessRuleError("Não é possível usar uma tag inativa.")
            tags.append(tag)
        return tags

    def _buscar_da_propriedade_do_usuario(self, transacao_id: int, usuario_id: int) -> Transacao:
        transacao = self.transacao_repo.get(transacao_id)
        if transacao is None or transacao.usuario_id != usuario_id:
            raise NotFoundError("Transação não encontrada.")
        return transacao

    # --- imutabilidade de fatura fechada --------------------------------------

    def _impedir_escrita_em_fatura_fechada(self, transacao: Transacao) -> None:
        """Só se aplica a transações de COMPRA (`fatura_id` preenchido) -
        transações de PAGAMENTO (`fatura_paga_id`) nunca são travadas (ver
        docstring de `excluir`)."""
        if transacao.fatura_id is None:
            return
        fatura = self.fatura_repo.get(transacao.fatura_id)
        if fatura is not None and fatura.status != StatusFatura.ABERTA:
            raise BusinessRuleError(
                "Não é possível alterar ou excluir uma transação vinculada a uma fatura já fechada."
            )
