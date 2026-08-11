"""Datas e fuso. CLAUDE.md §4.

O banco guarda UTC (TIMESTAMPTZ). O fuso do usuário vive em `contas.fuso`.
Nunca use `datetime.now()` solto no resto do código — passe por aqui, sempre
com o fuso da conta em mãos.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

__all__ = [
    "agora",
    "ancorar_dia",
    "hoje",
    "inicio_do_mes",
    "para_utc",
    "proximo_mes",
    "ultimo_dia_do_mes",
    "zona",
]


def zona(fuso: str) -> ZoneInfo:
    return ZoneInfo(fuso)


def agora(fuso: str) -> datetime:
    """Instante atual já no fuso da conta."""
    return datetime.now(tz=zona(fuso))


def hoje(fuso: str, *, instante: datetime | None = None) -> date:
    """Data de hoje no fuso da conta.

    Existe porque 02:30 UTC ainda é ontem em São Paulo — assumir a data de UTC
    joga lançamentos da madrugada para o dia seguinte (ESPEC §9 #10).
    """
    momento = instante or datetime.now(tz=UTC)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(zona(fuso)).date()


def para_utc(local: datetime, fuso: str) -> datetime:
    """Converte um horário local (ingênuo ou com fuso) para UTC."""
    if local.tzinfo is None:
        local = local.replace(tzinfo=zona(fuso))
    return local.astimezone(UTC)


def ultimo_dia_do_mes(ano: int, mes: int) -> int:
    return monthrange(ano, mes)[1]


def ancorar_dia(ano: int, mes: int, dia: int) -> date:
    """Resolve uma ancoragem de dia para um mês concreto.

    Dia 31 em fevereiro vira o último dia do mês. É a regra que quebra em
    fevereiro se ninguém escrever o teste — por isso ela mora em um só lugar.
    """
    if not 1 <= dia <= 31:
        raise ValueError(f"dia de ancoragem inválido: {dia}")
    return date(ano, mes, min(dia, ultimo_dia_do_mes(ano, mes)))


def inicio_do_mes(dia: date) -> date:
    return dia.replace(day=1)


def proximo_mes(dia: date) -> date:
    """Primeiro dia do mês seguinte."""
    return date(dia.year + 1, 1, 1) if dia.month == 12 else date(dia.year, dia.month + 1, 1)
