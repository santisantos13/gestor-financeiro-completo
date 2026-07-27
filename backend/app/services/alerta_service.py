"""Service de Alerta.

Alerta é a REGRA configurada (ex: "avise quando o cartão passar de 90% do
limite"), não um log/inbox de notificações já disparadas -
`ultima_disparada_em` é um único timestamp (última vez que foi avaliado
como disparado), sobrescrito a cada avaliação, nunca uma lista histórica.
`disparado`/`mensagem` são campos CALCULADOS em tempo real por
`listar_com_avaliacao`/`obter_avaliado` (nunca colunas persistidas) -
mesmo padrão de `limite_disponivel` em CartaoService e `saldo_atual` em
ContaService.

`entidade_tipo` nunca é aceito do cliente - é DERIVADO de `tipo` por
`_ENTIDADE_DO_TIPO`, eliminando a possibilidade de um par
tipo/entidade_tipo inconsistente vindo da borda da API.

Reaproveita os Services de domínio já existentes para toda validação de
posse e todo campo calculado que a avaliação precisa (nunca duplica essa
lógica aqui): `CartaoService.obter()` (`.limite`/`.limite_disponivel`),
`FaturaService.listar_recentes()` (+ `status_calculado`),
`ContaRecorrenteService.obter()` (`.proxima_execucao`/`.status`),
`MetaService.obter()` (`.concluida_em`), `ContaService.obter()`
(`.saldo_atual`). Cada um desses `obter()` já valida posse (filtra por
usuario_id, levanta NotFoundError) - `AlertaService` não reimplementa essa
checagem para a entidade referenciada, só para o próprio Alerta.

Este primeiro recorte NÃO cobre "SALDO_BAIXO agregando todas as contas"
(`entidade_id=None`) - toda regra criada aqui aponta para uma entidade
específica. `entidade_id` fica nullable no model só porque esse modo
agregado é um recorte futuro em aberto, não implementado agora.
"""
import json
from datetime import date, datetime

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Alerta
from app.models.enums import StatusFatura, StatusRecorrencia, TipoAlerta, TipoEntidadeReferenciavel
from app.repositories.alerta_repository import AlertaRepository
from app.schemas.alerta import AlertaCreate, AlertaUpdate
from app.services.cartao_service import CartaoService
from app.services.conta_recorrente_service import ContaRecorrenteService
from app.services.conta_service import ContaService
from app.services.fatura_service import FaturaService
from app.services.meta_service import MetaService

# Deriva entidade_tipo a partir de tipo - nunca escolhido pelo cliente (ver
# docstring do módulo e de `schemas/alerta.py`).
_ENTIDADE_DO_TIPO: dict[TipoAlerta, TipoEntidadeReferenciavel] = {
    TipoAlerta.LIMITE_CARTAO: TipoEntidadeReferenciavel.CARTAO,
    TipoAlerta.VENCIMENTO_FATURA: TipoEntidadeReferenciavel.CARTAO,
    TipoAlerta.VENCIMENTO_CONTA_RECORRENTE: TipoEntidadeReferenciavel.CONTA_RECORRENTE,
    TipoAlerta.META_ATINGIDA: TipoEntidadeReferenciavel.META,
    TipoAlerta.SALDO_BAIXO: TipoEntidadeReferenciavel.CONTA,
}

# Dias de antecedência padrão quando o cliente não informa `dias_antes` em
# VENCIMENTO_FATURA/VENCIMENTO_CONTA_RECORRENTE - decisão de produto (não é
# regra financeira nenhuma), só um valor de partida razoável.
_DIAS_ANTES_PADRAO = 3

# Status de Fatura que ainda representam saldo devedor em aberto - usados
# para achar "a próxima fatura a vencer" (ver `_avaliar_vencimento_fatura`).
# PAGA fica de fora de propósito: uma fatura já quitada não deveria
# disparar um alerta de vencimento.
_STATUS_FATURA_EM_ABERTO = {StatusFatura.ABERTA, StatusFatura.FECHADA, StatusFatura.PARCIALMENTE_PAGA, StatusFatura.ATRASADA}


class AlertaService:
    def __init__(
        self,
        alerta_repo: AlertaRepository,
        cartao_service: CartaoService,
        fatura_service: FaturaService,
        conta_recorrente_service: ContaRecorrenteService,
        meta_service: MetaService,
        conta_service: ContaService,
    ) -> None:
        self.alerta_repo = alerta_repo
        self.cartao_service = cartao_service
        self.fatura_service = fatura_service
        self.conta_recorrente_service = conta_recorrente_service
        self.meta_service = meta_service
        self.conta_service = conta_service

    def criar(self, dados: AlertaCreate, usuario_id: int) -> Alerta:
        entidade_tipo = _ENTIDADE_DO_TIPO[dados.tipo]
        # Valida posse da entidade referenciada ANTES de criar o alerta,
        # reaproveitando o obter() de cada Service de domínio (levanta
        # NotFoundError se não existir ou for de outro usuário) - evita
        # criar um alerta "órfão" apontando para algo inacessível.
        self._validar_entidade(dados.tipo, dados.entidade_id, usuario_id)
        condicao_normalizada = self._normalizar_condicao(dados.tipo, dados.condicao)

        alerta = Alerta(
            usuario_id=usuario_id,
            tipo=dados.tipo,
            entidade_tipo=entidade_tipo,
            entidade_id=dados.entidade_id,
            condicao=json.dumps(condicao_normalizada) if condicao_normalizada is not None else None,
            ativo=True,
        )
        alerta = self.alerta_repo.create(alerta)
        return self._com_avaliacao(alerta)

    def obter(self, alerta_id: int, usuario_id: int) -> Alerta:
        alerta = self._buscar_da_propriedade_do_usuario(alerta_id, usuario_id)
        return self._com_avaliacao(alerta)

    def listar(self, usuario_id: int, *, apenas_ativos: bool = False) -> list[Alerta]:
        alertas = self.alerta_repo.listar_do_usuario(usuario_id, apenas_ativos=apenas_ativos)
        return [self._com_avaliacao(alerta) for alerta in alertas]

    def atualizar(self, alerta_id: int, dados: AlertaUpdate, usuario_id: int) -> Alerta:
        """Só `condicao`/`ativo` são editáveis - `tipo`/`entidade_id` são
        imutáveis (ver docstring de `AlertaUpdate`: retargetar é, na
        prática, excluir e criar outro)."""
        alerta = self._buscar_da_propriedade_do_usuario(alerta_id, usuario_id)
        alteracoes = dados.model_dump(exclude_unset=True)

        if "condicao" in alteracoes:
            condicao_normalizada = self._normalizar_condicao(alerta.tipo, alteracoes["condicao"])
            alerta.condicao = json.dumps(condicao_normalizada) if condicao_normalizada is not None else None
        if "ativo" in alteracoes:
            alerta.ativo = alteracoes["ativo"]

        alerta = self.alerta_repo.update(alerta)
        return self._com_avaliacao(alerta)

    def excluir(self, alerta_id: int, usuario_id: int) -> None:
        alerta = self._buscar_da_propriedade_do_usuario(alerta_id, usuario_id)
        self.alerta_repo.delete(alerta)

    def _buscar_da_propriedade_do_usuario(self, alerta_id: int, usuario_id: int) -> Alerta:
        alerta = self.alerta_repo.get(alerta_id)
        if alerta is None or alerta.usuario_id != usuario_id:
            # Mesmo tratamento (404) para "não existe" e "é de outro
            # usuário" - anti-enumeração (BOLA), mesmo padrão do resto do projeto.
            raise NotFoundError("Alerta não encontrado.")
        return alerta

    def _validar_entidade(self, tipo: TipoAlerta, entidade_id: int, usuario_id: int) -> None:
        """Reaproveita `obter()` de cada Service de domínio só para validar
        posse - o resultado em si não é usado aqui (a avaliação de verdade
        acontece em `_com_avaliacao`, por request, para nunca ficar
        desatualizada)."""
        if tipo == TipoAlerta.LIMITE_CARTAO or tipo == TipoAlerta.VENCIMENTO_FATURA:
            self.cartao_service.obter(entidade_id, usuario_id)
        elif tipo == TipoAlerta.VENCIMENTO_CONTA_RECORRENTE:
            self.conta_recorrente_service.obter(entidade_id, usuario_id)
        elif tipo == TipoAlerta.META_ATINGIDA:
            self.meta_service.obter(entidade_id, usuario_id)
        elif tipo == TipoAlerta.SALDO_BAIXO:
            self.conta_service.obter(entidade_id, usuario_id)

    # --- condicao: formato depende do tipo, validado/normalizado aqui ------

    def _normalizar_condicao(self, tipo: TipoAlerta, condicao: dict | None) -> dict | None:
        """Valida os campos esperados por `tipo` e preenche default onde
        aplicável. Formato por tipo (documentado aqui, único lugar - ver
        docstring de `schemas/alerta.py`):
        - LIMITE_CARTAO: {"limite_percentual": float} - obrigatório.
        - VENCIMENTO_FATURA / VENCIMENTO_CONTA_RECORRENTE: {"dias_antes": int}
          - opcional, default `_DIAS_ANTES_PADRAO`.
        - META_ATINGIDA: nenhuma - sempre None.
        - SALDO_BAIXO: {"valor_minimo": float} - obrigatório.
        """
        condicao = condicao or {}
        if tipo == TipoAlerta.LIMITE_CARTAO:
            if "limite_percentual" not in condicao:
                raise BusinessRuleError('Informe "limite_percentual" (ex: 90 para avisar ao atingir 90% do limite).')
            valor = float(condicao["limite_percentual"])
            if valor <= 0:
                raise BusinessRuleError('"limite_percentual" deve ser maior que zero.')
            return {"limite_percentual": valor}

        if tipo in (TipoAlerta.VENCIMENTO_FATURA, TipoAlerta.VENCIMENTO_CONTA_RECORRENTE):
            dias_antes = int(condicao.get("dias_antes", _DIAS_ANTES_PADRAO))
            if dias_antes < 0:
                raise BusinessRuleError('"dias_antes" não pode ser negativo.')
            return {"dias_antes": dias_antes}

        if tipo == TipoAlerta.META_ATINGIDA:
            return None

        if tipo == TipoAlerta.SALDO_BAIXO:
            if "valor_minimo" not in condicao:
                raise BusinessRuleError('Informe "valor_minimo" (avisa quando o saldo da conta ficar abaixo deste valor).')
            return {"valor_minimo": float(condicao["valor_minimo"])}

        return None

    # --- avaliação em tempo real (nunca persistida como notificação) ------

    def _com_avaliacao(self, alerta: Alerta) -> Alerta:
        """Anexa `disparado`/`mensagem` (calculados, nunca armazenados) ao
        objeto Alerta antes de devolvê-lo - mesmo padrão de
        `limite_disponivel`/`saldo_atual`/`concluida_em` nos outros
        Services. Um alerta desativado não é avaliado (`disparado=None`) -
        evita gastar uma leitura de outra entidade à toa, e evita marcar
        `ultima_disparada_em` de uma regra que o usuário pausou.

        Quando disparado, atualiza `ultima_disparada_em` best-effort (não é
        crítico se ficar levemente desatualizado entre leituras - não há
        nenhuma outra lógica no sistema que dependa deste timestamp além de
        exibi-lo)."""
        if not alerta.ativo:
            alerta.disparado = None
            alerta.mensagem = None
            return alerta

        condicao = json.loads(alerta.condicao) if alerta.condicao else {}
        try:
            disparado, mensagem = self._avaliar(alerta, condicao)
        except NotFoundError:
            # A entidade referenciada foi excluída depois que o alerta foi
            # criado (ex: cartão apagado) - trata como "não dispara" em vez
            # de propagar o erro, para não quebrar a listagem inteira por
            # causa de um alerta órfão.
            disparado, mensagem = False, None

        alerta.disparado = disparado
        alerta.mensagem = mensagem
        if disparado:
            alerta.ultima_disparada_em = datetime.now()
            self.alerta_repo.update(alerta)
        return alerta

    def _avaliar(self, alerta: Alerta, condicao: dict) -> tuple[bool, str | None]:
        if alerta.tipo == TipoAlerta.LIMITE_CARTAO:
            return self._avaliar_limite_cartao(alerta, condicao)
        if alerta.tipo == TipoAlerta.VENCIMENTO_FATURA:
            return self._avaliar_vencimento_fatura(alerta, condicao)
        if alerta.tipo == TipoAlerta.VENCIMENTO_CONTA_RECORRENTE:
            return self._avaliar_vencimento_conta_recorrente(alerta, condicao)
        if alerta.tipo == TipoAlerta.META_ATINGIDA:
            return self._avaliar_meta_atingida(alerta)
        if alerta.tipo == TipoAlerta.SALDO_BAIXO:
            return self._avaliar_saldo_baixo(alerta, condicao)
        return False, None

    def _avaliar_limite_cartao(self, alerta: Alerta, condicao: dict) -> tuple[bool, str | None]:
        cartao = self.cartao_service.obter(alerta.entidade_id, alerta.usuario_id)
        if cartao.limite <= 0:
            return False, None
        percentual_utilizado = float((1 - (cartao.limite_disponivel / cartao.limite)) * 100)
        limite_percentual = condicao["limite_percentual"]
        disparado = percentual_utilizado >= limite_percentual
        mensagem = (
            f'Cartão "{cartao.nome}" já usou {percentual_utilizado:.0f}% do limite '
            f"(aviso configurado para {limite_percentual:.0f}%)."
            if disparado
            else None
        )
        return disparado, mensagem

    def _avaliar_vencimento_fatura(self, alerta: Alerta, condicao: dict) -> tuple[bool, str | None]:
        cartao = self.cartao_service.obter(alerta.entidade_id, alerta.usuario_id)
        faturas = self.fatura_service.listar_recentes(alerta.entidade_id, alerta.usuario_id, limit=12)
        em_aberto = [f for f in faturas if f.status_calculado in _STATUS_FATURA_EM_ABERTO]
        if not em_aberto:
            return False, None
        proxima = min(em_aberto, key=lambda f: f.data_vencimento)
        dias_restantes = (proxima.data_vencimento - date.today()).days
        dias_antes = condicao["dias_antes"]
        disparado = 0 <= dias_restantes <= dias_antes
        mensagem = (
            f'Fatura do cartão "{cartao.nome}" vence em {dias_restantes} dia(s) '
            f"({proxima.data_vencimento.strftime('%d/%m/%Y')})."
            if disparado
            else None
        )
        return disparado, mensagem

    def _avaliar_vencimento_conta_recorrente(self, alerta: Alerta, condicao: dict) -> tuple[bool, str | None]:
        recorrente = self.conta_recorrente_service.obter(alerta.entidade_id, alerta.usuario_id)
        if recorrente.status != StatusRecorrencia.ATIVA:
            return False, None
        dias_restantes = (recorrente.proxima_execucao - date.today()).days
        dias_antes = condicao["dias_antes"]
        disparado = 0 <= dias_restantes <= dias_antes
        mensagem = (
            f'"{recorrente.descricao}" vence em {dias_restantes} dia(s) '
            f"({recorrente.proxima_execucao.strftime('%d/%m/%Y')})."
            if disparado
            else None
        )
        return disparado, mensagem

    def _avaliar_meta_atingida(self, alerta: Alerta) -> tuple[bool, str | None]:
        meta = self.meta_service.obter(alerta.entidade_id, alerta.usuario_id)
        disparado = meta.concluida_em is not None
        mensagem = f'Meta "{meta.descricao}" foi atingida!' if disparado else None
        return disparado, mensagem

    def _avaliar_saldo_baixo(self, alerta: Alerta, condicao: dict) -> tuple[bool, str | None]:
        conta = self.conta_service.obter(alerta.entidade_id, alerta.usuario_id)
        valor_minimo = condicao["valor_minimo"]
        disparado = float(conta.saldo_atual) < valor_minimo
        mensagem = (
            f'Conta "{conta.nome}" está com saldo baixo: R$ {conta.saldo_atual:.2f} '
            f"(mínimo configurado: R$ {valor_minimo:.2f})."
            if disparado
            else None
        )
        return disparado, mensagem
