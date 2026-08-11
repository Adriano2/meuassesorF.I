"""Contexto de request: trace_id, conta e usuário.

Serve para log e auditoria. **Não** serve para filtrar query: o `conta_id` do
filtro é sempre passado explicitamente para o repository (CLAUDE.md §4).
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

_atual: ContextVar[Contexto | None] = ContextVar("contexto_atual", default=None)


@dataclass(frozen=True)
class Contexto:
    trace_id: str
    conta_id: uuid.UUID | None = None
    usuario_id: uuid.UUID | None = None
    fuso: str = "America/Sao_Paulo"
    ator: str = "usuario"


def novo_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def definir(ctx: Contexto) -> None:
    _atual.set(ctx)


def atual() -> Contexto:
    ctx = _atual.get()
    return ctx if ctx is not None else Contexto(trace_id=novo_trace_id())
