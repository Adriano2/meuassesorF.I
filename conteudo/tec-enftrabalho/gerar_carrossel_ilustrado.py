"""Monta os carrosséis ilustrados: arte gerada pelo Gemini + títulos, balões e cartões desenhados com as fontes da marca.

Uso:
    python3 gerar_carrossel_ilustrado.py --fontes DIR_TTF --ilustracoes ./ilustracoes --saida ./carrosseis-ilustrados
    python3 gerar_carrossel_ilustrado.py ... --teste      # sem arte: usa referencias/ref-ilustracao.png em todos os slides (só para ver o layout)

A arte vem de gerar_ilustracoes.py (arte-1.png, arte-2.png ...). O texto nunca é gerado pela IA.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from gerar_quiz import AMARELO, BR, NAVY, VERDE_OK, Fontes, pincel, quebrar

AQUI = Path(__file__).parent
W, H = 1080, 1350
IT = "BarlowCondensed_800ExtraBold_Italic"
AZUL = (21, 94, 179)


# ---------------------------------------------------------------- base

def arte(caminho: Path, foco: list[float], borrar: bool = False) -> Image.Image:
    im = Image.open(caminho).convert("RGB")
    esc = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * esc) + 1, int(im.height * esc) + 1), Image.LANCZOS)
    x0 = int(min(max(foco[0] * im.width - W / 2, 0), im.width - W))
    y0 = int(min(max(foco[1] * im.height - H / 2, 0), im.height - H))
    im = im.crop((x0, y0, x0 + W, y0 + H))
    return im.filter(ImageFilter.GaussianBlur(9)) if borrar else im


def escurecer(img: Image.Image, modo: str | None) -> Image.Image:
    if not modo:
        return img
    y, x = np.mgrid[0:H, 0:W]
    a = {"topo": np.clip(1 - y / 420, 0, 1) * .72, "esquerda": np.clip(1 - x / 760, 0, 1) * .8 + np.clip(1 - y / 300, 0, 1) * .3,
         "geral": np.full((H, W), .5), "baixo": np.clip((y - 900) / 450, 0, 1) * .7}[modo]
    cam = np.zeros((H, W, 4), dtype=np.uint8)
    cam[..., :3] = (8, 16, 30)
    cam[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    base = img.convert("RGBA")
    base.alpha_composite(Image.fromarray(cam, "RGBA"))
    return base.convert("RGB")


def sombra_texto(d: ImageDraw.ImageDraw, xy: tuple[float, float], txt: str, fonte: ImageFont.FreeTypeFont, fill=BR) -> None:
    d.text((xy[0] + 3, xy[1] + 3), txt, font=fonte, fill=(0, 0, 0, 150))
    d.text(xy, txt, font=fonte, fill=fill)


def camada() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return c, ImageDraw.Draw(c)


# ---------------------------------------------------------------- pictogramas

def pict(nome: str, s: int) -> Image.Image:
    """Selo colorido com símbolo branco (usado nos cartões)."""
    k = 4
    im = Image.new("RGBA", (s * k, s * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = s * k
    c = S / 2
    if nome == "alerta":
        d.polygon([(c, S * .06), (S * .96, S * .9), (S * .04, S * .9)], fill=AMARELO)
        d.rounded_rectangle([c - S * .05, S * .36, c + S * .05, S * .64], radius=S * .03, fill=NAVY)
        d.ellipse([c - S * .06, S * .7, c + S * .06, S * .82], fill=NAVY)
        return im.resize((s, s), Image.LANCZOS)
    d.ellipse([0, 0, S - 1, S - 1], fill=VERDE_OK if nome == "check" else AZUL)
    w = max(6, S // 12)
    if nome == "check":
        d.line([(S * .27, S * .52), (S * .44, S * .68), (S * .74, S * .33)], fill=BR, width=w + 4, joint="curve")
    elif nome == "gelo":
        for ang in (0, 60, 120):
            a = math.radians(ang)
            d.line([(c - S * .28 * math.cos(a), c - S * .28 * math.sin(a)), (c + S * .28 * math.cos(a), c + S * .28 * math.sin(a))], fill=BR, width=w)
        d.ellipse([c - S * .05, c - S * .05, c + S * .05, c + S * .05], fill=BR)
    elif nome == "elevar":
        d.line([(c, S * .72), (c, S * .3)], fill=BR, width=w + 2)
        d.line([(S * .3, S * .46), (c, S * .26), (S * .7, S * .46)], fill=BR, width=w + 2, joint="curve")
    elif nome == "proibido":
        d.ellipse([S * .2, S * .2, S * .8, S * .8], outline=BR, width=w)
        d.line([(S * .3, S * .7), (S * .7, S * .3)], fill=BR, width=w)
    elif nome == "pessoas":
        for cx in (S * .36, S * .64):
            d.ellipse([cx - S * .09, S * .26, cx + S * .09, S * .44], fill=BR)
            d.pieslice([cx - S * .17, S * .5, cx + S * .17, S * .86], 180, 360, fill=BR)
    elif nome == "imobilizar":
        cam = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        dd = ImageDraw.Draw(cam)
        dd.rounded_rectangle([S * .22, S * .38, S * .78, S * .62], radius=S * .06, fill=BR)
        dd.line([(S * .5, S * .42), (S * .5, S * .58)], fill=AZUL, width=w)
        dd.line([(S * .42, S * .5), (S * .58, S * .5)], fill=AZUL, width=w)
        im.alpha_composite(cam.rotate(35, resample=Image.BICUBIC))
    return im.resize((s, s), Image.LANCZOS)


def glifo(nome: str, s: int, cor) -> Image.Image:
    """Símbolo de contorno de uma cor (barras de ícones)."""
    k = 4
    S = s * k
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = max(5, S // 14)
    c = S / 2
    if nome == "escudo":
        pts = [(c, S * .06), (S * .88, S * .22), (S * .88, S * .52), (c, S * .94), (S * .12, S * .52), (S * .12, S * .22)]
        d.line(pts + [pts[0]], fill=cor, width=w, joint="curve")
        d.line([(S * .32, S * .5), (S * .45, S * .64), (S * .68, S * .36)], fill=cor, width=w, joint="curve")
    elif nome == "coracao":
        pts = []
        for i in range(0, 361, 5):
            t = math.radians(i)
            pts.append((c + 16 * math.sin(t) ** 3 * S / 38, S * .46 - (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) * S / 38))
        d.line(pts + [pts[0]], fill=cor, width=w, joint="curve")
        d.line([(S * .2, S * .5), (S * .38, S * .5), (S * .46, S * .32), (S * .56, S * .66), (S * .64, S * .5), (S * .8, S * .5)], fill=cor, width=w - 2, joint="curve")
    elif nome == "capacete":
        d.arc([S * .16, S * .16, S * .84, S * .88], 180, 360, fill=cor, width=w)
        d.rounded_rectangle([S * .08, S * .52, S * .92, S * .68], radius=S * .06, outline=cor, width=w)
        d.line([(c, S * .18), (c, S * .5)], fill=cor, width=w)
    elif nome == "folha":
        d.polygon([(S * .2, S * .8), (S * .24, S * .36), (S * .5, S * .12), (S * .84, S * .14), (S * .8, S * .5), (S * .56, S * .82)], outline=cor, width=w)
        d.line([(S * .2, S * .82), (S * .62, S * .38)], fill=cor, width=w)
    elif nome == "pessoas_glifo":
        for cx in (S * .34, S * .66):
            d.ellipse([cx - S * .1, S * .16, cx + S * .1, S * .36], outline=cor, width=w)
            d.arc([cx - S * .2, S * .46, cx + S * .2, S * .94], 180, 360, fill=cor, width=w)
    elif nome == "prancheta":
        d.rounded_rectangle([S * .2, S * .14, S * .8, S * .92], radius=S * .06, outline=cor, width=w)
        d.rounded_rectangle([S * .36, S * .06, S * .64, S * .22], radius=S * .04, fill=cor)
        for y in (.42, .58, .74):
            d.line([(S * .32, S * y), (S * .68, S * y)], fill=cor, width=w - 2)
    return im.resize((s, s), Image.LANCZOS)


# ---------------------------------------------------------------- blocos

def cabecalho(img: Image.Image, f: Fontes, contador: str | None) -> None:
    sel = f.selo(76)
    img.paste(sel, (32, 26), sel)
    c, d = camada()
    sombra_texto(d, (122, 38), "@tec.enftrabalho", f.get("Barlow_700Bold", 36))
    img.paste(c, (0, 0), c)
    if contador:
        c, d = camada()
        fc = f.get("BarlowCondensed_700Bold", 34)
        w = int(d.textlength(contador, font=fc)) + 40
        d.rounded_rectangle([W - 36 - w, 34, W - 36, 86], radius=26, fill=(14, 26, 43, 215))
        d.text((W - 36 - w + 20, 38), contador, font=fc, fill=BR)
        img.paste(c, (0, 0), c)


def titulo_numerado(img: Image.Image, f: Fontes, n: int, texto: str) -> None:
    c, d = camada()
    ft = f.get(IT, 58)
    tw = int(d.textlength(texto, font=ft))
    x, y = 36, 120
    d.rounded_rectangle([x + 40, y + 6, x + 40 + tw + 80, y + 82], radius=38, fill=(14, 26, 43, 238))
    d.ellipse([x, y, x + 88, y + 88], fill=(14, 26, 43, 255), outline=BR, width=5)
    fn = f.get(IT, 58)
    d.text((x + 44 - d.textlength(str(n), font=fn) / 2, y + 10), str(n), font=fn, fill=BR)
    d.text((x + 110, y + 12), texto, font=ft, fill=BR)
    img.paste(c, (0, 0), c)


def balao(img: Image.Image, f: Fontes, b: dict) -> None:
    c, d = camada()
    fb = f.get("Barlow_600SemiBold", 35)
    linhas = quebrar(d, b["texto"], fb, b["w"] - 56)
    x, y, w = b["x"], b["y"], b["w"]
    h = 50 + len(linhas) * 45
    tx, ty = b["cauda"]
    bx = min(max(tx, x + 50), x + w - 50)
    if ty > y + h:  # cauda para baixo
        d.polygon([(bx - 26, y + h - 4), (bx + 26, y + h - 4), (tx, ty)], fill=(255, 255, 255, 248))
    elif ty < y:
        d.polygon([(bx - 26, y + 4), (bx + 26, y + 4), (tx, ty)], fill=(255, 255, 255, 248))
    d.rounded_rectangle([x, y, x + w, y + h], radius=30, fill=(255, 255, 255, 248))
    for i, ln in enumerate(linhas):
        d.text((x + 28, y + 24 + i * 45), ln, font=fb, fill=NAVY)
    img.paste(c, (0, 0), c)


def faixa(img: Image.Image, f: Fontes, linhas: list[str], x: int, y: int, seed: int = 4) -> None:
    fp = f.get(IT, 56)
    d = ImageDraw.Draw(img)
    w = int(max(d.textlength(ln, font=fp) for ln in linhas)) + 76
    pincel(img, x, y, w, 36 + 66 * len(linhas), AMARELO, -4, seed, linhas, fp, NAVY, pad=36, alt_linha=66)


def cartao_check(img: Image.Image, f: Fontes, c_: dict) -> None:
    c, d = camada()
    x, y, w = c_["x"], c_["y"], c_["w"]
    h = 100 + 62 * len(c_["itens"])
    d.rounded_rectangle([x, y, x + w, y + h], radius=28, fill=(255, 255, 255, 242))
    d.text((x + 30, y + 22), c_["titulo"], font=f.get("Barlow_700Bold", 40), fill=NAVY)
    fi = f.get("Barlow_600SemiBold", 36)
    for i, it in enumerate(c_["itens"]):
        yy = y + 92 + i * 62
        d.rounded_rectangle([x + 30, yy + 2, x + 66, yy + 38], radius=8, fill=VERDE_OK)
        d.line([(x + 38, yy + 21), (x + 46, yy + 30), (x + 60, yy + 10)], fill=BR, width=5, joint="curve")
        d.text((x + 84, yy), it, font=fi, fill=NAVY)
    img.paste(c, (0, 0), c)


def cartao_icones(img: Image.Image, f: Fontes, c_: dict) -> None:
    grande = c_.get("grande", False)
    tam_ic, tam_tx = (96, 42) if grande else (70, 33)
    fi = f.get("Barlow_600SemiBold", tam_tx)
    c, d = camada()
    x, y, w = c_["x"], c_["y"], c_["w"]
    linhas = [quebrar(d, t, fi, w - tam_ic - 90) for _, t in c_["itens"]]
    alt = [max(tam_ic, len(l) * int(tam_tx * 1.28)) + 34 for l in linhas]
    h = sum(alt) + 20
    d.rounded_rectangle([x, y, x + w, y + h], radius=30, fill=(255, 255, 255, 242))
    img.paste(c, (0, 0), c)
    yy = y + 10
    for (ic, _), ln, a in zip(c_["itens"], linhas, alt):
        p = pict(ic, tam_ic)
        img.paste(p, (x + 26, yy + (a - tam_ic) // 2), p)
        c, d = camada()
        top = yy + (a - len(ln) * int(tam_tx * 1.28)) // 2 + 2
        for i, t in enumerate(ln):
            d.text((x + tam_ic + 52, top + i * int(tam_tx * 1.28)), t, font=fi, fill=NAVY)
        img.paste(c, (0, 0), c)
        yy += a


def barra_texto(img: Image.Image, f: Fontes, b: dict) -> None:
    c, d = camada()
    fb = f.get("Barlow_600SemiBold", 34)
    linhas = quebrar(d, b["texto"], fb, 800)
    h = 56 + len(linhas) * 44
    y = H - 100 - h
    d.rounded_rectangle([36, y, W - 36, y + h], radius=30, fill=(14, 26, 43, 240))
    g = glifo(b["icone"], 72, BR)
    c.alpha_composite(g, (66, y + (h - 72) // 2))
    for i, ln in enumerate(linhas):
        d.text((168, y + 28 + i * 44), ln, font=fb, fill=BR)
    img.paste(c, (0, 0), c)


def barra_icones(img: Image.Image, f: Fontes, itens: list[list[str]], clara: bool) -> None:
    c, d = camada()
    y0 = H - (250 if clara else 170)
    h = 120
    d.rounded_rectangle([36, y0, W - 36, y0 + h], radius=30, fill=(255, 255, 255, 248) if clara else (14, 26, 43, 215))
    fl = f.get("Barlow_600SemiBold", 28)
    cor = NAVY if clara else BR
    col = (W - 72) / len(itens)
    for i, (ic, rot) in enumerate(itens):
        cx = 36 + col * (i + .5)
        c.alpha_composite(glifo(ic, 52, cor), (int(cx - 26), y0 + 12))
        d.text((cx - d.textlength(rot, font=fl) / 2, y0 + 74), rot, font=fl, fill=cor)
    img.paste(c, (0, 0), c)


# ---------------------------------------------------------------- slides

def montar(c: dict, s: dict, n: int, total: int, f: Fontes, caminho_arte: Path, teste: bool) -> Image.Image:
    img = arte(caminho_arte, s.get("foco", [.5, .5]), borrar=teste and s.get("escurecer") == "geral")
    img = escurecer(img, s.get("escurecer"))
    if s["tipo"] == "capa":
        c_, d = camada()
        y = 150
        for ln, tam in zip(s["titulo"], s["tamanhos"]):
            while tam > 60 and d.textlength(ln, font=f.get(IT, tam)) > W - 110:  # título longo não passa da borda
                tam -= 4
            ft = f.get(IT, tam)
            sombra_texto(d, (50, y), ln, ft)
            y += int(tam * .98)
        img.paste(c_, (0, 0), c_)
        faixa(img, f, s["pincel"], 50, y + 50)
        barra_icones(img, f, s["barra_icones"], clara=False)
        cabecalho(img, f, f"{n} / {total}")
    elif s["tipo"] == "final":
        c_, d = camada()
        tam_f = 88
        while tam_f > 56 and max(ImageDraw.Draw(img).textlength(ln, font=f.get(IT, tam_f)) for ln in s["frase"]) > 520:
            tam_f -= 4  # frase longa não passa da borda
        ft = f.get(IT, tam_f)
        txt = Image.new("RGBA", (560, 260), (0, 0, 0, 0))
        dt = ImageDraw.Draw(txt)
        for i, ln in enumerate(s["frase"]):
            dt.text((10, 10 + i * 96), ln, font=ft, fill=BR)
        txt = txt.rotate(7, resample=Image.BICUBIC, expand=True)
        img.paste(txt, (500, 300), txt)
        img.paste(c_, (0, 0), c_)
        barra_icones(img, f, s["barra_icones"], clara=True)
        c_, d = camada()
        fp = f.get("Barlow_700Bold", 34)
        tw = int(d.textlength("@tec.enftrabalho", font=fp)) + 70
        d.rounded_rectangle([(W - tw) / 2, H - 108, (W + tw) / 2, H - 44], radius=32, fill=(14, 26, 43, 235), outline=BR, width=3)
        d.text(((W - d.textlength("@tec.enftrabalho", font=fp)) / 2, H - 98), "@tec.enftrabalho", font=fp, fill=BR)
        img.paste(c_, (0, 0), c_)
        cabecalho(img, f, None)
    else:
        titulo_numerado(img, f, s["numero"], s["titulo"])
        if "cartao_check" in s:
            cartao_check(img, f, s["cartao_check"])
        if "cartao_icones" in s:
            cartao_icones(img, f, s["cartao_icones"])
        if "balao" in s:
            balao(img, f, s["balao"])
        if "pincel" in s:
            p = s["pincel"]
            faixa(img, f, p["linhas"], p["x"], p["y"], seed=n + 4)
        if "barra" in s:
            barra_texto(img, f, s["barra"])
        if "rodape_texto" in s:
            c_, d = camada()
            fr = f.get("Barlow_700Bold", 36)
            tw = int(d.textlength(s["rodape_texto"], font=fr)) + 80
            d.rounded_rectangle([(W - tw) / 2, H - 170, (W + tw) / 2, H - 100], radius=35, fill=(14, 26, 43, 240))
            d.text(((W - tw) / 2 + 40, H - 160), s["rodape_texto"], font=fr, fill=BR)
            img.paste(c_, (0, 0), c_)
        cabecalho(img, f, f"{n} / {total}")
    return img.convert("RGB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=Path, required=True)
    ap.add_argument("--ilustracoes", type=Path, default=AQUI / "ilustracoes")
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--so")
    ap.add_argument("--teste", action="store_true", help="usa referencias/ref-ilustracao.png no lugar da arte, só para ver o layout")
    a = ap.parse_args()
    f = Fontes(a.fontes)
    for c in json.loads((AQUI / "carrosseis_ilustrados.json").read_text(encoding="utf-8")):
        if a.so and c["id"] != a.so:
            continue
        pasta = a.saida / c["id"]
        pasta.mkdir(parents=True, exist_ok=True)
        total = len(c["slides"])
        faltam = [f"arte-{i}.png" for i in range(1, total + 1) if not (a.ilustracoes / c["id"] / f"arte-{i}.png").exists()]
        if faltam and not a.teste:
            raise SystemExit(f"Faltam ilustrações em {a.ilustracoes / c['id']}: {', '.join(faltam)}. Rode gerar_ilustracoes.py.")
        for i, s in enumerate(c["slides"], 1):
            caminho = a.ilustracoes / c["id"] / f"arte-{i}.png"
            if not caminho.exists():
                caminho = AQUI / "referencias" / "ref-ilustracao.png"
            montar(c, s, i, total, f, caminho, a.teste).save(pasta / f"slide-{i}.png")
        print(f"{c['id']}: {total} slides")


if __name__ == "__main__":
    main()
