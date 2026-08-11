"""Aplicação FastAPI.

Um único exception handler traduz exceção de domínio para HTTP. Router nunca
monta HTTPException na mão (CLAUDE.md §9).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import auth, financas
from app.core.contexto import Contexto, atual, definir, novo_trace_id
from app.core.erros import ErroDominio

logger = logging.getLogger("assessoria")

app = FastAPI(
    title="Assessoria pessoal — API",
    version="0.1.0",
    description="Fase 1: fundação. Schema, autenticação e CRUD financeiro.",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(financas.router, prefix="/api/v1")


@app.middleware("http")
async def rastrear(request: Request, proximo: Any) -> Any:
    trace_id = request.headers.get("X-Trace-Id") or novo_trace_id()
    definir(Contexto(trace_id=trace_id))
    resposta = await proximo(request)
    resposta.headers["X-Trace-Id"] = trace_id
    return resposta


def _corpo_de_erro(codigo: str, mensagem: str, detalhe: dict[str, Any] | None = None) -> dict:
    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "trace_id": atual().trace_id,
        "detalhe": detalhe or {},
    }


@app.exception_handler(ErroDominio)
async def tratar_erro_dominio(_: Request, erro: ErroDominio) -> JSONResponse:
    # log estruturado sem payload financeiro nem conteúdo de mensagem
    logger.warning(
        "erro_dominio",
        extra={"codigo": erro.codigo, "trace_id": atual().trace_id, "conta_id": str(
            atual().conta_id)},
    )
    return JSONResponse(
        status_code=erro.http,
        content=_corpo_de_erro(erro.codigo, erro.mensagem, erro.detalhe),
    )


@app.exception_handler(RequestValidationError)
async def tratar_validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
    campos = [
        {"campo": ".".join(str(p) for p in e["loc"][1:]), "erro": e["msg"]} for e in erro.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_corpo_de_erro("dado_invalido", "Confira os dados enviados.", {"campos": campos}),
    )


@app.exception_handler(ValueError)
async def tratar_valor(_: Request, erro: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=422, content=_corpo_de_erro("dado_invalido", str(erro))
    )


@app.get("/saude", tags=["infra"])
def saude() -> dict[str, str]:
    return {"status": "ok"}
