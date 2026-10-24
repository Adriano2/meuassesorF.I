"""Gera a mesma frase em várias vozes femininas Chirp 3 HD (pt-BR) para comparar.

Uso:
    GOOGLE_TTS_API_KEY=... python3 amostras_voz.py --saida ./amostras
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gerar_quiz import falar_google

VOZES = {
    "Achernar": "suave",
    "Vindemiatrix": "gentil",
    "Sulafat": "acolhedora",
    "Leda": "jovem",
}
FRASE = (
    "Quiz de cinco segundos! Qual exame ocupacional é feito antes de o trabalhador assumir a função? "
    "Você tem cinco segundos. Resposta certa: letra C, admissional. "
    "O exame admissional é feito antes do início das atividades, conforme a NR sete."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", type=Path, required=True)
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)
    for nome, desc in VOZES.items():
        falar_google(FRASE, nome, a.saida / f"{nome}-{desc}.wav")
        print(nome, desc)


if __name__ == "__main__":
    main()
