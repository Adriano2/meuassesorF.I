"""Cadastro, login e resolução do usuário do request."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import config
from app.core.erros import Conflito, NaoAutenticado, SemPermissao
from app.core.seguranca import cifrar_senha, conferir_senha, emitir_token, ler_token
from app.models.base import PapelConta
from app.models.nucleo import Conta, MembroConta, Usuario
from app.repositories.nucleo import ContaRepository, UsuarioRepository
from app.services.financas import ServicoCategoria


@dataclass(frozen=True)
class Sessao:
    usuario: Usuario
    conta: Conta
    papel: PapelConta


@dataclass(frozen=True)
class Tokens:
    acesso: str
    refresh: str


class ServicoAutenticacao:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.contas = ContaRepository(db)

    def registrar(
        self, *, nome: str, email: str, senha: str, nome_conta: str | None = None
    ) -> tuple[Sessao, Tokens]:
        """Cria usuário, conta e as categorias padrão — o app precisa nascer útil."""
        if self.usuarios.por_email(email) is not None:
            raise Conflito("Já existe uma conta com este e-mail.")

        usuario = self.usuarios.inserir(
            Usuario(nome=nome, email=email, senha_hash=cifrar_senha(senha))
        )
        conta = self.contas.inserir(
            Conta(
                nome=nome_conta or f"Conta de {nome}",
                fuso=config().fuso_padrao,
                moeda=config().moeda_padrao,
            )
        )
        self.contas.vincular(conta.id, usuario.id, PapelConta.dono)
        ServicoCategoria(self.db).semear(conta.id)

        return Sessao(usuario, conta, PapelConta.dono), self._tokens(usuario.id, conta.id)

    def entrar(self, *, email: str, senha: str) -> tuple[Sessao, Tokens]:
        usuario = self.usuarios.por_email(email)
        # mensagem única para não revelar se o e-mail existe
        if usuario is None or not conferir_senha(senha, usuario.senha_hash):
            raise NaoAutenticado("E-mail ou senha incorretos.")

        vinculos = self.contas.contas_do_usuario(usuario.id)
        if not vinculos:
            raise SemPermissao("Este usuário não está em nenhuma conta.")

        vinculo = vinculos[0]
        conta = self.contas.por_id(vinculo.conta_id)
        assert conta is not None  # FK garante
        return Sessao(usuario, conta, vinculo.papel), self._tokens(usuario.id, conta.id)

    def renovar(self, refresh: str) -> Tokens:
        corpo = ler_token(refresh, tipo_esperado="refresh")
        return self._tokens(uuid.UUID(corpo["sub"]), uuid.UUID(corpo["conta_id"]))

    def sessao_do_token(self, token: str) -> Sessao:
        corpo = ler_token(token, tipo_esperado="acesso")
        usuario_id = uuid.UUID(corpo["sub"])
        conta_id = uuid.UUID(corpo["conta_id"])

        usuario = self.usuarios.por_id(usuario_id)
        if usuario is None:
            raise NaoAutenticado("Sessão inválida.")

        # o vínculo é reconferido a cada request: perder acesso vale na hora
        vinculo: MembroConta | None = self.contas.membro(conta_id, usuario_id)
        if vinculo is None:
            raise SemPermissao("Você não tem acesso a esta conta.")

        conta = self.contas.por_id(conta_id)
        assert conta is not None
        return Sessao(usuario, conta, vinculo.papel)

    def _tokens(self, usuario_id: uuid.UUID, conta_id: uuid.UUID) -> Tokens:
        return Tokens(
            acesso=emitir_token(usuario_id=usuario_id, conta_id=conta_id, tipo="acesso"),
            refresh=emitir_token(usuario_id=usuario_id, conta_id=conta_id, tipo="refresh"),
        )
