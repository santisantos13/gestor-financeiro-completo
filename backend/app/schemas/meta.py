"""Schemas de Meta: payloads de entrada e saída de `app/api/routes/meta.py`.

`valor_acumulado`/`percentual` existem SÓ em `MetaRead` - não são colunas do
model `Meta` (mesmo princípio de `ContaRead.saldo_atual`/
`CartaoRead.limite_disponivel`: valor sempre calculado, nunca armazenado).
`MetaService` calcula esses valores e os anexa como atributos transientes
ao objeto `Meta` antes de devolvê-lo ao Router. Ver
docs/analise-arquitetural-meta.md.

`conta_id` NÃO existe em `MetaCreate`/`MetaUpdate` (removido no
Refatoramento de Metas/Transferências) - deixou de ser uma escolha do
usuário: toda Meta ganha automaticamente um "cofrinho" (Conta dedicada e
oculta) criado por `MetaService.criar`. Continua em `MetaRead` (sempre
preenchido) para o Frontend montar o payload de aporte/resgate
(`POST /transferencias` com esse id como origem/destino). Ver
docs/analise-arquitetural-metas-transferencias.md, seção 2.
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import FrequenciaContribuicao, SituacaoPlanejamentoMeta
from app.schemas.base import OrmBaseModel


class MetaCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    valor_alvo: Decimal = Field(gt=0)
    data_alvo: date | None = None
    frequencia_contribuicao: FrequenciaContribuicao | None = None

    @field_validator("descricao", mode="before")
    @classmethod
    def _remover_espacos_nas_pontas(cls, descricao: str) -> str:
        # mode="before": mesmo raciocínio de TagCreate - roda ANTES do
        # min_length ser conferido, senão uma descrição só de espaços
        # passaria a checagem (tamanho >= 1) e só viraria vazia depois.
        # Sem a normalização, "Viagem" e "Viagem " também seriam
        # descrições DIFERENTES pro UniqueConstraint(usuario_id, descricao),
        # esvaziando na prática a regra de "nome único por usuário".
        return descricao.strip() if isinstance(descricao, str) else descricao


class MetaUpdate(BaseModel):
    """Todos os campos são opcionais - semântica de PATCH. `usuario_id`
    nunca aparece aqui: posse não se atualiza via payload."""

    descricao: str | None = Field(default=None, min_length=1, max_length=200)
    valor_alvo: Decimal | None = Field(default=None, gt=0)
    data_alvo: date | None = None
    ativo: bool | None = None
    frequencia_contribuicao: FrequenciaContribuicao | None = None

    @field_validator("descricao", mode="before")
    @classmethod
    def _remover_espacos_nas_pontas(cls, descricao: str | None) -> str | None:
        return descricao.strip() if isinstance(descricao, str) else descricao


class MetaRead(OrmBaseModel):
    id: int
    descricao: str
    valor_alvo: Decimal
    data_alvo: date | None
    # Sempre preenchido - o "cofrinho" automático desta Meta (ver docstring
    # do módulo). Frontend usa este id para montar o payload de aporte/
    # resgate, mas NUNCA mostra esta conta ao usuário diretamente.
    conta_id: int
    ativo: bool
    frequencia_contribuicao: FrequenciaContribuicao | None

    valor_acumulado: Decimal
    percentual: Decimal

    # Exposto para o Frontend calcular uma métrica de APRESENTAÇÃO
    # ("velocidade média de aporte desde a criação da meta") sem precisar
    # buscar o histórico de transações só para achar uma data de início -
    # é a mesma coluna que `TimestampMixin` já grava automaticamente em toda
    # tabela do projeto, só nunca tinha sido exposta em nenhum Read porque
    # nenhuma outra entidade precisou dela até agora. Não é um campo
    # calculado/regra de negócio - é a data real de criação da linha.
    criado_em: datetime

    # Data em que a meta foi concluída (percentual >= 100%) PELA PRIMEIRA
    # VEZ - coluna real, gravada lazily por `MetaService._com_progresso`
    # (ver docs/analise-arquitetural-metas-refinamento.md, seção 4.1).
    # Nunca é desfeita mesmo que o percentual caia depois.
    concluida_em: date | None

    # --- Campos de planejamento (Refinamento de Metas) - todos CALCULADOS
    # por `MetaService._com_progresso`, nunca colunas do model, nunca
    # substituem valor_acumulado/percentual (ver docs/analise-arquitetural-
    # metas-refinamento.md, seções 1-3). `None` sempre que não houver dados
    # suficientes para um valor confiável (sem data_alvo, sem frequência,
    # prazo já vencido, meta já concluída, ou sem nenhum sinal de
    # progresso ainda).
    contribuicao_sugerida_por_periodo: Decimal | None
    valor_planejado_ate_hoje: Decimal | None
    diferenca_planejado_realizado: Decimal | None
    situacao_planejamento: SituacaoPlanejamentoMeta | None
    data_prevista_conclusao: date | None
