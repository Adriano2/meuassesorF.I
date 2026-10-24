"""Gera os arquivos finais do logo do @tec.enftrabalho (selo escolhido, opção C).

Uso:
    python3 gerar_logo.py --fontes DIR_TTF --saida DIR_PNG
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from opcoes_logo import BRANCO, TINTA, opcao_selo

AZUL, VERDE, VERMELHO = (21, 94, 179), (26, 128, 72), (200, 38, 38)
NEVOA = (107, 122, 146)


def selo(fontes: Path, tam: int, fundo: tuple[int, int, int] | None) -> Image.Image:
    return opcao_selo(fontes, fundo).resize((tam, tam), Image.LANCZOS)


def perfil(fontes: Path, fundo: tuple[int, int, int], tam: int = 1080) -> Image.Image:
    """Foto de perfil: selo com margem, para o recorte circular do Instagram não cortar o aro."""
    img = Image.new("RGB", (tam, tam), fundo)
    m = selo(fontes, int(tam * 0.9), None)
    img.paste(m, ((tam - m.width) // 2, (tam - m.height) // 2), m)
    return img


def horizontal(fundo: tuple[int, int, int], fontes: Path) -> Image.Image:
    escuro = fundo[0] < 128
    w, h = 2400, 720
    img = Image.new("RGB", (w, h), fundo)
    d = ImageDraw.Draw(img)
    m = selo(fontes, 560, None)
    img.paste(m, (100, (h - 560) // 2), m)
    fb = ImageFont.truetype(str(next(fontes.rglob("BarlowCondensed_800ExtraBold.ttf"))), 230)
    fl = ImageFont.truetype(str(next(fontes.rglob("BarlowCondensed_600SemiBold.ttf"))), 230)
    ft = ImageFont.truetype(str(next(fontes.rglob("BarlowCondensed_700Bold.ttf"))), 62)
    x, y = 720, 150
    cor = (244, 246, 250) if escuro else TINTA
    d.text((x, y), "tec.enf", font=fb, fill=cor)
    d.text((x + d.textlength("tec.enf", font=fb), y), "trabalho", font=fl, fill=(169, 182, 202) if escuro else NEVOA)
    lx = 724
    for txt, c in [("ENFERMAGEM", AZUL), ("SEGURANÇA", VERDE), ("BOMBEIRO", VERMELHO)]:
        d.rectangle([lx, 470, lx + 22, 492], fill=c)
        d.text((lx + 38, 446), txt, font=ft, fill=cor)
        lx += 38 + d.textlength(txt, font=ft) + 52
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)
    perfil(a.fontes, BRANCO).save(a.saida / "logo-perfil-branco.png")
    perfil(a.fontes, TINTA).save(a.saida / "logo-perfil-escuro.png")
    selo(a.fontes, 1024, None).save(a.saida / "logo-selo-transparente.png")
    selo(a.fontes, 256, None).save(a.saida / "selo-256.png")
    horizontal(BRANCO, a.fontes).save(a.saida / "logo-horizontal-branco.png")
    horizontal(TINTA, a.fontes).save(a.saida / "logo-horizontal-escuro.png")


if __name__ == "__main__":
    main()
