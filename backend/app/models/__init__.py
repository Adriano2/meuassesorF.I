"""Modelos SQLAlchemy. Importar daqui garante que o Alembic enxergue tudo."""

from app.models.auditoria import Operacao
from app.models.base import (
    Base,
    Frequencia,
    OrigemRegistro,
    PapelConta,
    StatusFatura,
    StatusTransacao,
    TipoFluxo,
    TipoSerie,
)
from app.models.financas import (
    Cartao,
    Categoria,
    ContaBancaria,
    Fatura,
    Pessoa,
    Serie,
    SerieExcecao,
    Transacao,
)
from app.models.nucleo import Conta, MembroConta, Usuario

__all__ = [
    "Base",
    "Cartao",
    "Categoria",
    "Conta",
    "ContaBancaria",
    "Fatura",
    "Frequencia",
    "MembroConta",
    "Operacao",
    "OrigemRegistro",
    "PapelConta",
    "Pessoa",
    "Serie",
    "SerieExcecao",
    "StatusFatura",
    "StatusTransacao",
    "TipoFluxo",
    "TipoSerie",
    "Transacao",
    "Usuario",
]
