"""Engine e sessão. Um lugar só."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import config

_engine = create_engine(config().database_url, pool_pre_ping=True, future=True)
Sessao = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)


def engine():  # type: ignore[no-untyped-def]
    return _engine


def sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por request, commit no fim, rollback no erro."""
    db = Sessao()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
