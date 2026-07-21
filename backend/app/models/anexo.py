"""Model Anexo - arquivo anexado a uma Transacao (comprovante, nota fiscal,
foto do boleto...).

Redesenhado na etapa do CRUD de Anexo a partir do desenho especulativo
original (polimorfico, via `entidade_tipo`/`entidade_id`, mesma estrategia
de `Alerta`): as regras de dominio dadas explicitamente pelo usuario nesta
etapa sao diretas e sem ambiguidade - Anexo pertence SEMPRE a uma Transacao
(nunca a qualquer outra entidade) e NUNCA pertence diretamente ao usuario, a
posse e sempre transitiva via Transacao. Ver
docs/analise-arquitetural-anexo.md para o registro completo do conflito
entre o desenho inicial e essas regras, e por que a decisao foi redesenhar
o model em vez de manter o polimorfismo.

`TipoEntidadeReferenciavel` (o enum usado no desenho polimorfico anterior)
NAO foi alterado nem removido - continua reservado para `Alerta`, que ainda
nao teve suas regras de dominio definidas e pode legitimamente precisar de
referencia polimorfica de verdade.

O arquivo em si NAO fica no banco: `caminho_arquivo` guarda apenas a
referencia (caminho local, URL, chave de objeto em storage externo...) de
onde ele foi salvo. Onde/como armazenar o arquivo de fato e decisao de uma
camada de infraestrutura fora do escopo desta etapa (sem upload para cloud,
sem OCR, sem thumbnail, sem compressao, sem antivirus, sem versionamento,
sem compartilhamento, sem criptografia, sem download autenticado especial -
apenas CRUD e persistencia de metadados).

`ondelete="CASCADE"` em `transacao_id`: Transacao e removida de verdade
(hard delete, sem soft delete - ver docs/analise-arquitetural-transacao.md),
entao um Anexo orfao (apontando pra uma Transacao que nao existe mais) nao
faz sentido - ele desaparece junto quando a Transacao e excluida.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Anexo(Base):
    __tablename__ = "anexos"

    id: Mapped[int] = mapped_column(primary_key=True)
    transacao_id: Mapped[int] = mapped_column(ForeignKey("transacoes.id", ondelete="CASCADE"), index=True)

    nome_original: Mapped[str] = mapped_column(String(255))
    caminho_arquivo: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamanho_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # anexo e essencialmente imutavel apos criado (decisao confirmada
    # explicitamente com o usuario: sem PATCH - ver
    # docs/analise-arquitetural-anexo.md), entao aqui so guardamos
    # data_upload - sem TimestampMixin completo, que traria um
    # atualizado_em que nunca seria usado.
    data_upload: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- relacionamentos ---
    transacao: Mapped["Transacao"] = relationship(back_populates="anexos")
