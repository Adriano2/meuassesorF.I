"""Gera os vídeos "Quiz 5s" do @tec.enftrabalho (Reels 1080x1920, 30 fps).

Uso:
    python3 gerar_quiz.py --fontes DIR_TTF --saida DIR_MP4 [--voz mb-br3] [--fundo branco]

Requer: ffmpeg, espeak-ng com vozes MBROLA pt-BR (mbrola-br3/br4), Pillow, numpy.
DIR_TTF precisa conter BarlowCondensed_*.ttf e Barlow_*.ttf (Google Fonts, OFL).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from opcoes_logo import opcao_selo

W, H, FPS, SR = 1080, 1920, 30, 44100

# Paleta da identidade (cores de segurança ABNT NBR 7195 sobre tinta-marinho)
TINTA = (14, 26, 43)
PAINEL = (24, 40, 62)
PAINEL_BORDA = (44, 64, 92)
BRANCO = (244, 246, 250)
NEVOA = (150, 166, 190)
AMARELO = (242, 183, 5)
VERDE_OK = (30, 158, 90)
PILARES = {
    "enfermagem": ((21, 94, 179), "ENFERMAGEM DO TRABALHO"),
    "seguranca": ((26, 128, 72), "SEGURANÇA DO TRABALHO"),
    "bombeiro": ((200, 38, 38), "BOMBEIRO CIVIL"),
}
LETRAS = "ABCD"
CAIXA_EXPL, TEXTO_EXPL = BRANCO, TINTA


def usar_fundo_branco() -> None:
    """Troca a paleta para a versão em fundo branco."""
    global TINTA, PAINEL, PAINEL_BORDA, BRANCO, NEVOA, CAIXA_EXPL, TEXTO_EXPL
    CAIXA_EXPL, TEXTO_EXPL = TINTA, (244, 246, 250)
    TINTA, PAINEL, PAINEL_BORDA = (255, 255, 255), (241, 244, 248), (213, 220, 230)
    BRANCO, NEVOA = (14, 26, 43), (91, 107, 131)


@dataclass
class Fontes:
    dir: Path

    def __post_init__(self) -> None:
        self._cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        self._selo: Image.Image | None = None

    def selo(self, tam: int) -> Image.Image:
        if self._selo is None:
            self._selo = opcao_selo(self.dir, None)
        return self._selo.resize((tam, tam), Image.LANCZOS)

    def get(self, nome: str, tam: int) -> ImageFont.FreeTypeFont:
        chave = (nome, tam)
        if chave not in self._cache:
            arq = next(self.dir.rglob(f"{nome}.ttf"))
            self._cache[chave] = ImageFont.truetype(str(arq), tam)
        return self._cache[chave]


# ---------------------------------------------------------------- áudio

def falar(texto: str, voz: str, destino: Path) -> np.ndarray:
    subprocess.run(
        ["espeak-ng", "-v", voz, "-s", "158", "-p", "45", "-w", str(destino), texto],
        check=True, capture_output=True,
    )
    with wave.open(str(destino)) as w:
        sr = w.getframerate()
        dados = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if sr != SR:
        x = np.linspace(0, len(dados), int(len(dados) * SR / sr), endpoint=False)
        dados = np.interp(x, np.arange(len(dados)), dados)
    return dados * 0.95


def tom(freqs: list[float], dur: float, vol: float = 0.35) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    onda = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
    env = np.minimum(1, t / 0.01) * np.exp(-t * (6 / dur))
    return (onda * env * vol).astype(np.float32)


def mixar(trilhas: list[tuple[float, np.ndarray]], dur: float) -> np.ndarray:
    saida = np.zeros(int(dur * SR) + SR, dtype=np.float32)
    for ini, sinal in trilhas:
        i = int(ini * SR)
        saida[i:i + len(sinal)] += sinal[: len(saida) - i]
    return np.clip(saida, -1, 1)


# ---------------------------------------------------------------- desenho

def quebrar(draw: ImageDraw.ImageDraw, texto: str, fonte, largura: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) > largura and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    linhas.append(atual)
    return linhas


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def misturar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Cena:
    def __init__(self, q: dict, f: Fontes):
        self.q, self.f = q, f
        self.cor, self.rotulo = PILARES[q["pilar"]]
        self.fundo = self._fundo()
        d = ImageDraw.Draw(self.fundo)
        self.f_perg = f.get("BarlowCondensed_700Bold", 84)
        self.linhas_perg = quebrar(d, q["pergunta"], self.f_perg, 940)
        self.y_opc = 470 + len(self.linhas_perg) * 92 + 60

    def _fundo(self) -> Image.Image:
        img = Image.new("RGB", (W, H), TINTA)
        d = ImageDraw.Draw(img)
        # faixa de pilar no topo
        d.rectangle([0, 0, W, 14], fill=self.cor)
        m = self.f.selo(110)
        img.paste(m, (64, 134), m)
        d.text((190, 148), "@tec.enftrabalho", font=self.f.get("Barlow_700Bold", 44), fill=BRANCO)
        d.text((190, 202), "Enfermagem · Segurança · Bombeiro Civil", font=self.f.get("Barlow_500Medium", 30), fill=NEVOA)
        # chip do pilar + selo QUIZ 5s
        fchip = self.f.get("BarlowCondensed_700Bold", 34)
        lw = int(d.textlength(self.rotulo, font=fchip)) + 48
        d.rounded_rectangle([70, 300, 70 + lw, 356], radius=28, fill=self.cor)
        d.text((94, 306), self.rotulo, font=fchip, fill=(255, 255, 255))
        fq = self.f.get("BarlowCondensed_800ExtraBold", 56)
        qw = int(d.textlength("QUIZ 5s", font=fq)) + 40
        d.rounded_rectangle([W - 70 - qw, 296, W - 70, 360], radius=10, fill=AMARELO)
        d.text((W - 70 - qw + 20, 297), "QUIZ 5s", font=fq, fill=(14, 26, 43))
        return img

    def quadro(self, t: float, tl: dict) -> Image.Image:
        img = self.fundo.copy()
        d = ImageDraw.Draw(img, "RGBA")
        # pergunta
        a = ease((t - 0.1) / 0.5)
        for i, ln in enumerate(self.linhas_perg):
            y = 450 + i * 92 + int((1 - a) * 30)
            d.text((70, y), ln, font=self.f_perg, fill=BRANCO + (int(255 * a),))
        # opções
        f_op = self.f.get("Barlow_600SemiBold", 52)
        f_le = self.f.get("BarlowCondensed_800ExtraBold", 54)
        rev = ease((t - tl["revela"]) / 0.35)
        for i, txt in enumerate(self.q["opcoes"]):
            ai = ease((t - tl["opcoes"] - i * 0.18) / 0.35)
            if ai <= 0:
                continue
            y = self.y_opc + i * 136 + int((1 - ai) * 40)
            certa = i == self.q["correta"]
            fundo = misturar(PAINEL, VERDE_OK, rev) if certa else PAINEL
            alpha = int(255 * ai * (1 - 0.6 * rev if not certa else 1))
            d.rounded_rectangle([70, y, W - 70, y + 116], radius=20, fill=fundo + (alpha,),
                                outline=(PAINEL_BORDA if not certa or rev < 0.5 else VERDE_OK) + (alpha,), width=3)
            acesa = certa and rev > 0.5
            cor_letra = (255, 255, 255) if acesa else (AMARELO if TINTA[0] < 128 else (176, 128, 0))
            d.ellipse([96, y + 18, 176, y + 98], fill=(VERDE_OK if acesa else TINTA) + (alpha,), outline=cor_letra + (alpha,), width=4)
            lw = d.textlength(LETRAS[i], font=f_le)
            d.text((136 - lw / 2, y + 24), LETRAS[i], font=f_le, fill=cor_letra + (alpha,))
            d.text((208, y + 26), txt, font=f_op, fill=((255, 255, 255) if acesa else BRANCO) + (alpha,))
            if certa and rev > 0:
                cx, cy = W - 140, y + 58
                d.line([(cx - 26, cy), (cx - 6, cy + 22), (cx + 30, cy - 24)], fill=(255, 255, 255, int(255 * rev)), width=12, joint="curve")
        y_base = self.y_opc + 4 * 136 + 24
        # contagem regressiva
        ini, fim = tl["conta"], tl["conta"] + 5
        if ini <= t < tl["revela"] + 0.3:
            sai = 1 - ease((t - tl["revela"]) / 0.3)
            cx, cy, r = W // 2, y_base + 112, 100
            restante = max(0.0, fim - t)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=PAINEL_BORDA + (int(255 * sai),), width=16)
            frac = restante / 5
            if frac > 0:
                d.arc([cx - r, cy - r, cx + r, cy + r], start=-90, end=-90 + 360 * frac,
                      fill=AMARELO + (int(255 * sai),), width=16)
            n = str(int(np.ceil(restante))) if restante > 0 else "0"
            fn = self.f.get("BarlowCondensed_800ExtraBold", 150)
            nw = d.textlength(n, font=fn)
            pulso = 1 - (restante % 1)
            cor_n = AMARELO if restante > 2 else (232, 72, 60)
            d.text((cx - nw / 2, cy - 98 - int(pulso * 4)), n, font=fn, fill=cor_n + (int(255 * sai),))
        elif t < ini and t >= tl["opcoes"] + 0.8:
            fv = self.f.get("BarlowCondensed_700Bold", 56)
            msg = "Você tem 5 segundos"
            mw = d.textlength(msg, font=fv)
            d.text(((W - mw) / 2, y_base + 100), msg, font=fv, fill=NEVOA)
        # explicação
        ae = ease((t - tl["revela"] - 0.3) / 0.4)
        y_fim = y_base
        if ae > 0:
            fe = self.f.get("Barlow_500Medium", 42)
            linhas = quebrar(d, self.q["explicacao"], fe, W - 220)
            alt = 92 + len(linhas) * 54
            y0 = y_base + int((1 - ae) * 30)
            d.rounded_rectangle([70, y0, W - 70, y0 + alt], radius=20, fill=CAIXA_EXPL + (int(240 * ae),))
            d.text((106, y0 + 26), "POR QUÊ", font=self.f.get("BarlowCondensed_800ExtraBold", 38), fill=(AMARELO if CAIXA_EXPL[0] < 128 else self.cor) + (int(255 * ae),))
            for i, ln in enumerate(linhas):
                d.text((106, y0 + 76 + i * 54), ln, font=fe, fill=TEXTO_EXPL + (int(255 * ae),))
            y_fim = y_base + alt
        # chamada final
        ao = ease((t - tl["outro"]) / 0.4)
        if ao > 0:
            y0 = y_fim + 28 + int((1 - ao) * 40)
            d.rounded_rectangle([70, y0, W - 70, y0 + 120], radius=60, fill=AMARELO + (int(255 * ao),))
            fo = self.f.get("BarlowCondensed_800ExtraBold", 54)
            msg = "ACERTOU? COMENTA E SEGUE!"
            mw = d.textlength(msg, font=fo)
            d.text(((W - mw) / 2, y0 + 28), msg, font=fo, fill=(14, 26, 43, int(255 * ao)))
        return img


# ---------------------------------------------------------------- estilo "tema" (fundo branco, ilustração no topo)

NAVY, BR = (14, 26, 43), (255, 255, 255)
CINZA, LINHA_T, PAINEL_T = (91, 107, 131), (213, 220, 230), (241, 244, 248)
VERM = (200, 38, 38)


def pincel(img: Image.Image, x: int, y: int, w: int, h: int, cor, graus: float, seed: int,
           linhas: list[str] | None = None, fonte: ImageFont.FreeTypeFont | None = None, cor_texto=BR,
           pad: int = 28, alt_linha: int = 0) -> None:
    """Faixa de tinta com bordas irregulares, com texto opcional, levemente inclinada."""
    rnd = random.Random(seed)
    m = 40
    camada = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    n = 16
    pts = [(m + w * i / n, m + rnd.uniform(-5, 5)) for i in range(n + 1)]
    pts += [(m + w + rnd.uniform(-6, 12), m + h * i / 4) for i in range(1, 4)]
    pts += [(m + w * i / n, m + h + rnd.uniform(-5, 5)) for i in range(n, -1, -1)]
    pts += [(m + rnd.uniform(-12, 4), m + h * i / 4) for i in range(3, 0, -1)]
    d.polygon(pts, fill=cor)
    if linhas and fonte:
        total = alt_linha * len(linhas)
        y0 = m + (h - total) / 2
        for i, ln in enumerate(linhas):
            d.text((m + pad, y0 + i * alt_linha), ln, font=fonte, fill=cor_texto)
    camada = camada.rotate(graus, resample=Image.BICUBIC, expand=True)
    img.paste(camada, (x - (camada.width - w) // 2, y - (camada.height - h) // 2), camada)


def coracao(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, cor, larg: int) -> None:
    pts = []
    for i in range(0, 361, 4):
        t = math.radians(i)
        pts.append((cx + 16 * math.sin(t) ** 3 * s,
                    cy - (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) * s))
    d.polygon(pts, fill=BR)
    d.line(pts + [pts[0]], fill=cor, width=larg, joint="curve")
    zz = [(-11, 0), (-6, 0), (-3, -7), (1, 8), (4, -3), (6, 0), (11, 0)]
    d.line([(cx + a * s * .95, cy + b * s * .95 - s) for a, b in zz], fill=cor, width=max(3, larg - 2), joint="curve")


def icone(nome: str, cor_pilar) -> Image.Image:
    """Ilustração vetorial do tema (440 x 460), desenhada em código."""
    L = Image.new("RGBA", (440, 460), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.ellipse([50, 392, 390, 446], fill=(14, 26, 43, 38))  # sombra no chão
    if nome == "kit":
        d.rounded_rectangle([140, 80, 300, 180], radius=36, outline=(92, 24, 24), width=20)
        d.rounded_rectangle([40, 140, 400, 400], radius=44, fill=VERM)
        d.rounded_rectangle([40, 140, 400, 215], radius=44, fill=(220, 62, 62))
        d.rectangle([40, 180, 400, 215], fill=(220, 62, 62))
        d.rectangle([40, 292, 400, 300], fill=(160, 28, 28))
        d.rounded_rectangle([190, 210, 250, 340], radius=8, fill=BR)
        d.rounded_rectangle([155, 245, 285, 305], radius=8, fill=BR)
        coracao(d, 345, 96, 5.0, VERM, 7)
    elif nome == "prancheta":
        d.rounded_rectangle([80, 50, 360, 410], radius=28, fill=(58, 76, 104))
        d.rounded_rectangle([108, 96, 332, 384], radius=12, fill=BR)
        d.rounded_rectangle([160, 26, 280, 94], radius=18, fill=(160, 172, 190))
        d.rounded_rectangle([188, 42, 252, 70], radius=10, fill=(58, 76, 104))
        for y in (140, 190):
            d.line([(140, y), (300, y)], fill=LINHA_T, width=10)
            d.ellipse([124, y - 12, 148, y + 12], fill=VERDE_OK)
        d.line([(130, 290), (180, 290), (200, 250), (225, 332), (248, 270), (262, 290), (310, 290)], fill=VERM, width=10, joint="curve")
        coracao(d, 350, 96, 5.0, VERM, 7)
    elif nome == "capacete":
        d.pieslice([70, 90, 370, 390], 180, 360, fill=AZUL_T)
        d.rounded_rectangle([34, 232, 406, 296], radius=30, fill=(14, 70, 140))
        d.rounded_rectangle([196, 86, 244, 240], radius=22, fill=BR)
        d.rounded_rectangle([110, 140, 150, 232], radius=18, fill=(60, 140, 220))
        d.rounded_rectangle([196, 312, 244, 330], radius=8, fill=(14, 70, 140))
    elif nome == "extintor":
        d.rounded_rectangle([130, 150, 300, 410], radius=56, fill=VERM)
        d.rounded_rectangle([200, 98, 232, 160], radius=8, fill=(40, 48, 62))
        d.rounded_rectangle([160, 74, 262, 112], radius=16, fill=(40, 48, 62))
        d.rounded_rectangle([250, 80, 350, 102], radius=11, fill=(40, 48, 62))
        d.line([(232, 130), (330, 150), (372, 230), (352, 340)], fill=NAVY, width=16, joint="curve")
        d.rounded_rectangle([158, 250, 272, 340], radius=12, fill=BR)
        d.rectangle([158, 276, 272, 292], fill=cor_pilar)
        d.polygon([(215, 300), (200, 322), (230, 322)], fill=VERM)
    elif nome == "escudo":
        pts = [(220, 40), (370, 96), (370, 226)]
        for i in range(1, 25):
            t = i / 24
            pts.append((370 - 150 * t, 226 + 176 * math.sin(t * math.pi / 2)))
        for i in range(1, 25):
            t = i / 24
            pts.append((220 - 150 * t, 402 - 176 * (1 - math.cos(t * math.pi / 2))))
        pts.append((70, 96))
        d.polygon(pts, fill=VERDE_OK)
        d.line([(150, 230), (206, 292), (300, 160)], fill=BR, width=30, joint="curve")
    return L


AZUL_T = (21, 94, 179)


class CenaTema:
    """Quiz com ilustração do tema no topo, cartão de pergunta e caixa verde de resposta (fundo branco)."""

    def __init__(self, q: dict, f: Fontes, num: int, total: int):
        self.q, self.f = q, f
        self.t = q["tema"]
        self.cor = PILARES[q["pilar"]][0]
        img = Image.new("RGB", (W, H), BR)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=self.cor)
        sel = f.selo(96)
        img.paste(sel, (60, 50), sel)
        d.text((176, 66), "@tec.enftrabalho", font=f.get("Barlow_700Bold", 40), fill=NAVY)
        d.text((176, 112), PILARES[q["pilar"]][1].title().replace(" Do ", " do "), font=f.get("Barlow_500Medium", 26), fill=CINZA)
        # título
        it = "BarlowCondensed_800ExtraBold_Italic"
        pincel(img, 64, 196, 300, 104, VERM, -3, 3, ["QUIZ"], f.get(it, 92), BR, pad=34, alt_linha=100)
        def ajustar(txt: str, tam: int, larg: int) -> ImageFont.FreeTypeFont:
            while tam > 48 and d.textlength(txt, font=f.get(it, tam)) > larg:
                tam -= 4
            return f.get(it, tam)
        f1 = ajustar(self.t["linha1"], 118, 520)
        f2 = ajustar(self.t["linha2"], 150, 520)
        d.text((60, 318), self.t["linha1"], font=f1, fill=NAVY)
        d.text((60, 318 + int(f1.size * .86)), self.t["linha2"], font=f2, fill=self.cor)
        y_sub = 318 + int(f1.size * .86) + int(f2.size * .92) + 30
        fs = f.get("Barlow_600SemiBold", 30)
        for i, ln in enumerate(quebrar(d, self.t["sub"], fs, 540)[:3]):
            d.text((62, y_sub + i * 38), ln, font=fs, fill=CINZA)
        ic = icone(self.t["icone"], self.cor)
        img.paste(ic, (610, 110), ic)
        # cartão
        fq = f.get("BarlowCondensed_700Bold", 48)
        linhas = quebrar(d, q["pergunta"], fq, 760)
        self.bar_h = 40 + len(linhas) * 56
        self.card_y = max(y_sub + 3 * 38 + 36, 650)
        self.card_y = 650 if self.card_y < 650 else self.card_y
        self.bar_y = self.card_y + 36
        self.op_y = self.bar_y + self.bar_h + 34
        self.slot_y = self.op_y + 4 * 98 + 14
        card_b = self.slot_y + 200 + 28
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).rounded_rectangle([54, self.card_y + 10, W - 54, card_b + 10], radius=36, fill=(14, 26, 43, 60))
        sombra = sombra.filter(ImageFilter.GaussianBlur(14))
        img.paste(sombra, (0, 0), sombra)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([50, self.card_y, W - 50, card_b], radius=36, fill=BR, outline=LINHA_T, width=3)
        d.rounded_rectangle([120, self.bar_y, W - 76, self.bar_y + self.bar_h], radius=26, fill=NAVY)
        for i, ln in enumerate(linhas):
            d.text((196, self.bar_y + 22 + i * 56), ln, font=fq, fill=BR)
        # número da pergunta
        pincel(img, 66, self.bar_y + self.bar_h // 2 - 52, 104, 104, VERM, 8, 5)
        d = ImageDraw.Draw(img)
        fnum = f.get("BarlowCondensed_800ExtraBold_Italic", 78)
        nw = d.textlength(str(num), font=fnum)
        d.text((118 - nw / 2, self.bar_y + self.bar_h // 2 - 50), str(num), font=fnum, fill=BR)
        self.base = img
        self.card_b = card_b
        self.tips = self._tips(f)

    def _tips(self, f: Fontes) -> Image.Image:
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        y0 = self.card_b + 22
        pincel(L, 64, y0, 330, 76, AMARELO, -3, 7, ["Lembre-se:"], f.get("BarlowCondensed_800ExtraBold_Italic", 52), NAVY, pad=30, alt_linha=60)
        d = ImageDraw.Draw(L)
        ft = f.get("BarlowCondensed_600SemiBold", 40)
        for i, tip in enumerate(self.t["dicas"]):
            y = y0 + 100 + i * 50
            d.line([(70, y + 24), (84, y + 38), (110, y + 8)], fill=VERDE_OK, width=8, joint="curve")
            d.text((128, y), tip, font=ft, fill=NAVY)
        pincel(L, 590, y0 + 30, 410, 176, VERM, -4, 11, quebrar(d, self.t["slogan"], f.get("BarlowCondensed_800ExtraBold_Italic", 44), 350),
               f.get("BarlowCondensed_800ExtraBold_Italic", 44), BR, pad=30, alt_linha=52)
        return L

    def quadro(self, t: float, tl: dict) -> Image.Image:
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        f = self.f
        f_op, f_le = f.get("Barlow_600SemiBold", 42), f.get("BarlowCondensed_800ExtraBold", 48)
        rev = ease((t - tl["revela"]) / 0.35)
        for i, txt in enumerate(self.q["opcoes"]):
            ai = ease((t - tl["opcoes"] - i * 0.18) / 0.35)
            if ai <= 0:
                continue
            y = self.op_y + i * 98 + int((1 - ai) * 36)
            certa = i == self.q["correta"]
            fundo = misturar(PAINEL_T, VERDE_OK, rev) if certa else PAINEL_T
            a = int(255 * ai * (1 - 0.55 * rev if not certa else 1))
            d.rounded_rectangle([90, y, W - 90, y + 88], radius=22, fill=fundo + (a,),
                                outline=(VERDE_OK if certa and rev > .5 else LINHA_T) + (a,), width=3)
            acesa = certa and rev > .5
            d.ellipse([108, y + 10, 176, y + 78], fill=(BR if acesa else NAVY) + (a,))
            lw = d.textlength(LETRAS[i], font=f_le)
            d.text((142 - lw / 2, y + 15), LETRAS[i], font=f_le, fill=(VERDE_OK if acesa else BR) + (a,))
            d.text((208, y + 18), txt, font=f_op, fill=(BR if acesa else NAVY) + (a,))
            if certa and rev > 0:
                cx, cy = W - 150, y + 44
                d.line([(cx - 22, cy), (cx - 5, cy + 20), (cx + 26, cy - 20)], fill=BR + (int(255 * rev),), width=11, joint="curve")
        # espaço da contagem / resposta
        sy = self.slot_y
        ini, fim = tl["conta"], tl["conta"] + 5
        if t < tl["revela"] + 0.2:
            sai = 1 - ease((t - tl["revela"]) / 0.2)
            if t < ini and t >= tl["opcoes"] + 0.8:
                fv = f.get("BarlowCondensed_700Bold", 50)
                msg = "Você tem 5 segundos"
                d.text(((W - d.textlength(msg, font=fv)) / 2, sy + 70), msg, font=fv, fill=CINZA)
            elif t >= ini:
                restante = max(0.0, fim - t)
                cx, cy, r = W // 2, sy + 100, 82
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LINHA_T + (int(255 * sai),), width=14)
                if restante > 0:
                    d.arc([cx - r, cy - r, cx + r, cy + r], start=-90, end=-90 + 360 * restante / 5, fill=AMARELO + (int(255 * sai),), width=14)
                n = str(int(np.ceil(restante))) if restante > 0 else "0"
                fn = f.get("BarlowCondensed_800ExtraBold", 120)
                cor_n = NAVY if restante > 2 else (222, 62, 52)
                d.text((cx - d.textlength(n, font=fn) / 2, cy - 78), n, font=fn, fill=cor_n + (int(255 * sai),))
        ae = ease((t - tl["revela"] - 0.2) / 0.4)
        if ae > 0:
            y0 = sy + int((1 - ae) * 24)
            al = int(255 * ae)
            d.rounded_rectangle([90, y0, W - 90, y0 + 200], radius=26, fill=VERDE_OK + (al,))
            d.ellipse([112, y0 + 54, 200, y0 + 142], fill=BR + (al,))
            d.line([(134, y0 + 100), (152, y0 + 120), (182, y0 + 78)], fill=VERDE_OK + (al,), width=11, joint="curve")
            d.text((224, y0 + 18), f"Resposta correta: {LETRAS[self.q['correta']]}", font=f.get("Barlow_700Bold", 44), fill=BR + (al,))
            fe = f.get("Barlow_500Medium", 31)
            for i, ln in enumerate(quebrar(d, self.q["explicacao"], fe, 730)[:3]):
                d.text((224, y0 + 78 + i * 38), ln, font=fe, fill=BR + (al,))
        ao = ease((t - tl["outro"]) / 0.4)
        if ao > 0:
            camada = self.tips
            if ao < 1:
                camada = camada.copy()
                camada.putalpha(camada.getchannel("A").point(lambda v: int(v * ao)))
            img.paste(camada, (0, 0), camada)
        return img



def gerar(q: dict, fontes: Fontes, voz: str, saida: Path, tmp: Path, estilo: str = "classico", num: int = 1, total: int = 1) -> float:
    letra = LETRAS[q["correta"]]
    v1 = falar(f"Quiz de cinco segundos! {q['fala_pergunta']}", voz, tmp / "v1.wav")
    v2 = falar(". ".join(f"{LETRAS[i]}: {o}" for i, o in enumerate(q["fala_opcoes"])) + ".", voz, tmp / "v2.wav")
    v3 = falar(f"Resposta certa: letra {letra}, {q['fala_opcoes'][q['correta']]}. {q['fala_explicacao']}", voz, tmp / "v3.wav")
    v4 = falar("Acertou? Comenta aí e segue o perfil para mais quizzes.", voz, tmp / "v4.wav")
    d = lambda s: len(s) / SR  # noqa: E731
    tl = {"v1": 0.3}
    tl["opcoes"] = tl["v1"] + d(v1) + 0.2
    tl["conta"] = tl["opcoes"] + d(v2) + 0.4
    tl["revela"] = tl["conta"] + 5.0
    tl["v3"] = tl["revela"] + 0.5
    tl["outro"] = tl["v3"] + d(v3) + 0.3
    dur = tl["outro"] + d(v4) + 0.9

    trilhas = [(tl["v1"], v1), (tl["opcoes"], v2), (tl["v3"], v3), (tl["outro"], v4)]
    for s in range(5):
        trilhas.append((tl["conta"] + s, tom([880], 0.14, 0.30 if s < 3 else 0.38)))
    trilhas.append((tl["revela"], tom([1046.5, 1318.5, 1568], 0.6, 0.35)))
    audio = mixar(trilhas, dur)
    wav = tmp / "mix.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())

    cena = CenaTema(q, fontes, num, total) if estilo == "tema" else Cena(q, fontes)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(saida)],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin
    for n in range(int(dur * FPS)):
        proc.stdin.write(cena.quadro(n / FPS, tl).tobytes())
    proc.stdin.close()
    proc.wait()
    # capa (quadro de pergunta com opções, antes da contagem)
    cena.quadro(tl["conta"] - 0.05, tl).save(saida.with_suffix(".jpg"), quality=90)
    return dur


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--voz", default="mb-br3")
    ap.add_argument("--so", help="gera só o quiz com este id")
    ap.add_argument("--fundo", choices=["tinta", "branco"], default="tinta")
    ap.add_argument("--estilo", choices=["classico", "tema"], default="classico",
                    help="tema: ilustração no topo, cartão de pergunta e caixa verde de resposta (sempre fundo branco)")
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)
    quizzes = json.loads((Path(__file__).parent / "quiz.json").read_text(encoding="utf-8"))
    fontes = Fontes(a.fontes)
    if a.fundo == "branco" and a.estilo == "classico":
        usar_fundo_branco()
    sufixo = "-tema" if a.estilo == "tema" else ("-branco" if a.fundo == "branco" else "")
    for num, q in enumerate(quizzes, 1):
        if a.so and q["id"] != a.so:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            dur = gerar(q, fontes, a.voz, a.saida / f"{q['id']}{sufixo}.mp4", Path(tmp), a.estilo, num, len(quizzes))
        print(f"{q['id']}: {dur:.1f}s")


if __name__ == "__main__":
    main()
