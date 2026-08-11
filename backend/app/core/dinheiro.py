"""Dinheiro é sempre BIGINT de centavos. CLAUDE.md §4.

Nunca float, nunca Decimal solto, nunca string formatada no banco.
`formatar_brl` existe só para a borda de exibição — log, teste, mensagem
de agente. O banco e a API sempre trafegam o inteiro.
"""

from __future__ import annotations

__all__ = ["ValorInvalido", "dividir_parcelas", "formatar_brl", "parcelas_de_valor"]


class ValorInvalido(ValueError):
    """Valor monetário fora do contrato: não-inteiro, negativo ou divisão impossível."""


def _exigir_inteiro(valor: object, campo: str) -> int:
    # bool é subclasse de int e nunca é um valor monetário legítimo
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValorInvalido(f"{campo} deve ser int de centavos, recebido {type(valor).__name__}")
    return valor


def dividir_parcelas(total_centavos: int, n: int) -> list[int]:
    """Divide um total em `n` parcelas sem perder centavo.

    O resto vai para as primeiras parcelas, que é como as operadoras fazem:
    `dividir_parcelas(1000, 3)` devolve `[334, 333, 333]`.
    """
    total = _exigir_inteiro(total_centavos, "total_centavos")
    quantidade = _exigir_inteiro(n, "n")

    if quantidade < 1:
        raise ValorInvalido("número de parcelas deve ser >= 1")
    if total < 0:
        raise ValorInvalido("total_centavos não pode ser negativo")

    base, resto = divmod(total, quantidade)
    return [base + 1 if i < resto else base for i in range(quantidade)]


def parcelas_de_valor(valor_parcela_centavos: int, n: int) -> list[int]:
    """Repete um valor por parcela — o caso "12x de 400", em que o usuário
    informa o valor da parcela e não o total."""
    valor = _exigir_inteiro(valor_parcela_centavos, "valor_parcela_centavos")
    quantidade = _exigir_inteiro(n, "n")

    if quantidade < 1:
        raise ValorInvalido("número de parcelas deve ser >= 1")
    if valor <= 0:
        raise ValorInvalido("valor da parcela deve ser positivo")

    return [valor] * quantidade


def formatar_brl(centavos: int) -> str:
    """Formata para exibição. Só na borda — nunca persistido, nunca em resposta de API."""
    valor = _exigir_inteiro(centavos, "centavos")
    sinal = "-" if valor < 0 else ""
    inteiro, resto = divmod(abs(valor), 100)
    milhar = f"{inteiro:,}".replace(",", ".")
    return f"{sinal}R$ {milhar},{resto:02d}"
