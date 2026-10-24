"""Gera a mesma frase em várias vozes femininas (Gemini TTS ou Chirp 3 HD) para comparar.

Uso:
    GEMINI_API_KEY=... python3 amostras_voz.py --saida ./amostras
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gerar_quiz import falar_gemini, falar_google

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
    ap.add_argument("--motor", choices=["gemini", "chirp"], default="gemini",
                    help="gemini: chave do AI Studio (GEMINI_API_KEY); chirp: Cloud TTS (GOOGLE_TTS_API_KEY)")
    a = ap.parse_args()
    falar = falar_gemini if a.motor == "gemini" else falar_google
    a.saida.mkdir(parents=True, exist_ok=True)
    for nome, desc in VOZES.items():
        falar(FRASE, nome, a.saida / f"{a.motor}-{nome}-{desc}.wav")
        print(nome, desc)


if __name__ == "__main__":
    main()
