"""Contas, usuários e vínculo. O modelo de tenancy."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PapelConta, criado_em, deletado, pk


class Conta(Base):
    __tablename__ = "contas"

    id: Mapped[uuid.UUID] = pk()
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    fuso: Mapped[str] = mapped_column(Text, nullable=False, default="America/Sao_Paulo")
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    idioma: Mapped[str] = mapped_column(Text, nullable=False, default="pt-BR")
    criada_em: Mapped[datetime] = criado_em()


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    senha_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    telefone_e164: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    telefone_verificado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criado_em: Mapped[datetime] = criado_em()
    deleted_at: Mapped[datetime | None] = deletado()


class MembroConta(Base):
    __tablename__ = "membros_conta"

    conta_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("contas.id"), primary_key=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    papel: Mapped[PapelConta] = mapped_column(
        Enum(PapelConta, name="papel_conta", native_enum=True),
        nullable=False,
        default=PapelConta.membro,
    )
    criado_em: Mapped[datetime] = criado_em()
