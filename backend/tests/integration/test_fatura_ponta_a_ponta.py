"""Critério de aceite da Fase 1: bordas de fatura, pela API.

O teste que importa: gasto no cartão não é saída de caixa no dia da compra.
O caixa só se move quando a fatura é paga (CLAUDE.md §4).
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.integracao

BASE = "/api/v1"


@pytest.fixture
def cartao_e_conta(cliente: Any, conta_pronta: Any) -> dict[str, Any]:
    cab = conta_pronta["cabecalhos"]
    conta = cliente.post(
        f"{BASE}/contas-bancarias", headers=cab,
        json={"nome": "Nubank", "saldo_centavos": 1000000},
    ).json()
    cartao = cliente.post(
        f"{BASE}/cartoes",
        headers=cab,
        json={
            "nome": "Inter",
            "dia_fechamento": 20,
            "dia_vencimento": 28,
            "conta_pagamento_id": conta["id"],
        },
    ).json()
    return {"cab": cab, "conta": conta, "cartao": cartao}


def _faturas(cliente: Any, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    resposta = cliente.get(f"{BASE}/cartoes/{ctx['cartao']['id']}/faturas", headers=ctx["cab"])
    assert resposta.status_code == 200
    return sorted(resposta.json(), key=lambda f: f["competencia"])


class TestCompraNoCartao:
    def test_compra_antes_do_fechamento_abre_a_fatura_do_mes(
        self, cliente: Any, cartao_e_conta: Any
    ) -> None:
        ctx = cartao_e_conta
        cliente.post(
            f"{BASE}/transacoes",
            headers=ctx["cab"],
            json={
                "tipo": "saida",
                "descricao": "Tênis",
                "valor_centavos": 39900,
                "data": "2026-08-15",
                "cartao_id": ctx["cartao"]["id"],
            },
        )
        faturas = _faturas(cliente, ctx)
        assert len(faturas) == 1
        assert faturas[0]["competencia"] == "2026-08-01"
        assert faturas[0]["data_fechamento"] == "2026-08-20"
        assert faturas[0]["data_vencimento"] == "2026-08-28"
        assert faturas[0]["total_centavos"] == 39900

    def test_compra_depois_do_fechamento_vai_para_a_proxima(
        self, cliente: Any, cartao_e_conta: Any
    ) -> None:
        ctx = cartao_e_conta
        cliente.post(
            f"{BASE}/transacoes",
            headers=ctx["cab"],
            json={
                "tipo": "saida",
                "descricao": "Tênis",
                "valor_centavos": 39900,
                "data": "2026-08-21",
                "cartao_id": ctx["cartao"]["id"],
            },
        )
        faturas = _faturas(cliente, ctx)
        assert [f["competencia"] for f in faturas] == ["2026-09-01"]

    def test_compra_no_cartao_nao_move_o_caixa(self, cliente: Any, cartao_e_conta: Any) -> None:
        ctx = cartao_e_conta
        criada = cliente.post(
            f"{BASE}/transacoes",
            headers=ctx["cab"],
            json={
                "tipo": "saida",
                "descricao": "Tênis",
                "valor_centavos": 39900,
                "data": "2026-08-15",
                "cartao_id": ctx["cartao"]["id"],
            },
        ).json()

        # a transação existe e conta na competência de agosto...
        assert criada["data_competencia"] == "2026-08-15"
        # ...mas o dinheiro não moveu: sem data_efetiva e saldo intacto
        assert criada["data_efetiva"] is None
        saldo = cliente.get(f"{BASE}/contas-bancarias", headers=ctx["cab"]).json()[0]
        assert saldo["saldo_centavos"] == 1000000


class TestParcelamento:
    def test_doze_parcelas_em_doze_faturas(self, cliente: Any, cartao_e_conta: Any) -> None:
        ctx = cartao_e_conta
        cliente.post(
            f"{BASE}/transacoes",
            headers=ctx["cab"],
            json={
                "tipo": "saida",
                "descricao": "TV",
                "valor_centavos": 480000,
                "data": "2026-08-15",
                "cartao_id": ctx["cartao"]["id"],
                "parcelas": 12,
            },
        )
        faturas = _faturas(cliente, ctx)
        assert len(faturas) == 12
        assert faturas[0]["competencia"] == "2026-08-01"
        assert faturas[-1]["competencia"] == "2027-07-01"
        assert all(f["total_centavos"] == 40000 for f in faturas)

        lancamentos = cliente.get(
            f"{BASE}/transacoes", headers=ctx["cab"], params={"limite": 50}
        ).json()
        assert len(lancamentos) == 12
        assert {t["descricao"] for t in lancamentos} >= {"TV (1/12)", "TV (12/12)"}
        assert sum(t["valor_centavos"] for t in lancamentos) == 480000

    def test_parcelamento_com_resto_de_centavo(self, cliente: Any, cartao_e_conta: Any) -> None:
        ctx = cartao_e_conta
        cliente.post(
            f"{BASE}/transacoes",
            headers=ctx["cab"],
            json={
                "tipo": "saida",
                "descricao": "Curso",
                "valor_centavos": 1000,
                "data": "2026-08-15",
                "cartao_id": ctx["cartao"]["id"],
                "parcelas": 3,
            },
        )
        totais = [f["total_centavos"] for f in _faturas(cliente, ctx)]
        assert totais == [334, 333, 333]
        assert sum(totais) == 1000

    def test_parcelamento_sem_cartao_e_recusado(self, cliente: Any, cartao_e_conta: Any) -> None:
        resposta = cliente.post(
            f"{BASE}/transacoes",
            headers=cartao_e_conta["cab"],
            json={
                "tipo": "saida",
                "descricao": "TV",
                "valor_centavos": 480000,
                "parcelas": 12,
            },
        )
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "regra_de_negocio"


class TestPagamentoDaFatura:
    def _uma_compra(self, cliente: Any, ctx: dict[str, Any], valor: int = 39900) -> None:
        cliente.post(
            f"{BASE}/transacoes",
            headers=ctx["cab"],
            json={
                "tipo": "saida",
                "descricao": "Tênis",
                "valor_centavos": valor,
                "data": "2026-08-15",
                "cartao_id": ctx["cartao"]["id"],
            },
        )

    def test_pagar_move_o_caixa_e_fecha_a_fatura(
        self, cliente: Any, cartao_e_conta: Any
    ) -> None:
        ctx = cartao_e_conta
        self._uma_compra(cliente, ctx)
        fatura = _faturas(cliente, ctx)[0]

        resposta = cliente.post(
            f"{BASE}/faturas/{fatura['id']}/pagar",
            headers=ctx["cab"],
            json={"data": "2026-08-28"},
        )
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["status"] == "paga"
        assert resposta.json()["pago_centavos"] == 39900

        # agora sim o dinheiro saiu
        saldo = cliente.get(f"{BASE}/contas-bancarias", headers=ctx["cab"]).json()[0]
        assert saldo["saldo_centavos"] == 1000000 - 39900

        pagamento = [
            t
            for t in cliente.get(f"{BASE}/transacoes", headers=ctx["cab"]).json()
            if t["descricao"].startswith("Pagamento fatura")
        ]
        assert len(pagamento) == 1
        assert pagamento[0]["data_efetiva"] == "2026-08-28"

    def test_pagamento_parcial_deixa_a_fatura_parcial(
        self, cliente: Any, cartao_e_conta: Any
    ) -> None:
        ctx = cartao_e_conta
        self._uma_compra(cliente, ctx, valor=100000)
        fatura = _faturas(cliente, ctx)[0]

        resposta = cliente.post(
            f"{BASE}/faturas/{fatura['id']}/pagar",
            headers=ctx["cab"],
            json={"valor_centavos": 40000},
        )
        assert resposta.json()["status"] == "parcial"
        assert resposta.json()["pago_centavos"] == 40000

    def test_nao_paga_mais_do_que_deve(self, cliente: Any, cartao_e_conta: Any) -> None:
        ctx = cartao_e_conta
        self._uma_compra(cliente, ctx, valor=10000)
        fatura = _faturas(cliente, ctx)[0]

        resposta = cliente.post(
            f"{BASE}/faturas/{fatura['id']}/pagar",
            headers=ctx["cab"],
            json={"valor_centavos": 20000},
        )
        assert resposta.status_code == 422
        assert resposta.json()["codigo"] == "regra_de_negocio"

    def test_nao_paga_duas_vezes(self, cliente: Any, cartao_e_conta: Any) -> None:
        ctx = cartao_e_conta
        self._uma_compra(cliente, ctx)
        fatura = _faturas(cliente, ctx)[0]

        cliente.post(f"{BASE}/faturas/{fatura['id']}/pagar", headers=ctx["cab"], json={})
        segunda = cliente.post(
            f"{BASE}/faturas/{fatura['id']}/pagar", headers=ctx["cab"], json={}
        )
        assert segunda.status_code == 422
        assert segunda.json()["codigo"] == "fatura_ja_paga"

    def test_fatura_vazia_nao_se_paga(self, cliente: Any, cartao_e_conta: Any) -> None:
        ctx = cartao_e_conta
        self._uma_compra(cliente, ctx)
        fatura = _faturas(cliente, ctx)[0]

        lancamento = [
            t
            for t in cliente.get(f"{BASE}/transacoes", headers=ctx["cab"]).json()
            if t["fatura_id"] == fatura["id"]
        ][0]
        cliente.delete(f"{BASE}/transacoes/{lancamento['id']}", headers=ctx["cab"])

        resposta = cliente.post(f"{BASE}/faturas/{fatura['id']}/pagar", headers=ctx["cab"],
                                json={})
        assert resposta.status_code == 422


class TestTotalDerivado:
    def test_excluir_lancamento_recalcula_o_total(
        self, cliente: Any, cartao_e_conta: Any
    ) -> None:
        """Total da fatura é soma, nunca campo mantido à mão (ESPEC §4.2)."""
        ctx = cartao_e_conta
        for valor in (10000, 25000):
            cliente.post(
                f"{BASE}/transacoes",
                headers=ctx["cab"],
                json={
                    "tipo": "saida",
                    "descricao": f"Compra {valor}",
                    "valor_centavos": valor,
                    "data": "2026-08-15",
                    "cartao_id": ctx["cartao"]["id"],
                },
            )
        assert _faturas(cliente, ctx)[0]["total_centavos"] == 35000

        alvo = [
            t
            for t in cliente.get(f"{BASE}/transacoes", headers=ctx["cab"]).json()
            if t["valor_centavos"] == 10000
        ][0]
        cliente.delete(f"{BASE}/transacoes/{alvo['id']}", headers=ctx["cab"])

        assert _faturas(cliente, ctx)[0]["total_centavos"] == 25000
