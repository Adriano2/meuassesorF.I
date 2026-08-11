"""Rotas do domínio financeiro. Só HTTP: nenhuma regra de negócio aqui."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import BD, Autenticado, AutorEscrita, Idempotencia
from app.models.base import StatusTransacao, TipoFluxo
from app.schemas.financas import (
    CartaoEntrada,
    CartaoSaida,
    CategoriaEntrada,
    CategoriaSaida,
    ContaBancariaEntrada,
    ContaBancariaSaida,
    FaturaSaida,
    PagamentoFatura,
    ResumoPeriodo,
    TransacaoEntrada,
    TransacaoSaida,
    TrocaCategoria,
)
from app.services.financas import (
    Resultado,
    ServicoCartao,
    ServicoCategoria,
    ServicoContaBancaria,
    ServicoFatura,
    ServicoTransacao,
)

router = APIRouter()


def _com_operacao(resposta: Response, resultado: Resultado) -> object:
    """Expõe o operacao_id no header também, para clientes que não leem o corpo."""
    resposta.headers["X-Operacao-Id"] = str(resultado.operacao_id)
    entidade = resultado.entidade
    entidade.operacao_id = resultado.operacao_id  # type: ignore[attr-defined]
    return entidade


# ── categorias ───────────────────────────────────────────────────────────

@router.get("/categorias", response_model=list[CategoriaSaida], tags=["categorias"])
def listar_categorias(
    sessao: Autenticado, db: BD, tipo: TipoFluxo | None = None
) -> object:
    return ServicoCategoria(db).listar(sessao.conta.id, tipo)


@router.post("/categorias", response_model=CategoriaSaida, tags=["categorias"],
             status_code=status.HTTP_201_CREATED)
def criar_categoria(
    dados: CategoriaEntrada,
    autor: AutorEscrita,
    db: BD,
    resposta: Response,
    idempotency_key: Idempotencia = None,
) -> object:
    resultado = ServicoCategoria(db).criar(
        autor,
        nome=dados.nome,
        tipo=dados.tipo,
        cor=dados.cor,
        icone=dados.icone,
        palavras_chave=dados.palavras_chave,
        orcamento_mensal_centavos=dados.orcamento_mensal_centavos,
        meta_receita_centavos=dados.meta_receita_centavos,
        idempotency_key=idempotency_key,
    )
    return _com_operacao(resposta, resultado)


@router.delete("/categorias/{categoria_id}", response_model=CategoriaSaida, tags=["categorias"])
def excluir_categoria(
    categoria_id: uuid.UUID, autor: AutorEscrita, db: BD, resposta: Response
) -> object:
    return _com_operacao(resposta, ServicoCategoria(db).excluir(autor, categoria_id))


# ── contas bancárias ─────────────────────────────────────────────────────

@router.get("/contas-bancarias", response_model=list[ContaBancariaSaida], tags=["contas"])
def listar_contas(sessao: Autenticado, db: BD) -> object:
    return ServicoContaBancaria(db).listar(sessao.conta.id)


@router.post("/contas-bancarias", response_model=ContaBancariaSaida, tags=["contas"],
             status_code=status.HTTP_201_CREATED)
def criar_conta(
    dados: ContaBancariaEntrada,
    autor: AutorEscrita,
    db: BD,
    resposta: Response,
    idempotency_key: Idempotencia = None,
) -> object:
    resultado = ServicoContaBancaria(db).criar(
        autor,
        nome=dados.nome,
        instituicao=dados.instituicao,
        tipo=dados.tipo,
        saldo_centavos=dados.saldo_centavos,
        incluir_no_total=dados.incluir_no_total,
        idempotency_key=idempotency_key,
    )
    return _com_operacao(resposta, resultado)


# ── cartões e faturas ────────────────────────────────────────────────────

@router.get("/cartoes", response_model=list[CartaoSaida], tags=["cartoes"])
def listar_cartoes(sessao: Autenticado, db: BD) -> object:
    return ServicoCartao(db).listar(sessao.conta.id)


@router.post("/cartoes", response_model=CartaoSaida, tags=["cartoes"],
             status_code=status.HTTP_201_CREATED)
def criar_cartao(
    dados: CartaoEntrada,
    autor: AutorEscrita,
    db: BD,
    resposta: Response,
    idempotency_key: Idempotencia = None,
) -> object:
    resultado = ServicoCartao(db).criar(
        autor,
        nome=dados.nome,
        dia_fechamento=dados.dia_fechamento,
        dia_vencimento=dados.dia_vencimento,
        bandeira=dados.bandeira,
        limite_centavos=dados.limite_centavos,
        conta_pagamento_id=dados.conta_pagamento_id,
        idempotency_key=idempotency_key,
    )
    return _com_operacao(resposta, resultado)


@router.get("/cartoes/{cartao_id}/faturas", response_model=list[FaturaSaida], tags=["cartoes"])
def listar_faturas(cartao_id: uuid.UUID, sessao: Autenticado, db: BD) -> object:
    ServicoCartao(db).obter(sessao.conta.id, cartao_id)
    return ServicoFatura(db).listar_do_cartao(sessao.conta.id, cartao_id)


@router.post("/faturas/{fatura_id}/pagar", response_model=FaturaSaida, tags=["cartoes"])
def pagar_fatura(
    fatura_id: uuid.UUID,
    dados: PagamentoFatura,
    autor: AutorEscrita,
    db: BD,
    resposta: Response,
    idempotency_key: Idempotencia = None,
) -> object:
    resultado = ServicoFatura(db).pagar(
        autor,
        fatura_id,
        valor_centavos=dados.valor_centavos,
        conta_bancaria_id=dados.conta_bancaria_id,
        data=dados.data,
        idempotency_key=idempotency_key,
    )
    return _com_operacao(resposta, resultado)


# ── transações ───────────────────────────────────────────────────────────

@router.get("/transacoes", response_model=list[TransacaoSaida], tags=["transacoes"])
def listar_transacoes(
    sessao: Autenticado,
    db: BD,
    de: date | None = None,
    ate: date | None = None,
    tipo: TipoFluxo | None = None,
    status_: Annotated[StatusTransacao | None, Query(alias="status")] = None,
    categoria_id: uuid.UUID | None = None,
    conta_bancaria_id: uuid.UUID | None = None,
    cartao_id: uuid.UUID | None = None,
    pessoa_id: uuid.UUID | None = None,
    q: str | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
) -> object:
    return ServicoTransacao(db).buscar(
        sessao.conta.id,
        de=de,
        ate=ate,
        tipo=tipo,
        status=status_,
        categoria_id=categoria_id,
        conta_bancaria_id=conta_bancaria_id,
        cartao_id=cartao_id,
        pessoa_id=pessoa_id,
        texto=q,
        limite=limite,
        deslocamento=deslocamento,
    )


@router.post("/transacoes", response_model=TransacaoSaida, tags=["transacoes"],
             status_code=status.HTTP_201_CREATED)
def criar_transacao(
    dados: TransacaoEntrada,
    autor: AutorEscrita,
    db: BD,
    resposta: Response,
    idempotency_key: Idempotencia = None,
) -> object:
    resultado = ServicoTransacao(db).registrar(
        autor,
        tipo=dados.tipo,
        descricao=dados.descricao,
        valor_centavos=dados.valor_centavos,
        data=dados.data,
        status=dados.status,
        categoria_id=dados.categoria_id,
        conta_bancaria_id=dados.conta_bancaria_id,
        cartao_id=dados.cartao_id,
        pessoa_id=dados.pessoa_id,
        parcelas=dados.parcelas,
        observacao=dados.observacao,
        idempotency_key=idempotency_key,
    )
    return _com_operacao(resposta, resultado)


@router.get("/transacoes/{transacao_id}", response_model=TransacaoSaida, tags=["transacoes"])
def obter_transacao(transacao_id: uuid.UUID, sessao: Autenticado, db: BD) -> object:
    return ServicoTransacao(db).obter(sessao.conta.id, transacao_id)


@router.patch("/transacoes/{transacao_id}/categoria", response_model=TransacaoSaida,
              tags=["transacoes"])
def trocar_categoria(
    transacao_id: uuid.UUID,
    dados: TrocaCategoria,
    autor: AutorEscrita,
    db: BD,
    resposta: Response,
) -> object:
    resultado = ServicoTransacao(db).alterar_categoria(autor, transacao_id, dados.categoria_id)
    return _com_operacao(resposta, resultado)


@router.delete("/transacoes/{transacao_id}", response_model=TransacaoSaida, tags=["transacoes"])
def excluir_transacao(
    transacao_id: uuid.UUID, autor: AutorEscrita, db: BD, resposta: Response
) -> object:
    return _com_operacao(resposta, ServicoTransacao(db).excluir(autor, transacao_id))


@router.get("/resumo", response_model=ResumoPeriodo, tags=["transacoes"])
def resumo(sessao: Autenticado, db: BD, de: date, ate: date) -> ResumoPeriodo:
    numeros = ServicoTransacao(db).resumo(sessao.conta.id, de=de, ate=ate)
    return ResumoPeriodo(de=de, ate=ate, **numeros)
