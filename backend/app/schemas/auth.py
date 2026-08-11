"""Schemas de autenticação."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import PapelConta


class Registro(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    nome_conta: str | None = Field(default=None, max_length=120)


class Login(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=72)


class Renovacao(BaseModel):
    refresh: str


class TokensSaida(BaseModel):
    acesso: str
    refresh: str
    tipo: str = "bearer"


class ContaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    fuso: str
    moeda: str


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str


class SessaoSaida(BaseModel):
    usuario: UsuarioSaida
    conta: ContaSaida
    papel: PapelConta


class EntradaComTokens(BaseModel):
    sessao: SessaoSaida
    tokens: TokensSaida
