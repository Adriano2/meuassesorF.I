"""Repository base. ÚNICO lugar do código com SQL/ORM. CLAUDE.md §3.

Duas garantias que este arquivo existe para dar:

1. `conta_id` é o primeiro argumento explícito de toda operação — nunca vem de
   variável de contexto implícita;
2. toda leitura filtra `deleted_at IS NULL`.

Se você precisar escapar disso, é sinal de que a regra está no lugar errado.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.base import Base

M = TypeVar("M", bound=Base)


class RepositoryBase(Generic[M]):
    modelo: type[M]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── leitura ──────────────────────────────────────────────────────────

    def _base(self, conta_id: uuid.UUID) -> Select[tuple[M]]:
        consulta = select(self.modelo).where(self.modelo.conta_id == conta_id)  # type: ignore[attr-defined]
        if hasattr(self.modelo, "deleted_at"):
            consulta = consulta.where(self.modelo.deleted_at.is_(None))  # type: ignore[attr-defined]
        return consulta

    def por_id(self, conta_id: uuid.UUID, id_: uuid.UUID) -> M | None:
        return self.db.scalars(self._base(conta_id).where(self.modelo.id == id_)).first()  # type: ignore[attr-defined]

    def listar(
        self,
        conta_id: uuid.UUID,
        *,
        limite: int = 100,
        deslocamento: int = 0,
        ordem: Any = None,
    ) -> Sequence[M]:
        consulta = self._base(conta_id)
        if ordem is not None:
            consulta = consulta.order_by(ordem)
        return self.db.scalars(consulta.limit(limite).offset(deslocamento)).all()

    def contar(self, conta_id: uuid.UUID) -> int:
        from sqlalchemy import func

        consulta = select(func.count()).select_from(self.modelo).where(
            self.modelo.conta_id == conta_id  # type: ignore[attr-defined]
        )
        if hasattr(self.modelo, "deleted_at"):
            consulta = consulta.where(self.modelo.deleted_at.is_(None))  # type: ignore[attr-defined]
        return self.db.scalar(consulta) or 0

    # ── escrita ──────────────────────────────────────────────────────────

    def inserir(self, entidade: M) -> M:
        self.db.add(entidade)
        self.db.flush()
        self.db.refresh(entidade)
        return entidade

    def marcar_excluido(self, entidade: M) -> M:
        """Soft delete. Nenhum DELETE físico em tabela de domínio."""
        if not hasattr(entidade, "deleted_at"):
            raise TypeError(f"{type(entidade).__name__} não suporta soft delete")
        entidade.deleted_at = datetime.now(tz=UTC)  # type: ignore[attr-defined]
        self.db.flush()
        return entidade
