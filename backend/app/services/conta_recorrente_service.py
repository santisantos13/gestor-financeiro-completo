"""Service de ContaRecorrente.

Regra de negócio central: ContaRecorrente é um TEMPLATE (frequência, valor,
dia de vencimento, categoria, conta/cartão) - a fonte da verdade de saldo e
relatórios continua sendo exclusivamente a Transacao gerada para cada
ocorrência (marcando `origem_recorrente_id`), nunca o template em si.

Expansão 2026-07-20 (docs/analise-arquitetural-conta-recorrente-expansao.md,
decisões aprovadas pelo usuário):

- TODAS as 8 frequências suportadas, via a função única
  `app/core/datas.avancar_data` (QUINZENAL = 14 dias fixos).
- `proxima_execucao` é o cursor MATERIALIZADO de geração: avança a cada
  ocorrência gerada e nunca olha para trás - excluir uma Transacao gerada
  não a ressuscita, e reativar uma pausa NUNCA gera retroativos (o cursor
  pula para a primeira data futura).
- Ciclo de vida explícito: ATIVA / PAUSADA / ENCERRADA. ENCERRADA é
  terminal - inclusive o DELETE HTTP encerra (preserva histórico e
  transações), nunca apaga fisicamente; o hard delete (`excluir`) existe
  só para a cascata de exclusão de Conta.
- Sincronização global (`sincronizar`) - o gatilho que o frontend chama no
  login para dar UX de geração automática, sem nenhum scheduler. Um futuro
  worker chamará exatamente este mesmo método (evolução sem refatoração).

Geração continua SEMPRE sob demanda (lazy) e síncrona - nunca scheduler,
cron, job ou fila. Este Service NUNCA constrói uma Transacao nem fala com
TransacaoRepository para escrever - toda ocorrência nasce através de
`TransacaoService.criar()`, reaproveitando toda a validação que já existe
lá (posse/ativo de Conta ou Cartão, resolução de fatura, categoria,
duplicidade de data).
"""
from datetime import date, timedelta

from app.core.datas import (
    FREQUENCIAS_BASEADAS_EM_DIAS,
    avancar_data,
    dia_valido,
)
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import ContaRecorrente, Transacao
from app.models.enums import FrequenciaRecorrencia, StatusRecorrencia
from app.repositories.conta_recorrente_repository import ContaRecorrenteRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.schemas.conta_recorrente import ContaRecorrenteCreate, ContaRecorrenteUpdate
from app.schemas.transacao import TransacaoCreate
from app.services.transacao_service import TransacaoService

# Horizonte da projeção virtual no Calendário (dias a partir de hoje) -
# decisão do usuário (2026-07-20): ocorrências futuras aparecem projetadas
# por até 90 dias, sem NUNCA serem persistidas.
HORIZONTE_PROJECAO_DIAS = 90


class ContaRecorrenteService:
    def __init__(
        self,
        conta_recorrente_repo: ContaRecorrenteRepository,
        transacao_repo: TransacaoRepository,
        transacao_service: TransacaoService,
    ) -> None:
        self.conta_recorrente_repo = conta_recorrente_repo
        self.transacao_repo = transacao_repo
        self.transacao_service = transacao_service

    def criar(self, dados: ContaRecorrenteCreate, usuario_id: int) -> ContaRecorrente:
        self._validar_estrutura(dados.conta_id, dados.cartao_id)
        self._validar_dia_vencimento(dados.frequencia, dados.dia_vencimento)
        self._validar_datas(dados.data_inicio, dados.data_fim)

        conta_recorrente = ContaRecorrente(
            usuario_id=usuario_id,
            descricao=dados.descricao,
            valor=dados.valor,
            tipo=dados.tipo,
            frequencia=dados.frequencia,
            dia_vencimento=dados.dia_vencimento,
            categoria_id=dados.categoria_id,
            conta_id=dados.conta_id,
            cartao_id=dados.cartao_id,
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
            proxima_execucao=self._primeira_execucao(
                dados.frequencia, dados.dia_vencimento, dados.data_inicio
            ),
            status=StatusRecorrencia.ATIVA,
        )
        conta_recorrente = self.conta_recorrente_repo.create(conta_recorrente)

        # Gera imediatamente as ocorrências já vencidas (cursor <= hoje) -
        # cobre o caso comum de cadastrar uma recorrência que já está em
        # andamento. data_inicio futura => nada gerado ainda.
        self._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id, date.today())
        return conta_recorrente

    def obter(self, conta_recorrente_id: int, usuario_id: int) -> ContaRecorrente:
        return self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)

    def listar(
        self,
        usuario_id: int,
        *,
        status: StatusRecorrencia | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ContaRecorrente]:
        return list(
            self.conta_recorrente_repo.listar_do_usuario(
                usuario_id, status=status, skip=skip, limit=limit
            )
        )

    def atualizar(
        self, conta_recorrente_id: int, dados: ContaRecorrenteUpdate, usuario_id: int
    ) -> ContaRecorrente:
        """PATCH em campos do template - só afeta ocorrências FUTURAS (cada
        ocorrência já gerada é uma Transacao independente). Mudar
        `frequencia`/`dia_vencimento` NÃO reancora o cursor no passado: a
        próxima data continua sendo `proxima_execucao`; só os avanços a
        partir dela passam a usar a regra nova. Exceção: mudar
        `data_inicio` de um template que ainda não gerou nada reancora o
        cursor (é o único caso em que o cursor ainda é só um reflexo da
        data_inicio, sem história a preservar)."""
        conta_recorrente = self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)
        if conta_recorrente.status == StatusRecorrencia.ENCERRADA:
            raise BusinessRuleError("Uma recorrência encerrada não pode ser editada.")
        alteracoes = dados.model_dump(exclude_unset=True)

        conta_id = alteracoes.get("conta_id", conta_recorrente.conta_id)
        cartao_id = alteracoes.get("cartao_id", conta_recorrente.cartao_id)
        self._validar_estrutura(conta_id, cartao_id)

        frequencia = alteracoes.get("frequencia", conta_recorrente.frequencia)
        # `dia_vencimento` ausente do PATCH herda o atual; presente (mesmo
        # como None explícito) usa o novo - exclude_unset distingue os dois.
        dia_vencimento = (
            alteracoes["dia_vencimento"]
            if "dia_vencimento" in alteracoes
            else conta_recorrente.dia_vencimento
        )
        self._validar_dia_vencimento(frequencia, dia_vencimento)

        data_inicio = alteracoes.get("data_inicio", conta_recorrente.data_inicio)
        data_fim = (
            alteracoes["data_fim"] if "data_fim" in alteracoes else conta_recorrente.data_fim
        )
        self._validar_datas(data_inicio, data_fim)

        for campo, valor in alteracoes.items():
            setattr(conta_recorrente, campo, valor)

        if not self._tem_ocorrencia_gerada(conta_recorrente.id, usuario_id):
            conta_recorrente.proxima_execucao = self._primeira_execucao(
                conta_recorrente.frequencia,
                conta_recorrente.dia_vencimento,
                conta_recorrente.data_inicio,
            )
        return self.conta_recorrente_repo.update(conta_recorrente)

    # --- ciclo de vida (ATIVA / PAUSADA / ENCERRADA) --------------------------

    def pausar(self, conta_recorrente_id: int, usuario_id: int) -> ContaRecorrente:
        """ATIVA -> PAUSADA. Nenhum efeito colateral: nada futuro existe
        para desfazer (invariante lazy - ocorrência nunca nasce adiantada)."""
        conta_recorrente = self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)
        if conta_recorrente.status != StatusRecorrencia.ATIVA:
            raise BusinessRuleError("Só uma recorrência ativa pode ser pausada.")
        conta_recorrente.status = StatusRecorrencia.PAUSADA
        return self.conta_recorrente_repo.update(conta_recorrente)

    def reativar(self, conta_recorrente_id: int, usuario_id: int) -> ContaRecorrente:
        """PAUSADA -> ATIVA. NUNCA gera retroativos (decisão do usuário,
        2026-07-20): o cursor avança até a primeira data estritamente
        futura - o período pausado fica sem ocorrências (assinatura
        suspensa: não houve cobrança, não deve haver lançamento). Se o
        avanço estourar `data_fim`, a recorrência é encerrada em vez de
        reativada (não sobrou nenhuma execução válida)."""
        conta_recorrente = self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)
        if conta_recorrente.status != StatusRecorrencia.PAUSADA:
            raise BusinessRuleError("Só uma recorrência pausada pode ser reativada.")

        hoje = date.today()
        proxima = conta_recorrente.proxima_execucao
        while proxima <= hoje:
            proxima = avancar_data(
                proxima, conta_recorrente.frequencia, conta_recorrente.dia_vencimento
            )
        conta_recorrente.proxima_execucao = proxima

        if conta_recorrente.data_fim is not None and proxima > conta_recorrente.data_fim:
            conta_recorrente.status = StatusRecorrencia.ENCERRADA
        else:
            conta_recorrente.status = StatusRecorrencia.ATIVA
        return self.conta_recorrente_repo.update(conta_recorrente)

    def encerrar(self, conta_recorrente_id: int, usuario_id: int) -> ContaRecorrente:
        """ATIVA ou PAUSADA -> ENCERRADA (terminal). Preserva o template
        como histórico e todas as Transacoes já geradas. `data_fim` é
        preenchida/antecipada para hoje - o registro conta a história real
        ("vigorou até aqui"). É também o comportamento do DELETE HTTP
        (decisão do usuário, 2026-07-20: nunca apagar fisicamente)."""
        conta_recorrente = self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)
        if conta_recorrente.status == StatusRecorrencia.ENCERRADA:
            raise BusinessRuleError("Esta recorrência já está encerrada.")
        hoje = date.today()
        if conta_recorrente.data_fim is None or conta_recorrente.data_fim > hoje:
            # nunca ANTES de data_inicio - um encerramento no dia da criação
            # de um template futuro guardaria data_fim < data_inicio,
            # violando a validação de datas do próprio Service.
            conta_recorrente.data_fim = max(hoje, conta_recorrente.data_inicio)
        conta_recorrente.status = StatusRecorrencia.ENCERRADA
        return self.conta_recorrente_repo.update(conta_recorrente)

    def excluir(self, conta_recorrente_id: int, usuario_id: int) -> None:
        """Hard delete - NÃO exposto em rota própria (o DELETE HTTP
        encerra, ver `encerrar`). Existe exclusivamente para a cascata de
        exclusão de Conta (`ContaService.excluir(..., apagar_vinculos=True)`,
        docs/analise-arquitetural-exclusao-conta-com-historico.md)."""
        conta_recorrente = self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)
        self.conta_recorrente_repo.delete(conta_recorrente)

    # --- geração de ocorrências (cursor materializado) ------------------------

    def gerar_ocorrencias_pendentes(self, conta_recorrente_id: int, usuario_id: int) -> list[Transacao]:
        """Ação explícita de sincronização/catch-up de UM template -
        idempotente (o cursor só anda para frente; a
        UniqueConstraint(origem_recorrente_id, data) é a rede de segurança
        no banco)."""
        conta_recorrente = self._buscar_da_propriedade_do_usuario(conta_recorrente_id, usuario_id)
        if conta_recorrente.status != StatusRecorrencia.ATIVA:
            raise BusinessRuleError("Só uma recorrência ativa gera ocorrências.")
        return self._gerar_ocorrencias_pendentes(conta_recorrente, usuario_id, date.today())

    def sincronizar(self, usuario_id: int) -> dict:
        """Sincronização GLOBAL: catch-up de todos os templates ATIVOS do
        usuário. É o que o frontend chama uma vez por sessão (mount do
        AppLayout) para dar a UX de "geração automática" sem nenhum
        scheduler - e é o mesmo método que um worker futuro chamará
        (evolução sem refatoração, ver análise, seção 11). Retorna
        contadores para o frontend só invalidar caches quando houve
        novidade."""
        hoje = date.today()
        geradas = 0
        encerradas = 0
        for template in self.conta_recorrente_repo.listar_do_usuario(
            usuario_id, status=StatusRecorrencia.ATIVA, limit=1000
        ):
            geradas += len(self._gerar_ocorrencias_pendentes(template, usuario_id, hoje))
            if template.status == StatusRecorrencia.ENCERRADA:
                encerradas += 1
        return {"geradas": geradas, "encerradas": encerradas}

    def projetar_ocorrencias(self, usuario_id: int, data_inicio: date, data_fim: date) -> list[dict]:
        """Projeção VIRTUAL das ocorrências futuras dos templates ATIVOS
        dentro da janela pedida - NADA é persistido (decisão do usuário,
        2026-07-20). Consumida por `CentralFinanceiraService.calendario_financeiro`
        (eventos com `previsto=True`). Janela efetiva: interseção entre a
        pedida, o futuro estrito (> hoje - o passado pendente vira
        Transacao real via sincronização, nunca projeção) e o horizonte de
        90 dias (`HORIZONTE_PROJECAO_DIAS`)."""
        hoje = date.today()
        horizonte = hoje + timedelta(days=HORIZONTE_PROJECAO_DIAS)
        inicio_efetivo = max(data_inicio, hoje + timedelta(days=1))
        fim_efetivo = min(data_fim, horizonte)
        if inicio_efetivo > fim_efetivo:
            return []

        projecoes: list[dict] = []
        for template in self.conta_recorrente_repo.listar_do_usuario(
            usuario_id, status=StatusRecorrencia.ATIVA, limit=1000
        ):
            limite_template = (
                min(fim_efetivo, template.data_fim) if template.data_fim else fim_efetivo
            )
            data = template.proxima_execucao
            while data <= limite_template:
                if data >= inicio_efetivo:
                    projecoes.append(
                        {
                            "data": data,
                            "descricao": template.descricao,
                            "valor": template.valor,
                            "tipo": template.tipo,
                            "origem_id": template.id,
                        }
                    )
                data = avancar_data(data, template.frequencia, template.dia_vencimento)
        return projecoes

    def _gerar_ocorrencias_pendentes(
        self, conta_recorrente: ContaRecorrente, usuario_id: int, hoje: date
    ) -> list[Transacao]:
        """Laço sobre o cursor: enquanto `proxima_execucao <= min(hoje,
        data_fim)`, gera a Transacao e avança o cursor. Ao ultrapassar
        `data_fim`, transiciona ATIVA -> ENCERRADA automaticamente (a
        recorrência cumpriu seu período - sai de "ativas" sem ação
        manual)."""
        geradas: list[Transacao] = []
        limite = min(hoje, conta_recorrente.data_fim) if conta_recorrente.data_fim else hoje

        while conta_recorrente.proxima_execucao <= limite:
            dados_transacao = TransacaoCreate(
                tipo=conta_recorrente.tipo,
                valor=conta_recorrente.valor,
                data=conta_recorrente.proxima_execucao,
                descricao=conta_recorrente.descricao,
                categoria_id=conta_recorrente.categoria_id,
                conta_id=conta_recorrente.conta_id,
                cartao_id=conta_recorrente.cartao_id,
                origem_recorrente_id=conta_recorrente.id,
            )
            geradas.append(self.transacao_service.criar(dados_transacao, usuario_id))
            conta_recorrente.proxima_execucao = avancar_data(
                conta_recorrente.proxima_execucao,
                conta_recorrente.frequencia,
                conta_recorrente.dia_vencimento,
            )

        if (
            conta_recorrente.data_fim is not None
            and conta_recorrente.proxima_execucao > conta_recorrente.data_fim
            and conta_recorrente.status == StatusRecorrencia.ATIVA
        ):
            conta_recorrente.status = StatusRecorrencia.ENCERRADA

        self.conta_recorrente_repo.update(conta_recorrente)
        return geradas

    # --- validações e cálculos internos ---------------------------------------

    @staticmethod
    def _primeira_execucao(
        frequencia: FrequenciaRecorrencia, dia_vencimento: int | None, data_inicio: date
    ) -> date:
        """Cursor inicial. Frequências baseadas em dias: a própria
        `data_inicio` (ela é a âncora - uma semanal iniciada numa sexta
        ocorre toda sexta). Baseadas em meses: `dia_vencimento` no mês da
        `data_inicio`, avançando um período se cair antes dela (lógica da
        etapa 1, preservada)."""
        if frequencia in FREQUENCIAS_BASEADAS_EM_DIAS:
            return data_inicio
        primeira = dia_valido(data_inicio.year, data_inicio.month, dia_vencimento)
        if primeira < data_inicio:
            primeira = avancar_data(primeira, frequencia, dia_vencimento)
        return primeira

    def _tem_ocorrencia_gerada(self, conta_recorrente_id: int, usuario_id: int) -> bool:
        return bool(
            self.transacao_repo.listar_do_usuario(
                usuario_id, origem_recorrente_id=conta_recorrente_id, limit=1
            )
        )

    @staticmethod
    def _validar_estrutura(conta_id: int | None, cartao_id: int | None) -> None:
        """Mesma família do `ck_conta_recorrente_cartao_xor_conta` do banco -
        validado antes para devolver um erro de negócio claro em vez de um
        IntegrityError cru."""
        if (conta_id is None) == (cartao_id is None):
            raise BusinessRuleError("Informe exatamente um entre conta_id e cartao_id.")

    @staticmethod
    def _validar_datas(data_inicio: date, data_fim: date | None) -> None:
        if data_fim is not None and data_fim < data_inicio:
            raise BusinessRuleError("data_fim não pode ser anterior a data_inicio.")

    @staticmethod
    def _validar_dia_vencimento(
        frequencia: FrequenciaRecorrencia, dia_vencimento: int | None
    ) -> None:
        """Obrigatório numa família, proibido na outra - erro claro nos
        dois sentidos (expansão 2026-07-20, substitui o bloqueio antigo de
        frequências não-MENSAL)."""
        if frequencia in FREQUENCIAS_BASEADAS_EM_DIAS:
            if dia_vencimento is not None:
                raise BusinessRuleError(
                    f"dia_vencimento não se aplica à frequência {frequencia.value} - "
                    "a âncora é a própria data_inicio."
                )
        elif dia_vencimento is None:
            raise BusinessRuleError(
                f"dia_vencimento é obrigatório para a frequência {frequencia.value}."
            )

    def _buscar_da_propriedade_do_usuario(
        self, conta_recorrente_id: int, usuario_id: int
    ) -> ContaRecorrente:
        conta_recorrente = self.conta_recorrente_repo.get(conta_recorrente_id)
        if conta_recorrente is None or conta_recorrente.usuario_id != usuario_id:
            raise NotFoundError("Conta recorrente não encontrada.")
        return conta_recorrente
