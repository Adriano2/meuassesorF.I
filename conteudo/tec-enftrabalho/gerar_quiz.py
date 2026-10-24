"""Gera os vídeos "Quiz 5s" do @tec.enftrabalho (Reels 1080x1920, 30 fps).

Uso:
    python3 gerar_quiz.py --fontes DIR_TTF --saida DIR_MP4 [--voz mb-br3] [--fundo branco]

Requer: ffmpeg, espeak-ng com vozes MBROLA pt-BR (mbrola-br3/br4), Pillow, numpy.
DIR_TTF precisa conter BarlowCondensed_*.ttf e Barlow_*.ttf (Google Fonts, OFL).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

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


def gerar(q: dict, fontes: Fontes, voz: str, saida: Path, tmp: Path) -> float:
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

    cena = Cena(q, fontes)
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
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)
    quizzes = json.loads((Path(__file__).parent / "quiz.json").read_text(encoding="utf-8"))
    fontes = Fontes(a.fontes)
    if a.fundo == "branco":
        usar_fundo_branco()
    sufixo = "-branco" if a.fundo == "branco" else ""
    for q in quizzes:
        if a.so and q["id"] != a.so:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            dur = gerar(q, fontes, a.voz, a.saida / f"{q['id']}{sufixo}.mp4", Path(tmp))
        print(f"{q['id']}: {dur:.1f}s")


if __name__ == "__main__":
    main()
