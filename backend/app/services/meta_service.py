"""Service de Meta.

Regras de negócio concentradas aqui: descrição única por usuário (mesma
tensão com soft delete já resolvida em TagService/CartaoService - ver
criar()) e o cálculo de `valor_acumulado`/`percentual`.

Refatoramento de Metas/Transferências (ver
docs/analise-arquitetural-metas-transferencias.md): `valor_acumulado` soma
DUAS fontes - o histórico legado (`Transacao.meta_id`, CONGELADO, nenhuma
Transacao nova pode mais ser marcada assim) e o saldo do "cofrinho" (Conta
dedicada e oculta, sempre criada automaticamente por este Service, que
recebe aportes/resgates como `Transferencia` de verdade). `conta_id`
deixou de ser opcional/organizacional - é sempre o cofrinho, nunca escolhido
pelo usuário.

MetaService NUNCA cria/edita/paga uma Transacao por conta própria - só lê
(via `MetaRepository.somar_transacoes_pagas`) para calcular a parte legada
do progresso. Diferente de Parcelamento/ContaRecorrente/Financiamento/
Empréstimo, não compõe `TransacaoService`. Cria/apaga `Conta` diretamente
(via `ContaRepository`, sem passar por `ContaService`/`ContaCreate`) só
para o cofrinho - a única exceção a "Service só mexe na própria entidade"
deste projeto, documentada e deliberada (seção 2 da análise).
"""
import math
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Conta, Meta
from app.models.enums import FrequenciaContribuicao, SituacaoPlanejamentoMeta, TipoConta
from app.repositories.conta_repository import ContaRepository
from app.repositories.meta_repository import MetaRepository
from app.schemas.meta import MetaCreate, MetaUpdate

_DUAS_CASAS = Decimal("0.01")
_PERCENTUAL_CONCLUIDA = Decimal("100")

# Aproximação deliberada (não usa meses de calendário exatos) - o número
# resultante é só uma sugestão de apoio ao usuário, nunca autoritativo (ver
# docs/analise-arquitetural-metas-refinamento.md, seção 1.2).
_DIAS_POR_PERIODO: dict[FrequenciaContribuicao, int] = {
    FrequenciaContribuicao.DIARIA: 1,
    FrequenciaContribuicao.SEMANAL: 7,
    FrequenciaContribuicao.QUINZENAL: 15,
    FrequenciaContribuicao.MENSAL: 30,
}

# Banda de tolerância de "dentro do planejado" (seção 2.3) - decisão de
# produto, não uma verdade matemática: evita o indicador oscilar entre
# ADIANTADO/ATRASADO por flutuações naturais de poucos reais em torno do
# planejado exato.
_TOLERANCIA_PLANEJAMENTO_PERCENTUAL = Decimal("0.02")

# Acima disso, uma "previsão de conclusão" deixa de ser útil/confiável
# (ritmo baixo demais) - mesmo critério de "sem dados suficientes, não
# exibir" (seção 3.1).
_HORIZONTE_MAXIMO_PREVISAO_DIAS = 365 * 100


class MetaService:
    def __init__(self, meta_repo: MetaRepository, conta_repo: ContaRepository) -> None:
        self.meta_repo = meta_repo
        self.conta_repo = conta_repo

    def criar(self, dados: MetaCreate, usuario_id: int) -> Meta:
        """Cria uma meta nova - ou REATIVA uma existente, se a descrição
        colidir com uma meta desativada do mesmo usuário. Mesmo raciocínio
        de TagService.criar()/CartaoService.criar(): a
        UniqueConstraint(usuario_id, descricao) não distingue meta ativa de
        desativada, então reativar em vez de inserir evita "queimar" a
        descrição permanentemente quando uma meta é apagada e o usuário
        quer reusar o nome depois."""
        existente = self.meta_repo.buscar_por_descricao(usuario_id, dados.descricao)
        if existente is not None:
            if existente.ativo:
                raise ConflictError("Já existe uma meta com esta descrição.")
            # Semântica de CRIAÇÃO, não de "restaurar como estava" - mesmo
            # raciocínio de TagService/CartaoService.criar(): o payload é
            # aplicado por completo, o valor_alvo/data_alvo antigos são
            # sobrescritos de propósito. `conta_id` NÃO está em `dados`
            # (não existe mais em `MetaCreate`) - o cofrinho que a meta já
            # tinha é preservado automaticamente, com todo o saldo que já
            # havia acumulado.
            for campo, valor in dados.model_dump().items():
                setattr(existente, campo, valor)
            existente.ativo = True
            meta = self.meta_repo.update(existente)
            return self._com_progresso(meta)

        # ativo=True explícito - mesmo motivo de Conta/Categoria/Tag/Cartão
        # Service.criar: o default da coluna só é aplicado num flush de
        # verdade. O cofrinho é criado ANTES da Meta para já existir um id
        # real a atribuir a `conta_id` (NOT NULL, sem valor default).
        cofrinho = self._criar_cofrinho(dados.descricao, usuario_id)
        meta = Meta(**dados.model_dump(), usuario_id=usuario_id, ativo=True, conta_id=cofrinho.id)
        meta = self.meta_repo.create(meta)
        return self._com_progresso(meta)

    def _criar_cofrinho(self, descricao_meta: str, usuario_id: int) -> Conta:
        """Cria a Conta dedicada e oculta desta Meta - nunca escolhida
        pelo usuário, nunca reaproveitada por outra Meta. `TipoConta.
        CARTEIRA` é só a natureza mais próxima de "dinheiro guardado", sem
        nenhum outro efeito (ver docs/analise-arquitetural-metas-
        transferencias.md, seção 1.2 - `oculta` é o que importa, não o
        tipo)."""
        cofrinho = Conta(
            usuario_id=usuario_id,
            nome=f"Cofrinho — {descricao_meta}",
            tipo=TipoConta.CARTEIRA,
            saldo_inicial=Decimal("0"),
            ativo=True,
            oculta=True,
        )
        return self.conta_repo.create(cofrinho)

    def obter(self, meta_id: int, usuario_id: int) -> Meta:
        meta = self._buscar_da_propriedade_do_usuario(meta_id, usuario_id)
        return self._com_progresso(meta)

    def listar(
        self, usuario_id: int, *, apenas_ativas: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Meta]:
        metas = self.meta_repo.listar_do_usuario(usuario_id, apenas_ativas=apenas_ativas, skip=skip, limit=limit)
        return [self._com_progresso(meta) for meta in metas]

    def atualizar(self, meta_id: int, dados: MetaUpdate, usuario_id: int) -> Meta:
        meta = self._buscar_da_propriedade_do_usuario(meta_id, usuario_id)
        alteracoes = dados.model_dump(exclude_unset=True)

        nova_descricao = alteracoes.get("descricao")
        if nova_descricao is not None and nova_descricao != meta.descricao:
            # Renomear NÃO reativa/mescla com uma meta inativa de mesma
            # descrição - mesma decisão (e mesmo motivo) de
            # TagService/CartaoService.atualizar: fundir identidades
            # implicitamente ao renomear seria arriscado demais para ser
            # automático. Bloqueia com 409, igual a qualquer outra colisão.
            colisao = self.meta_repo.buscar_por_descricao(usuario_id, nova_descricao)
            if colisao is not None and colisao.id != meta.id:
                raise ConflictError("Já existe uma meta com esta descrição.")

        for campo, valor in alteracoes.items():
            setattr(meta, campo, valor)
        meta = self.meta_repo.update(meta)
        return self._com_progresso(meta)

    def desativar(self, meta_id: int, usuario_id: int) -> None:
        """"Exclui" uma meta sem apagar a linha - só marca ativo=False,
        mesmo padrão de Conta/Categoria/Tag/Cartão. Transações antigas que
        já têm `meta_id` apontando pra essa meta (histórico legado
        congelado) continuam intactas, e o cofrinho continua existindo
        normalmente (`ativo=True`) - desativar a Meta não desativa/apaga a
        Conta dela. A meta só some das listas de novas seleções."""
        meta = self._buscar_da_propriedade_do_usuario(meta_id, usuario_id)
        meta.ativo = False
        self.meta_repo.update(meta)

    def excluir(self, meta_id: int, usuario_id: int) -> None:
        """Exclusão DEFINITIVA (hard delete) - uma AÇÃO NOVA, nunca
        substitui `desativar()` acima. Mesmo padrão adotado para Fatura
        (mudança de regra de 2026-07-24): nunca bloqueia por haver
        transações (aportes legados) ou transferências (aportes/resgates
        novos) vinculadas - o usuário precisa poder desfazer/corrigir uma
        meta cadastrada errada mesmo depois de já ter usado ela.
        `desvincular_transacoes` zera `meta_id` de toda transação legada
        vinculada antes de apagar a meta - o aporte antigo em si nunca é
        removido, só perde o vínculo com uma meta que deixou de existir.

        O cofrinho é tratado à parte (`_encerrar_cofrinho`, seção 2.1 da
        análise): apagado de verdade se nunca recebeu nenhuma
        Transferencia, ou só desativado/desocultado (vira uma Conta comum,
        visível, desativada) se já tem saldo real - nunca apagado com
        dinheiro dentro."""
        meta = self._buscar_da_propriedade_do_usuario(meta_id, usuario_id)
        conta_id_cofrinho = meta.conta_id
        self.meta_repo.desvincular_transacoes(meta.id)
        self.meta_repo.delete(meta)
        self._encerrar_cofrinho(conta_id_cofrinho)

    def _encerrar_cofrinho(self, conta_id: int) -> None:
        if self.conta_repo.existe_vinculo(conta_id):
            cofrinho = self.conta_repo.get(conta_id)
            cofrinho.oculta = False
            cofrinho.ativo = False
            self.conta_repo.update(cofrinho)
        else:
            cofrinho = self.conta_repo.get(conta_id)
            self.conta_repo.delete(cofrinho)

    def _buscar_da_propriedade_do_usuario(self, meta_id: int, usuario_id: int) -> Meta:
        meta = self.meta_repo.get(meta_id)
        if meta is None or meta.usuario_id != usuario_id:
            # Mesmo tratamento (404) para "não existe" e "é de outro
            # usuário" - mesmo raciocínio anti-enumeração de sempre (BOLA).
            raise NotFoundError("Meta não encontrada.")
        return meta

    def _com_progresso(self, meta: Meta) -> Meta:
        """Anexa valor_acumulado/percentual (calculados, nunca
        armazenados) ao objeto Meta antes de devolvê-lo. Atributos
        transientes: não são colunas mapeadas, nunca são persistidos,
        existem só para o Router/Schema lerem. `percentual` não tem teto
        artificial - pode passar de 100% se a meta for superada, mesma
        filosofia de `CartaoService._com_limite_disponivel` não clampar
        um estouro real.

        Também calcula os campos de planejamento do Refinamento de Metas
        (contribuição sugerida por período, planejado x realizado,
        situação do planejamento, previsão de conclusão - ver
        docs/analise-arquitetural-metas-refinamento.md) e observa/persiste
        a transição de `concluida_em` na primeira vez em que `percentual`
        cruza 100%. Nenhum desses campos é regra de negócio que valida ou
        bloqueia algo - são só apoio ao usuário, nunca substituem
        valor_acumulado/percentual.

        `valor_acumulado` soma DUAS fontes (Refatoramento de Metas/
        Transferências, seção 3): o histórico legado (`Transacao.meta_id`,
        CONGELADO, sem alteração) + o saldo do cofrinho (`Transferencia`
        envolvendo `meta.conta_id`, os aportes/resgates de verdade). Como o
        cofrinho nunca recebe `Transacao` (fica oculto de todo picker de
        conta/cartão), essa segunda soma É, na prática, "aportes −
        resgates" - nenhuma fórmula nova, as duas somas já existiam nos
        Repositories de cada entidade."""
        hoje = date.today()

        valor_acumulado = self.meta_repo.somar_transacoes_pagas(
            meta.id
        ) + self.conta_repo.somar_transferencias(meta.conta_id)
        percentual = (valor_acumulado / meta.valor_alvo * 100).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)
        meta.valor_acumulado = valor_acumulado
        meta.percentual = percentual

        concluida = percentual >= _PERCENTUAL_CONCLUIDA
        if concluida and meta.concluida_em is None:
            # Gatilho lazy: Meta não tem uma ação explícita de "concluir"
            # vinda do usuário (o progresso é sempre derivado ao vivo de
            # Transacao.meta_id) - este é o único ponto que observa a
            # transição. Nunca desfeito depois (ver docstring de
            # `Meta.concluida_em`). `update()` só dá flush - o commit real
            # acontece no fim do request como qualquer outra escrita.
            meta.concluida_em = hoje
            self.meta_repo.update(meta)

        valor_restante = meta.valor_alvo - valor_acumulado

        valor_planejado_ate_hoje = self._calcular_valor_planejado_ate_hoje(meta, hoje)
        diferenca_planejado_realizado = (
            (valor_acumulado - valor_planejado_ate_hoje) if valor_planejado_ate_hoje is not None else None
        )

        meta.valor_planejado_ate_hoje = valor_planejado_ate_hoje
        meta.diferenca_planejado_realizado = diferenca_planejado_realizado
        meta.situacao_planejamento = (
            None
            if concluida or diferenca_planejado_realizado is None
            else self._derivar_situacao_planejamento(diferenca_planejado_realizado, meta.valor_alvo)
        )
        meta.contribuicao_sugerida_por_periodo = (
            None
            if concluida
            else self._calcular_contribuicao_sugerida(meta, valor_restante, hoje)
        )
        meta.data_prevista_conclusao = (
            None if concluida else self._calcular_data_prevista_conclusao(meta, valor_acumulado, valor_restante, hoje)
        )
        return meta

    @staticmethod
    def _calcular_valor_planejado_ate_hoje(meta: Meta, hoje: date) -> Decimal | None:
        """Projeção linear desde a criação da meta até `data_alvo`,
        alcançando `valor_alvo` exatamente no prazo (seção 2.1)."""
        if meta.data_alvo is None:
            return None
        criado_em_data = meta.criado_em.date()
        dias_totais = (meta.data_alvo - criado_em_data).days
        if dias_totais <= 0:
            return None
        dias_decorridos = max(0, min(dias_totais, (hoje - criado_em_data).days))
        return (meta.valor_alvo * dias_decorridos / dias_totais).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)

    @staticmethod
    def _derivar_situacao_planejamento(
        diferenca: Decimal, valor_alvo: Decimal
    ) -> SituacaoPlanejamentoMeta:
        """Banda de tolerância de 2% do valor_alvo (seção 2.3) - decisão de
        produto para não oscilar entre estados por flutuações naturais."""
        tolerancia = valor_alvo * _TOLERANCIA_PLANEJAMENTO_PERCENTUAL
        if diferenca > tolerancia:
            return SituacaoPlanejamentoMeta.ADIANTADO
        if diferenca < -tolerancia:
            return SituacaoPlanejamentoMeta.ATRASADO
        return SituacaoPlanejamentoMeta.DENTRO_DO_PLANEJADO

    @staticmethod
    def _calcular_contribuicao_sugerida(meta: Meta, valor_restante: Decimal, hoje: date) -> Decimal | None:
        """Quanto guardar por período (frequência escolhida) para chegar
        no prazo (seção 1.2). `None` sem frequência/prazo definidos, ou
        com o prazo já vencido."""
        if meta.frequencia_contribuicao is None or meta.data_alvo is None:
            return None
        dias_restantes = (meta.data_alvo - hoje).days
        if dias_restantes <= 0:
            return None
        dias_por_periodo = _DIAS_POR_PERIODO[meta.frequencia_contribuicao]
        periodos_restantes = max(1, math.ceil(dias_restantes / dias_por_periodo))
        return (valor_restante / periodos_restantes).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)

    @staticmethod
    def _calcular_data_prevista_conclusao(
        meta: Meta, valor_acumulado: Decimal, valor_restante: Decimal, hoje: date
    ) -> date | None:
        """No ritmo atual (desde a criação da meta), quando a meta seria
        concluída (seção 3.1). `None` sem nenhum sinal real de progresso
        ainda, ou se o ritmo for baixo demais para uma previsão confiável."""
        if valor_acumulado <= 0:
            return None
        dias_decorridos = max(1, (hoje - meta.criado_em.date()).days)
        ritmo_diario = valor_acumulado / dias_decorridos
        if ritmo_diario <= 0:
            return None
        dias_necessarios = math.ceil(valor_restante / ritmo_diario)
        if dias_necessarios > _HORIZONTE_MAXIMO_PREVISAO_DIAS:
            return None
        return hoje + timedelta(days=max(0, dias_necessarios))
