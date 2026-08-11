"""Ciclo de fatura do cartão. ESPEC §4.2 — critério de aceite da Fase 1.

A compra entra na fatura cuja data_fechamento é a primeira posterior ou igual
à data da compra. Parcelada distribui uma parcela por fatura consecutiva.
"""

from datetime import date

import pytest

from app.motores.fatura import (
    CicloCartao,
    competencia_da_compra,
    datas_da_fatura,
    parcelas_em_faturas,
)

# fecha dia 20, vence dia 28 — vencimento no mesmo mês do fechamento
FECHA_20_VENCE_28 = CicloCartao(dia_fechamento=20, dia_vencimento=28)
# fecha dia 28, vence dia 5 — vencimento no mês seguinte ao fechamento
FECHA_28_VENCE_05 = CicloCartao(dia_fechamento=28, dia_vencimento=5)
# ancoragem no fim do mês
FECHA_31_VENCE_10 = CicloCartao(dia_fechamento=31, dia_vencimento=10)


class TestCompetenciaDaCompra:
    def test_compra_antes_do_fechamento_cai_na_fatura_do_mes(self) -> None:
        assert competencia_da_compra(date(2026, 8, 15), FECHA_20_VENCE_28) == date(2026, 8, 1)

    def test_compra_no_dia_do_fechamento_ainda_entra_nessa_fatura(self) -> None:
        # "primeira posterior OU IGUAL" — a borda pertence à fatura que fecha
        assert competencia_da_compra(date(2026, 8, 20), FECHA_20_VENCE_28) == date(2026, 8, 1)

    def test_compra_depois_do_fechamento_vai_para_a_proxima(self) -> None:
        assert competencia_da_compra(date(2026, 8, 21), FECHA_20_VENCE_28) == date(2026, 9, 1)

    def test_virada_de_ano(self) -> None:
        assert competencia_da_compra(date(2026, 12, 25), FECHA_20_VENCE_28) == date(2027, 1, 1)

    def test_primeiro_dia_do_mes(self) -> None:
        assert competencia_da_compra(date(2026, 8, 1), FECHA_20_VENCE_28) == date(2026, 8, 1)

    def test_fechamento_dia_31_em_fevereiro(self) -> None:
        # fevereiro fecha no dia 28; compra em 27/02 ainda é da fatura de fevereiro
        assert competencia_da_compra(date(2026, 2, 27), FECHA_31_VENCE_10) == date(2026, 2, 1)

    def test_compra_no_ultimo_dia_de_fevereiro_com_fechamento_31(self) -> None:
        assert competencia_da_compra(date(2026, 2, 28), FECHA_31_VENCE_10) == date(2026, 2, 1)

    def test_compra_em_29_de_fevereiro_bissexto_com_fechamento_31(self) -> None:
        assert competencia_da_compra(date(2028, 2, 29), FECHA_31_VENCE_10) == date(2028, 2, 1)


class TestDatasDaFatura:
    def test_vencimento_no_mesmo_mes_quando_posterior_ao_fechamento(self) -> None:
        fechamento, vencimento = datas_da_fatura(date(2026, 8, 1), FECHA_20_VENCE_28)
        assert fechamento == date(2026, 8, 20)
        assert vencimento == date(2026, 8, 28)

    def test_vencimento_rola_para_o_mes_seguinte_quando_anterior(self) -> None:
        fechamento, vencimento = datas_da_fatura(date(2026, 8, 1), FECHA_28_VENCE_05)
        assert fechamento == date(2026, 8, 28)
        assert vencimento == date(2026, 9, 5)

    def test_vencimento_rola_o_ano(self) -> None:
        _, vencimento = datas_da_fatura(date(2026, 12, 1), FECHA_28_VENCE_05)
        assert vencimento == date(2027, 1, 5)

    def test_fechamento_31_ancora_no_ultimo_dia(self) -> None:
        fechamento, vencimento = datas_da_fatura(date(2026, 2, 1), FECHA_31_VENCE_10)
        assert fechamento == date(2026, 2, 28)
        assert vencimento == date(2026, 3, 10)

    def test_vencimento_sempre_posterior_ao_fechamento(self) -> None:
        for f in range(1, 32):
            for v in range(1, 32):
                ciclo = CicloCartao(dia_fechamento=f, dia_vencimento=v)
                fechamento, vencimento = datas_da_fatura(date(2026, 6, 1), ciclo)
                assert vencimento > fechamento, (f, v)


class TestParcelasEmFaturas:
    def test_doze_parcelas_caem_em_doze_faturas_consecutivas(self) -> None:
        # ESPEC §9 #11: "comprei uma tv em 12x de 400"
        parcelas = parcelas_em_faturas(
            data_compra=date(2026, 8, 15),
            ciclo=FECHA_20_VENCE_28,
            valor_total_centavos=480000,
            total_parcelas=12,
        )
        assert len(parcelas) == 12
        assert [p.competencia for p in parcelas[:3]] == [
            date(2026, 8, 1),
            date(2026, 9, 1),
            date(2026, 10, 1),
        ]
        assert parcelas[-1].competencia == date(2027, 7, 1)
        assert [p.numero for p in parcelas] == list(range(1, 13))
        assert all(p.valor_centavos == 40000 for p in parcelas)

    def test_nenhum_centavo_se_perde_no_parcelamento(self) -> None:
        parcelas = parcelas_em_faturas(
            data_compra=date(2026, 8, 15),
            ciclo=FECHA_20_VENCE_28,
            valor_total_centavos=1000,
            total_parcelas=3,
        )
        assert [p.valor_centavos for p in parcelas] == [334, 333, 333]
        assert sum(p.valor_centavos for p in parcelas) == 1000

    def test_parcelamento_atravessa_a_virada_de_ano(self) -> None:
        parcelas = parcelas_em_faturas(
            data_compra=date(2026, 11, 25),
            ciclo=FECHA_20_VENCE_28,
            valor_total_centavos=30000,
            total_parcelas=3,
        )
        # compra em 25/11 é depois do fechamento de novembro -> começa em dezembro
        assert [p.competencia for p in parcelas] == [
            date(2026, 12, 1),
            date(2027, 1, 1),
            date(2027, 2, 1),
        ]

    def test_recusa_parcelamento_invalido(self) -> None:
        with pytest.raises(ValueError):
            parcelas_em_faturas(
                data_compra=date(2026, 8, 15),
                ciclo=FECHA_20_VENCE_28,
                valor_total_centavos=1000,
                total_parcelas=0,
            )


class TestCicloCartao:
    def test_recusa_dia_fora_do_intervalo(self) -> None:
        with pytest.raises(ValueError):
            CicloCartao(dia_fechamento=0, dia_vencimento=10)
        with pytest.raises(ValueError):
            CicloCartao(dia_fechamento=10, dia_vencimento=32)
