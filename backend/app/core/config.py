"""Configuração. Tudo vem de variável de ambiente; nada de segredo no código."""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SEGREDO_PADRAO = "troque-em-producao"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ambiente: str = "dev"
    database_url: str = "postgresql+psycopg://assessoria:assessoria@localhost:5432/assessoria"

    jwt_segredo: str = SEGREDO_PADRAO
    jwt_algoritmo: str = "HS256"
    jwt_minutos_acesso: int = 30
    jwt_dias_refresh: int = 30

    fuso_padrao: str = "America/Sao_Paulo"
    moeda_padrao: str = "BRL"

    log_json: bool = True

    @property
    def producao(self) -> bool:
        return self.ambiente == "prod"

    @model_validator(mode="after")
    def _exigir_segredo_forte_em_producao(self) -> Config:
        # HS256 com chave curta é assinatura fraca; em produção não passa
        if self.producao and (
            self.jwt_segredo == SEGREDO_PADRAO or len(self.jwt_segredo) < 32
        ):
            raise ValueError(
                "JWT_SEGREDO precisa ter ao menos 32 caracteres e não pode ser o padrão."
            )
        return self


@lru_cache
def config() -> Config:
    return Config()
