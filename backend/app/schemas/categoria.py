"""Schemas de Categoria: payloads de entrada e saída de
`app/api/routes/categoria.py`.

`e_do_sistema` existe só em `CategoriaRead` - é um `@computed_field`
derivado de `usuario_id` (True quando nulo), não uma coluna do model.
Diferente de `Conta.saldo_atual` (que precisa de uma agregação no banco,
calculada pelo Service), esta derivação é pura leitura de um campo já
carregado - por isso vive no Schema, não no Service: não há necessidade de
tocar o banco de novo nem de anexar atributo transiente ao objeto ORM.

`oculta_para_mim` (Sprint de Refinamento Premium, item 4) é o caso
oposto: é por-usuário, não pode ser derivado de nenhuma coluna já
carregada de `Categoria` - por isso é um campo comum (não
`@computed_field`), preenchido pelo `CategoriaService` via
`_anexar_oculta_para_mim` (atributo transiente no objeto ORM, mesmo
padrão de `Conta.saldo_atual`) antes de `model_validate`.
"""
from pydantic import BaseModel, Field, computed_field

from app.models.enums import TipoCategoria
from app.schemas.base import OrmBaseModel

# "#RRGGBB" - usado na UI para colorir a categoria.
_PADRAO_COR_HEX = r"^#[0-9A-Fa-f]{6}$"


class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    tipo: TipoCategoria = TipoCategoria.AMBOS
    cor: str | None = Field(default=None, pattern=_PADRAO_COR_HEX)
    icone: str | None = Field(default=None, max_length=40)
    categoria_pai_id: int | None = None


class CategoriaUpdate(BaseModel):
    """Todos os campos opcionais - semântica de PATCH (só o que for enviado
    é alterado). `usuario_id` nunca aparece aqui: posse não se atualiza via
    payload."""

    nome: str | None = Field(default=None, min_length=1, max_length=80)
    tipo: TipoCategoria | None = None
    cor: str | None = Field(default=None, pattern=_PADRAO_COR_HEX)
    icone: str | None = Field(default=None, max_length=40)
    categoria_pai_id: int | None = None
    ativo: bool | None = None


class CategoriaRead(OrmBaseModel):
    id: int
    nome: str
    tipo: TipoCategoria
    cor: str | None
    icone: str | None
    ativo: bool
    usuario_id: int | None
    categoria_pai_id: int | None
    oculta_para_mim: bool = False

    @computed_field
    @property
    def e_do_sistema(self) -> bool:
        return self.usuario_id is None
