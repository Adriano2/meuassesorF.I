"""Rotas de autenticação. Router só faz HTTP."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import BD, Autenticado
from app.schemas.auth import (
    EntradaComTokens,
    Login,
    Registro,
    Renovacao,
    SessaoSaida,
    TokensSaida,
)
from app.services.autenticacao import ServicoAutenticacao

router = APIRouter(tags=["auth"])


@router.post("/auth/registrar", response_model=EntradaComTokens,
             status_code=status.HTTP_201_CREATED)
def registrar(dados: Registro, db: BD) -> EntradaComTokens:
    sessao, tokens = ServicoAutenticacao(db).registrar(
        nome=dados.nome, email=dados.email, senha=dados.senha, nome_conta=dados.nome_conta
    )
    return EntradaComTokens(
        sessao=SessaoSaida(usuario=sessao.usuario, conta=sessao.conta, papel=sessao.papel),
        tokens=TokensSaida(acesso=tokens.acesso, refresh=tokens.refresh),
    )


@router.post("/auth/login", response_model=EntradaComTokens)
def login(dados: Login, db: BD) -> EntradaComTokens:
    sessao, tokens = ServicoAutenticacao(db).entrar(email=dados.email, senha=dados.senha)
    return EntradaComTokens(
        sessao=SessaoSaida(usuario=sessao.usuario, conta=sessao.conta, papel=sessao.papel),
        tokens=TokensSaida(acesso=tokens.acesso, refresh=tokens.refresh),
    )


@router.post("/auth/refresh", response_model=TokensSaida)
def refresh(dados: Renovacao, db: BD) -> TokensSaida:
    tokens = ServicoAutenticacao(db).renovar(dados.refresh)
    return TokensSaida(acesso=tokens.acesso, refresh=tokens.refresh)


@router.get("/me", response_model=SessaoSaida)
def me(sessao: Autenticado) -> SessaoSaida:
    return SessaoSaida(usuario=sessao.usuario, conta=sessao.conta, papel=sessao.papel)
