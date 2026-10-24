"""Gera quatro conceitos de logo para escolha (1080 x 1080 cada) e uma prancha comparativa.

Uso:
    python3 opcoes_logo.py --fontes DIR_TTF --saida DIR_PNG
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TINTA = (14, 26, 43)
CLARO = (244, 246, 250)
BRANCO = (255, 255, 255)
AZUL, VERDE, VERMELHO, AMARELO = (21, 94, 179), (26, 128, 72), (200, 38, 38), (242, 183, 5)
T = 1080
K = 4  # superamostragem
S = T * K


def fonte(dir_: Path, nome: str, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(next(dir_.rglob(f"{nome}.ttf"))), tam)


def ecg(d: ImageDraw.ImageDraw, x0: float, x1: float, y: float, amp: float, cor, larg: int) -> None:
    """Linha de batimento: plano, pequena onda, pico, vale, plano."""
    w = x1 - x0
    pts = [(0, 0), (.30, 0), (.36, -.18), (.42, 0), (.47, 0), (.53, -1), (.60, .55), (.66, 0), (.74, -.22), (.80, 0), (1, 0)]
    d.line([(x0 + px * w, y + py * amp) for px, py in pts], fill=cor, width=larg, joint="curve")


def escudo(d: ImageDraw.ImageDraw, cx: float, top: float, w: float, h: float, cor) -> None:
    pts = [(cx - w / 2, top + h * .08), (cx, top), (cx + w / 2, top + h * .08), (cx + w / 2, top + h * .48)]
    for i in range(1, 21):  # curva até a ponta
        t = i / 20
        pts.append((cx + w / 2 * (1 - t), top + h * .48 + (h * .52) * math.sin(t * math.pi / 2)))
    for i in range(1, 21):
        t = i / 20
        pts.append((cx - w / 2 * t, top + h - (h * .52) * (1 - math.cos(t * math.pi / 2))))
    d.polygon(pts, fill=cor)


def opcao_escudo(fd: Path) -> Image.Image:
    """A · Escudo da segurança com a cruz da saúde e o batimento da enfermagem."""
    img = Image.new("RGB", (S, S), TINTA)
    d = ImageDraw.Draw(img)
    escudo(d, S / 2, S * .17, S * .56, S * .66, AMARELO)
    escudo(d, S / 2, S * .17 + S * .025, S * .56 - S * .05, S * .66 - S * .05, VERDE)
    u = S * .095
    cx, cy = S / 2, S * .46
    d.rectangle([cx - u / 2, cy - u * 1.6, cx + u / 2, cy + u * 1.6], fill=BRANCO)
    d.rectangle([cx - u * 1.6, cy - u / 2, cx + u * 1.6, cy + u / 2], fill=BRANCO)
    ecg(d, S * .27, S * .73, cy, S * .12, VERMELHO, int(S * .022))
    return img


def opcao_capacete(_fd: Path) -> Image.Image:
    """B · Capacete de segurança com batimento cardíaco: SST + enfermagem."""
    img = Image.new("RGB", (S, S), AZUL)
    d = ImageDraw.Draw(img)
    cx, base = S / 2, S * .56
    r = S * .25
    d.pieslice([cx - r, base - r, cx + r, base + r], 180, 360, fill=BRANCO)          # casco
    d.rounded_rectangle([cx - r * 1.38, base - S * .012, cx + r * 1.38, base + S * .05], radius=S * .03, fill=BRANCO)  # aba
    d.rounded_rectangle([cx - S * .035, base - r - S * .01, cx + S * .035, base - S * .02], radius=S * .03, fill=AZUL)  # friso
    d.rounded_rectangle([cx - S * .02, base - r + S * .01, cx + S * .02, base - S * .03], radius=S * .02, fill=BRANCO)
    ecg(d, S * .16, S * .84, S * .73, S * .09, AMARELO, int(S * .02))
    return img


def texto_em_arco(img: Image.Image, txt: str, f, cx: float, cy: float, r: float, ini: float, fim: float, cor, por_baixo: bool = False) -> None:
    d = ImageDraw.Draw(img)
    larguras = [d.textlength(c, font=f) for c in txt]
    total = sum(larguras)
    ang_total = total / r
    centro = (ini + fim) / 2
    a = centro - ang_total / 2 if not por_baixo else centro + ang_total / 2
    for c, lw in zip(txt, larguras):
        passo = lw / r
        meio = a + (passo / 2 if not por_baixo else -passo / 2)
        x, y = cx + r * math.cos(meio), cy + r * math.sin(meio)
        tile = Image.new("RGBA", (int(lw * 2 + 4), int(f.size * 2)), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((tile.width / 2 - lw / 2, tile.height / 2 - f.size * .62), c, font=f, fill=cor)
        rot = -math.degrees(meio) - 90 if not por_baixo else -math.degrees(meio) + 90
        tile = tile.rotate(rot, resample=Image.BICUBIC)
        img.paste(tile, (int(x - tile.width / 2), int(y - tile.height / 2)), tile)
        a += passo if not por_baixo else -passo


def opcao_selo(fd: Path) -> Image.Image:
    """C · Selo circular de brigada, com a cruz da saúde ao centro."""
    img = Image.new("RGB", (S, S), BRANCO)
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    R = S * .44
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=TINTA)
    ri = R * .66
    d.ellipse([cx - ri - S * .012, cy - ri - S * .012, cx + ri + S * .012, cy + ri + S * .012], fill=AMARELO)
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=VERDE)  # cruz branca no verde: sinal de primeiros socorros
    u = ri * .34
    d.rounded_rectangle([cx - u / 2, cy - u * 1.5, cx + u / 2, cy + u * 1.5], radius=u * .15, fill=BRANCO)
    d.rounded_rectangle([cx - u * 1.5, cy - u / 2, cx + u * 1.5, cy + u / 2], radius=u * .15, fill=BRANCO)
    f = fonte(fd, "BarlowCondensed_800ExtraBold", int(S * .062))
    rt = (R + ri) / 2
    texto_em_arco(img, "TEC.ENF TRABALHO", f, cx, cy, rt, math.radians(200), math.radians(340), BRANCO)
    f2 = fonte(fd, "BarlowCondensed_700Bold", int(S * .046))
    texto_em_arco(img, "SAÚDE · SEGURANÇA · BRIGADA", f2, cx, cy, rt - S * .012, math.radians(20), math.radians(160), AMARELO, por_baixo=True)
    for ang in (180, 0):  # estrelas-ponto separadoras
        x, y = cx + rt * math.cos(math.radians(ang)), cy + rt * math.sin(math.radians(ang))
        d.ellipse([x - S * .012, y - S * .012, x + S * .012, y + S * .012], fill=AMARELO)
    return img


def opcao_monograma(fd: Path) -> Image.Image:
    """D · Monograma "te" com a cruz no lugar do pingo, sobre tinta."""
    img = Image.new("RGB", (S, S), TINTA)
    d = ImageDraw.Draw(img)
    f = fonte(fd, "BarlowCondensed_800ExtraBold", int(S * .62))
    txt = "te"
    w = d.textlength(txt, font=f)
    bb = d.textbbox((0, 0), txt, font=f)
    x = (S - w) / 2 - S * .04
    y = (S - (bb[3] - bb[1])) / 2 - bb[1] + S * .04
    d.text((x, y), txt, font=f, fill=CLARO)
    # cruz verde à direita (cor de primeiros socorros; a cruz vermelha é emblema protegido)
    u = S * .07
    cx, cy = x + w + u * 1.2, y + bb[1] + S * .07
    d.rectangle([cx - u / 2, cy - u * 1.5, cx + u / 2, cy + u * 1.5], fill=VERDE)
    d.rectangle([cx - u * 1.5, cy - u / 2, cx + u * 1.5, cy + u / 2], fill=VERDE)
    d.rectangle([S * .2, S * .8, S * .8, S * .8 + S * .022], fill=AMARELO)
    return img


OPCOES = [
    ("A", "Escudo + cruz + batimento", opcao_escudo),
    ("B", "Capacete + batimento", opcao_capacete),
    ("C", "Selo de brigada", opcao_selo),
    ("D", "Monograma te+", opcao_monograma),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)
    prancha = Image.new("RGB", (2 * 540 + 60, 2 * 640 + 40), (232, 236, 242))
    fl = fonte(a.fontes, "BarlowCondensed_800ExtraBold", 44)
    dp = ImageDraw.Draw(prancha)
    for i, (letra, nome, fn) in enumerate(OPCOES):
        img = fn(a.fontes).resize((T, T), Image.LANCZOS)
        img.save(a.saida / f"opcao-{letra}.png")
        mini = img.resize((500, 500), Image.LANCZOS)
        mask = Image.new("L", (500, 500), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 499, 499], fill=255)  # como aparece no Instagram
        x, y = 40 + (i % 2) * 540, 30 + (i // 2) * 640
        prancha.paste(mini, (x, y), mask)
        dp.text((x, y + 520), f"{letra} · {nome}", font=fl, fill=TINTA)
    prancha.save(a.saida / "prancha-opcoes.png")


if __name__ == "__main__":
    main()
