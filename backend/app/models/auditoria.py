"""Registro de operações — o coração do Desfazer e da auditoria. CLAUDE.md §4."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, conta_fk, criado_em, pk


class Operacao(Base):
    __tablename__ = "operacoes"
    __table_args__ = (
        Index(
            "uq_operacoes_idempotency",
            "conta_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_operacoes_conta_data", "conta_id", "criada_em"),
    )

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    # 'usuario' | 'agente:financas' | 'sistema:sync'
    ator: Mapped[str] = mapped_column(Text, nullable=False)
    # 'transacao.criar', 'cartao.excluir', ...
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    entidade: Mapped[str] = mapped_column(Text, nullable=False)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    antes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    depois: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    revertida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revertida_por_op: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("operacoes.id"), nullable=True
    )
    mensagem_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    criada_em: Mapped[datetime] = criado_em()
