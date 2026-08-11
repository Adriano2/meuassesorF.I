"""Base declarativa e enums do domínio."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def conta_fk() -> Mapped[uuid.UUID]:
    """Toda tabela de domínio carrega conta_id. CLAUDE.md §4."""
    return mapped_column(PgUUID(as_uuid=True), ForeignKey("contas.id"), nullable=False, index=True)


def criado_em() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def deletado() -> Mapped[datetime | None]:
    """Soft delete. Nenhum DELETE físico em tabela de domínio."""
    return mapped_column(DateTime(timezone=True), nullable=True)


class PapelConta(enum.StrEnum):
    dono = "dono"
    administrador = "administrador"
    membro = "membro"
    leitor = "leitor"


class TipoFluxo(enum.StrEnum):
    entrada = "entrada"
    saida = "saida"


class StatusTransacao(enum.StrEnum):
    previsto = "previsto"
    realizado = "realizado"
    cancelado = "cancelado"


class OrigemRegistro(enum.StrEnum):
    manual = "manual"
    agente = "agente"
    open_finance = "open_finance"
    serie = "serie"
    importacao = "importacao"


class StatusFatura(enum.StrEnum):
    aberta = "aberta"
    fechada = "fechada"
    paga = "paga"
    parcial = "parcial"


class TipoSerie(enum.StrEnum):
    recorrente = "recorrente"
    parcelada = "parcelada"


class Frequencia(enum.StrEnum):
    diaria = "diaria"
    semanal = "semanal"
    quinzenal = "quinzenal"
    mensal = "mensal"
    bimestral = "bimestral"
    trimestral = "trimestral"
    semestral = "semestral"
    anual = "anual"
