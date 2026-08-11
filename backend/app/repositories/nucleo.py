"""Acesso a dados de contas e usuários.

Não herda de RepositoryBase porque `usuarios` e `contas` não são tabelas
multi-tenant no mesmo sentido: um usuário pode pertencer a mais de uma conta.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nucleo import Conta, MembroConta, Usuario


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def por_email(self, email: str) -> Usuario | None:
        consulta = select(Usuario).where(Usuario.email == email, Usuario.deleted_at.is_(None))
        return self.db.scalars(consulta).first()

    def por_id(self, id_: uuid.UUID) -> Usuario | None:
        consulta = select(Usuario).where(Usuario.id == id_, Usuario.deleted_at.is_(None))
        return self.db.scalars(consulta).first()

    def inserir(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        self.db.refresh(usuario)
        return usuario


class ContaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def por_id(self, id_: uuid.UUID) -> Conta | None:
        return self.db.get(Conta, id_)

    def inserir(self, conta: Conta) -> Conta:
        self.db.add(conta)
        self.db.flush()
        self.db.refresh(conta)
        return conta

    def vincular(self, conta_id: uuid.UUID, usuario_id: uuid.UUID, papel: object) -> MembroConta:
        membro = MembroConta(conta_id=conta_id, usuario_id=usuario_id, papel=papel)  # type: ignore[arg-type]
        self.db.add(membro)
        self.db.flush()
        return membro

    def membro(self, conta_id: uuid.UUID, usuario_id: uuid.UUID) -> MembroConta | None:
        consulta = select(MembroConta).where(
            MembroConta.conta_id == conta_id, MembroConta.usuario_id == usuario_id
        )
        return self.db.scalars(consulta).first()

    def contas_do_usuario(self, usuario_id: uuid.UUID) -> Sequence[MembroConta]:
        consulta = (
            select(MembroConta)
            .where(MembroConta.usuario_id == usuario_id)
            .order_by(MembroConta.criado_em)
        )
        return self.db.scalars(consulta).all()
