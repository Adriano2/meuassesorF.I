"""Critério de aceite da Fase 1: criar transação, categoria, conta e cartão pela API."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.integracao

BASE = "/api/v1"


def _categoria_saida(cliente: Any, cab: dict[str, str], nome: str) -> str:
    resposta = cliente.get(f"{BASE}/categorias", params={"tipo": "saida"}, headers=cab)
    assert resposta.status_code == 200
    return next(c["id"] for c in resposta.json() if c["nome"] == nome)


class TestCadastroInicial:
    def test_registro_semeia_categorias_padrao(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.get(f"{BASE}/categorias", headers=conta_pronta["cabecalhos"])
        assert resposta.status_code == 200
        categorias = resposta.json()
        assert len(categorias) >= 10
        assert {"Alimentação", "Transporte", "Salário"} <= {c["nome"] for c in categorias}
        assert all(c["sistema"] for c in categorias)

    def test_me_devolve_conta_e_papel(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.get(f"{BASE}/me", headers=conta_pronta["cabecalhos"])
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["papel"] == "dono"
        assert corpo["conta"]["fuso"] == "America/Sao_Paulo"
        assert corpo["conta"]["moeda"] == "BRL"

    def test_sem_token_nao_entra(self, cliente: Any) -> None:
        assert cliente.get(f"{BASE}/categorias").status_code == 401

    def test_login_com_senha_errada(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/auth/login", json={"email": "adriano@exemplo.com", "senha": "errada-mesmo"}
        )
        assert resposta.status_code == 401
        assert resposta.json()["codigo"] == "nao_autenticado"

    def test_email_duplicado(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/auth/registrar",
            json={"nome": "Outro", "email": "adriano@exemplo.com", "senha": "senha-comprida"},
        )
        assert resposta.status_code == 409
        assert resposta.json()["codigo"] == "conflito"


class TestCategorias:
    def test_criar_categoria_com_orcamento(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/categorias",
            headers=conta_pronta["cabecalhos"],
            json={
                "nome": "Pets",
                "tipo": "saida",
                "palavras_chave": ["petshop", "ração"],
                "orcamento_mensal_centavos": 30000,
            },
        )
        assert resposta.status_code == 201, resposta.text
        corpo = resposta.json()
        assert corpo["orcamento_mensal_centavos"] == 30000
        assert corpo["operacao_id"] is not None
        assert resposta.headers["X-Operacao-Id"] == corpo["operacao_id"]

    def test_nome_repetido_no_mesmo_tipo(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/categorias",
            headers=conta_pronta["cabecalhos"],
            json={"nome": "Alimentação", "tipo": "saida"},
        )
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "regra_de_negocio"

    def test_orcamento_em_categoria_de_entrada_e_recusado(
        self, cliente: Any, conta_pronta: Any
    ) -> None:
        resposta = cliente.post(
            f"{BASE}/categorias",
            headers=conta_pronta["cabecalhos"],
            json={"nome": "Bônus", "tipo": "entrada", "orcamento_mensal_centavos": 1000},
        )
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "dado_invalido"

    def test_categoria_do_sistema_nao_se_exclui(self, cliente: Any, conta_pronta: Any) -> None:
        cab = conta_pronta["cabecalhos"]
        alimentacao = _categoria_saida(cliente, cab, "Alimentação")
        resposta = cliente.delete(f"{BASE}/categorias/{alimentacao}", headers=cab)
        assert resposta.status_code == 422

    def test_exclusao_e_soft_delete(self, cliente: Any, conta_pronta: Any) -> None:
        cab = conta_pronta["cabecalhos"]
        criada = cliente.post(
            f"{BASE}/categorias", headers=cab, json={"nome": "Temporária", "tipo": "saida"}
        ).json()
        assert cliente.delete(f"{BASE}/categorias/{criada['id']}", headers=cab).status_code == 200

        nomes = {c["nome"] for c in cliente.get(f"{BASE}/categorias", headers=cab).json()}
        assert "Temporária" not in nomes


class TestContasECartoes:
    def test_criar_conta_bancaria(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/contas-bancarias",
            headers=conta_pronta["cabecalhos"],
            json={"nome": "Nubank", "instituicao": "Nu", "saldo_centavos": 250000},
        )
        assert resposta.status_code == 201, resposta.text
        assert resposta.json()["saldo_centavos"] == 250000

    def test_criar_cartao(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/cartoes",
            headers=conta_pronta["cabecalhos"],
            json={"nome": "Inter", "dia_fechamento": 20, "dia_vencimento": 28},
        )
        assert resposta.status_code == 201, resposta.text
        assert resposta.json()["dia_fechamento"] == 20

    def test_cartao_com_dia_invalido(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/cartoes",
            headers=conta_pronta["cabecalhos"],
            json={"nome": "Ruim", "dia_fechamento": 0, "dia_vencimento": 40},
        )
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "dado_invalido"

    def test_cartao_apontando_para_conta_de_outra_conta(
        self, cliente: Any, conta_pronta: Any, outra_conta: Any
    ) -> None:
        alheia = cliente.post(
            f"{BASE}/contas-bancarias",
            headers=outra_conta["cabecalhos"],
            json={"nome": "Conta da vizinha"},
        ).json()

        resposta = cliente.post(
            f"{BASE}/cartoes",
            headers=conta_pronta["cabecalhos"],
            json={
                "nome": "Inter",
                "dia_fechamento": 20,
                "dia_vencimento": 28,
                "conta_pagamento_id": alheia["id"],
            },
        )
        assert resposta.status_code == 404


class TestTransacoes:
    def test_registrar_saida_move_o_saldo(self, cliente: Any, conta_pronta: Any) -> None:
        cab = conta_pronta["cabecalhos"]
        conta = cliente.post(
            f"{BASE}/contas-bancarias", headers=cab,
            json={"nome": "Nubank", "saldo_centavos": 100000},
        ).json()

        resposta = cliente.post(
            f"{BASE}/transacoes",
            headers=cab,
            json={
                "tipo": "saida",
                "descricao": "Mercado",
                "valor_centavos": 5000,
                "data": "2026-08-13",
                "conta_bancaria_id": conta["id"],
                "categoria_id": _categoria_saida(cliente, cab, "Alimentação"),
            },
        )
        assert resposta.status_code == 201, resposta.text
        criada = resposta.json()
        assert criada["valor_centavos"] == 5000
        assert criada["data_efetiva"] == "2026-08-13"

        atual = cliente.get(f"{BASE}/contas-bancarias", headers=cab).json()[0]
        assert atual["saldo_centavos"] == 95000

    def test_previsto_nao_move_saldo_nem_tem_data_efetiva(
        self, cliente: Any, conta_pronta: Any
    ) -> None:
        cab = conta_pronta["cabecalhos"]
        conta = cliente.post(
            f"{BASE}/contas-bancarias", headers=cab,
            json={"nome": "Nubank", "saldo_centavos": 100000},
        ).json()

        criada = cliente.post(
            f"{BASE}/transacoes",
            headers=cab,
            json={
                "tipo": "saida",
                "descricao": "Conta de luz",
                "valor_centavos": 12000,
                "data": "2026-08-25",
                "status": "previsto",
                "conta_bancaria_id": conta["id"],
            },
        ).json()
        assert criada["data_efetiva"] is None

        atual = cliente.get(f"{BASE}/contas-bancarias", headers=cab).json()[0]
        assert atual["saldo_centavos"] == 100000

    def test_valor_zero_e_recusado(self, cliente: Any, conta_pronta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/transacoes",
            headers=conta_pronta["cabecalhos"],
            json={"tipo": "saida", "descricao": "Nada", "valor_centavos": 0},
        )
        assert resposta.status_code == 422

    def test_conta_e_cartao_ao_mesmo_tempo_e_recusado(
        self, cliente: Any, conta_pronta: Any
    ) -> None:
        cab = conta_pronta["cabecalhos"]
        conta = cliente.post(
            f"{BASE}/contas-bancarias", headers=cab, json={"nome": "Nubank"}
        ).json()
        cartao = cliente.post(
            f"{BASE}/cartoes", headers=cab,
            json={"nome": "Inter", "dia_fechamento": 20, "dia_vencimento": 28},
        ).json()

        resposta = cliente.post(
            f"{BASE}/transacoes",
            headers=cab,
            json={
                "tipo": "saida",
                "descricao": "Confuso",
                "valor_centavos": 1000,
                "conta_bancaria_id": conta["id"],
                "cartao_id": cartao["id"],
            },
        )
        assert resposta.status_code == 422

    def test_exclusao_devolve_o_saldo(self, cliente: Any, conta_pronta: Any) -> None:
        cab = conta_pronta["cabecalhos"]
        conta = cliente.post(
            f"{BASE}/contas-bancarias", headers=cab,
            json={"nome": "Nubank", "saldo_centavos": 100000},
        ).json()
        criada = cliente.post(
            f"{BASE}/transacoes",
            headers=cab,
            json={
                "tipo": "saida",
                "descricao": "Mercado",
                "valor_centavos": 5000,
                "conta_bancaria_id": conta["id"],
            },
        ).json()

        assert cliente.delete(f"{BASE}/transacoes/{criada['id']}", headers=cab).status_code == 200
        assert cliente.get(f"{BASE}/contas-bancarias", headers=cab).json()[0][
            "saldo_centavos"
        ] == 100000
        assert cliente.get(f"{BASE}/transacoes", headers=cab).json() == []

    def test_trocar_categoria_trava_a_categoria(self, cliente: Any, conta_pronta: Any) -> None:
        cab = conta_pronta["cabecalhos"]
        criada = cliente.post(
            f"{BASE}/transacoes",
            headers=cab,
            json={"tipo": "saida", "descricao": "Consulta", "valor_centavos": 20000},
        ).json()
        assert criada["categoria_travada"] is False

        saude = _categoria_saida(cliente, cab, "Saúde")
        resposta = cliente.patch(
            f"{BASE}/transacoes/{criada['id']}/categoria",
            headers=cab,
            json={"categoria_id": saude},
        )
        assert resposta.status_code == 200
        assert resposta.json()["categoria_travada"] is True
        assert resposta.json()["categoria_id"] == saude

    def test_resumo_do_periodo(self, cliente: Any, conta_pronta: Any) -> None:
        cab = conta_pronta["cabecalhos"]
        for tipo, valor in (("entrada", 500000), ("saida", 120000), ("saida", 30000)):
            cliente.post(
                f"{BASE}/transacoes",
                headers=cab,
                json={
                    "tipo": tipo,
                    "descricao": f"{tipo} teste",
                    "valor_centavos": valor,
                    "data": "2026-08-10",
                },
            )
        resumo = cliente.get(
            f"{BASE}/resumo", headers=cab, params={"de": "2026-08-01", "ate": "2026-08-31"}
        ).json()
        assert resumo["entradas_centavos"] == 500000
        assert resumo["saidas_centavos"] == 150000
        assert resumo["saldo_centavos"] == 350000


class TestIdempotencia:
    def test_mesma_chave_nao_duplica(self, cliente: Any, conta_pronta: Any) -> None:
        cab = {**conta_pronta["cabecalhos"], "Idempotency-Key": "abc-123"}
        corpo = {"tipo": "saida", "descricao": "Mercado", "valor_centavos": 5000}

        primeira = cliente.post(f"{BASE}/transacoes", headers=cab, json=corpo)
        segunda = cliente.post(f"{BASE}/transacoes", headers=cab, json=corpo)

        assert primeira.status_code == 201
        assert segunda.status_code == 201
        assert primeira.json()["id"] == segunda.json()["id"]
        assert primeira.json()["operacao_id"] == segunda.json()["operacao_id"]

        listagem = cliente.get(f"{BASE}/transacoes", headers=conta_pronta["cabecalhos"]).json()
        assert len(listagem) == 1

    def test_chaves_diferentes_criam_duas(self, cliente: Any, conta_pronta: Any) -> None:
        corpo = {"tipo": "saida", "descricao": "Mercado", "valor_centavos": 5000}
        for chave in ("k1", "k2"):
            cliente.post(
                f"{BASE}/transacoes",
                headers={**conta_pronta["cabecalhos"], "Idempotency-Key": chave},
                json=corpo,
            )
        listagem = cliente.get(f"{BASE}/transacoes", headers=conta_pronta["cabecalhos"]).json()
        assert len(listagem) == 2
