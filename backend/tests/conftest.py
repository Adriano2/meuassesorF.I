"""Fixtures. Os testes de integração exigem PostgreSQL de verdade.

O schema tem citext, arrays, enums nativos e índices parciais — testar contra
SQLite daria uma falsa sensação de verde.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

BANCO = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://assessoria:assessoria@127.0.0.1:5432/assessoria_test",
)
os.environ.setdefault("DATABASE_URL", BANCO)
os.environ.setdefault("JWT_SEGREDO", "segredo-de-teste-com-mais-de-32-caracteres")


def _postgres_disponivel() -> bool:
    try:
        import psycopg

        with psycopg.connect(BANCO.replace("postgresql+psycopg", "postgresql"), connect_timeout=2):
            return True
    except Exception:
        return False


TEM_BANCO = _postgres_disponivel()
sem_banco = pytest.mark.skipif(not TEM_BANCO, reason="PostgreSQL indisponível")


@pytest.fixture(scope="session")
def esquema() -> Iterator[None]:
    """Cria o schema uma vez por sessão, a partir dos modelos."""
    if not TEM_BANCO:
        pytest.skip("PostgreSQL indisponível")

    from sqlalchemy import text

    from app.db.session import engine
    from app.models import Base

    with engine().begin() as conexao:
        conexao.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        conexao.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())
    yield
    Base.metadata.drop_all(engine())


@pytest.fixture
def db(esquema: None) -> Iterator[Any]:
    """Sessão limpa por teste: tudo é truncado antes de começar."""
    from sqlalchemy import text

    from app.db.session import Sessao, engine
    from app.models import Base

    tabelas = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    with engine().begin() as conexao:
        conexao.execute(text(f"TRUNCATE {tabelas} RESTART IDENTITY CASCADE"))

    sessao = Sessao()
    try:
        yield sessao
        sessao.commit()
    finally:
        sessao.close()


@pytest.fixture
def cliente(db: Any) -> Iterator[Any]:
    """TestClient com a sessão do teste injetada, para o rollback ser previsível."""
    from fastapi.testclient import TestClient

    from app.db.session import sessao as dependencia_sessao
    from app.main import app

    def sessao_de_teste() -> Iterator[Any]:
        yield db
        db.flush()

    app.dependency_overrides[dependencia_sessao] = sessao_de_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def conta_pronta(cliente: Any) -> dict[str, Any]:
    """Uma conta registrada, com token pronto e as categorias padrão semeadas."""
    resposta = cliente.post(
        "/api/v1/auth/registrar",
        json={
            "nome": "Adriano",
            "email": "adriano@exemplo.com",
            "senha": "senha-bem-comprida",
            "nome_conta": "Casa",
        },
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    return {
        "cabecalhos": {"Authorization": f"Bearer {corpo['tokens']['acesso']}"},
        "conta_id": corpo["sessao"]["conta"]["id"],
        "usuario_id": corpo["sessao"]["usuario"]["id"],
    }


@pytest.fixture
def outra_conta(cliente: Any) -> dict[str, Any]:
    """Segunda conta — existe só para provar que uma não enxerga a outra."""
    resposta = cliente.post(
        "/api/v1/auth/registrar",
        json={"nome": "Vizinha", "email": "vizinha@exemplo.com", "senha": "outra-senha-longa"},
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    return {
        "cabecalhos": {"Authorization": f"Bearer {corpo['tokens']['acesso']}"},
        "conta_id": corpo["sessao"]["conta"]["id"],
    }
