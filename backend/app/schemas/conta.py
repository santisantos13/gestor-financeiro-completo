"""Schemas de Conta: payloads de entrada e saída de `app/api/routes/conta.py`.

`saldo_atual` existe SÓ em `ContaRead` - não é uma coluna do model `Conta`
(ver docstring do model: saldo atual é sempre calculado, nunca armazenado).
`ContaService` calcula esse valor e o anexa como atributo transiente ao
objeto `Conta` antes de devolvê-lo ao Router; `ContaRead.model_validate()`
lê esse atributo normalmente (Pydantic com `from_attributes=True` não
distingue uma coluna mapeada de um atributo Python comum).
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import CategoriaMovimentacaoConta, TipoConta, TipoEntidadeReferenciavel
from app.schemas.base import OrmBaseModel


class ContaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    tipo: TipoConta = TipoConta.CORRENTE
    saldo_inicial: Decimal = Decimal("0")
    instituicao: str | None = Field(default=None, max_length=120)


class ContaUpdate(BaseModel):
    """Todos os campos são opcionais - só o que for enviado é alterado
    (semântica de PATCH). `usuario_id` nunca aparece aqui: a posse de uma
    conta não é algo que se atualiza via payload."""

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    tipo: TipoConta | None = None
    saldo_inicial: Decimal | None = None
    instituicao: str | None = Field(default=None, max_length=120)
    ativo: bool | None = None


class ContaRead(OrmBaseModel):
    id: int
    nome: str
    tipo: TipoConta
    saldo_inicial: Decimal
    saldo_atual: Decimal
    instituicao: str | None
    ativo: bool
    # True = conta gerenciada pelo sistema (cofrinho automático de uma
    # Meta) - nunca aparece em `GET /contas` por padrão (ver
    # `ContaRepository.listar_do_usuario`, parâmetro `apenas_visiveis`),
    # então na prática o Frontend só vê `oculta=True` se buscar
    # explicitamente com `apenas_visiveis=False` (hoje, nenhum consumidor
    # faz isso) - exposto aqui só por completude do schema, nunca setável
    # via `ContaCreate`/`ContaUpdate`. Ver
    # docs/analise-arquitetural-metas-transferencias.md, seção 1.
    oculta: bool


class MovimentacaoContaRead(OrmBaseModel):
    """Um item do histórico de uma Conta (`GET /contas/{id}/extrato`) -
    mesmo molde de `EventoCalendario`/`EventoAgenda`
    (schemas/central_financeira.py): `origem_tipo`/`origem_id` reaproveitam
    `TipoEntidadeReferenciavel`, sem nenhum discriminador novo. `positivo`
    (entrada = True, saída = False) evita o frontend ter que conhecer a
    regra de sinal de cada `categoria` - mesmo campo já usado por
    `ItemHistoricoMeta` no frontend (`MetaResumoCard.tsx`). Ver
    docs/analise-arquitetural-extrato-conta.md."""

    data: date
    descricao: str
    valor: Decimal
    positivo: bool
    categoria: CategoriaMovimentacaoConta
    origem_tipo: TipoEntidadeReferenciavel
    origem_id: int


class MaiorMovimentacaoRead(OrmBaseModel):
    """Recorte mínimo de uma movimentação, usado só por
    `ContaResumoMesAtual.maior_entrada`/`maior_saida` - não é o item
    completo de `MovimentacaoContaRead` porque ali `categoria`/`positivo`/
    `origem_*` não agregam nada (já se sabe se é a maior entrada ou a
    maior saída pelo campo que a contém)."""

    data: date
    descricao: str
    valor: Decimal


class ContaExtratoResumo(BaseModel):
    """Resumo do PERÍODO navegado (`ano`/`mes` da requisição, default mês
    atual) - `saldo_atual`/`saldo_inicial` são sempre o valor real de
    agora, independente do período; os demais campos são só daquele mês.
    Ver docs/analise-arquitetural-extrato-conta.md, seção "Período vs
    resumo do mês"."""

    saldo_atual: Decimal
    saldo_inicial: Decimal
    entradas_periodo: Decimal
    saidas_periodo: Decimal
    saldo_liquido_periodo: Decimal
    ultima_movimentacao: date | None
    quantidade_movimentacoes: int


class ContaResumoMesAtual(BaseModel):
    """Mini resumo SEMPRE do mês corrente do calendário (`date.today()`),
    constante independente do período navegado no bloco `resumo` acima -
    "o pulso de agora". Ver docs/analise-arquitetural-extrato-conta.md."""

    entradas_mes: Decimal
    saidas_mes: Decimal
    saldo_mes: Decimal
    maior_entrada: MaiorMovimentacaoRead | None
    maior_saida: MaiorMovimentacaoRead | None


class ContaExtratoRead(BaseModel):
    """Resposta de `GET /contas/{id}/extrato` - painel "extrato bancário"
    pedido explicitamente pelo usuário (histórico expansível de
    `ContaResumoCard` no frontend). `movimentacoes` já vem ordenada da mais
    recente para a mais antiga, escopada ao mesmo `ano`/`mes` de `resumo`."""

    resumo: ContaExtratoResumo
    resumo_mes_atual: ContaResumoMesAtual
    movimentacoes: list[MovimentacaoContaRead]
