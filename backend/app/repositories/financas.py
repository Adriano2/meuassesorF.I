"""Acesso a dados do domínio financeiro."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select

from app.models.base import StatusTransacao, TipoFluxo
from app.models.financas import Cartao, Categoria, ContaBancaria, Fatura, Pessoa, Transacao
from app.repositories.base import RepositoryBase


class CategoriaRepository(RepositoryBase[Categoria]):
    modelo = Categoria

    def por_nome(self, conta_id: uuid.UUID, nome: str, tipo: TipoFluxo) -> Categoria | None:
        consulta = self._base(conta_id).where(
            func.lower(Categoria.nome) == nome.lower(), Categoria.tipo == tipo
        )
        return self.db.scalars(consulta).first()

    def listar_por_tipo(self, conta_id: uuid.UUID, tipo: TipoFluxo | None) -> Sequence[Categoria]:
        consulta = self._base(conta_id).order_by(Categoria.nome)
        if tipo is not None:
            consulta = consulta.where(Categoria.tipo == tipo)
        return self.db.scalars(consulta).all()


class ContaBancariaRepository(RepositoryBase[ContaBancaria]):
    modelo = ContaBancaria

    def saldo_total(self, conta_id: uuid.UUID) -> int:
        consulta = (
            select(func.coalesce(func.sum(ContaBancaria.saldo_centavos), 0))
            .where(ContaBancaria.conta_id == conta_id)
            .where(ContaBancaria.deleted_at.is_(None))
            .where(ContaBancaria.incluir_no_total.is_(True))
        )
        return int(self.db.scalar(consulta) or 0)


class CartaoRepository(RepositoryBase[Cartao]):
    modelo = Cartao


class PessoaRepository(RepositoryBase[Pessoa]):
    modelo = Pessoa


class FaturaRepository(RepositoryBase[Fatura]):
    modelo = Fatura

    def por_competencia(
        self, conta_id: uuid.UUID, cartao_id: uuid.UUID, competencia: date
    ) -> Fatura | None:
        consulta = self._base(conta_id).where(
            Fatura.cartao_id == cartao_id, Fatura.competencia == competencia
        )
        return self.db.scalars(consulta).first()

    def listar_do_cartao(self, conta_id: uuid.UUID, cartao_id: uuid.UUID) -> Sequence[Fatura]:
        consulta = (
            self._base(conta_id)
            .where(Fatura.cartao_id == cartao_id)
            .order_by(Fatura.competencia.desc())
        )
        return self.db.scalars(consulta).all()

    def somar_transacoes(self, conta_id: uuid.UUID, fatura_id: uuid.UUID) -> int:
        """Total da fatura derivado por soma — nunca campo mantido à mão (ESPEC §4.2)."""
        consulta = (
            select(func.coalesce(func.sum(Transacao.valor_centavos), 0))
            .where(Transacao.conta_id == conta_id)
            .where(Transacao.fatura_id == fatura_id)
            .where(Transacao.deleted_at.is_(None))
            .where(Transacao.status != StatusTransacao.cancelado)
        )
        return int(self.db.scalar(consulta) or 0)


class TransacaoRepository(RepositoryBase[Transacao]):
    modelo = Transacao

    def buscar(
        self,
        conta_id: uuid.UUID,
        *,
        de: date | None = None,
        ate: date | None = None,
        tipo: TipoFluxo | None = None,
        status: StatusTransacao | None = None,
        categoria_id: uuid.UUID | None = None,
        conta_bancaria_id: uuid.UUID | None = None,
        cartao_id: uuid.UUID | None = None,
        pessoa_id: uuid.UUID | None = None,
        texto: str | None = None,
        limite: int = 100,
        deslocamento: int = 0,
    ) -> Sequence[Transacao]:
        consulta = self._base(conta_id)
        if de is not None:
            consulta = consulta.where(Transacao.data_competencia >= de)
        if ate is not None:
            consulta = consulta.where(Transacao.data_competencia <= ate)
        if tipo is not None:
            consulta = consulta.where(Transacao.tipo == tipo)
        if status is not None:
            consulta = consulta.where(Transacao.status == status)
        if categoria_id is not None:
            consulta = consulta.where(Transacao.categoria_id == categoria_id)
        if conta_bancaria_id is not None:
            consulta = consulta.where(Transacao.conta_bancaria_id == conta_bancaria_id)
        if cartao_id is not None:
            consulta = consulta.where(Transacao.cartao_id == cartao_id)
        if pessoa_id is not None:
            consulta = consulta.where(Transacao.pessoa_id == pessoa_id)
        if texto:
            consulta = consulta.where(Transacao.descricao.ilike(f"%{texto}%"))

        consulta = consulta.order_by(
            Transacao.data_competencia.desc(), Transacao.criado_em.desc()
        )
        return self.db.scalars(consulta.limit(limite).offset(deslocamento)).all()

    def somar(
        self,
        conta_id: uuid.UUID,
        *,
        de: date,
        ate: date,
        tipo: TipoFluxo,
        status: StatusTransacao | None = StatusTransacao.realizado,
    ) -> int:
        consulta = (
            select(func.coalesce(func.sum(Transacao.valor_centavos), 0))
            .where(Transacao.conta_id == conta_id)
            .where(Transacao.deleted_at.is_(None))
            .where(Transacao.data_competencia >= de)
            .where(Transacao.data_competencia <= ate)
            .where(Transacao.tipo == tipo)
        )
        if status is not None:
            consulta = consulta.where(Transacao.status == status)
        return int(self.db.scalar(consulta) or 0)

    def da_serie(self, conta_id: uuid.UUID, serie_id: uuid.UUID) -> Sequence[Transacao]:
        consulta = self._base(conta_id).where(Transacao.serie_id == serie_id).order_by(
            Transacao.data_competencia
        )
        return self.db.scalars(consulta).all()
