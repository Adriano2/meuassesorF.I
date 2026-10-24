"""Gera os slides dos carrosséis do @tec.enftrabalho (1080 x 1350, fundo branco), no mesmo estilo dos quizzes.

Uso:
    python3 gerar_carrossel.py --fontes DIR_TTF --saida DIR_PNG [--so pcmso]

Lê carrosseis.json. Cada carrossel vira: capa, slides internos e slide final (salve + fonte).
Reaproveita pincel, ilustrações e selo de gerar_quiz.py para manter a mesma identidade dos vídeos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from gerar_quiz import (
    AMARELO, BR, CINZA, LINHA_T, NAVY, PAINEL_T, PILARES, VERDE_OK, VERM,
    Fontes, icone, pincel, quebrar,
)

W, H = 1080, 1350
IT = "BarlowCondensed_800ExtraBold_Italic"


def ajustar(f: Fontes, d: ImageDraw.ImageDraw, nome: str, txt: str, tam: int, larg: int, minimo: int = 52) -> ImageFont.FreeTypeFont:
    while tam > minimo and d.textlength(txt, font=f.get(nome, tam)) > larg:
        tam -= 4
    return f.get(nome, tam)


def cabecalho(img: Image.Image, f: Fontes, cor, pilar_nome: str, contador: str | None) -> None:
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=cor)
    sel = f.selo(88)
    img.paste(sel, (60, 48), sel)
    d.text((166, 58), "@tec.enftrabalho", font=f.get("Barlow_700Bold", 38), fill=NAVY)
    d.text((166, 102), pilar_nome.title().replace(" Do ", " do "), font=f.get("Barlow_500Medium", 25), fill=CINZA)
    if contador:
        fc = f.get("BarlowCondensed_700Bold", 34)
        w = int(d.textlength(contador, font=fc)) + 40
        d.rounded_rectangle([W - 60 - w, 62, W - 60, 114], radius=26, fill=NAVY)
        d.text((W - 60 - w + 20, 66), contador, font=fc, fill=BR)


def rodape(img: Image.Image, f: Fontes, texto_dir: str) -> None:
    d = ImageDraw.Draw(img)
    sel = f.selo(60)
    img.paste(sel, (60, H - 96), sel)
    d.text((134, H - 84), "@tec.enftrabalho", font=f.get("Barlow_700Bold", 30), fill=NAVY)
    fr = f.get("BarlowCondensed_700Bold", 32)
    d.text((W - 60 - d.textlength(texto_dir, font=fr), H - 80), texto_dir, font=fr, fill=CINZA)


def icone_escala(nome: str, cor, esc: float) -> Image.Image:
    ic = icone(nome, cor)
    return ic.resize((int(ic.width * esc), int(ic.height * esc)), Image.LANCZOS)


def sombra_cartao(img: Image.Image, caixa: tuple[int, int, int, int]) -> None:
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = caixa
    ImageDraw.Draw(sombra).rounded_rectangle([x0, y0 + 10, x1, y1 + 10], radius=36, fill=(14, 26, 43, 60))
    sombra = sombra.filter(ImageFilter.GaussianBlur(14))
    img.paste(sombra, (0, 0), sombra)


def capa(c: dict, f: Fontes, total: int) -> Image.Image:
    cor, nome = PILARES[c["pilar"]]
    img = Image.new("RGB", (W, H), BR)
    cabecalho(img, f, cor, nome, None)
    d = ImageDraw.Draw(img)
    pincel(img, 64, 236, 360, 96, VERM, -3, 3, ["GUIA RÁPIDO"], f.get(IT, 66), BR, pad=34, alt_linha=78)
    d = ImageDraw.Draw(img)
    f1 = ajustar(f, d, IT, c["linha1"], 170, 940)
    f2 = ajustar(f, d, IT, c["linha2"], 190, 940)
    y = 380
    d.text((60, y), c["linha1"], font=f1, fill=NAVY)
    y2 = y + int(f1.size * .88)
    d.text((60, y2), c["linha2"], font=f2, fill=cor)
    y_sub = y2 + int(f2.size * .95) + 24
    fs = f.get("Barlow_600SemiBold", 38)
    for i, ln in enumerate(quebrar(d, c["sub"], fs, 440)[:4]):
        d.text((62, y_sub + i * 48), ln, font=fs, fill=CINZA)
    y_ref = y_sub + 4 * 48 + 20
    pincel(img, 64, max(y_ref, 900), 280, 70, cor, -2, 9, [c["ref"].upper()], f.get(IT, 44), BR, pad=26, alt_linha=56)
    ic = icone_escala(c["icone"], cor, 1.2)
    img.paste(ic, (W - 50 - ic.width, 1230 - ic.height), ic)
    fa = f.get(IT, 46)
    wa = int(d.textlength("ARRASTE", font=fa))
    pincel(img, 64, 1120, wa + 128, 72, AMARELO, -3, 7, ["ARRASTE"], fa, NAVY, pad=30, alt_linha=58)
    d = ImageDraw.Draw(img)
    ax, ay = 64 + 30 + wa + 22, 1120 + 34  # seta desenhada (a fonte não tem "→")
    d.line([(ax, ay), (ax + 46, ay - 2)], fill=NAVY, width=7)
    d.line([(ax + 30, ay - 16), (ax + 48, ay - 2), (ax + 30, ay + 12)], fill=NAVY, width=7, joint="curve")
    rodape(img, f, f"1 / {total}")
    return img


def interno(c: dict, s: dict, n: int, total: int, f: Fontes) -> Image.Image:
    cor, nome = PILARES[c["pilar"]]
    img = Image.new("RGB", (W, H), BR)
    cabecalho(img, f, cor, nome, f"{n} / {total}")
    d = ImageDraw.Draw(img)
    alerta = bool(s.get("alerta"))
    rotulo = "ATENÇÃO" if alerta else c["ref"].upper()
    fr = f.get(IT, 44)
    wr = int(d.textlength(rotulo, font=fr)) + 64
    pincel(img, 64, 178, wr, 72, AMARELO if alerta else cor, -3, 5, [rotulo], fr, NAVY if alerta else BR, pad=30, alt_linha=56)
    d = ImageDraw.Draw(img)
    ft = ajustar(f, d, IT, s["t"], 112, 940, 64)
    d.text((60, 282), s["t"], font=ft, fill=NAVY)
    pincel(img, 64, 282 + int(ft.size * 1.0) + 8, 170, 14, cor, -1, 13)
    # cartão com os tópicos
    fi = f.get("Barlow_600SemiBold", 44)
    limite = H - 150
    escolhido = None
    for tam, lim in [(t, H - 330) for t in (54, 50, 46, 42)] + [(t, H - 150) for t in (42, 40, 38, 36)]:
        fi = f.get("Barlow_600SemiBold", tam)
        linhas = [quebrar(d, it, fi, 700) for it in s["i"]]
        alturas = [38 + len(l) * int(tam * 1.25) for l in linhas]
        total_h = sum(alturas) + 18 * (len(alturas) - 1) + 60
        if 440 + total_h <= lim:
            escolhido = True
            break
    card = (50, 440, W - 50, 440 + total_h)
    sombra_cartao(img, card)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(card, radius=36, fill=BR, outline=LINHA_T, width=3)
    y = card[1] + 30
    for lns, h in zip(linhas, alturas):
        d.rounded_rectangle([86, y, W - 86, y + h], radius=22, fill=PAINEL_T, outline=LINHA_T, width=2)
        cx, cy = 150, y + h // 2
        d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], fill=VERM if alerta else cor)
        if alerta:
            d.rounded_rectangle([cx - 4, cy - 18, cx + 4, cy + 4], radius=3, fill=BR)
            d.ellipse([cx - 5, cy + 10, cx + 5, cy + 20], fill=BR)
        else:
            d.line([(cx - 14, cy + 1), (cx - 4, cy + 12), (cx + 15, cy - 11)], fill=BR, width=8, joint="curve")
        for i, ln in enumerate(lns):
            d.text((206, y + 19 + i * int(fi.size * 1.25)), ln, font=fi, fill=NAVY)
        y += h + 18
    # ilustração pequena no espaço que sobrar
    livre = (H - 130) - (card[3] + 24)
    if livre >= 170:
        esc = min(livre / 460, 0.62)
        ic = icone_escala(c["icone"], cor, esc)
        img.paste(ic, (W - 60 - ic.width, card[3] + 24 + (livre - ic.height) // 2), ic)
    rodape(img, f, c["ref"])
    return img


def final(c: dict, f: Fontes, total: int) -> Image.Image:
    cor, nome = PILARES[c["pilar"]]
    img = Image.new("RGB", (W, H), BR)
    cabecalho(img, f, cor, nome, f"{total} / {total}")
    d = ImageDraw.Draw(img)
    pincel(img, 64, 200, 280, 90, VERM, -3, 3, ["SALVE!"], f.get(IT, 64), BR, pad=36, alt_linha=74)
    d = ImageDraw.Draw(img)
    f1 = f.get(IT, 150)
    d.text((60, 340), "Salve para", font=f1, fill=NAVY)
    d.text((60, 340 + 130), "consultar depois", font=ajustar(f, d, IT, "consultar depois", 150, 940), fill=cor)
    fs = f.get("Barlow_600SemiBold", 40)
    for i, ln in enumerate(quebrar(d, "Compartilhe com quem cuida de saúde e segurança na sua empresa.", fs, 900)):
        d.text((62, 680 + i * 52), ln, font=fs, fill=CINZA)
    # fonte
    card = (50, 840, W - 50, 1060)
    sombra_cartao(img, card)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(card, radius=36, fill=PAINEL_T, outline=LINHA_T, width=3)
    d.text((90, 872), "FONTE", font=f.get("BarlowCondensed_800ExtraBold", 38), fill=cor)
    ff = f.get("Barlow_500Medium", 34)
    for i, ln in enumerate(quebrar(d, c["fonte"], ff, 880)[:3]):
        d.text((90, 928 + i * 44), ln, font=ff, fill=NAVY)
    lin = quebrar(d, c["slogan"], f.get(IT, 46), 420)
    pincel(img, 560, 1090, 450, 44 + 54 * len(lin), VERM, -3, 11, lin, f.get(IT, 46), BR, pad=32, alt_linha=54)
    pincel(img, 64, 1110, 330, 74, AMARELO, -3, 7, ["Comente!"], f.get(IT, 50), NAVY, pad=32, alt_linha=58)
    rodape(img, f, c["ref"])
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--so")
    a = ap.parse_args()
    dados = json.loads((Path(__file__).parent / "carrosseis.json").read_text(encoding="utf-8"))
    f = Fontes(a.fontes)
    for c in dados:
        if a.so and c["id"] != a.so:
            continue
        pasta = a.saida / c["id"]
        pasta.mkdir(parents=True, exist_ok=True)
        total = len(c["slides"]) + 2
        capa(c, f, total).save(pasta / "slide-1.png")
        for i, s in enumerate(c["slides"], 2):
            interno(c, s, i, total, f).save(pasta / f"slide-{i}.png")
        final(c, f, total).save(pasta / f"slide-{total}.png")
        print(f"{c['id']}: {total} slides")


if __name__ == "__main__":
    main()
