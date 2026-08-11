"""Schemas Pydantic — entrada e saída da API.

Dinheiro atravessa como inteiro de centavos, sempre. O backend nunca devolve
"R$ 1.234,56" (CLAUDE.md §4); quem formata é a interface.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import StatusFatura, StatusTransacao, TipoFluxo

Centavos = Field(ge=1, description="Valor em centavos. Nunca float.")


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Escrita(Saida):
    """Toda resposta de escrita carrega o id da operação que a registrou."""

    operacao_id: uuid.UUID | None = None


# ── categorias ───────────────────────────────────────────────────────────

class CategoriaEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    tipo: TipoFluxo
    cor: str | None = None
    icone: str | None = None
    palavras_chave: list[str] = Field(default_factory=list)
    orcamento_mensal_centavos: int | None = Field(default=None, ge=0)
    meta_receita_centavos: int | None = Field(default=None, ge=0)


class CategoriaSaida(Escrita):
    id: uuid.UUID
    nome: str
    tipo: TipoFluxo
    cor: str | None
    icone: str | None
    palavras_chave: list[str]
    orcamento_mensal_centavos: int | None
    meta_receita_centavos: int | None
    sistema: bool


# ── contas bancárias ─────────────────────────────────────────────────────

class ContaBancariaEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    instituicao: str | None = None
    tipo: str | None = None
    saldo_centavos: int = 0
    incluir_no_total: bool = True


class ContaBancariaSaida(Escrita):
    id: uuid.UUID
    nome: str
    instituicao: str | None
    tipo: str | None
    saldo_centavos: int
    incluir_no_total: bool


# ── cartões ──────────────────────────────────────────────────────────────

class CartaoEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    dia_fechamento: int = Field(ge=1, le=31)
    dia_vencimento: int = Field(ge=1, le=31)
    bandeira: str | None = None
    limite_centavos: int | None = Field(default=None, ge=0)
    conta_pagamento_id: uuid.UUID | None = None


class CartaoSaida(Escrita):
    id: uuid.UUID
    nome: str
    bandeira: str | None
    limite_centavos: int | None
    dia_fechamento: int
    dia_vencimento: int
    conta_pagamento_id: uuid.UUID | None


# ── faturas ──────────────────────────────────────────────────────────────

class FaturaSaida(Escrita):
    id: uuid.UUID
    cartao_id: uuid.UUID
    competencia: date
    data_fechamento: date
    data_vencimento: date
    total_centavos: int
    pago_centavos: int
    status: StatusFatura


class PagamentoFatura(BaseModel):
    valor_centavos: int | None = Field(default=None, ge=1)
    conta_bancaria_id: uuid.UUID | None = None
    data: date | None = None


# ── transações ───────────────────────────────────────────────────────────

class TransacaoEntrada(BaseModel):
    tipo: TipoFluxo
    descricao: str = Field(min_length=1, max_length=200)
    valor_centavos: int = Centavos
    data: date | None = Field(default=None, description="Padrão: hoje no fuso da conta.")
    status: StatusTransacao = StatusTransacao.realizado
    categoria_id: uuid.UUID | None = None
    conta_bancaria_id: uuid.UUID | None = None
    cartao_id: uuid.UUID | None = None
    pessoa_id: uuid.UUID | None = None
    parcelas: int | None = Field(default=None, ge=2, le=99)
    observacao: str | None = None


class TrocaCategoria(BaseModel):
    categoria_id: uuid.UUID


class TransacaoSaida(Escrita):
    id: uuid.UUID
    tipo: TipoFluxo
    descricao: str
    valor_centavos: int
    data_competencia: date
    data_efetiva: date | None
    status: StatusTransacao
    categoria_id: uuid.UUID | None
    categoria_travada: bool
    conta_bancaria_id: uuid.UUID | None
    cartao_id: uuid.UUID | None
    fatura_id: uuid.UUID | None
    pessoa_id: uuid.UUID | None
    parcela_num: int | None
    observacao: str | None


class ResumoPeriodo(BaseModel):
    de: date
    ate: date
    entradas_centavos: int
    saidas_centavos: int
    saldo_centavos: int
