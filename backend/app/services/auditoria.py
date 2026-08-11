"""registrar_operacao() — toda escrita passa por aqui. CLAUDE.md §4.

Guarda snapshot `antes` e `depois`. É o que sustenta o Desfazer, a auditoria e
a idempotência: repetir a mesma `Idempotency-Key` devolve a operação original
em vez de executar de novo.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auditoria import Operacao
from app.models.base import Base


def instantanear(entidade: Base | None) -> dict[str, Any] | None:
    """Snapshot serializável de uma entidade, para gravar em JSONB.

    Sem payload sensível: este dicionário vai para o banco, não para o log.
    """
    if entidade is None:
        return None

    dados: dict[str, Any] = {}
    for coluna in entidade.__table__.columns:  # type: ignore[attr-defined]
        valor = getattr(entidade, coluna.name, None)
        dados[coluna.name] = _serializar(valor)
    return dados


def _serializar(valor: Any) -> Any:
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        # dinheiro nunca é Decimal aqui, mas não deixa passar em silêncio
        return str(valor)
    if isinstance(valor, list):
        return [_serializar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _serializar(v) for k, v in valor.items()}
    return valor


def operacao_por_chave(
    db: Session, conta_id: uuid.UUID, idempotency_key: str | None
) -> Operacao | None:
    if not idempotency_key:
        return None
    consulta = select(Operacao).where(
        Operacao.conta_id == conta_id, Operacao.idempotency_key == idempotency_key
    )
    return db.scalars(consulta).first()


def registrar_operacao(
    db: Session,
    *,
    conta_id: uuid.UUID,
    usuario_id: uuid.UUID | None,
    ator: str,
    acao: str,
    entidade: str,
    entidade_id: uuid.UUID | None,
    antes: dict[str, Any] | None = None,
    depois: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> Operacao:
    operacao = Operacao(
        conta_id=conta_id,
        usuario_id=usuario_id,
        ator=ator,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        antes=antes,
        depois=depois,
        idempotency_key=idempotency_key,
    )
    db.add(operacao)
    db.flush()
    db.refresh(operacao)
    return operacao
