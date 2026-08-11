"""Motor de ciclo de fatura. ESPEC §4.2.

Determinístico e sem dependência de banco: recebe datas e dias de ancoragem,
devolve competência, fechamento, vencimento e a distribuição das parcelas.

Lembrete que vale repetir (CLAUDE.md §4): gasto no cartão não é saída de caixa
no dia da compra. Este motor decide em qual fatura a compra entra; quem decide
quando o dinheiro sai é o pagamento da fatura.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.datas import ancorar_dia, inicio_do_mes, proximo_mes
from app.core.dinheiro import dividir_parcelas

__all__ = ["CicloCartao", "ParcelaEmFatura", "competencia_da_compra", "datas_da_fatura",
           "parcelas_em_faturas"]


@dataclass(frozen=True)
class CicloCartao:
    """Os dois dias que definem o ciclo do cartão."""

    dia_fechamento: int
    dia_vencimento: int

    def __post_init__(self) -> None:
        for campo, valor in (
            ("dia_fechamento", self.dia_fechamento),
            ("dia_vencimento", self.dia_vencimento),
        ):
            if not 1 <= valor <= 31:
                raise ValueError(f"{campo} deve estar entre 1 e 31, recebido {valor}")


@dataclass(frozen=True)
class ParcelaEmFatura:
    numero: int
    competencia: date
    valor_centavos: int


def competencia_da_compra(data_compra: date, ciclo: CicloCartao) -> date:
    """Competência da fatura em que a compra entra.

    A compra entra na fatura cuja data de fechamento é a primeira posterior ou
    igual à data da compra — comprar no próprio dia do fechamento ainda cai
    nessa fatura.
    """
    fechamento_do_mes = ancorar_dia(data_compra.year, data_compra.month, ciclo.dia_fechamento)
    if data_compra <= fechamento_do_mes:
        return inicio_do_mes(data_compra)
    return proximo_mes(data_compra)


def datas_da_fatura(competencia: date, ciclo: CicloCartao) -> tuple[date, date]:
    """Fechamento e vencimento concretos de uma competência.

    Regra de vencimento: quando o dia de vencimento é posterior ao de
    fechamento, vence no mesmo mês; caso contrário, rola para o mês seguinte.
    Vencimento no mesmo dia do fechamento também rola — uma fatura não vence
    antes de existir.
    """
    fechamento = ancorar_dia(competencia.year, competencia.month, ciclo.dia_fechamento)

    if ciclo.dia_vencimento > ciclo.dia_fechamento:
        vencimento = ancorar_dia(competencia.year, competencia.month, ciclo.dia_vencimento)
    else:
        seguinte = proximo_mes(competencia)
        vencimento = ancorar_dia(seguinte.year, seguinte.month, ciclo.dia_vencimento)

    # a ancoragem pode empatar as duas datas (fechamento 31 e vencimento 31 em
    # fevereiro, por exemplo); nesse caso o vencimento vai para o mês seguinte
    if vencimento <= fechamento:
        seguinte = proximo_mes(competencia)
        vencimento = ancorar_dia(seguinte.year, seguinte.month, ciclo.dia_vencimento)

    return fechamento, vencimento


def parcelas_em_faturas(
    *,
    data_compra: date,
    ciclo: CicloCartao,
    valor_total_centavos: int,
    total_parcelas: int,
) -> list[ParcelaEmFatura]:
    """Distribui uma compra parcelada em faturas consecutivas.

    Uma parcela por fatura, a partir da fatura em que a compra entra. O resto
    da divisão vai para as primeiras parcelas (CLAUDE.md §4).
    """
    if total_parcelas < 1:
        raise ValueError("total_parcelas deve ser >= 1")

    valores = dividir_parcelas(valor_total_centavos, total_parcelas)
    competencia = competencia_da_compra(data_compra, ciclo)

    parcelas: list[ParcelaEmFatura] = []
    for numero, valor in enumerate(valores, start=1):
        parcelas.append(ParcelaEmFatura(numero=numero, competencia=competencia,
                                        valor_centavos=valor))
        competencia = proximo_mes(competencia)
    return parcelas
