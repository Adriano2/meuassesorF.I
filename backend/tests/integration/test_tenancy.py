"""Critério de aceite da Fase 1: multi-tenancy isolado.

Enquanto a RLS não entra (Fase 2), o filtro por `conta_id` no repository é a
única barreira. Estes testes existem para que ela não caia em silêncio.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.integracao

BASE = "/api/v1"


@pytest.fixture
def dados_da_vizinha(cliente: Any, outra_conta: Any) -> dict[str, Any]:
    cab = outra_conta["cabecalhos"]
    conta = cliente.post(
        f"{BASE}/contas-bancarias", headers=cab,
        json={"nome": "Conta alheia", "saldo_centavos": 999999},
    ).json()
    cartao = cliente.post(
        f"{BASE}/cartoes", headers=cab,
        json={"nome": "Cartão alheio", "dia_fechamento": 10, "dia_vencimento": 20},
    ).json()
    categoria = cliente.post(
        f"{BASE}/categorias", headers=cab, json={"nome": "Alheia", "tipo": "saida"}
    ).json()
    transacao = cliente.post(
        f"{BASE}/transacoes",
        headers=cab,
        json={
            "tipo": "saida",
            "descricao": "Segredo da vizinha",
            "valor_centavos": 77700,
            "conta_bancaria_id": conta["id"],
        },
    ).json()
    return {"conta": conta, "cartao": cartao, "categoria": categoria, "transacao": transacao}


class TestIsolamentoDeLeitura:
    def test_listagens_nao_vazam(
        self, cliente: Any, conta_pronta: Any, dados_da_vizinha: Any
    ) -> None:
        cab = conta_pronta["cabecalhos"]
        assert cliente.get(f"{BASE}/transacoes", headers=cab).json() == []
        assert cliente.get(f"{BASE}/contas-bancarias", headers=cab).json() == []
        assert cliente.get(f"{BASE}/cartoes", headers=cab).json() == []
        nomes = {c["nome"] for c in cliente.get(f"{BASE}/categorias", headers=cab).json()}
        assert "Alheia" not in nomes

    def test_id_alheio_responde_404_e_nao_403(
        self, cliente: Any, conta_pronta: Any, dados_da_vizinha: Any
    ) -> None:
        # 404 e não 403: um 403 confirmaria que o recurso existe
        resposta = cliente.get(
            f"{BASE}/transacoes/{dados_da_vizinha['transacao']['id']}",
            headers=conta_pronta["cabecalhos"],
        )
        assert resposta.status_code == 404

    def test_faturas_de_cartao_alheio(
        self, cliente: Any, conta_pronta: Any, dados_da_vizinha: Any
    ) -> None:
        resposta = cliente.get(
            f"{BASE}/cartoes/{dados_da_vizinha['cartao']['id']}/faturas",
            headers=conta_pronta["cabecalhos"],
        )
        assert resposta.status_code == 404

    def test_resumo_nao_soma_a_conta_alheia(
        self, cliente: Any, conta_pronta: Any, dados_da_vizinha: Any
    ) -> None:
        resumo = cliente.get(
            f"{BASE}/resumo",
            headers=conta_pronta["cabecalhos"],
            params={"de": "2020-01-01", "ate": "2030-12-31"},
        ).json()
        assert resumo["saidas_centavos"] == 0


class TestIsolamentoDeEscrita:
    def test_nao_exclui_transacao_alheia(
        self, cliente: Any, conta_pronta: Any, outra_conta: Any, dados_da_vizinha: Any
    ) -> None:
        alvo = dados_da_vizinha["transacao"]["id"]
        assert cliente.delete(
            f"{BASE}/transacoes/{alvo}", headers=conta_pronta["cabecalhos"]
        ).status_code == 404

        # e continua lá para a dona
        ainda = cliente.get(f"{BASE}/transacoes", headers=outra_conta["cabecalhos"]).json()
        assert len(ainda) == 1

    def test_nao_lanca_na_conta_bancaria_alheia(
        self, cliente: Any, conta_pronta: Any, dados_da_vizinha: Any
    ) -> None:
        resposta = cliente.post(
            f"{BASE}/transacoes",
            headers=conta_pronta["cabecalhos"],
            json={
                "tipo": "saida",
                "descricao": "Tentativa",
                "valor_centavos": 1000,
                "conta_bancaria_id": dados_da_vizinha["conta"]["id"],
            },
        )
        assert resposta.status_code == 404

    def test_nao_usa_categoria_alheia(
        self, cliente: Any, conta_pronta: Any, dados_da_vizinha: Any
    ) -> None:
        resposta = cliente.post(
            f"{BASE}/transacoes",
            headers=conta_pronta["cabecalhos"],
            json={
                "tipo": "saida",
                "descricao": "Tentativa",
                "valor_centavos": 1000,
                "categoria_id": dados_da_vizinha["categoria"]["id"],
            },
        )
        assert resposta.status_code == 404

    def test_idempotency_key_nao_cruza_contas(
        self, cliente: Any, conta_pronta: Any, outra_conta: Any
    ) -> None:
        """A chave é única por conta — a mesma string em duas contas cria duas coisas."""
        corpo = {"tipo": "saida", "descricao": "Mercado", "valor_centavos": 5000}
        uma = cliente.post(
            f"{BASE}/transacoes",
            headers={**conta_pronta["cabecalhos"], "Idempotency-Key": "mesma"},
            json=corpo,
        )
        outra = cliente.post(
            f"{BASE}/transacoes",
            headers={**outra_conta["cabecalhos"], "Idempotency-Key": "mesma"},
            json=corpo,
        )
        assert uma.status_code == outra.status_code == 201
        assert uma.json()["id"] != outra.json()["id"]


class TestTokenAdulterado:
    def test_token_de_outra_conta_nao_serve(
        self, cliente: Any, conta_pronta: Any, outra_conta: Any
    ) -> None:
        """O conta_id vem do token, nunca do corpo — trocar o corpo não muda nada."""
        cab = conta_pronta["cabecalhos"]
        criada = cliente.post(
            f"{BASE}/transacoes",
            headers=cab,
            json={
                "tipo": "saida",
                "descricao": "Minha",
                "valor_centavos": 1000,
                "conta_id": outra_conta["conta_id"],  # campo extra: deve ser ignorado
            },
        )
        assert criada.status_code == 201
        # foi para a conta do token, não para a do corpo
        assert len(cliente.get(f"{BASE}/transacoes", headers=cab).json()) == 1
        assert cliente.get(f"{BASE}/transacoes", headers=outra_conta["cabecalhos"]).json() == []

    def test_token_invalido(self, cliente: Any) -> None:
        resposta = cliente.get(
            f"{BASE}/categorias", headers={"Authorization": "Bearer nao-e-um-token"}
        )
        assert resposta.status_code == 401
