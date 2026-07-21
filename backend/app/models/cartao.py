"""Model Cartao - cartao de credito.

Diferente de Conta, um Cartao nao guarda saldo: ele tem um LIMITE, e os
gastos se acumulam em Faturas (ciclos mensais, ver model Fatura) ate serem
pagas a partir de uma Conta.

Nome unico por usuario, com a mesma tensao ja resolvida em Tag: a
UniqueConstraint nao distingue cartao ativo de desativado, entao
CartaoService.criar() reativa um cartao inativo de mesmo nome em vez de
tentar inserir uma linha nova (ver docstring de TagService.criar para o
raciocinio completo - o mesmo se aplica aqui).
"""
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Bandeira
from app.models.mixins import TimestampMixin


class Cartao(Base, TimestampMixin):
    __tablename__ = "cartoes"
    __table_args__ = (
        UniqueConstraint("usuario_id", "nome", name="uq_cartao_usuario_nome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    # conta de onde o dinheiro sai quando a fatura e paga. Precisa pertencer
    # ao MESMO usuario do cartao - validado em CartaoService, nao no banco
    # (uma FK sozinha nao consegue expressar "so se o dono for o mesmo").
    conta_pagamento_id: Mapped[int] = mapped_column(ForeignKey("contas.id"), index=True)

    nome: Mapped[str] = mapped_column(String(120))
    instituicao: Mapped[str] = mapped_column(String(120))
    bandeira: Mapped[Bandeira] = mapped_column()
    # so os 4 ultimos digitos - nunca o numero completo do cartao (nem
    # coletado, nem armazenado; nao ha campo pra isso em nenhum lugar).
    ultimos_quatro_digitos: Mapped[str] = mapped_column(String(4))
    limite: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # dia do mes (1-31) em que o ciclo fecha / a fatura vence. A validacao de
    # intervalo (1-31) fica na camada de schema (Pydantic), nao no banco.
    dia_fechamento: Mapped[int] = mapped_column(Integer)
    dia_vencimento: Mapped[int] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # "Estado Inicial do Cartao" (Sprint de Refinamento Premium, 2026-07):
    # quanto do limite ja estava em uso quando o usuario comecou a usar o
    # sistema, declarado diretamente, SEM nenhuma Fatura/Transacao por
    # tras - substitui o fluxo anterior que criava uma Fatura do mes
    # corrente so para poder guardar `Fatura.ajuste_manual` (confuso: virava
    # "uma fatura que o sistema criou sozinho" aos olhos do usuario, ver
    # docs/analise-arquitetural-sprint-refinamento-premium.md, secao 1).
    # Consome limite_disponivel permanentemente ate o usuario editar/zerar -
    # nao tem ciclo, nao e Fatura.
    saldo_inicial_utilizado: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="cartoes")
    conta_pagamento: Mapped["Conta"] = relationship(back_populates="cartoes")
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="cartao")
    # passive_deletes=True (bug encontrado em 2026-07, ver
    # docs/analise-arquitetural-exclusao-cartao-com-historico.md): sem isso,
    # o SQLAlchemy ORM tenta, por padrao, ZERAR `Parcelamento.cartao_id` ao
    # apagar o Cartao (mesmo sem nenhum `cascade` declarado aqui) - o que
    # quebra a CHECK `ck_parcelamento_cartao_xor_conta` (cartao_id/conta_id
    # sao mutuamente exclusivos, nunca os dois nulos). `passive_deletes=True`
    # desliga essa "limpeza" automatica do lado do Python: o Parcelamento
    # (sempre preservado, nunca apagado - so fica `ativo=False`, ver
    # ParcelamentoService.cancelar) fica com uma referencia "pendurada"
    # (dangling) a um cartao que nao existe mais - mesmo trade-off ja aceito
    # e documentado para este projeto (SQLite aqui nunca liga
    # PRAGMA foreign_keys=ON, ver fatura_repository.py::desvincular_transacoes).
    parcelamentos: Mapped[list["Parcelamento"]] = relationship(
        back_populates="cartao", passive_deletes=True
    )
    faturas: Mapped[list["Fatura"]] = relationship(back_populates="cartao", cascade="all, delete-orphan")
    # Mesmo raciocinio/bug do `parcelamentos` acima -
    # `ck_conta_recorrente_cartao_xor_conta` tem a mesma exclusividade
    # mutua.
    contas_recorrentes: Mapped[list["ContaRecorrente"]] = relationship(
        back_populates="cartao", passive_deletes=True
    )
