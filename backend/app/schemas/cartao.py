"""Schemas de Cartao: payloads de entrada e saída de `app/api/routes/cartao.py`.

`limite_disponivel` existe SÓ em `CartaoRead` - não é uma coluna do model
`Cartao` (mesmo princípio de `ContaRead.saldo_atual`: valor sempre
calculado, nunca armazenado). `CartaoService` calcula esse valor e o anexa
como atributo transiente ao objeto `Cartao` antes de devolvê-lo ao Router.
"""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import Bandeira
from app.schemas.base import OrmBaseModel

_PADRAO_ULTIMOS_QUATRO_DIGITOS = r"^\d{4}$"


class CartaoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    conta_pagamento_id: int
    instituicao: str = Field(min_length=1, max_length=120)
    bandeira: Bandeira
    ultimos_quatro_digitos: str = Field(pattern=_PADRAO_ULTIMOS_QUATRO_DIGITOS)
    limite: Decimal = Field(ge=0)
    dia_fechamento: int = Field(ge=1, le=31)
    dia_vencimento: int = Field(ge=1, le=31)
    # "Estado Inicial do Cartao" - quanto do limite ja estava em uso quando
    # o cartao foi cadastrado, informado direto na criacao (sem Fatura/
    # Transacao por tras). Opcional - default 0 (cartao novo, sem uso
    # anterior), ver docstring de `Cartao.saldo_inicial_utilizado`.
    saldo_inicial_utilizado: Decimal = Field(default=Decimal("0"), ge=0)


class CartaoUpdate(BaseModel):
    """Todos os campos são opcionais - só o que for enviado é alterado
    (semântica de PATCH). `usuario_id` nunca aparece aqui: a posse de um
    cartão não é algo que se atualiza via payload."""

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    conta_pagamento_id: int | None = None
    instituicao: str | None = Field(default=None, min_length=1, max_length=120)
    bandeira: Bandeira | None = None
    ultimos_quatro_digitos: str | None = Field(default=None, pattern=_PADRAO_ULTIMOS_QUATRO_DIGITOS)
    limite: Decimal | None = Field(default=None, ge=0)
    dia_fechamento: int | None = Field(default=None, ge=1, le=31)
    dia_vencimento: int | None = Field(default=None, ge=1, le=31)
    ativo: bool | None = None
    saldo_inicial_utilizado: Decimal | None = Field(default=None, ge=0)


class CartaoRead(OrmBaseModel):
    id: int
    nome: str
    conta_pagamento_id: int
    instituicao: str
    bandeira: Bandeira
    ultimos_quatro_digitos: str
    limite: Decimal
    limite_disponivel: Decimal
    dia_fechamento: int
    dia_vencimento: int
    ativo: bool
    saldo_inicial_utilizado: Decimal
