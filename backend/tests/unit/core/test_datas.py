"""Fuso e ancoragem de dia. CLAUDE.md §4 — o teste de fevereiro é obrigatório."""

from datetime import UTC, date, datetime

from app.core.datas import (
    agora,
    ancorar_dia,
    hoje,
    inicio_do_mes,
    para_utc,
    proximo_mes,
    ultimo_dia_do_mes,
)

SP = "America/Sao_Paulo"


class TestAncorarDia:
    def test_dia_normal(self) -> None:
        assert ancorar_dia(2026, 8, 15) == date(2026, 8, 15)

    def test_dia_31_em_fevereiro_comum(self) -> None:
        assert ancorar_dia(2026, 2, 31) == date(2026, 2, 28)

    def test_dia_31_em_fevereiro_bissexto(self) -> None:
        assert ancorar_dia(2028, 2, 31) == date(2028, 2, 29)

    def test_dia_31_em_mes_de_30(self) -> None:
        assert ancorar_dia(2026, 4, 31) == date(2026, 4, 30)
        assert ancorar_dia(2026, 9, 31) == date(2026, 9, 30)

    def test_dia_30_em_fevereiro(self) -> None:
        assert ancorar_dia(2026, 2, 30) == date(2026, 2, 28)

    def test_dia_31_em_mes_de_31_nao_muda(self) -> None:
        for mes in (1, 3, 5, 7, 8, 10, 12):
            assert ancorar_dia(2026, mes, 31).day == 31


class TestUltimoDiaDoMes:
    def test_fevereiro_comum_e_bissexto(self) -> None:
        assert ultimo_dia_do_mes(2026, 2) == 28
        assert ultimo_dia_do_mes(2028, 2) == 29

    def test_meses_de_30_e_31(self) -> None:
        assert ultimo_dia_do_mes(2026, 4) == 30
        assert ultimo_dia_do_mes(2026, 12) == 31


class TestNavegacaoDeMes:
    def test_inicio_do_mes(self) -> None:
        assert inicio_do_mes(date(2026, 8, 13)) == date(2026, 8, 1)

    def test_proximo_mes_vira_o_ano(self) -> None:
        assert proximo_mes(date(2026, 12, 1)) == date(2027, 1, 1)

    def test_proximo_mes_normaliza_para_o_dia_1(self) -> None:
        assert proximo_mes(date(2026, 1, 31)) == date(2026, 2, 1)


class TestFuso:
    def test_hoje_usa_o_fuso_da_conta_e_nao_utc(self) -> None:
        # 02:30 UTC de 14/08 ainda é 23:30 de 13/08 em São Paulo
        instante = datetime(2026, 8, 14, 2, 30, tzinfo=UTC)
        assert hoje(SP, instante=instante) == date(2026, 8, 13)
        assert hoje("UTC", instante=instante) == date(2026, 8, 14)

    def test_agora_devolve_datetime_com_fuso(self) -> None:
        momento = agora(SP)
        assert momento.tzinfo is not None
        assert momento.utcoffset() is not None

    def test_para_utc_converte_horario_local(self) -> None:
        local = datetime(2026, 8, 13, 15, 0)
        convertido = para_utc(local, SP)
        assert convertido.tzinfo == UTC
        assert convertido.hour == 18  # BRT = UTC-3

    def test_horario_de_verao_historico(self) -> None:
        # o Brasil tinha DST em 2017: 13/01/2017 era UTC-2
        local = datetime(2017, 1, 13, 15, 0)
        assert para_utc(local, SP).hour == 17
