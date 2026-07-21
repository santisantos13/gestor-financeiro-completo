"""Service da Central Financeira - camada de orquestração e agregação pura.

Ver docs/analise-arquitetural-central-financeira.md para a análise completa
que precede este código. Três regras estruturais, sem exceção, em todo
método abaixo:

1. Nunca acessa um Repository - só os Services de domínio já existentes
   (`ContaService`, `CartaoService`, `FaturaService`, `TransacaoService`,
   `FinanciamentoService`, `EmprestimoService`, `ParcelamentoService`,
   `MetaService`), injetados por construtor. Este Service não tem
   Repository próprio.
2. Nunca duplica um cálculo que já existe em outro Service - `saldo_atual`,
   `limite_disponivel`, `valor_total_calculado`/`status_calculado`,
   `valor_acumulado`/`percentual`, `saldo_devedor` são sempre LIDOS do
   objeto que o Service dono já devolveu calculado, nunca recalculados
   aqui.
3. Toda soma/contagem feita AQUI (nunca dentro de um Service de domínio) é
   aritmética sobre resultados já agregados por outro Service (ex: fluxo de
   caixa = entradas − saídas) ou uma contagem/soma em Python sobre uma lista
   já pequena e limitada por natureza (parcelas de UM contrato, cartões de
   UMA pessoa) - nunca uma agregação sobre a tabela inteira de `Transacao`
   feita em Python (isso é sempre delegado a
   `TransacaoService.somar_por_periodo`, que roda como `SUM` no banco).

Nenhum método aqui levanta `BusinessRuleError`/`ConflictError` - são
sempre leituras, nunca haveria uma regra de negócio para violar. `obter()`
dos Services de domínio já garante isolamento por usuário (404 uniforme
para "não existe" e "é de outro usuário"), então essa camada herda essa
garantia de graça, sem reimplementar nada.
"""
import calendar
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.models import Cartao, Fatura
from app.models.enums import (
    CategoriaEventoCalendario,
    StatusContratoCredito,
    StatusFatura,
    StatusTransacao,
    TipoEntidadeReferenciavel,
    TipoTransacao,
)
from app.services.cartao_service import CartaoService
from app.services.conta_recorrente_service import ContaRecorrenteService
from app.services.conta_service import ContaService
from app.services.emprestimo_service import EmprestimoService
from app.services.fatura_service import FaturaService
from app.services.financiamento_service import FinanciamentoService
from app.services.meta_service import MetaService
from app.services.parcelamento_service import ParcelamentoService
from app.services.transacao_service import TransacaoService
from app.services.transferencia_service import TransferenciaService

_DUAS_CASAS = Decimal("0.01")
_LIMITE_TRANSACOES_AGENDA = 500
_LIMITE_TRANSACOES_ATRASADAS = 1000
_LIMITE_TRANSACOES_CALENDARIO = 500
_LIMITE_TRANSFERENCIAS_CALENDARIO = 500


class CentralFinanceiraService:
    def __init__(
        self,
        conta_service: ContaService,
        cartao_service: CartaoService,
        fatura_service: FaturaService,
        transacao_service: TransacaoService,
        financiamento_service: FinanciamentoService,
        emprestimo_service: EmprestimoService,
        parcelamento_service: ParcelamentoService,
        meta_service: MetaService,
        transferencia_service: TransferenciaService,
        conta_recorrente_service: "ContaRecorrenteService | None" = None,
    ) -> None:
        self.conta_service = conta_service
        self.cartao_service = cartao_service
        self.fatura_service = fatura_service
        self.transacao_service = transacao_service
        self.financiamento_service = financiamento_service
        self.emprestimo_service = emprestimo_service
        self.parcelamento_service = parcelamento_service
        self.meta_service = meta_service
        # Só usado por `calendario_financeiro` (seção "Calendário Financeiro",
        # Etapa de Transferências) - nenhum outro método desta classe lê
        # Transferencia. Injetado por último para não reordenar os
        # parâmetros posicionais já usados por `get_central_financeira_service`
        # (`api/deps.py`) e pelos testes unitários existentes.
        self.transferencia_service = transferencia_service
        # Expansão de Contas Recorrentes (2026-07-20): usado só por
        # `calendario_financeiro` para a projeção VIRTUAL de ocorrências
        # futuras (eventos `previsto=True`, horizonte de 90 dias, nada
        # persistido). Default None pelo mesmo motivo do comentário acima
        # (testes unitários constroem com posicionais); quando None, o
        # calendário simplesmente não projeta nada.
        self.conta_recorrente_service = conta_recorrente_service

    # --- 1. resumo financeiro geral ------------------------------------------

    def resumo_financeiro(self, usuario_id: int, *, ano: int | None = None, mes: int | None = None) -> dict:
        hoje = date.today()
        ano = ano or hoje.year
        mes = mes or hoje.month
        data_inicio, data_fim = self._limites_do_mes(ano, mes)

        saldo_total = self._saldo_total(usuario_id)
        entradas_mes = self._somar_periodo(usuario_id, TipoTransacao.RECEITA, data_inicio, data_fim)
        saidas_mes = self._somar_periodo(usuario_id, TipoTransacao.DESPESA, data_inicio, data_fim)
        fluxo_caixa_mes = entradas_mes - saidas_mes

        divida_total = (
            self._saldo_devedor_total(self.financiamento_service.listar(usuario_id, apenas_ativos=True))
            + self._saldo_devedor_total(self.emprestimo_service.listar(usuario_id, apenas_ativos=True))
            + self._total_faturas_em_aberto(usuario_id)
            + self._saldo_restante_parcelamentos(usuario_id)
        )

        return {
            "ano": ano,
            "mes": mes,
            "saldo_total": saldo_total,
            "entradas_mes": entradas_mes,
            "saidas_mes": saidas_mes,
            "fluxo_caixa_mes": fluxo_caixa_mes,
            "patrimonio_liquido": saldo_total - divida_total,
        }

    # --- 2. saldo consolidado -------------------------------------------------

    def saldo_consolidado(self, usuario_id: int) -> dict:
        """`saldo_total` PRECISA somar todo cofrinho de Meta também (o
        dinheiro é real e conta no patrimônio, ver
        docs/analise-arquitetural-metas-transferencias.md, seção 1.1) -
        por isso busca com `apenas_visiveis=False`. A lista `contas`
        (usada pelo Frontend para o detalhamento por conta, ver
        `SaldoPorContaCard`) continua excluindo cofrinhos - o usuário nunca
        pediu para vê-los individualmente, só o valor deles já embutido no
        total."""
        todas_as_contas = self.conta_service.listar(usuario_id, apenas_ativas=True, apenas_visiveis=False)
        return {
            "saldo_total": sum((c.saldo_atual for c in todas_as_contas), Decimal("0")),
            "contas": [c for c in todas_as_contas if not c.oculta],
        }

    # --- 3. resumo das contas --------------------------------------------------

    def resumo_contas(self, usuario_id: int) -> dict:
        return {"contas": self.conta_service.listar(usuario_id, apenas_ativas=True)}

    # --- 4. resumo dos cartões --------------------------------------------------

    def resumo_cartoes(self, usuario_id: int) -> dict:
        cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)
        return {
            "cartoes": cartoes,
            "total_utilizado": self._total_faturas_em_aberto(usuario_id, cartoes=cartoes),
        }

    # --- 4b. panorama agregado dos cartões ("Dashboard de Cartões") --------------

    def resumo_cartoes_agregado(self, usuario_id: int) -> dict:
        """Panorama agregado para o "Dashboard de Cartões" (Sprint de
        Refinamento Premium, item 3) - só soma/conta/ordena sobre
        `CartaoRead`/`FaturaRead` que `CartaoService`/`FaturaService` já
        devolvem calculados (`limite`, `limite_disponivel`,
        `status_calculado`, `data_vencimento`, `valor_total_calculado`) -
        nenhuma fórmula nova. Deliberadamente SEM nenhum gráfico por
        cartão individual - isso continua exclusivo de `/cartoes/:id`."""
        cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)

        limite_total = sum((c.limite for c in cartoes), Decimal("0"))
        limite_disponivel_total = sum((c.limite_disponivel for c in cartoes), Decimal("0"))
        limite_usado_total = limite_total - limite_disponivel_total
        percentual_usado_geral = (
            (limite_usado_total / limite_total * 100).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)
            if limite_total > 0
            else Decimal("0")
        )

        distribuicao_uso = []
        for cartao in cartoes:
            percentual = (
                ((cartao.limite - cartao.limite_disponivel) / cartao.limite * 100).quantize(
                    _DUAS_CASAS, rounding=ROUND_HALF_UP
                )
                if cartao.limite > 0
                else Decimal("0")
            )
            distribuicao_uso.append({"cartao_id": cartao.id, "nome": cartao.nome, "percentual_usado": percentual})

        faturas_em_aberto = 0
        proximos_vencimentos = []
        for cartao in cartoes:
            fatura = self._fatura_aberta_do_cartao(cartao, usuario_id)
            if fatura is None:
                continue
            if fatura.status_calculado == StatusFatura.ABERTA:
                faturas_em_aberto += 1
            if fatura.status_calculado in (StatusFatura.ABERTA, StatusFatura.FECHADA, StatusFatura.ATRASADA):
                proximos_vencimentos.append(
                    {
                        "cartao_id": cartao.id,
                        "cartao_nome": cartao.nome,
                        "fatura_id": fatura.id,
                        "data_vencimento": fatura.data_vencimento,
                        "valor_total": fatura.valor_total_calculado,
                    }
                )
        proximos_vencimentos.sort(key=lambda evento: evento["data_vencimento"])

        return {
            "limite_total": limite_total,
            "limite_disponivel_total": limite_disponivel_total,
            "limite_usado_total": limite_usado_total,
            "percentual_usado_geral": percentual_usado_geral,
            "quantidade_cartoes": len(cartoes),
            "faturas_em_aberto": faturas_em_aberto,
            "proximos_vencimentos": proximos_vencimentos[:3],
            "distribuicao_uso": distribuicao_uso,
        }

    # --- 5. resumo das faturas --------------------------------------------------

    def resumo_faturas(self, usuario_id: int, *, limite_por_cartao: int = 12) -> dict:
        cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)
        faturas: list[Fatura] = []
        for cartao in cartoes:
            faturas.extend(self.fatura_service.listar(cartao.id, usuario_id, limit=limite_por_cartao))
        return {"faturas": faturas}

    # --- 6. resumo de financiamentos --------------------------------------------

    def resumo_financiamentos(self, usuario_id: int) -> dict:
        financiamentos = self.financiamento_service.listar(usuario_id, apenas_ativos=True)
        resumos = []
        for financiamento in financiamentos:
            metricas = self._metricas_de_parcelas(
                usuario_id, financiamento_id=financiamento.id, num_parcelas=financiamento.num_parcelas
            )
            resumos.append(self._combinar(financiamento, metricas))
        return {"financiamentos": resumos}

    # --- 7. resumo de empréstimos ------------------------------------------------

    def resumo_emprestimos(self, usuario_id: int) -> dict:
        emprestimos = self.emprestimo_service.listar(usuario_id, apenas_ativos=True)
        resumos = []
        for emprestimo in emprestimos:
            metricas = self._metricas_de_parcelas(
                usuario_id, emprestimo_id=emprestimo.id, num_parcelas=emprestimo.num_parcelas
            )
            resumos.append(self._combinar(emprestimo, metricas))
        return {"emprestimos": resumos}

    # --- 8. progresso das metas ---------------------------------------------------

    def progresso_metas(self, usuario_id: int) -> dict:
        return {"metas": self.meta_service.listar(usuario_id, apenas_ativas=True)}

    # --- 9. agenda financeira (próximos vencimentos) -------------------------------

    def agenda_financeira(self, usuario_id: int, *, dias: int = 30) -> dict:
        """Funde duas fontes já materializadas - `Transacao` PENDENTE e
        `Fatura` com vencimento futuro - num único DTO ordenado por data.
        Não projeta ocorrências futuras de `ContaRecorrente` ainda não
        geradas: gap consciente, registrado em
        docs/analise-arquitetural-central-financeira.md (seção 4)."""
        hoje = date.today()
        limite = hoje + timedelta(days=dias)

        eventos = []
        parcelas = self.transacao_service.listar(
            usuario_id,
            status=StatusTransacao.PENDENTE,
            data_inicio=hoje,
            data_fim=limite,
            limit=_LIMITE_TRANSACOES_AGENDA,
        )
        for parcela in parcelas:
            origem_tipo, origem_id = self._origem_da_transacao(parcela)
            eventos.append(
                {
                    "data": parcela.data,
                    "descricao": parcela.descricao,
                    "valor": parcela.valor,
                    "origem_tipo": origem_tipo,
                    "origem_id": origem_id,
                }
            )

        cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)
        for cartao in cartoes:
            for fatura in self.fatura_service.listar_recentes(cartao.id, usuario_id, limit=3):
                if fatura.status_calculado == StatusFatura.PAGA:
                    continue
                if not (hoje <= fatura.data_vencimento <= limite):
                    continue
                eventos.append(
                    {
                        "data": fatura.data_vencimento,
                        "descricao": f"Fatura {cartao.nome}",
                        "valor": fatura.valor_total_calculado,
                        "origem_tipo": TipoEntidadeReferenciavel.FATURA,
                        "origem_id": fatura.id,
                    }
                )

        eventos.sort(key=lambda evento: evento["data"])
        return {"eventos": eventos}

    # --- 9b. calendário financeiro (mês inteiro, todo status) -----------------------

    def calendario_financeiro(self, usuario_id: int, *, ano: int | None = None, mes: int | None = None) -> dict:
        """Irmão de `agenda_financeira` acima, NÃO uma substituição - ver
        docstring de `EventoCalendario` (`schemas/central_financeira.py`).
        Diferenças deliberadas: (1) escopo é o MÊS inteiro (`ano`/`mes`,
        mesmo padrão de `resumo_financeiro`/`visao_mensal`), não "próximos N
        dias"; (2) Transacao entra com QUALQUER status (PAGO e PENDENTE) -
        o calendário conta a história do mês inteiro, passado e futuro, não
        só o que falta acontecer; (3) inclui Transferencia e Meta, que
        `agenda_financeira` nunca incluiu (gap identificado na análise
        arquitetural de Transferências, seção 2); (4) Fatura entra até DUAS
        vezes (fechamento e vencimento), quando ambas as datas caem dentro
        do mês - `agenda_financeira` só olha vencimento.

        `apenas_conta=True` na busca de Transacao (bug real corrigido em
        2026-07-20, pedido explícito do usuário: "o ideal é que no
        calendário apareça apenas pagamento de faturas, faturas abertas,
        etc" - parcelas de compra no cartão não deveriam aparecer aqui).
        Sem esse filtro, cada parcela de uma compra parcelada no cartão
        (sempre `status=PAGO`, nunca some do filtro por status como em
        `agenda_financeira`) virava um evento RECEITA/DESPESA todo santo
        mês do parcelamento - poluição visual e redundante com o evento de
        "Vencimento — fatura" (que já representa o ciclo inteiro). O
        cartão permanece representado no calendário só pelos eventos de
        Fatura (fechamento/vencimento) logo abaixo - nunca por transação
        individual.

        Nenhuma soma/cálculo novo é inventado aqui: todo valor exposto já
        vem pronto do Service dono (mesmas 3 regras estruturais do
        cabeçalho deste arquivo)."""
        hoje = date.today()
        ano = ano or hoje.year
        mes = mes or hoje.month
        data_inicio, data_fim = self._limites_do_mes(ano, mes)

        eventos = []

        # Transações do mês, qualquer status - PAGO conta o que já aconteceu,
        # PENDENTE o que está previsto (mesma distinção que colore o dot).
        transacoes = self.transacao_service.listar(
            usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_conta=True,
            limit=_LIMITE_TRANSACOES_CALENDARIO,
        )
        for transacao in transacoes:
            origem_tipo, origem_id = self._origem_da_transacao(transacao)
            # Financiamento/Empréstimo ganham categoria própria (cor
            # dedicada na legenda) em vez de caírem em RECEITA/DESPESA
            # genérico - pedido do usuário (2026-07-21): "o calendário
            # precisa marcar TODOS os tipos de evento". O dado já estava
            # correto (confirmado via reprodução direta no backend: parcela
            # de Financiamento/Empréstimo sempre aparecia aqui), o gap real
            # era só de exibição - as duas ficavam visualmente idênticas a
            # qualquer outra Transacao. Parcelamento/ContaRecorrente
            # continuam RECEITA/DESPESA (não pedido, e já distinguíveis pelo
            # ícone no Drawer via origemNavegacao.ts).
            if origem_tipo == TipoEntidadeReferenciavel.FINANCIAMENTO:
                categoria = CategoriaEventoCalendario.FINANCIAMENTO
            elif origem_tipo == TipoEntidadeReferenciavel.EMPRESTIMO:
                categoria = CategoriaEventoCalendario.EMPRESTIMO
            else:
                categoria = (
                    CategoriaEventoCalendario.RECEITA
                    if transacao.tipo == TipoTransacao.RECEITA
                    else CategoriaEventoCalendario.DESPESA
                )
            eventos.append(
                {
                    "data": transacao.data,
                    "descricao": transacao.descricao,
                    "valor": transacao.valor,
                    "categoria": categoria,
                    "origem_tipo": origem_tipo,
                    "origem_id": origem_id,
                    "status": transacao.status.value,
                }
            )

        # Fatura: fechamento e vencimento são dois eventos DISTINTOS (cores
        # diferentes) quando os dois caem no mês consultado - mesmo cartão
        # pode gerar até 2 linhas. `limit=3` é o mesmo recorte já usado por
        # `agenda_financeira` (o ciclo do mês corrente + folga de 2 ciclos) -
        # `listar_recentes` (mais recente primeiro), NUNCA `listar` (ordem
        # cronológica ascendente, para a tela de listagem de faturas): bug
        # real corrigido em 2026-07-21 ("calendário não exibe fechamento/
        # vencimento de fatura") - com `listar` + `limit=3`, qualquer cartão
        # com mais de 3 meses de uso só devolvia os 3 ciclos mais ANTIGOS,
        # nunca o atual.
        cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)
        for cartao in cartoes:
            for fatura in self.fatura_service.listar_recentes(cartao.id, usuario_id, limit=3):
                status_fatura = fatura.status_calculado.value
                if data_inicio <= fatura.data_fechamento <= data_fim:
                    eventos.append(
                        {
                            "data": fatura.data_fechamento,
                            "descricao": f"Fechamento — fatura {cartao.nome}",
                            "valor": fatura.valor_total_calculado,
                            "categoria": CategoriaEventoCalendario.FATURA_FECHAMENTO,
                            "origem_tipo": TipoEntidadeReferenciavel.FATURA,
                            "origem_id": fatura.id,
                            "status": status_fatura,
                        }
                    )
                if data_inicio <= fatura.data_vencimento <= data_fim:
                    eventos.append(
                        {
                            "data": fatura.data_vencimento,
                            "descricao": f"Vencimento — fatura {cartao.nome}",
                            "valor": fatura.valor_total_calculado,
                            "categoria": CategoriaEventoCalendario.FATURA_VENCIMENTO,
                            "origem_tipo": TipoEntidadeReferenciavel.FATURA,
                            "origem_id": fatura.id,
                            "status": status_fatura,
                        }
                    )

        # Transferência: só as ATIVAS (mesmo raciocínio de saldo - uma
        # transferência cancelada não moveu dinheiro nenhum, não faz sentido
        # como evento do mês). Nomes de conta vêm de uma única listagem
        # (`apenas_ativas=False` inclui contas já desativadas - uma
        # transferência antiga pode referenciar uma conta hoje inativa;
        # `apenas_visiveis=False` inclui cofrinhos de Meta - um aporte/
        # resgate é uma Transferência normal e precisa do nome real do
        # cofrinho no evento, não do fallback genérico "Conta").
        contas = self.conta_service.listar(usuario_id, apenas_ativas=False, apenas_visiveis=False)
        nome_conta_por_id = {conta.id: conta.nome for conta in contas}
        transferencias = self.transferencia_service.listar(
            usuario_id, apenas_ativas=True, limit=_LIMITE_TRANSFERENCIAS_CALENDARIO
        )
        for transferencia in transferencias:
            if not (data_inicio <= transferencia.data <= data_fim):
                continue
            origem_nome = nome_conta_por_id.get(transferencia.conta_origem_id, "Conta")
            destino_nome = nome_conta_por_id.get(transferencia.conta_destino_id, "Conta")
            descricao = transferencia.descricao or f"{origem_nome} → {destino_nome}"
            eventos.append(
                {
                    "data": transferencia.data,
                    "descricao": descricao,
                    "valor": transferencia.valor,
                    "categoria": CategoriaEventoCalendario.TRANSFERENCIA,
                    "origem_tipo": TipoEntidadeReferenciavel.TRANSFERENCIA,
                    "origem_id": transferencia.id,
                    "status": "ATIVA",
                }
            )

        # Meta: prazo (`data_alvo`) dentro do mês - campo opcional no model,
        # metas sem prazo definido nunca entram no calendário (nada a
        # marcar).
        metas = self.meta_service.listar(usuario_id, apenas_ativas=True)
        for meta in metas:
            if meta.data_alvo is None or not (data_inicio <= meta.data_alvo <= data_fim):
                continue
            eventos.append(
                {
                    "data": meta.data_alvo,
                    "descricao": meta.descricao,
                    "valor": meta.valor_alvo,
                    "categoria": CategoriaEventoCalendario.META,
                    "origem_tipo": TipoEntidadeReferenciavel.META,
                    "origem_id": meta.id,
                    "status": f"{meta.percentual}%",
                }
            )

        # Projeção VIRTUAL de recorrências futuras (expansão de Contas
        # Recorrentes, 2026-07-20, decisão do usuário: até 90 dias à
        # frente, nunca persistido). Eventos saem com `previsto=True` - o
        # frontend os renderiza com estilo próprio (previsão, não
        # história). Só datas estritamente futuras entram: o passado
        # pendente vira Transacao REAL via sincronização, nunca projeção
        # (as duas nunca se sobrepõem, então não há risco de o mesmo
        # lançamento aparecer duas vezes).
        if self.conta_recorrente_service is not None:
            projecoes = self.conta_recorrente_service.projetar_ocorrencias(
                usuario_id, data_inicio, data_fim
            )
            for projecao in projecoes:
                categoria = (
                    CategoriaEventoCalendario.RECEITA
                    if projecao["tipo"] == TipoTransacao.RECEITA
                    else CategoriaEventoCalendario.DESPESA
                )
                eventos.append(
                    {
                        "data": projecao["data"],
                        "descricao": projecao["descricao"],
                        "valor": projecao["valor"],
                        "categoria": categoria,
                        "origem_tipo": TipoEntidadeReferenciavel.CONTA_RECORRENTE,
                        "origem_id": projecao["origem_id"],
                        "status": "PREVISTO",
                        "previsto": True,
                    }
                )

        eventos.sort(key=lambda evento: evento["data"])
        return {"ano": ano, "mes": mes, "eventos": eventos}

    # --- 9c. central de atividades (feed cronológico) -------------------------------

    def atividades_recentes(self, usuario_id: int, *, limit: int = 30) -> dict:
        """Central de Atividades (Sprint de Refinamento Premium, item 17,
        `docs/analise-arquitetural-sprint-refinamento-premium.md`, seção
        17): "o que aconteceu recentemente", combinando Transação +
        Transferência + Meta concluída. `data_hora` usa sempre a data
        REGISTRADA no lançamento (`data` de Transação/Transferência,
        `concluida_em` de Meta) combinada com meia-noite - nunca
        `criado_em` (timestamp de auditoria de quando a linha foi
        inserida no banco), que fazia tudo aparecer com a data/hora de
        HOJE independente da data real do lançamento (bug relatado pelo
        usuário, 2026-07-21). Nenhuma tabela/campo novo: cada fonte já
        vem de um Service de domínio existente, e a combinação/ordenação
        abaixo é só Python sobre 3 listas já pequenas e limitadas (regra
        3 do cabeçalho deste arquivo), nunca uma query nova."""
        atividades = []

        transacoes = self.transacao_service.listar(usuario_id, limit=limit)
        for transacao in transacoes:
            origem_tipo, origem_id = self._origem_da_transacao(transacao)
            atividades.append(
                {
                    # `criado_em` é o timestamp de AUDITORIA (quando a linha foi
                    # inserida no banco) - usá-lo aqui fazia toda transação
                    # aparecer com a data/hora de HOJE no feed, mesmo para
                    # lançamentos com data passada/futura (ex: parcelas de
                    # cartão). O campo correto é `data`, a data efetivamente
                    # registrada no lançamento (bug relatado pelo usuário,
                    # 2026-07-21). `data` é só Date (sem hora), então
                    # combinamos com meia-noite, igual já era feito para Meta
                    # logo abaixo - mesma convenção, sem inventar hora nenhuma.
                    "data_hora": datetime.combine(transacao.data, time.min),
                    "descricao": transacao.descricao,
                    "valor": transacao.valor,
                    "origem_tipo": origem_tipo,
                    "origem_id": origem_id,
                }
            )

        transferencias = self.transferencia_service.listar(usuario_id, apenas_ativas=True, limit=limit)
        for transferencia in transferencias:
            atividades.append(
                {
                    "data_hora": datetime.combine(transferencia.data, time.min),
                    "descricao": transferencia.descricao or "Transferência entre contas",
                    "valor": transferencia.valor,
                    "origem_tipo": TipoEntidadeReferenciavel.TRANSFERENCIA,
                    "origem_id": transferencia.id,
                }
            )

        metas = self.meta_service.listar(usuario_id, apenas_ativas=True, limit=limit)
        for meta in metas:
            if meta.concluida_em is None:
                continue
            atividades.append(
                {
                    "data_hora": datetime.combine(meta.concluida_em, time.min),
                    "descricao": f"Meta concluída: {meta.descricao}",
                    "valor": meta.valor_alvo,
                    "origem_tipo": TipoEntidadeReferenciavel.META,
                    "origem_id": meta.id,
                }
            )

        atividades.sort(key=lambda atividade: atividade["data_hora"], reverse=True)
        return {"atividades": atividades[:limit]}

    # --- 10. visão mensal ------------------------------------------------------------

    def visao_mensal(self, usuario_id: int, *, ano: int | None = None, mes: int | None = None) -> dict:
        hoje = date.today()
        ano = ano or hoje.year
        mes = mes or hoje.month
        data_inicio, data_fim = self._limites_do_mes(ano, mes)
        entradas = self._somar_periodo(usuario_id, TipoTransacao.RECEITA, data_inicio, data_fim)
        saidas = self._somar_periodo(usuario_id, TipoTransacao.DESPESA, data_inicio, data_fim)
        return {"ano": ano, "mes": mes, "entradas": entradas, "saidas": saidas, "fluxo_caixa": entradas - saidas}

    # --- 11. indicadores gerais --------------------------------------------------------

    def indicadores_gerais(self, usuario_id: int) -> dict:
        contas = self.conta_service.listar(usuario_id, apenas_ativas=True)
        cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)
        financiamentos = self.financiamento_service.listar(usuario_id, apenas_ativos=True)
        emprestimos = self.emprestimo_service.listar(usuario_id, apenas_ativos=True)
        metas = self.meta_service.listar(usuario_id, apenas_ativas=True)

        faturas_abertas = sum(
            1
            for cartao in cartoes
            if (fatura := self._fatura_aberta_do_cartao(cartao, usuario_id)) is not None
            and fatura.status_calculado == StatusFatura.ABERTA
        )

        percentual_medio = (
            (sum((m.percentual for m in metas), Decimal("0")) / len(metas)).quantize(
                _DUAS_CASAS, rounding=ROUND_HALF_UP
            )
            if metas
            else Decimal("0.00")
        )

        return {
            "contas_ativas": len(contas),
            "cartoes_ativos": len(cartoes),
            "faturas_em_aberto": faturas_abertas,
            "financiamentos_ativos": len(financiamentos),
            "emprestimos_ativos": len(emprestimos),
            "metas_ativas": len(metas),
            "percentual_medio_metas": percentual_medio,
            "parcelas_atrasadas": self._contar_parcelas_atrasadas(usuario_id),
        }

    # --- helpers privados de orquestração (nenhuma regra de negócio nova) ------------

    @staticmethod
    def _limites_do_mes(ano: int, mes: int) -> tuple[date, date]:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return date(ano, mes, 1), date(ano, mes, ultimo_dia)

    def _saldo_total(self, usuario_id: int) -> Decimal:
        """`apenas_visiveis=False`: patrimônio líquido precisa somar
        também o saldo de todo cofrinho de Meta (dinheiro real do
        usuário, só guardado num objetivo) - mesmo raciocínio de
        `saldo_consolidado` acima."""
        contas = self.conta_service.listar(usuario_id, apenas_ativas=True, apenas_visiveis=False)
        return sum((c.saldo_atual for c in contas), Decimal("0"))

    def _somar_periodo(
        self, usuario_id: int, tipo: TipoTransacao, data_inicio: date, data_fim: date
    ) -> Decimal:
        return self.transacao_service.somar_por_periodo(
            usuario_id, tipo=tipo, status=StatusTransacao.PAGO, data_inicio=data_inicio, data_fim=data_fim
        )

    @staticmethod
    def _saldo_devedor_total(contratos) -> Decimal:
        return sum(
            (c.saldo_devedor for c in contratos if c.status != StatusContratoCredito.QUITADO),
            Decimal("0"),
        )

    def _fatura_aberta_do_cartao(self, cartao: Cartao, usuario_id: int) -> Fatura | None:
        """O ciclo mais recente (`mes_referencia` desc, ordenação padrão de
        `FaturaService.listar`) é sempre o único que pode estar ABERTA -
        ciclos fechados nunca reabrem. `limit=1` evita buscar histórico
        inteiro só para achar o ciclo corrente."""
        faturas = self.fatura_service.listar(cartao.id, usuario_id, limit=1)
        return faturas[0] if faturas else None

    def _total_faturas_em_aberto(self, usuario_id: int, *, cartoes: list[Cartao] | None = None) -> Decimal:
        if cartoes is None:
            cartoes = self.cartao_service.listar(usuario_id, apenas_ativos=True)
        total = Decimal("0")
        for cartao in cartoes:
            fatura = self._fatura_aberta_do_cartao(cartao, usuario_id)
            if fatura is not None and fatura.status_calculado == StatusFatura.ABERTA:
                total += fatura.valor_total_calculado
        return total

    def _saldo_restante_parcelamentos(self, usuario_id: int) -> Decimal:
        """Diferente de Financiamento/Empréstimo, `Parcelamento` não guarda
        `saldo_devedor` - a soma das parcelas `PENDENTE` de cada
        parcelamento ativo é a mesma fonte de verdade já usada em qualquer
        outro lugar do domínio (nenhuma coluna nova, nenhum cálculo novo)."""
        total = Decimal("0")
        for parcelamento in self.parcelamento_service.listar(usuario_id, apenas_ativos=True):
            parcelas_pendentes = self.transacao_service.listar(
                usuario_id,
                parcelamento_id=parcelamento.id,
                status=StatusTransacao.PENDENTE,
                limit=parcelamento.num_parcelas,
            )
            total += sum((p.valor for p in parcelas_pendentes), Decimal("0"))
        return total

    def _metricas_de_parcelas(
        self,
        usuario_id: int,
        *,
        num_parcelas: int,
        financiamento_id: int | None = None,
        emprestimo_id: int | None = None,
    ) -> dict:
        """Deriva parcelas pagas/restantes/valor pago/próxima parcela a
        partir de `TransacaoService.listar` - N é sempre `num_parcelas` de
        UM contrato (pequeno e finito, nunca a tabela inteira), mesmo
        raciocínio já registrado na análise arquitetural (seção 2.2.1)."""
        parcelas = self.transacao_service.listar(
            usuario_id,
            financiamento_id=financiamento_id,
            emprestimo_id=emprestimo_id,
            limit=num_parcelas,
        )
        pagas = [p for p in parcelas if p.status == StatusTransacao.PAGO]
        pendentes = [p for p in parcelas if p.status == StatusTransacao.PENDENTE]
        proxima = min(pendentes, key=lambda p: p.data) if pendentes else None

        return {
            "parcelas_pagas": len(pagas),
            "parcelas_restantes": num_parcelas - len(pagas),
            "valor_total_pago": sum((p.valor for p in pagas), Decimal("0")),
            "proxima_parcela_data": proxima.data if proxima else None,
            "proxima_parcela_valor": proxima.valor if proxima else None,
        }

    @staticmethod
    def _combinar(contrato, metricas: dict) -> dict:
        base = {
            "id": contrato.id,
            "descricao": contrato.descricao,
            "instituicao_financeira": contrato.instituicao_financeira,
            "numero_contrato": contrato.numero_contrato,
            "taxa_juros": contrato.taxa_juros,
            "sistema_amortizacao": contrato.sistema_amortizacao,
            "num_parcelas": contrato.num_parcelas,
            "cet": contrato.cet,
            "data_inicio": contrato.data_inicio,
            "saldo_devedor": contrato.saldo_devedor,
            "permite_quitacao_antecipada": contrato.permite_quitacao_antecipada,
            "status": contrato.status,
            "conta_id": contrato.conta_id,
            "categoria_id": contrato.categoria_id,
        }
        if hasattr(contrato, "valor_financiado"):
            base["valor_financiado"] = contrato.valor_financiado
            base["valor_entrada"] = contrato.valor_entrada
            base["bem_financiado"] = contrato.bem_financiado
        else:
            base["valor_liberado"] = contrato.valor_liberado
            base["finalidade"] = contrato.finalidade
        base.update(metricas)
        return base

    @staticmethod
    def _origem_da_transacao(transacao) -> tuple[TipoEntidadeReferenciavel, int]:
        if transacao.financiamento_id is not None:
            return TipoEntidadeReferenciavel.FINANCIAMENTO, transacao.financiamento_id
        if transacao.emprestimo_id is not None:
            return TipoEntidadeReferenciavel.EMPRESTIMO, transacao.emprestimo_id
        if transacao.parcelamento_id is not None:
            return TipoEntidadeReferenciavel.PARCELAMENTO, transacao.parcelamento_id
        if transacao.origem_recorrente_id is not None:
            return TipoEntidadeReferenciavel.CONTA_RECORRENTE, transacao.origem_recorrente_id
        return TipoEntidadeReferenciavel.TRANSACAO, transacao.id

    def _contar_parcelas_atrasadas(self, usuario_id: int) -> int:
        """Parcela `PENDENTE` de contrato (financiamento/empréstimo/
        parcelamento) com data no passado. Uma única chamada a
        `TransacaoService.listar` (filtro `status` + `data_fim`, já
        adicionado nesta etapa) em vez de uma consulta por contrato -
        mesma diretriz de performance de `somar_por_periodo`."""
        ontem = date.today() - timedelta(days=1)
        pendentes_passadas = self.transacao_service.listar(
            usuario_id,
            status=StatusTransacao.PENDENTE,
            data_fim=ontem,
            limit=_LIMITE_TRANSACOES_ATRASADAS,
        )
        return sum(
            1
            for t in pendentes_passadas
            if t.financiamento_id is not None or t.emprestimo_id is not None or t.parcelamento_id is not None
        )
