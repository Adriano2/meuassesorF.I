"""Categorias, contas bancárias, cartões, faturas, pessoas, séries e transações."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    Frequencia,
    OrigemRegistro,
    StatusFatura,
    StatusTransacao,
    TipoFluxo,
    TipoSerie,
    conta_fk,
    criado_em,
    deletado,
    pk,
)


def _fk(tabela: str) -> Mapped[uuid.UUID | None]:
    return mapped_column(PgUUID(as_uuid=True), ForeignKey(f"{tabela}.id"), nullable=True)


class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("conta_id", "nome", "tipo", name="uq_categoria_nome_tipo"),)

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[TipoFluxo] = mapped_column(
        Enum(TipoFluxo, name="tipo_fluxo", native_enum=True), nullable=False
    )
    cor: Mapped[str | None] = mapped_column(Text, nullable=True)
    icone: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = _fk("categorias")
    palavras_chave: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    orcamento_mensal_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    meta_receita_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = deletado()


class ContaBancaria(Base):
    __tablename__ = "contas_bancarias"

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    instituicao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str | None] = mapped_column(Text, nullable=True)
    saldo_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    saldo_atualizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # conexao_id ganha FK para conexoes_of na Fase 4, quando a tabela existir
    conexao_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    externo_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    incluir_no_total: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = deletado()


class Cartao(Base):
    __tablename__ = "cartoes"
    __table_args__ = (
        CheckConstraint("dia_fechamento BETWEEN 1 AND 31", name="ck_cartao_fechamento"),
        CheckConstraint("dia_vencimento BETWEEN 1 AND 31", name="ck_cartao_vencimento"),
    )

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    bandeira: Mapped[str | None] = mapped_column(Text, nullable=True)
    limite_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dia_fechamento: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    dia_vencimento: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    conta_pagamento_id: Mapped[uuid.UUID | None] = _fk("contas_bancarias")
    conexao_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    externo_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = deletado()


class Fatura(Base):
    __tablename__ = "faturas"
    __table_args__ = (UniqueConstraint("cartao_id", "competencia", name="uq_fatura_competencia"),)

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    cartao_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("cartoes.id"), nullable=False
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    data_fechamento: Mapped[date] = mapped_column(Date, nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    # total_centavos é derivado por soma (ESPEC §4.2); a coluna é cache de leitura
    total_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    pago_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[StatusFatura] = mapped_column(
        Enum(StatusFatura, name="status_fatura", native_enum=True),
        nullable=False,
        default=StatusFatura.aberta,
    )


class Pessoa(Base):
    __tablename__ = "pessoas"

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    apelidos: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    telefone_e164: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    documento: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = deletado()


class Serie(Base):
    """Recorrência e parcelamento na mesma abstração.

    A tabela nasce na Fase 1 porque `transacoes.serie_id` aponta para ela.
    O motor de materialização é da Fase 2 (ESPEC §4.1).
    """

    __tablename__ = "series"

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    tipo: Mapped[TipoSerie] = mapped_column(
        Enum(TipoSerie, name="tipo_serie", native_enum=True), nullable=False
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_fluxo: Mapped[TipoFluxo] = mapped_column(
        Enum(TipoFluxo, name="tipo_fluxo", native_enum=True, create_type=False), nullable=False
    )
    valor_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    categoria_id: Mapped[uuid.UUID | None] = _fk("categorias")
    conta_bancaria_id: Mapped[uuid.UUID | None] = _fk("contas_bancarias")
    cartao_id: Mapped[uuid.UUID | None] = _fk("cartoes")
    pessoa_id: Mapped[uuid.UUID | None] = _fk("pessoas")
    freq: Mapped[Frequencia | None] = mapped_column(
        Enum(Frequencia, name="frequencia", native_enum=True), nullable=True
    )
    dia_do_mes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    politica_dia_util: Mapped[str] = mapped_column(Text, nullable=False, default="manter")
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_parcelas: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = deletado()


class SerieExcecao(Base):
    __tablename__ = "series_excecoes"

    serie_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("series.id"), primary_key=True
    )
    data_prevista: Mapped[date] = mapped_column(Date, primary_key=True)
    acao: Mapped[str] = mapped_column(Text, nullable=False)
    transacao_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


class Transacao(Base):
    __tablename__ = "transacoes"
    __table_args__ = (
        CheckConstraint("valor_centavos > 0", name="ck_transacao_valor_positivo"),
        Index(
            "ix_transacoes_conta_competencia",
            "conta_id",
            "data_competencia",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_transacoes_conta_categoria", "conta_id", "categoria_id", "data_competencia"),
        Index(
            "uq_transacoes_externo",
            "conta_id",
            "externo_id",
            unique=True,
            postgresql_where=text("externo_id IS NOT NULL"),
        ),
        Index(
            "ix_transacoes_hash_dedup",
            "conta_id",
            "hash_dedup",
            postgresql_where=text("hash_dedup IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = pk()
    conta_id: Mapped[uuid.UUID] = conta_fk()
    criado_por: Mapped[uuid.UUID | None] = _fk("usuarios")
    tipo: Mapped[TipoFluxo] = mapped_column(
        Enum(TipoFluxo, name="tipo_fluxo", native_enum=True, create_type=False), nullable=False
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    valor_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # data_competencia: em que mês conta. data_efetiva: quando o dinheiro moveu.
    data_competencia: Mapped[date] = mapped_column(Date, nullable=False)
    data_efetiva: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[StatusTransacao] = mapped_column(
        Enum(StatusTransacao, name="status_transacao", native_enum=True),
        nullable=False,
        default=StatusTransacao.realizado,
    )
    categoria_id: Mapped[uuid.UUID | None] = _fk("categorias")
    categoria_travada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    conta_bancaria_id: Mapped[uuid.UUID | None] = _fk("contas_bancarias")
    cartao_id: Mapped[uuid.UUID | None] = _fk("cartoes")
    fatura_id: Mapped[uuid.UUID | None] = _fk("faturas")
    pessoa_id: Mapped[uuid.UUID | None] = _fk("pessoas")
    serie_id: Mapped[uuid.UUID | None] = _fk("series")
    parcela_num: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    origem: Mapped[OrigemRegistro] = mapped_column(
        Enum(OrigemRegistro, name="origem_registro", native_enum=True),
        nullable=False,
        default=OrigemRegistro.manual,
    )
    externo_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    hash_dedup: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    anexos: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    criado_em: Mapped[datetime] = criado_em()
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = deletado()
