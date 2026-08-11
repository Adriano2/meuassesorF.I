"""Dependências do FastAPI: sessão de banco, autenticação e autor da escrita."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.contexto import Contexto, definir, novo_trace_id
from app.core.erros import NaoAutenticado, SemPermissao
from app.db.session import sessao
from app.models.base import PapelConta
from app.services.autenticacao import ServicoAutenticacao
from app.services.autenticacao import Sessao as SessaoUsuario
from app.services.financas import Autor

esquema = HTTPBearer(auto_error=False)

BD = Annotated[Session, Depends(sessao)]

# papéis que podem escrever; 'leitor' só lê
PAPEIS_DE_ESCRITA = {PapelConta.dono, PapelConta.administrador, PapelConta.membro}


def sessao_atual(
    db: BD,
    credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema)] = None,
) -> SessaoUsuario:
    if credencial is None or not credencial.credentials:
        raise NaoAutenticado()
    sessao_usuario = ServicoAutenticacao(db).sessao_do_token(credencial.credentials)
    definir(
        Contexto(
            trace_id=novo_trace_id(),
            conta_id=sessao_usuario.conta.id,
            usuario_id=sessao_usuario.usuario.id,
            fuso=sessao_usuario.conta.fuso,
        )
    )
    return sessao_usuario


Autenticado = Annotated[SessaoUsuario, Depends(sessao_atual)]

# A chave de idempotência é do protocolo, não do corpo da requisição.
Idempotencia = Annotated[str | None, Header(alias="Idempotency-Key")]


def autor_de(sessao_usuario: SessaoUsuario) -> Autor:
    """Converte a sessão HTTP no `Autor` que os services entendem.

    O `conta_id` sai daqui — do token — e nunca do corpo da requisição.
    """
    return Autor(
        conta_id=sessao_usuario.conta.id,
        usuario_id=sessao_usuario.usuario.id,
        fuso=sessao_usuario.conta.fuso,
        ator="usuario",
    )


def exigir_escrita(sessao_usuario: Autenticado) -> Autor:
    if sessao_usuario.papel not in PAPEIS_DE_ESCRITA:
        raise SemPermissao("Seu papel nesta conta é somente leitura.")
    return autor_de(sessao_usuario)


AutorEscrita = Annotated[Autor, Depends(exigir_escrita)]
