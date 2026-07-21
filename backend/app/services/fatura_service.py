"""Service de Fatura.

Regras de negócio concentradas aqui: derivação de `data_fechamento`/
`data_vencimento` a partir da configuração do Cartão, cálculo de
`valor_total`/`status` (sempre derivados, nunca lidos direto das colunas -
ver docstring de `app/schemas/fatura.py`), transição explícita
ABERTA -> FECHADA (com snapshot), registro de pagamento (total ou
parcial, via `Transacao.fatura_paga_id`), resolução lazy da fatura aberta
de um ciclo por data (usada por `TransacaoService` ao lançar uma compra de
cartão - ver docs/analise-arquitetural-transacao.md) e exclusão restrita a
faturas ainda vazias. Geração automática de próximos ciclos como rotina
agendada e integração com Parcelamento/Financiamento ficam fora desta
etapa - ver docs/analise-arquitetural-fatura.md.

A aritmética de "somar meses com clamping de dia" (`proximo_mes`/
`dia_valido`) mora em `app/core/datas.py`, não aqui - `ParcelamentoService`
precisa exatamente do mesmo cálculo para datar as parcelas de uma compra
parcelada, e duplicá-lo violaria o mesmo princípio de "evitar duplicação
de regras" já aplicado em todo o projeto (ver
docs/analise-arquitetural-parcelamento.md).
"""
from datetime import date
from decimal import Decimal

from app.core.datas import dia_valido, proximo_mes
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Cartao, Fatura, Transacao
from app.models.enums import StatusFatura, TipoTransacao
from app.repositories.cartao_repository import CartaoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.schemas.fatura import (
    FaturaAjusteManualUpdate,
    FaturaAjustePosFechamentoCreate,
    FaturaCreate,
    FaturaImportarCreate,
    FaturaPagamentoCreate,
)


class FaturaService:
    def __init__(
        self,
        fatura_repo: FaturaRepository,
        cartao_repo: CartaoRepository,
        transacao_repo: TransacaoRepository,
    ) -> None:
        self.fatura_repo = fatura_repo
        self.cartao_repo = cartao_repo
        self.transacao_repo = transacao_repo

    def criar(self, dados: FaturaCreate, usuario_id: int) -> Fatura:
        cartao = self._validar_cartao_do_usuario(dados.cartao_id, usuario_id)

        existente = self.fatura_repo.buscar_por_cartao_e_mes(dados.cartao_id, dados.mes_referencia)
        if existente is not None:
            raise ConflictError("Já existe uma fatura para este cartão neste mês de referência.")

        data_fechamento, data_vencimento = self._calcular_datas_ciclo(cartao, dados.mes_referencia)
        fatura = Fatura(
            cartao_id=dados.cartao_id,
            mes_referencia=dados.mes_referencia,
            data_fechamento=data_fechamento,
            data_vencimento=data_vencimento,
            status=StatusFatura.ABERTA,
            # explícito - mesmo motivo de ativo=True em Conta/Cartão/Meta:
            # o default da coluna só é aplicado num flush de verdade.
            ajuste_manual=Decimal("0"),
        )
        fatura = self.fatura_repo.create(fatura)
        return self._com_valores_calculados(fatura)

    def importar(self, dados: FaturaImportarCreate, usuario_id: int) -> Fatura:
        """Cria uma Fatura HISTÓRICA já FECHADA, com `valor_total` informado
        diretamente pelo usuário - nunca derivado de `Transacao` (única
        exceção deliberada a esse invariante, ver docstring de
        `FaturaImportarCreate`). Mesma checagem de posse/unicidade de
        `criar()`, mesma derivação de `data_fechamento`/`data_vencimento`
        a partir do Cartão (o ciclo em si é real, só o valor não veio de
        transações recriadas uma a uma).

        Depois de importada, `_com_valores_calculados` trata essa fatura
        exatamente como qualquer outra já FECHADA - `valor_total` frozen,
        `status_calculado` derivado normalmente a partir de `valor_pago`
        (ainda zero, até um `registrar_pagamento` ser chamado) - nenhuma
        mudança necessária ali.

        Bloqueia ciclo cujo fechamento ainda não passou (pedido explícito
        do usuário, 2026-07-20: "estou registrando uma fatura futura, como
        vai estar fechada? deveria apenas registrar o valor e, caso eu
        quiser, registrar as compras"). "Histórica" só faz sentido para um
        ciclo que JÁ aconteceu antes do usuário começar a usar o app -
        nasce FECHADA (imutável, sem `PATCH`/compra possível) porque é
        documento financeiro do passado, ver docstring de
        `FaturaImportarCreate`. Um ciclo atual/futuro que o usuário só
        quer "deixar o valor já anotado, podendo lançar compras depois" é
        exatamente o caso de uso de uma fatura normal (`criar()`, nasce
        ABERTA) + `ajustar_saldo_inicial` (`Fatura.ajuste_manual` - mesmo
        efeito sobre `limite_disponivel`, ver `CartaoRepository.
        somar_gastos_nao_pagos`, mas editável e combinável com compras
        reais a qualquer momento antes do fechamento)."""
        cartao = self._validar_cartao_do_usuario(dados.cartao_id, usuario_id)

        existente = self.fatura_repo.buscar_por_cartao_e_mes(dados.cartao_id, dados.mes_referencia)
        if existente is not None:
            raise ConflictError("Já existe uma fatura para este cartão neste mês de referência.")

        data_fechamento, data_vencimento = self._calcular_datas_ciclo(cartao, dados.mes_referencia)
        if data_fechamento >= date.today():
            raise BusinessRuleError(
                "Este ciclo ainda não fechou (fecha em "
                f"{data_fechamento.isoformat()}) - não pode ser importado como fatura "
                "histórica. Para um ciclo atual ou futuro, crie uma fatura normal e use "
                "\"Informar saldo já utilizado\" para declarar o valor: diferente da "
                "importação, ela continua aberta e você pode ajustar o valor ou lançar "
                "compras reais nela depois."
            )
        fatura = Fatura(
            cartao_id=dados.cartao_id,
            mes_referencia=dados.mes_referencia,
            data_fechamento=data_fechamento,
            data_vencimento=data_vencimento,
            status=StatusFatura.FECHADA,
            valor_total=dados.valor_total,
            importada=True,
            # explícito - mesmo motivo do comentário em criar(). Uma
            # fatura importada nasce FECHADA com valor_total já pronto -
            # ajuste_manual nunca se aplica aqui (não existe ciclo ABERTO
            # a ajustar), fica 0 só por consistência de coluna NOT NULL.
            ajuste_manual=Decimal("0"),
        )
        fatura = self.fatura_repo.create(fatura)
        return self._com_valores_calculados(fatura)

    def obter(self, fatura_id: int, usuario_id: int) -> Fatura:
        fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
        return self._com_valores_calculados(fatura)

    def listar(
        self, cartao_id: int, usuario_id: int, *, skip: int = 0, limit: int = 100
    ) -> list[Fatura]:
        self._validar_cartao_do_usuario(cartao_id, usuario_id)
        faturas = self.fatura_repo.listar_do_cartao(cartao_id, skip=skip, limit=limit)
        return [self._com_valores_calculados(fatura) for fatura in faturas]

    def listar_recentes(self, cartao_id: int, usuario_id: int, *, limit: int = 100) -> list[Fatura]:
        """Mais recente primeiro - só para
        `CentralFinanceiraService.calendario_financeiro`/
        `agenda_financeira`, que buscam com `limit` pequeno esperando "o
        ciclo atual + folga de ciclos próximos" (ver docstring de
        `FaturaRepository.listar_recentes_do_cartao`). Nunca usar para a
        tela de listagem de faturas - essa quer `listar()` (ordem
        cronológica ascendente)."""
        self._validar_cartao_do_usuario(cartao_id, usuario_id)
        faturas = self.fatura_repo.listar_recentes_do_cartao(cartao_id, limit=limit)
        return [self._com_valores_calculados(fatura) for fatura in faturas]

    def resolver_fatura_aberta(self, cartao_id: int, data_transacao: date, usuario_id: int) -> Fatura:
        """Find-or-create da fatura cujo ciclo cobre `data_transacao` neste
        cartão - usada por `TransacaoService` para resolver `fatura_id` ao
        lançar uma compra de cartão (nunca aceito do payload do cliente).

        Extensão pontual prevista desde a arquitetura de Fatura (ver
        docs/analise-arquitetural-fatura.md, "Geração automática das
        próximas faturas") e detalhada em
        docs/analise-arquitetural-transacao.md: NÃO é geração em lote/
        scheduler (isso continua fora de escopo) - é a resolução lazy, sob
        demanda, de um único ciclo por vez, reaproveitando
        `_calcular_datas_ciclo`/`buscar_por_cartao_e_mes` já existentes.

        Se o ciclo resolvido já existir mas não estiver mais `ABERTA`
        (fechado manualmente, ou uma tentativa de forçar uma data para
        dentro de um ciclo já encerrado), rejeita explicitamente em vez de
        redirecionar silenciosamente para outro ciclo - mesmo raciocínio já
        documentado para não mascarar um provável erro de data.
        """
        cartao = self._validar_cartao_do_usuario(cartao_id, usuario_id)
        mes_referencia = self._mes_referencia_do_ciclo(cartao, data_transacao)

        fatura = self.fatura_repo.buscar_por_cartao_e_mes(cartao_id, mes_referencia)
        if fatura is None:
            data_fechamento, data_vencimento = self._calcular_datas_ciclo(cartao, mes_referencia)
            fatura = Fatura(
                cartao_id=cartao_id,
                mes_referencia=mes_referencia,
                data_fechamento=data_fechamento,
                data_vencimento=data_vencimento,
                status=StatusFatura.ABERTA,
                ajuste_manual=Decimal("0"),
            )
            fatura = self.fatura_repo.create(fatura)

        if fatura.status != StatusFatura.ABERTA:
            raise BusinessRuleError(
                "Não é possível lançar uma transação com esta data: o ciclo correspondente já foi fechado."
            )
        return fatura

    def fechar(self, fatura_id: int, usuario_id: int) -> Fatura:
        """Transição real ABERTA -> FECHADA: soma as compras vinculadas
        uma última vez e CONGELA o resultado em `valor_total` - a partir
        daqui esse valor nunca mais é recalculado, mesmo que algo mudasse
        depois (documento financeiro histórico, ver
        docs/analise-arquitetural-fatura.md)."""
        fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
        if fatura.status != StatusFatura.ABERTA:
            raise BusinessRuleError("Esta fatura já foi fechada.")

        fatura.valor_total = self.fatura_repo.somar_transacoes(fatura.id) + fatura.ajuste_manual
        # Zera aqui - o valor enquanto ABERTA já foi embutido no
        # valor_total congelado acima. Deixar o número antigo em
        # `ajuste_manual` faria `_com_valores_calculados` somá-lo de novo
        # por cima do total já congelado (dobrando a conta) e se
        # confundiria com uma correção pós-fechamento de verdade, feita
        # depois por `ajustar_valor_pos_fechamento` (que reaproveita este
        # mesmo campo com semântica diferente - ver lá).
        fatura.ajuste_manual = Decimal("0")
        fatura.status = StatusFatura.FECHADA
        fatura = self.fatura_repo.update(fatura)
        return self._com_valores_calculados(fatura)

    def ajustar_valor_pos_fechamento(
        self, fatura_id: int, dados: FaturaAjustePosFechamentoCreate, usuario_id: int
    ) -> Fatura:
        """Soma um valor esquecido ao total de uma fatura JÁ FECHADA (ou
        paga/atrasada/parcialmente paga) - pedido explícito do usuário
        (2026-07-20): "quero adicionar uma transação em uma fatura que já
        foi fechada e paga, porém tinha esquecido dela antes". Entre três
        opções oferecidas (reabrir a fatura para lançar a compra de
        verdade; lançar na fatura atual aberta, com a data de hoje; só
        ajustar o número), o usuário escolheu a terceira - por isso nenhuma
        Transacao é criada aqui, só o número muda.

        Reaproveita `Fatura.ajuste_manual` (mesmo campo de
        `ajustar_saldo_inicial`), mas com semântica diferente: enquanto
        ABERTA o campo é SUBSTITUÍDO (usuário informa o saldo total já
        utilizado, editando o mesmo número sempre que precisar corrigir);
        aqui é SOMADO (usuário informa só o valor esquecido, sem precisar
        saber/recalcular o total já congelado - e pode chamar de novo mais
        tarde se lembrar de outra compra, acumulando). Isso só é seguro
        porque `fechar()` zera `ajuste_manual` no momento de congelar
        `valor_total` (ver comentário lá) - qualquer valor que apareça
        aqui depois disso é sempre uma correção pós-fechamento nova, nunca
        o que já estava embutido no total congelado.

        `valor_total` (a coluna congelada) nunca é reescrita - o ajuste
        fica isolado em `ajuste_manual` e é somado por cima em
        `_com_valores_calculados` (ver comentário lá). `CartaoRepository.
        somar_gastos_nao_pagos` já soma `ajuste_manual` de toda fatura
        ainda não paga sem filtro de status (pedido original de
        `ajustar_saldo_inicial`), então `limite_disponivel` reflete esta
        correção automaticamente, sem nenhuma mudança adicional lá.

        Efeito colateral esperado e intencional: se a fatura estava PAGA,
        `status_calculado` deixa de ser PAGA (o valor pago não mudou, mas
        o total aumentou) - reflete corretamente que passou a faltar
        pagar a diferença. O usuário pode registrar um pagamento adicional
        pela ação normal de "Registrar pagamento"."""
        fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
        if fatura.status == StatusFatura.ABERTA:
            raise BusinessRuleError(
                "Esta fatura ainda está aberta - lance a compra normalmente ou use "
                '"Informar saldo já utilizado".'
            )
        fatura.ajuste_manual = fatura.ajuste_manual + dados.valor
        fatura = self.fatura_repo.update(fatura)
        return self._com_valores_calculados(fatura)

    def ajustar_saldo_inicial(
        self, fatura_id: int, dados: FaturaAjusteManualUpdate, usuario_id: int
    ) -> Fatura:
        """Declara `ajuste_manual` diretamente - pedido explícito do
        usuário: poder informar o saldo já usado do cartão SEM vincular a
        nenhuma compra/Transacao (diferente do botão "Registrar saldo já
        gasto neste cartão" que já existia, que cria uma Transacao real de
        ajuste). Só permitido com a fatura ainda ABERTA: uma fatura
        FECHADA/histórica já tem seu `valor_total` congelado para sempre
        (documento financeiro histórico) - editar o "ponto de partida" de
        um ciclo que já aconteceu é exatamente o que `FaturaImportarCreate`
        resolve, de um jeito diferente (informa o total já pronto, não um
        ajuste somado a transações futuras)."""
        fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
        if fatura.status != StatusFatura.ABERTA:
            raise BusinessRuleError(
                "Só é possível ajustar o saldo já utilizado em uma fatura ainda aberta. "
                "Para um ciclo já fechado/histórico, use a importação de fatura histórica."
            )
        fatura.ajuste_manual = dados.ajuste_manual
        fatura = self.fatura_repo.update(fatura)
        return self._com_valores_calculados(fatura)

    def registrar_pagamento(
        self, fatura_id: int, dados: FaturaPagamentoCreate, usuario_id: int
    ) -> Fatura:
        """Cria uma Transacao de despesa na Conta de pagamento do cartão,
        vinculada a esta fatura via `fatura_paga_id`. Não exige quitação
        total - várias chamadas a este método são o mecanismo de
        pagamento parcial/múltiplo (`valor_pago` é sempre a soma de todas
        elas). Só permitido em fatura já FECHADA: uma fatura ABERTA ainda
        não tem um valor emitido definitivo para "pagar"."""
        fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
        if fatura.status == StatusFatura.ABERTA:
            raise BusinessRuleError(
                "Não é possível registrar pagamento em uma fatura ainda aberta - feche o ciclo primeiro."
            )

        cartao = self.cartao_repo.get(fatura.cartao_id)
        pagamento = Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.DESPESA,
            valor=dados.valor,
            data=dados.data,
            descricao=dados.descricao or f"Pagamento de fatura - {cartao.nome}",
            conta_id=cartao.conta_pagamento_id,
            fatura_paga_id=fatura.id,
        )
        self.transacao_repo.create(pagamento)
        return self._com_valores_calculados(fatura)

    def ids_faturas_pagas(self, cartao_id: int) -> set[int]:
        """Ids das faturas deste cartão cujo `status_calculado` é PAGA -
        única fonte de verdade sobre "o que conta como pago", usada por
        `CartaoService` para calcular `limite_disponivel` sem duplicar essa
        regra (correção do bug em que `CartaoRepository.somar_gastos_nao_pagos`
        comparava com `Fatura.status` diretamente - coluna que só grava
        ABERTA/FECHADA, nunca PAGA, ver docstring de `StatusFatura`). Não
        valida posse por usuário aqui: `cartao_id` já foi validado por quem
        chama (mesmo padrão de método interno usado só entre services)."""
        faturas = self.fatura_repo.listar_do_cartao(cartao_id, limit=10_000)
        return {
            fatura.id
            for fatura in faturas
            if self._com_valores_calculados(fatura).status_calculado == StatusFatura.PAGA
        }

    def excluir(self, fatura_id: int, usuario_id: int) -> None:
        """Fatura não tem soft delete: não é um recurso que faz sentido
        "desativar" (é um registro histórico de ciclo, não um cadastro).
        Hard delete, sempre permitido, independente do status ou de ter
        transação vinculada (compra e/ou pagamento) - o objetivo é deixar o
        usuário desfazer/corrigir uma fatura cadastrada errada mesmo depois
        de já ter comprado ou pago algo nela.

        Mudança de regra (2026-07-24, pedido explícito do usuário): antes,
        qualquer transação vinculada bloqueava a exclusão com
        `BusinessRuleError` - na prática, isso deixava sem saída quem
        registrou uma fatura errada (ex: valor importado incorreto, ou um
        pagamento lançado no ciclo errado) e só percebia o erro depois de
        já ter alguma transação ali. A trava original existia pra proteger
        o "histórico real" de ser perdido - mas excluir a FATURA nunca
        precisou apagar a TRANSAÇÃO: `desvincular_transacoes` só zera
        `fatura_id`/`fatura_paga_id` das transações desta fatura (nunca as
        remove) antes de apagar a fatura em si. A compra ou o pagamento
        continuam existindo, com o mesmo valor/data, só sem fatura
        associada - o usuário pode inclusive apagar essa transação órfã
        depois, pela própria tela de Transações, se ela também estiver
        errada.

        Efeito sobre `limite_disponivel` (bug corrigido em 2026-07-20,
        relatado pelo usuário como "excluí todas as faturas selecionadas e
        o limite não voltou"): uma compra que fica sem `fatura_id` por
        causa desta exclusão deixa de contar como dívida ativa do cartão -
        ver a mudança em `CartaoRepository.somar_gastos_nao_pagos`, que
        agora exige `fatura_id` preenchido para somar. Ou seja, excluir uma
        fatura já libera o limite correspondente de imediato, mesmo sem
        nenhum pagamento ter sido registrado - o documento do ciclo foi
        removido deliberadamente pelo usuário, então a compra órfã que
        sobra não deveria travar limite para sempre sem nenhum jeito de
        "pagar" (não há mais fatura para vincular um pagamento)."""
        fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
        self.fatura_repo.desvincular_transacoes(fatura.id)
        self.fatura_repo.delete(fatura)

    def excluir_em_lote(self, fatura_ids: list[int], usuario_id: int) -> None:
        """Pedido explícito do usuário: "quero poder selecionar várias
        faturas para excluir". Reaproveita `excluir()` 100% (mesma posse,
        mesmo desvínculo de transação, sem nenhuma regra nova) - só chama
        em loop. Nenhuma tolerância a erro no meio da lista: se qualquer
        `fatura_id` não existir ou não for do usuário, `excluir()` levanta
        `NotFoundError` normalmente, e a rota inteira falha - a sessão de
        banco do request (`app/db/session.py::get_db`) só dá `commit` se
        NENHUMA exceção acontecer, então uma falha no meio desfaz também as
        faturas já apagadas por chamadas anteriores deste mesmo loop
        (tudo ou nada, sem precisar de nenhum código de rollback manual
        aqui)."""
        for fatura_id in fatura_ids:
            self.excluir(fatura_id, usuario_id)

    def pagar_em_lote(self, fatura_ids: list[int], data_pagamento: date, usuario_id: int) -> int:
        """Pedido explícito do usuário (2026-07-20): "seria interessante
        poder pagar todas selecionadas" — a mesma seleção múltipla já usada
        por `excluir_em_lote`, agora também para pagamento. Paga o RESTANTE
        de cada fatura elegível (mesmo valor do atalho "Pagar restante" do
        Drawer, via `registrar_pagamento` reaproveitado 100%) - nunca um
        valor único para todas, porque faturas diferentes quase sempre têm
        saldos diferentes.

        Diferente de `excluir_em_lote` ("tudo ou nada"): aqui, faturas
        ABERTAS (ciclo ainda não fechado, não é possível pagar) ou já
        totalmente quitadas (`restante <= 0`) são PULADAS silenciosamente
        em vez de derrubar o lote inteiro. Motivo: "Selecionar todas" já
        existe na mesma tela e naturalmente inclui o ciclo aberto atual -
        bloquear a ação inteira por causa de uma fatura que simplesmente
        não se aplica seria pior experiência que só pagar as que fazem
        sentido. Só levanta erro se NENHUMA fatura da lista for elegível
        (evita devolver "0 pagas" silenciosamente, o que pareceria bug)."""
        pagas = 0
        for fatura_id in fatura_ids:
            fatura = self._buscar_fatura_do_usuario(fatura_id, usuario_id)
            if fatura.status == StatusFatura.ABERTA:
                continue
            fatura = self._com_valores_calculados(fatura)
            restante = fatura.valor_total_calculado - fatura.valor_pago
            if restante <= 0:
                continue
            self.registrar_pagamento(
                fatura_id, FaturaPagamentoCreate(valor=restante, data=data_pagamento), usuario_id
            )
            pagas += 1

        if pagas == 0:
            raise BusinessRuleError(
                "Nenhuma das faturas selecionadas pôde ser paga - todas já estão quitadas ou ainda estão abertas."
            )
        return pagas

    def _validar_cartao_do_usuario(self, cartao_id: int, usuario_id: int) -> Cartao:
        """Mesmo padrão de validação cruzada já usado em
        CartaoService._validar_conta_do_usuario: garante que o cartão
        existe E pertence ao usuário, mesma resposta (404) pros dois
        casos, mesmo raciocínio anti-enumeração de sempre."""
        cartao = self.cartao_repo.get(cartao_id)
        if cartao is None or cartao.usuario_id != usuario_id:
            raise NotFoundError("Cartão não encontrado.")
        return cartao

    def _buscar_fatura_do_usuario(self, fatura_id: int, usuario_id: int) -> Fatura:
        """Fatura não tem `usuario_id` próprio - a posse é sempre
        transitiva via `Fatura.cartao.usuario_id`. Mesma resposta (404)
        para "fatura não existe" e "existe mas o cartão é de outro
        usuário" - nunca vaza qual das duas coisas aconteceu."""
        fatura = self.fatura_repo.get(fatura_id)
        if fatura is None:
            raise NotFoundError("Fatura não encontrada.")
        cartao = self.cartao_repo.get(fatura.cartao_id)
        if cartao is None or cartao.usuario_id != usuario_id:
            raise NotFoundError("Fatura não encontrada.")
        return fatura

    def _com_valores_calculados(self, fatura: Fatura) -> Fatura:
        """Anexa valor_pago/valor_total_calculado/status_calculado como
        atributos TRANSIENTES (nomes que não colidem com nenhuma coluna
        real do model) - nunca sobrescreve `fatura.status`/`fatura.valor_total`
        diretamente, para nunca correr o risco de um valor derivado (ex:
        PARCIALMENTE_PAGA) ser commitado por engano numa coluna que só
        deveria guardar ABERTA/FECHADA."""
        valor_pago = self.fatura_repo.somar_pagamentos(fatura.id)
        valor_corrente = self.fatura_repo.somar_transacoes(fatura.id) + fatura.ajuste_manual

        if fatura.status != StatusFatura.ABERTA and fatura.valor_total is not None:
            # `ajuste_manual` enquanto ABERTA já foi embutido no
            # `valor_total` congelado por `fechar()` (que zera o campo
            # nesse momento - ver lá) - por isso NÃO é `valor_corrente`
            # aqui (isso duplicaria a conta). Qualquer valor em
            # `ajuste_manual` depois de fechada é sempre uma correção
            # pós-fechamento nova (`ajustar_valor_pos_fechamento`, pedido
            # do usuário 2026-07-20: "esqueci uma compra numa fatura já
            # fechada e paga") - soma-se por cima do total congelado, sem
            # nunca reescrever a coluna `valor_total` em si.
            valor_total_calculado = fatura.valor_total + fatura.ajuste_manual
        else:
            valor_total_calculado = valor_corrente

        fatura.valor_pago = valor_pago
        fatura.valor_total_calculado = valor_total_calculado
        fatura.status_calculado = self._derivar_status(fatura, valor_pago, valor_total_calculado)
        return fatura

    @staticmethod
    def _derivar_status(fatura: Fatura, valor_pago: Decimal, valor_total: Decimal) -> StatusFatura:
        """Só ABERTA/FECHADA são valores reais gravados na coluna - os
        demais são sempre calculados aqui a partir de valor_pago/
        valor_total/data_vencimento, nunca persistidos (ver docstring de
        StatusFatura em app/models/enums.py). Prioridade: quitada >
        atrasada > parcial > apenas fechada (uma fatura em aberto com
        saldo devedor e já vencida e tratada como atrasada mesmo se
        parcialmente paga - o risco/urgência importa mais que o progresso)."""
        if fatura.status == StatusFatura.ABERTA:
            return StatusFatura.ABERTA
        if valor_total > 0 and valor_pago >= valor_total:
            return StatusFatura.PAGA
        if date.today() > fatura.data_vencimento and valor_pago < valor_total:
            return StatusFatura.ATRASADA
        if valor_pago > 0:
            return StatusFatura.PARCIALMENTE_PAGA
        return StatusFatura.FECHADA

    def _calcular_datas_ciclo(self, cartao: Cartao, mes_referencia: date) -> tuple[date, date]:
        """`data_fechamento`/`data_vencimento` nunca vêm do cliente -
        sempre derivadas de `Cartao.dia_fechamento`/`dia_vencimento`. Se o
        dia configurado não existir no mês (ex: dia 31 em fevereiro), usa
        o último dia válido daquele mês (`dia_valido`). Se `dia_vencimento`
        for numericamente menor ou igual a `dia_fechamento`, o vencimento
        vira o mês seguinte (caso comum: fecha dia 28, vence dia 5) - senão,
        vencimento fica no mesmo mês do fechamento."""
        ano_fechamento, mes_fechamento = mes_referencia.year, mes_referencia.month
        data_fechamento = dia_valido(ano_fechamento, mes_fechamento, cartao.dia_fechamento)

        if cartao.dia_vencimento <= cartao.dia_fechamento:
            ano_vencimento, mes_vencimento = proximo_mes(ano_fechamento, mes_fechamento)
        else:
            ano_vencimento, mes_vencimento = ano_fechamento, mes_fechamento
        data_vencimento = dia_valido(ano_vencimento, mes_vencimento, cartao.dia_vencimento)

        return data_fechamento, data_vencimento

    def _mes_referencia_do_ciclo(self, cartao: Cartao, data_transacao: date) -> date:
        """A que ciclo (mes_referencia) uma transação com esta data
        pertence, dado o dia de fechamento do cartão: se a data cai em ou
        antes do fechamento do mês corrente, pertence ao ciclo deste mês;
        senão, já pertence ao ciclo do mês seguinte (o fechamento deste mês
        já passou). Mesma lógica de dia inexistente (clamp no último dia
        válido) de `_calcular_datas_ciclo`, para as duas ficarem sempre
        consistentes entre si."""
        ano, mes = data_transacao.year, data_transacao.month
        data_fechamento_candidata = dia_valido(ano, mes, cartao.dia_fechamento)

        if data_transacao <= data_fechamento_candidata:
            return date(ano, mes, 1)
        ano_seguinte, mes_seguinte = proximo_mes(ano, mes)
        return date(ano_seguinte, mes_seguinte, 1)
