"""Model Conta - onde o dinheiro do usuario efetivamente fica guardado.

Exemplos: conta corrente, poupanca, carteira (dinheiro fisico), conta de
investimento. Cartao de credito NAO e uma Conta: ele nao guarda saldo,
guarda limite e acumula gastos em Faturas (ver model Cartao e Fatura).
"""
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TipoConta
from app.models.mixins import TimestampMixin


class Conta(Base, TimestampMixin):
    __tablename__ = "contas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    nome: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[TipoConta] = mapped_column(default=TipoConta.CORRENTE)
    # saldo informado pelo usuario ao cadastrar a conta. O saldo ATUAL nunca
    # fica guardado numa coluna: e calculado por servico somando
    # Transacao + Transferencia relacionadas a conta, para nunca existir um
    # numero "em cache" que possa ficar desatualizado/inconsistente.
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    instituicao: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # True = conta gerenciada pelo próprio sistema (hoje, só o "cofrinho"
    # automático de uma Meta - ver app/models/meta.py) - nunca aparece em
    # listagens/pickers normais (ContasPage, AccountSelect,
    # TransferenciaFormDialog), mas CONTINUA contando no patrimônio total
    # (ContaRepository.somar_transferencias/somar_transacoes_pagas não
    # filtram por isso - só a listagem filtra, ver
    # ContaRepository.listar_do_usuario). Ver
    # docs/analise-arquitetural-metas-transferencias.md, seção 1.
    oculta: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- relacionamentos ---
    # passive_deletes=True em TODAS as relações abaixo (bug encontrado em
    # 2026-07, mesma classe do já corrigido em `Cartao.parcelamentos`/
    # `Cartao.contas_recorrentes` - ver
    # docs/analise-arquitetural-exclusao-conta-com-historico.md): sem isso,
    # o SQLAlchemy ORM tenta, por padrao, ZERAR o `conta_id` de qualquer
    # linha relacionada carregada na sessao antes de apagar a Conta - o que
    # quebra as CHECK `ck_transacao_conta_xor_cartao`/
    # `ck_parcelamento_cartao_xor_conta`/`ck_conta_recorrente_cartao_xor_conta`
    # e as colunas NOT NULL de `Transferencia.conta_origem_id`/
    # `conta_destino_id`/`Cartao.conta_pagamento_id`/`Meta.conta_id`.
    # `passive_deletes=True` desliga essa "limpeza" automatica do lado do
    # Python: `ContaService.excluir(..., apagar_vinculos=True)` ja apaga (ou
    # ja apagou) cada linha relacionada explicitamente ANTES de chegar em
    # `conta_repo.delete()` - qualquer referencia que ainda assim sobrar
    # fica "pendurada" (dangling), nunca um crash (mesmo trade-off ja aceito
    # para Cartao - este projeto nunca liga PRAGMA foreign_keys=ON, ver
    # fatura_repository.py::desvincular_transacoes).
    usuario: Mapped["Usuario"] = relationship(back_populates="contas")

    # cartoes cuja fatura e paga a partir desta conta
    cartoes: Mapped[list["Cartao"]] = relationship(back_populates="conta_pagamento", passive_deletes=True)

    # transacoes feitas diretamente nesta conta (nao via cartao)
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="conta", passive_deletes=True)

    parcelamentos: Mapped[list["Parcelamento"]] = relationship(back_populates="conta", passive_deletes=True)
    financiamentos: Mapped[list["Financiamento"]] = relationship(back_populates="conta", passive_deletes=True)
    emprestimos: Mapped[list["Emprestimo"]] = relationship(back_populates="conta", passive_deletes=True)
    contas_recorrentes: Mapped[list["ContaRecorrente"]] = relationship(
        back_populates="conta", passive_deletes=True
    )
    metas: Mapped[list["Meta"]] = relationship(back_populates="conta", passive_deletes=True)

    # uma conta pode ser origem em varias transferencias e destino em outras;
    # precisamos de dois relationships distintos, cada um amarrado a uma
    # foreign key diferente la em Transferencia (veja foreign_keys=... nesse model).
    transferencias_enviadas: Mapped[list["Transferencia"]] = relationship(
        back_populates="conta_origem", foreign_keys="Transferencia.conta_origem_id", passive_deletes=True
    )
    transferencias_recebidas: Mapped[list["Transferencia"]] = relationship(
        back_populates="conta_destino", foreign_keys="Transferencia.conta_destino_id", passive_deletes=True
    )
