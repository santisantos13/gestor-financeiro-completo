"""Repository de Cartao.

Além do CRUD genérico, expõe as buscas específicas de Cartao: listar os
cartões de um usuário, buscar por nome (unicidade por usuário, mesmo
padrão de TagRepository) e somar os gastos que ainda consomem limite -
matéria-prima que CartaoService usa para calcular limite_disponivel (a
fórmula em si é regra de negócio e mora no Service; aqui só a query).
"""
from decimal import Decimal
from typing import Sequence

from sqlalchemy import exists, func, select

from app.models import Cartao, Fatura, Transacao
from app.models.enums import TipoTransacao
from app.repositories.base import SQLAlchemyRepository


class CartaoRepository(SQLAlchemyRepository[Cartao]):
    model = Cartao

    def listar_do_usuario(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Cartao]:
        condicoes = [Cartao.usuario_id == usuario_id]
        if apenas_ativos:
            condicoes.append(Cartao.ativo.is_(True))
        stmt = select(Cartao).where(*condicoes).order_by(Cartao.nome).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def buscar_por_nome(self, usuario_id: int, nome: str) -> Cartao | None:
        stmt = select(Cartao).where(Cartao.usuario_id == usuario_id, Cartao.nome == nome)
        return self.db.execute(stmt).scalar_one_or_none()

    def somar_gastos_nao_pagos(self, cartao_id: int, ids_faturas_pagas: set[int]) -> Decimal:
        """Soma as despesas lançadas neste cartão que ainda consomem
        limite: transações com fatura ainda não paga. Uma fatura PAGA
        libera o limite correspondente; qualquer outro status (ABERTA,
        FECHADA, ATRASADA) ainda representa dívida em aberto no cartão.

        `ids_faturas_pagas` vem de `FaturaService.ids_faturas_pagas()` -
        NUNCA comparamos aqui com a coluna `Fatura.status` diretamente
        (bug corrigido em 2026-07: essa coluna só grava ABERTA/FECHADA de
        verdade, nunca PAGA - `status_calculado` é sempre derivado em
        runtime a partir de `valor_pago`/`valor_total`, ver docstring de
        `StatusFatura`. Comparar com a coluna fazia `limite_disponivel`
        nunca se recuperar depois de um pagamento real). A regra de "o que
        conta como pago" mora inteiramente em `FaturaService` - aqui só a
        query com o conjunto de ids já resolvido.

        Exige `Transacao.fatura_id IS NOT NULL` (join normal, não mais
        `outerjoin` com um `Fatura.id.is_(None)` OR - bug real corrigido em
        2026-07-20, mesmo relato do "excluir todas as faturas selecionadas
        e o limite não voltou"). A versão anterior contava como dívida
        ativa qualquer compra "sem fatura associada", pensando nisso como
        "ainda não fechada em nenhum ciclo" - mas `TransacaoService.criar`
        SEMPRE resolve `fatura_id` no momento da criação de uma compra de
        cartão (nunca vem do payload do cliente, nunca fica em branco por
        opção do usuário - ver docstring do método). A ÚNICA forma real de
        uma compra de cartão ficar com `fatura_id = NULL` hoje é
        `FaturaRepository.desvincular_transacoes`, chamado quando o
        usuário EXCLUI a fatura (`FaturaService.excluir`/`excluir_em_lote`)
        - nesse caso a compra continua existindo (nunca é apagada), mas o
        documento/ciclo que a organizava foi deliberadamente removido pelo
        usuário. Continuar contando essa compra órfã como dívida ativa
        prendia `limite_disponivel` para sempre nesse estado, sem nenhum
        jeito de "pagar" (não existe mais nenhuma `Fatura` para vincular um
        pagamento) nem de revisar (a compra também some da tela de
        Transações, filtrada por `apenas_conta`) - um beco sem saída. Isso
        vale igualmente para um pagamento (`Transacao.fatura_paga_id`)
        cuja fatura foi excluída: como esse pagamento nunca teve
        `cartao_id` (sempre `conta_id`, ver `FaturaService.
        registrar_pagamento`), ele nunca entrou nesta soma - só o lado da
        compra ficava contando sozinho, dívida sem a baixa correspondente.

        Também soma `Fatura.ajuste_manual` de toda fatura deste cartão
        ainda não paga - pedido explícito do usuário: um valor "já
        utilizado" declarado diretamente (sem nenhuma Transacao por trás,
        ver `FaturaService.ajustar_saldo_inicial`) precisa consumir limite
        exatamente como uma compra real consumiria. Sem essa soma aqui, o
        ajuste apareceria em `FaturaRead.valor_total` mas nunca afetaria
        `limite_disponivel` (esta query não lê `valor_total`, soma
        `Transacao.valor` diretamente - por isso o ajuste precisa entrar
        como um termo à parte).

        Também soma `Fatura.valor_total` de toda fatura IMPORTADA
        (`Fatura.importada=True`) ainda não paga - bug real encontrado
        (2026-07-20, inspeção direta do banco de um usuário: uma fatura
        importada de R$796,60, FECHADA, sem nenhuma Transacao nem
        `ajuste_manual`, contribuía ZERO para `limite_disponivel`, mesmo
        estando em aberto). `FaturaService.importar()` cria a fatura já
        FECHADA com `valor_total` informado diretamente pelo usuário e
        `ajuste_manual=0` SEMPRE (ver docstring de `FaturaImportarCreate`)
        - ao contrário de uma fatura fechada normalmente (`fechar()`), cujo
        `valor_total` é só o `SUM` das `Transacao` reais do ciclo (já
        cobertas por `stmt_transacoes` acima) mais o `ajuste_manual` que
        havia sido declarado enquanto ainda ABERTA (já coberto por
        `stmt_ajustes`), uma fatura importada não tem NENHUMA Transacao por
        trás por desenho (`docs/analise-arquitetural-fatura.md` -
        "`valor_total` nunca derivado de Transacao real, exceção
        deliberada") - sem este terceiro termo, seu valor nunca aparecia em
        lugar nenhum do cálculo de limite, só em `FaturaRead.valor_total`.
        Filtrado por `importada=True` para nunca somar `valor_total` de uma
        fatura fechada normalmente (já contado via `stmt_transacoes`/
        `stmt_ajustes` - somar de novo aqui duplicaria a dívida).
        """
        fatura_nao_paga = Fatura.id.not_in(ids_faturas_pagas) if ids_faturas_pagas else True
        stmt_transacoes = (
            select(func.coalesce(func.sum(Transacao.valor), 0))
            .select_from(Transacao)
            .join(Fatura, Transacao.fatura_id == Fatura.id)
            .where(
                Transacao.cartao_id == cartao_id,
                Transacao.tipo == TipoTransacao.DESPESA,
                fatura_nao_paga,
            )
        )
        stmt_ajustes = select(func.coalesce(func.sum(Fatura.ajuste_manual), 0)).where(
            Fatura.cartao_id == cartao_id,
            fatura_nao_paga,
        )
        stmt_importadas = select(func.coalesce(func.sum(Fatura.valor_total), 0)).where(
            Fatura.cartao_id == cartao_id,
            Fatura.importada.is_(True),
            fatura_nao_paga,
        )
        soma_transacoes = Decimal(self.db.execute(stmt_transacoes).scalar_one())
        soma_ajustes = Decimal(self.db.execute(stmt_ajustes).scalar_one())
        soma_importadas = Decimal(self.db.execute(stmt_importadas).scalar_one())
        return soma_transacoes + soma_ajustes + soma_importadas

    def existe_fatura_vinculada(self, cartao_id: int) -> bool:
        """Usado só pela exclusão definitiva (hard delete,
        `docs/analise-arquitetural-exclusao.md`, seção 2.4) - bloqueia em
        QUALQUER status (ABERTA, FECHADA, PAGA etc.), mesma decisão que
        `FaturaService.excluir()` já aplica a si mesma: fatura é documento
        financeiro histórico, nunca desaparece via cascade de outra coisa.
        `Fatura.cartao_id` tem `ondelete=CASCADE` - um DELETE físico
        apagaria todas as faturas do cartão."""
        stmt = select(exists().where(Fatura.cartao_id == cartao_id))
        return self.db.execute(stmt).scalar_one()
