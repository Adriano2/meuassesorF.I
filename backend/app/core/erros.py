"""Exceções de domínio. CLAUDE.md §9.

Router não monta HTTPException na mão. Serviço levanta uma destas, e um único
exception handler traduz para HTTP com `codigo` estável, `mensagem` em pt-BR e
`trace_id`. O agente usa o código; o usuário lê a mensagem.
"""

from __future__ import annotations


class ErroDominio(Exception):
    codigo = "erro_interno"
    http = 500
    mensagem = "Algo deu errado do nosso lado."

    def __init__(self, mensagem: str | None = None, *, detalhe: dict[str, object] | None = None):
        self.mensagem = mensagem or self.mensagem
        self.detalhe = detalhe or {}
        super().__init__(self.mensagem)


class NaoAutenticado(ErroDominio):
    codigo = "nao_autenticado"
    http = 401
    mensagem = "Faça login para continuar."


class SemPermissao(ErroDominio):
    codigo = "sem_permissao"
    http = 403
    mensagem = "Você não tem permissão para esta ação."


class NaoEncontrado(ErroDominio):
    codigo = "nao_encontrado"
    http = 404
    mensagem = "Não encontramos o que você pediu."


class Conflito(ErroDominio):
    codigo = "conflito"
    http = 409
    mensagem = "Isso já existe."


class DadoInvalido(ErroDominio):
    codigo = "dado_invalido"
    http = 422
    mensagem = "Confira os dados enviados."


class RegraDeNegocio(ErroDominio):
    """Requisição bem formada que viola uma regra do domínio financeiro."""

    codigo = "regra_de_negocio"
    http = 422
    mensagem = "Essa operação não é permitida."


class CategoriaTravada(RegraDeNegocio):
    codigo = "categoria_travada"
    mensagem = "Esta transação teve a categoria ajustada à mão e não é sobrescrita."


class FaturaJaPaga(RegraDeNegocio):
    codigo = "fatura_ja_paga"
    mensagem = "Esta fatura já está paga."
