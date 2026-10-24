"""Gera os arquivos de logo do @tec.enftrabalho em PNG.

Uso:
    python3 gerar_logo.py --fontes DIR_TTF --saida DIR_PNG
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TINTA = (14, 26, 43)
PAINEL = (24, 40, 62)
BORDA = (44, 64, 92)
CLARO = (244, 246, 250)
AZUL, VERDE, VERMELHO, AMARELO = (21, 94, 179), (26, 128, 72), (200, 38, 38), (242, 183, 5)
NEVOA = (107, 122, 146)
ESCALA = 4  # desenha grande e reduz, para bordas suaves


def cruz(d: ImageDraw.ImageDraw, x0: int, y0: int, s: int, centro: tuple[int, int, int] = CLARO) -> None:
    """Cruz contínua: braço de cima azul, esquerdo verde, direito vermelho, de baixo amarelo, centro claro."""
    u = s // 3
    r = u // 5  # só as pontas externas são arredondadas
    d.rounded_rectangle([x0 + u, y0, x0 + 2 * u, y0 + u + r], radius=r, fill=AZUL)
    d.rounded_rectangle([x0, y0 + u, x0 + u + r, y0 + 2 * u], radius=r, fill=VERDE)
    d.rounded_rectangle([x0 + 2 * u - r, y0 + u, x0 + 3 * u, y0 + 2 * u], radius=r, fill=VERMELHO)
    d.rounded_rectangle([x0 + u, y0 + 2 * u - r, x0 + 2 * u, y0 + 3 * u], radius=r, fill=AMARELO)
    d.rectangle([x0 + u, y0 + u, x0 + 2 * u, y0 + 2 * u], fill=centro)


def marca(tam: int) -> Image.Image:
    """Cruz dentro de placa quadrada (forma das placas de informação de segurança)."""
    s = tam * ESCALA
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.2), fill=PAINEL, outline=BORDA, width=max(2, s // 60))
    c = int(s * 0.72)
    cruz(d, (s - c) // 2, (s - c) // 2, c)
    return img.resize((tam, tam), Image.LANCZOS)


def perfil(fundo: tuple[int, int, int], tam: int = 1080) -> Image.Image:
    """Foto de perfil: cruz direto sobre o fundo, dentro da área segura do recorte circular."""
    s = tam * ESCALA
    img = Image.new("RGB", (s, s), fundo)
    d = ImageDraw.Draw(img)
    c = int(s * 0.54)
    # no fundo branco o centro claro sumiria; ele passa a ser tinta
    cruz(d, (s - c) // 2, (s - c) // 2, c, TINTA if fundo[0] > 128 else CLARO)
    return img.resize((tam, tam), Image.LANCZOS)


def horizontal(fundo: tuple[int, int, int], fontes: Path) -> Image.Image:
    escuro = fundo[0] < 128
    w, h = 2400, 720
    img = Image.new("RGB", (w, h), fundo)
    d = ImageDraw.Draw(img)
    m = marca(440)
    img.paste(m, (140, (h - 440) // 2), m)
    fb = ImageFont.truetype(str(next(fontes.rglob("BarlowCondensed_800ExtraBold.ttf"))), 230)
    fl = ImageFont.truetype(str(next(fontes.rglob("BarlowCondensed_600SemiBold.ttf"))), 230)
    ft = ImageFont.truetype(str(next(fontes.rglob("BarlowCondensed_700Bold.ttf"))), 62)
    x, y = 660, 150
    cor = CLARO if escuro else TINTA
    d.text((x, y), "tec.enf", font=fb, fill=cor)
    x2 = x + d.textlength("tec.enf", font=fb)
    d.text((x2, y), "trabalho", font=fl, fill=(169, 182, 202) if escuro else NEVOA)
    lx = 664
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
    perfil(TINTA).save(a.saida / "logo-perfil-escuro.png")
    perfil((255, 255, 255)).save(a.saida / "logo-perfil-branco.png")
    marca(1024).save(a.saida / "logo-marca-transparente.png")
    horizontal((255, 255, 255), a.fontes).save(a.saida / "logo-horizontal-branco.png")
    horizontal(TINTA, a.fontes).save(a.saida / "logo-horizontal-escuro.png")


if __name__ == "__main__":
    main()
