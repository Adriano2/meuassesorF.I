"""Senha e token. CLAUDE.md §5 — nada de segredo em log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import config
from app.core.erros import NaoAutenticado

TipoToken = Literal["acesso", "refresh"]

# bcrypt trunca em 72 bytes; recusar antes é melhor que truncar em silêncio
LIMITE_SENHA_BYTES = 72


def cifrar_senha(senha: str) -> str:
    bruta = senha.encode("utf-8")
    if len(bruta) > LIMITE_SENHA_BYTES:
        raise ValueError("senha longa demais")
    return bcrypt.hashpw(bruta, bcrypt.gensalt()).decode("utf-8")


def conferir_senha(senha: str, hash_armazenado: str | None) -> bool:
    if not hash_armazenado:
        return False
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8"))
    except ValueError:
        return False


def emitir_token(
    *,
    usuario_id: uuid.UUID,
    conta_id: uuid.UUID,
    tipo: TipoToken = "acesso",
) -> str:
    cfg = config()
    agora_utc = datetime.now(tz=UTC)
    duracao = (
        timedelta(minutes=cfg.jwt_minutos_acesso)
        if tipo == "acesso"
        else timedelta(days=cfg.jwt_dias_refresh)
    )
    corpo: dict[str, Any] = {
        "sub": str(usuario_id),
        "conta_id": str(conta_id),
        "tipo": tipo,
        "iat": int(agora_utc.timestamp()),
        "exp": int((agora_utc + duracao).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(corpo, cfg.jwt_segredo, algorithm=cfg.jwt_algoritmo)


def ler_token(token: str, *, tipo_esperado: TipoToken = "acesso") -> dict[str, Any]:
    cfg = config()
    try:
        corpo: dict[str, Any] = jwt.decode(token, cfg.jwt_segredo, algorithms=[cfg.jwt_algoritmo])
    except jwt.ExpiredSignatureError as e:
        raise NaoAutenticado("Sua sessão expirou. Entre de novo.") from e
    except jwt.InvalidTokenError as e:
        raise NaoAutenticado("Sessão inválida.") from e

    if corpo.get("tipo") != tipo_esperado:
        raise NaoAutenticado("Sessão inválida.")
    return corpo


def redigir(texto: str) -> str:
    """Marca conteúdo sensível antes de qualquer gravação ou log."""
    return "[redigido]" if texto else texto
