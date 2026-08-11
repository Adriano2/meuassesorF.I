"""Dinheiro é BIGINT de centavos e nenhum centavo se perde. CLAUDE.md §4."""

import pytest

from app.core.dinheiro import ValorInvalido, dividir_parcelas, formatar_brl, parcelas_de_valor


class TestDividirParcelas:
    def test_divisao_exata(self) -> None:
        assert dividir_parcelas(120000, 12) == [10000] * 12

    def test_resto_vai_para_as_primeiras(self) -> None:
        # o caso da CLAUDE.md §4: 1000 / 3 -> 334, 333, 333
        assert dividir_parcelas(1000, 3) == [334, 333, 333]

    def test_resto_de_dois_centavos(self) -> None:
        assert dividir_parcelas(100, 3) == [34, 33, 33]

    def test_soma_sempre_bate_com_o_total(self) -> None:
        for total in (1, 7, 99, 100, 1000, 123456, 999999):
            for n in range(1, 25):
                parcelas = dividir_parcelas(total, n)
                assert sum(parcelas) == total, (total, n)
                assert len(parcelas) == n
                assert all(p > 0 for p in parcelas) or total < n

    def test_parcela_unica(self) -> None:
        assert dividir_parcelas(4999, 1) == [4999]

    def test_recusa_numero_de_parcelas_invalido(self) -> None:
        with pytest.raises(ValorInvalido):
            dividir_parcelas(1000, 0)

    def test_recusa_valor_negativo(self) -> None:
        with pytest.raises(ValorInvalido):
            dividir_parcelas(-1, 3)

    def test_recusa_float(self) -> None:
        # nunca float em valor monetário
        with pytest.raises(ValorInvalido):
            dividir_parcelas(10.5, 3)  # type: ignore[arg-type]


class TestParcelasDeValor:
    def test_valor_por_parcela_multiplica(self) -> None:
        # "comprei em 12x de 400" -> 12 parcelas de 40000, total 480000
        parcelas = parcelas_de_valor(40000, 12)
        assert parcelas == [40000] * 12
        assert sum(parcelas) == 480000


class TestFormatarBrl:
    """Formatação existe só para a borda — log e teste. Nunca vai para o banco."""

    @pytest.mark.parametrize(
        ("centavos", "esperado"),
        [
            (0, "R$ 0,00"),
            (5, "R$ 0,05"),
            (100, "R$ 1,00"),
            (123456, "R$ 1.234,56"),
            (-99582, "-R$ 995,82"),
            (100000000, "R$ 1.000.000,00"),
        ],
    )
    def test_formatacao_brasileira(self, centavos: int, esperado: str) -> None:
        assert formatar_brl(centavos) == esperado
