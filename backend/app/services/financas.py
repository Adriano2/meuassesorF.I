"""Regra de negócio do domínio financeiro.

Service não importa FastAPI e não fala SQL: orquestra repositories, motores e
o registro de operação. CLAUDE.md §3.

Duas decisões que valem explicar, porque não estavam escritas na espec:

1. **Saldo da conta bancária.** Uma transação `realizado` vinculada a conta
   bancária move `saldo_centavos` (+entrada, −saída). Compra no cartão não move
   — quem move é o pagamento da fatura. Na Fase 4 o saldo informado pelo Open
   Finance passa a ser a fonte da verdade e este ajuste vira conciliação.
2. **Competência da parcela.** Numa compra parcelada no cartão, cada parcela
   tem `data_competencia` no primeiro dia do mês da sua fatura. A compra à
   vista mantém a data da compra.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.datas import hoje, inicio_do_mes
from app.core.dinheiro import dividir_parcelas
from app.core.erros import DadoInvalido, FaturaJaPaga, NaoEncontrado, RegraDeNegocio
from app.models.base import OrigemRegistro, StatusFatura, StatusTransacao, TipoFluxo
from app.models.financas import Cartao, Categoria, ContaBancaria, Fatura, Transacao
from app.motores.fatura import CicloCartao, competencia_da_compra, datas_da_fatura
from app.repositories.financas import (
    CartaoRepository,
    CategoriaRepository,
    ContaBancariaRepository,
    FaturaRepository,
    PessoaRepository,
    TransacaoRepository,
)
from app.services.auditoria import instantanear, operacao_por_chave, registrar_operacao


@dataclass(frozen=True)
class Autor:
    """Quem está escrevendo. O agente preenche isto igual à interface web."""

    conta_id: uuid.UUID
    usuario_id: uuid.UUID | None
    fuso: str = "America/Sao_Paulo"
    ator: str = "usuario"


@dataclass(frozen=True)
class Resultado:
    """Toda escrita devolve a entidade e o id da operação que a registrou."""

    entidade: object
    operacao_id: uuid.UUID
    repetida: bool = False


CATEGORIAS_SEMENTE: tuple[tuple[str, TipoFluxo, tuple[str, ...]], ...] = (
    ("Alimentação", TipoFluxo.saida,
     ("mercado", "supermercado", "ifood", "restaurante", "padaria")),
    ("Transporte", TipoFluxo.saida, ("uber", "99", "gasolina", "combustível", "estacionamento")),
    ("Moradia", TipoFluxo.saida, ("aluguel", "condomínio", "luz", "água", "internet", "iptu")),
    ("Saúde", TipoFluxo.saida, ("farmácia", "médico", "dentista", "consulta", "exame")),
    ("Assinaturas", TipoFluxo.saida, ("spotify", "netflix", "assinatura", "mensalidade")),
    ("Lazer", TipoFluxo.saida, ("cinema", "bar", "viagem", "show")),
    ("Educação", TipoFluxo.saida, ("curso", "faculdade", "livro")),
    ("Outros", TipoFluxo.saida, ()),
    ("Salário", TipoFluxo.entrada, ("salário", "pagamento", "holerite")),
    ("Reembolso", TipoFluxo.entrada, ("reembolso", "estorno")),
    ("Outros", TipoFluxo.entrada, ()),
)


class ServicoCategoria:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CategoriaRepository(db)

    def semear(self, conta_id: uuid.UUID) -> list[Categoria]:
        """Categorias padrão de uma conta nova. O app precisa ser útil no minuto zero."""
        criadas = []
        for nome, tipo, palavras in CATEGORIAS_SEMENTE:
            categoria = Categoria(
                conta_id=conta_id,
                nome=nome,
                tipo=tipo,
                palavras_chave=list(palavras),
                sistema=True,
            )
            criadas.append(self.repo.inserir(categoria))
        return criadas

    def listar(self, conta_id: uuid.UUID, tipo: TipoFluxo | None = None) -> Sequence[Categoria]:
        return self.repo.listar_por_tipo(conta_id, tipo)

    def obter(self, conta_id: uuid.UUID, categoria_id: uuid.UUID) -> Categoria:
        categoria = self.repo.por_id(conta_id, categoria_id)
        if categoria is None:
            raise NaoEncontrado("Categoria não encontrada.")
        return categoria

    def criar(
        self,
        autor: Autor,
        *,
        nome: str,
        tipo: TipoFluxo,
        cor: str | None = None,
        icone: str | None = None,
        palavras_chave: Sequence[str] = (),
        orcamento_mensal_centavos: int | None = None,
        meta_receita_centavos: int | None = None,
        idempotency_key: str | None = None,
    ) -> Resultado:
        anterior = operacao_por_chave(self.db, autor.conta_id, idempotency_key)
        if anterior is not None:
            return Resultado(
                self.obter(autor.conta_id, anterior.entidade_id),  # type: ignore[arg-type]
                anterior.id,
                repetida=True,
            )

        if self.repo.por_nome(autor.conta_id, nome, tipo) is not None:
            raise RegraDeNegocio(f"Já existe uma categoria de {tipo.value} chamada {nome}.")

        if orcamento_mensal_centavos is not None and tipo is TipoFluxo.entrada:
            raise DadoInvalido("Orçamento só faz sentido em categoria de saída.")
        if meta_receita_centavos is not None and tipo is TipoFluxo.saida:
            raise DadoInvalido("Meta de receita só faz sentido em categoria de entrada.")

        categoria = self.repo.inserir(
            Categoria(
                conta_id=autor.conta_id,
                nome=nome,
                tipo=tipo,
                cor=cor,
                icone=icone,
                palavras_chave=list(palavras_chave),
                orcamento_mensal_centavos=orcamento_mensal_centavos,
                meta_receita_centavos=meta_receita_centavos,
            )
        )
        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="categoria.criar",
            entidade="categorias",
            entidade_id=categoria.id,
            antes=None,
            depois=instantanear(categoria),
            idempotency_key=idempotency_key,
        )
        return Resultado(categoria, operacao.id)

    def excluir(self, autor: Autor, categoria_id: uuid.UUID) -> Resultado:
        categoria = self.obter(autor.conta_id, categoria_id)
        if categoria.sistema:
            raise RegraDeNegocio("Categoria padrão não pode ser excluída.")

        antes = instantanear(categoria)
        self.repo.marcar_excluido(categoria)
        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="categoria.excluir",
            entidade="categorias",
            entidade_id=categoria.id,
            antes=antes,
            depois=instantanear(categoria),
        )
        return Resultado(categoria, operacao.id)


class ServicoContaBancaria:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ContaBancariaRepository(db)

    def listar(self, conta_id: uuid.UUID) -> Sequence[ContaBancaria]:
        return self.repo.listar(conta_id, ordem=ContaBancaria.nome)

    def obter(self, conta_id: uuid.UUID, id_: uuid.UUID) -> ContaBancaria:
        conta = self.repo.por_id(conta_id, id_)
        if conta is None:
            raise NaoEncontrado("Conta bancária não encontrada.")
        return conta

    def criar(
        self,
        autor: Autor,
        *,
        nome: str,
        instituicao: str | None = None,
        tipo: str | None = None,
        saldo_centavos: int = 0,
        incluir_no_total: bool = True,
        idempotency_key: str | None = None,
    ) -> Resultado:
        anterior = operacao_por_chave(self.db, autor.conta_id, idempotency_key)
        if anterior is not None:
            return Resultado(
                self.obter(autor.conta_id, anterior.entidade_id),  # type: ignore[arg-type]
                anterior.id,
                repetida=True,
            )

        conta = self.repo.inserir(
            ContaBancaria(
                conta_id=autor.conta_id,
                nome=nome,
                instituicao=instituicao,
                tipo=tipo,
                saldo_centavos=saldo_centavos,
                incluir_no_total=incluir_no_total,
            )
        )
        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="conta_bancaria.criar",
            entidade="contas_bancarias",
            entidade_id=conta.id,
            depois=instantanear(conta),
            idempotency_key=idempotency_key,
        )
        return Resultado(conta, operacao.id)


class ServicoCartao:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CartaoRepository(db)
        self.faturas = FaturaRepository(db)

    def listar(self, conta_id: uuid.UUID) -> Sequence[Cartao]:
        return self.repo.listar(conta_id, ordem=Cartao.nome)

    def obter(self, conta_id: uuid.UUID, id_: uuid.UUID) -> Cartao:
        cartao = self.repo.por_id(conta_id, id_)
        if cartao is None:
            raise NaoEncontrado("Cartão não encontrado.")
        return cartao

    def criar(
        self,
        autor: Autor,
        *,
        nome: str,
        dia_fechamento: int,
        dia_vencimento: int,
        bandeira: str | None = None,
        limite_centavos: int | None = None,
        conta_pagamento_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> Resultado:
        anterior = operacao_por_chave(self.db, autor.conta_id, idempotency_key)
        if anterior is not None:
            return Resultado(
                self.obter(autor.conta_id, anterior.entidade_id),  # type: ignore[arg-type]
                anterior.id,
                repetida=True,
            )

        # valida o ciclo pelo motor, não por regra solta aqui
        CicloCartao(dia_fechamento=dia_fechamento, dia_vencimento=dia_vencimento)

        if conta_pagamento_id is not None:
            ServicoContaBancaria(self.db).obter(autor.conta_id, conta_pagamento_id)

        cartao = self.repo.inserir(
            Cartao(
                conta_id=autor.conta_id,
                nome=nome,
                bandeira=bandeira,
                limite_centavos=limite_centavos,
                dia_fechamento=dia_fechamento,
                dia_vencimento=dia_vencimento,
                conta_pagamento_id=conta_pagamento_id,
            )
        )
        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="cartao.criar",
            entidade="cartoes",
            entidade_id=cartao.id,
            depois=instantanear(cartao),
            idempotency_key=idempotency_key,
        )
        return Resultado(cartao, operacao.id)


class ServicoFatura:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FaturaRepository(db)
        self.cartoes = CartaoRepository(db)
        self.contas = ContaBancariaRepository(db)

    def obter(self, conta_id: uuid.UUID, id_: uuid.UUID) -> Fatura:
        fatura = self.repo.por_id(conta_id, id_)
        if fatura is None:
            raise NaoEncontrado("Fatura não encontrada.")
        return fatura

    def listar_do_cartao(self, conta_id: uuid.UUID, cartao_id: uuid.UUID) -> Sequence[Fatura]:
        return self.repo.listar_do_cartao(conta_id, cartao_id)

    def garantir(self, conta_id: uuid.UUID, cartao: Cartao, competencia: date) -> Fatura:
        """Devolve a fatura da competência, criando se ainda não existir."""
        existente = self.repo.por_competencia(conta_id, cartao.id, competencia)
        if existente is not None:
            return existente

        ciclo = CicloCartao(
            dia_fechamento=cartao.dia_fechamento, dia_vencimento=cartao.dia_vencimento
        )
        fechamento, vencimento = datas_da_fatura(competencia, ciclo)
        return self.repo.inserir(
            Fatura(
                conta_id=conta_id,
                cartao_id=cartao.id,
                competencia=competencia,
                data_fechamento=fechamento,
                data_vencimento=vencimento,
            )
        )

    def recalcular_total(self, conta_id: uuid.UUID, fatura: Fatura) -> Fatura:
        """Total sempre derivado por soma. ESPEC §4.2."""
        fatura.total_centavos = self.repo.somar_transacoes(conta_id, fatura.id)
        if fatura.status is not StatusFatura.paga:
            fatura.status = (
                StatusFatura.parcial if 0 < fatura.pago_centavos < fatura.total_centavos
                else fatura.status
            )
        self.db.flush()
        return fatura

    def pagar(
        self,
        autor: Autor,
        fatura_id: uuid.UUID,
        *,
        valor_centavos: int | None = None,
        conta_bancaria_id: uuid.UUID | None = None,
        data: date | None = None,
        idempotency_key: str | None = None,
    ) -> Resultado:
        """Pagar a fatura é o momento em que o dinheiro sai do caixa."""
        anterior = operacao_por_chave(self.db, autor.conta_id, idempotency_key)
        if anterior is not None:
            return Resultado(self.obter(autor.conta_id, fatura_id), anterior.id, repetida=True)

        fatura = self.obter(autor.conta_id, fatura_id)
        if fatura.status is StatusFatura.paga:
            raise FaturaJaPaga()

        self.recalcular_total(autor.conta_id, fatura)
        if fatura.total_centavos <= 0:
            raise RegraDeNegocio("Fatura sem lançamentos não pode ser paga.")

        restante = fatura.total_centavos - fatura.pago_centavos
        valor = valor_centavos if valor_centavos is not None else restante
        if valor <= 0:
            raise DadoInvalido("Valor de pagamento deve ser positivo.")
        if valor > restante:
            raise RegraDeNegocio(
                f"Pagamento maior que o saldo da fatura ({restante} centavos)."
            )

        cartao = self.cartoes.por_id(autor.conta_id, fatura.cartao_id)
        if cartao is None:
            raise NaoEncontrado("Cartão da fatura não encontrado.")

        origem_id = conta_bancaria_id or cartao.conta_pagamento_id
        if origem_id is None:
            raise DadoInvalido("Informe a conta bancária que paga a fatura.")
        origem = self.contas.por_id(autor.conta_id, origem_id)
        if origem is None:
            raise NaoEncontrado("Conta bancária não encontrada.")

        antes = instantanear(fatura)
        quando = data or hoje(autor.fuso)

        pagamento = Transacao(
            conta_id=autor.conta_id,
            criado_por=autor.usuario_id,
            tipo=TipoFluxo.saida,
            descricao=f"Pagamento fatura {cartao.nome}",
            valor_centavos=valor,
            data_competencia=quando,
            data_efetiva=quando,
            status=StatusTransacao.realizado,
            conta_bancaria_id=origem.id,
            origem=OrigemRegistro.manual if autor.ator == "usuario" else OrigemRegistro.agente,
        )
        self.db.add(pagamento)
        origem.saldo_centavos -= valor

        fatura.pago_centavos += valor
        fatura.status = (
            StatusFatura.paga
            if fatura.pago_centavos >= fatura.total_centavos
            else StatusFatura.parcial
        )
        self.db.flush()

        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="fatura.pagar",
            entidade="faturas",
            entidade_id=fatura.id,
            antes=antes,
            depois=instantanear(fatura),
            idempotency_key=idempotency_key,
        )
        return Resultado(fatura, operacao.id)


class ServicoTransacao:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TransacaoRepository(db)
        self.categorias = CategoriaRepository(db)
        self.contas = ContaBancariaRepository(db)
        self.cartoes = CartaoRepository(db)
        self.pessoas = PessoaRepository(db)
        self.faturas = ServicoFatura(db)

    # ── leitura ──────────────────────────────────────────────────────────

    def obter(self, conta_id: uuid.UUID, id_: uuid.UUID) -> Transacao:
        transacao = self.repo.por_id(conta_id, id_)
        if transacao is None:
            raise NaoEncontrado("Transação não encontrada.")
        return transacao

    def buscar(self, conta_id: uuid.UUID, **filtros: object) -> Sequence[Transacao]:
        return self.repo.buscar(conta_id, **filtros)  # type: ignore[arg-type]

    # ── escrita ──────────────────────────────────────────────────────────

    def registrar(
        self,
        autor: Autor,
        *,
        tipo: TipoFluxo,
        descricao: str,
        valor_centavos: int,
        data: date | None = None,
        status: StatusTransacao = StatusTransacao.realizado,
        categoria_id: uuid.UUID | None = None,
        conta_bancaria_id: uuid.UUID | None = None,
        cartao_id: uuid.UUID | None = None,
        pessoa_id: uuid.UUID | None = None,
        parcelas: int | None = None,
        observacao: str | None = None,
        idempotency_key: str | None = None,
    ) -> Resultado:
        anterior = operacao_por_chave(self.db, autor.conta_id, idempotency_key)
        if anterior is not None:
            return Resultado(
                self.obter(autor.conta_id, anterior.entidade_id),  # type: ignore[arg-type]
                anterior.id,
                repetida=True,
            )

        if valor_centavos <= 0:
            raise DadoInvalido("Valor deve ser maior que zero.")
        if conta_bancaria_id is not None and cartao_id is not None:
            raise DadoInvalido("Uma transação é da conta ou do cartão, não das duas.")
        if parcelas is not None and parcelas > 1 and cartao_id is None:
            raise RegraDeNegocio("Parcelamento exige um cartão.")

        quando = data or hoje(autor.fuso)
        self._validar_vinculos(autor.conta_id, categoria_id, conta_bancaria_id, cartao_id,
                               pessoa_id)

        origem = OrigemRegistro.manual if autor.ator == "usuario" else OrigemRegistro.agente

        if cartao_id is not None:
            criadas = self._registrar_no_cartao(
                autor,
                cartao_id=cartao_id,
                tipo=tipo,
                descricao=descricao,
                valor_centavos=valor_centavos,
                data_compra=quando,
                categoria_id=categoria_id,
                pessoa_id=pessoa_id,
                parcelas=parcelas or 1,
                observacao=observacao,
                origem=origem,
            )
        else:
            criadas = [
                self._registrar_na_conta(
                    autor,
                    tipo=tipo,
                    descricao=descricao,
                    valor_centavos=valor_centavos,
                    data=quando,
                    status=status,
                    categoria_id=categoria_id,
                    conta_bancaria_id=conta_bancaria_id,
                    pessoa_id=pessoa_id,
                    observacao=observacao,
                    origem=origem,
                )
            ]

        principal = criadas[0]
        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="transacao.criar",
            entidade="transacoes",
            entidade_id=principal.id,
            antes=None,
            depois={"lancamentos": [instantanear(t) for t in criadas]},
            idempotency_key=idempotency_key,
        )
        return Resultado(principal, operacao.id)

    def _validar_vinculos(
        self,
        conta_id: uuid.UUID,
        categoria_id: uuid.UUID | None,
        conta_bancaria_id: uuid.UUID | None,
        cartao_id: uuid.UUID | None,
        pessoa_id: uuid.UUID | None,
    ) -> None:
        """Todo id vem da própria conta. É aqui que um id de outro tenant morre."""
        if categoria_id and self.categorias.por_id(conta_id, categoria_id) is None:
            raise NaoEncontrado("Categoria não encontrada.")
        if conta_bancaria_id and self.contas.por_id(conta_id, conta_bancaria_id) is None:
            raise NaoEncontrado("Conta bancária não encontrada.")
        if cartao_id and self.cartoes.por_id(conta_id, cartao_id) is None:
            raise NaoEncontrado("Cartão não encontrado.")
        if pessoa_id and self.pessoas.por_id(conta_id, pessoa_id) is None:
            raise NaoEncontrado("Pessoa não encontrada.")

    def _registrar_na_conta(
        self,
        autor: Autor,
        *,
        tipo: TipoFluxo,
        descricao: str,
        valor_centavos: int,
        data: date,
        status: StatusTransacao,
        categoria_id: uuid.UUID | None,
        conta_bancaria_id: uuid.UUID | None,
        pessoa_id: uuid.UUID | None,
        observacao: str | None,
        origem: OrigemRegistro,
    ) -> Transacao:
        realizado = status is StatusTransacao.realizado
        transacao = self.repo.inserir(
            Transacao(
                conta_id=autor.conta_id,
                criado_por=autor.usuario_id,
                tipo=tipo,
                descricao=descricao,
                valor_centavos=valor_centavos,
                data_competencia=data,
                data_efetiva=data if realizado else None,
                status=status,
                categoria_id=categoria_id,
                conta_bancaria_id=conta_bancaria_id,
                pessoa_id=pessoa_id,
                observacao=observacao,
                origem=origem,
            )
        )
        if realizado and conta_bancaria_id is not None:
            self._mover_saldo(autor.conta_id, conta_bancaria_id, tipo, valor_centavos)
        return transacao

    def _registrar_no_cartao(
        self,
        autor: Autor,
        *,
        cartao_id: uuid.UUID,
        tipo: TipoFluxo,
        descricao: str,
        valor_centavos: int,
        data_compra: date,
        categoria_id: uuid.UUID | None,
        pessoa_id: uuid.UUID | None,
        parcelas: int,
        observacao: str | None,
        origem: OrigemRegistro,
    ) -> list[Transacao]:
        cartao = self.cartoes.por_id(autor.conta_id, cartao_id)
        if cartao is None:
            raise NaoEncontrado("Cartão não encontrado.")

        ciclo = CicloCartao(
            dia_fechamento=cartao.dia_fechamento, dia_vencimento=cartao.dia_vencimento
        )
        competencia = competencia_da_compra(data_compra, ciclo)
        valores = dividir_parcelas(valor_centavos, parcelas)

        criadas: list[Transacao] = []
        for numero, valor in enumerate(valores, start=1):
            fatura = self.faturas.garantir(autor.conta_id, cartao, competencia)
            # à vista mantém a data da compra; parcelada conta no mês da fatura
            competencia_lancamento = data_compra if parcelas == 1 else competencia
            sufixo = f" ({numero}/{parcelas})" if parcelas > 1 else ""
            transacao = self.repo.inserir(
                Transacao(
                    conta_id=autor.conta_id,
                    criado_por=autor.usuario_id,
                    tipo=tipo,
                    descricao=f"{descricao}{sufixo}",
                    valor_centavos=valor,
                    data_competencia=competencia_lancamento,
                    # compra no cartão não é saída de caixa: data_efetiva fica
                    # vazia até o pagamento da fatura (CLAUDE.md §4)
                    data_efetiva=None,
                    status=StatusTransacao.realizado,
                    categoria_id=categoria_id,
                    cartao_id=cartao.id,
                    fatura_id=fatura.id,
                    pessoa_id=pessoa_id,
                    parcela_num=numero if parcelas > 1 else None,
                    observacao=observacao,
                    origem=origem,
                )
            )
            criadas.append(transacao)
            self.faturas.recalcular_total(autor.conta_id, fatura)
            competencia = _mes_seguinte(competencia)

        return criadas

    def _mover_saldo(
        self, conta_id: uuid.UUID, conta_bancaria_id: uuid.UUID, tipo: TipoFluxo, valor: int
    ) -> None:
        conta = self.contas.por_id(conta_id, conta_bancaria_id)
        if conta is None:
            raise NaoEncontrado("Conta bancária não encontrada.")
        conta.saldo_centavos += valor if tipo is TipoFluxo.entrada else -valor
        self.db.flush()

    def excluir(self, autor: Autor, transacao_id: uuid.UUID) -> Resultado:
        transacao = self.obter(autor.conta_id, transacao_id)
        antes = instantanear(transacao)

        # desfaz o efeito no saldo antes de apagar
        if (
            transacao.status is StatusTransacao.realizado
            and transacao.conta_bancaria_id is not None
        ):
            inverso = (
                TipoFluxo.saida if transacao.tipo is TipoFluxo.entrada else TipoFluxo.entrada
            )
            self._mover_saldo(
                autor.conta_id, transacao.conta_bancaria_id, inverso, transacao.valor_centavos
            )

        self.repo.marcar_excluido(transacao)

        if transacao.fatura_id is not None:
            fatura = self.faturas.obter(autor.conta_id, transacao.fatura_id)
            self.faturas.recalcular_total(autor.conta_id, fatura)

        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="transacao.excluir",
            entidade="transacoes",
            entidade_id=transacao.id,
            antes=antes,
            depois=instantanear(transacao),
        )
        return Resultado(transacao, operacao.id)

    def alterar_categoria(
        self, autor: Autor, transacao_id: uuid.UUID, categoria_id: uuid.UUID
    ) -> Resultado:
        """Correção manual sempre trava a categoria. CLAUDE.md §4."""
        transacao = self.obter(autor.conta_id, transacao_id)
        self._validar_vinculos(autor.conta_id, categoria_id, None, None, None)

        antes = instantanear(transacao)
        transacao.categoria_id = categoria_id
        transacao.categoria_travada = True
        self.db.flush()

        operacao = registrar_operacao(
            self.db,
            conta_id=autor.conta_id,
            usuario_id=autor.usuario_id,
            ator=autor.ator,
            acao="transacao.categorizar",
            entidade="transacoes",
            entidade_id=transacao.id,
            antes=antes,
            depois=instantanear(transacao),
        )
        return Resultado(transacao, operacao.id)

    def resumo(self, conta_id: uuid.UUID, *, de: date, ate: date) -> dict[str, int]:
        entradas = self.repo.somar(conta_id, de=de, ate=ate, tipo=TipoFluxo.entrada)
        saidas = self.repo.somar(conta_id, de=de, ate=ate, tipo=TipoFluxo.saida)
        return {
            "entradas_centavos": entradas,
            "saidas_centavos": saidas,
            "saldo_centavos": entradas - saidas,
        }


def _mes_seguinte(competencia: date) -> date:
    base = inicio_do_mes(competencia)
    return date(base.year + 1, 1, 1) if base.month == 12 else date(base.year, base.month + 1, 1)
