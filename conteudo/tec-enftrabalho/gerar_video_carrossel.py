"""Transforma os slides de um carrossel (1080 x 1350) em vídeo vertical para Reels (1080 x 1920), sem áudio.

Uso:
    python3 gerar_video_carrossel.py --fontes DIR_TTF --slides ./carrosseis/pcr --saida pcr.mp4 [--segundos 4]

O slide fica no centro sobre fundo azul-marinho, com o selo e o @ no topo e o progresso embaixo.
Entre um slide e outro há uma dissolvência curta.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from gerar_quiz import AMARELO, BR, Fontes

W, H, FPS = 1080, 1920, 30
TINTA = (14, 26, 43)
NEVOA = (169, 182, 202)
TRANS = 0.5  # segundos de transição


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fundo(f: Fontes, n: int) -> tuple[Image.Image, int]:
    img = Image.new("RGB", (W, H), TINTA)
    d = ImageDraw.Draw(img)
    sel = f.selo(110)
    img.paste(sel, (60, 120), sel)
    d.text((190, 136), "@tec.enftrabalho", font=f.get("Barlow_700Bold", 46), fill=BR)
    d.text((190, 192), "Enfermagem · Segurança · Bombeiro Civil", font=f.get("Barlow_500Medium", 30), fill=NEVOA)
    return img, n


def quadro(base: Image.Image, slides: list[Image.Image], t: float, seg: float, f: Fontes) -> Image.Image:
    img = base.copy()
    n = len(slides)
    i = min(int(t // seg), n - 1)
    local = t - i * seg
    y0 = (H - 1350) // 2 + 20
    atual = slides[i]
    if i > 0 and local < TRANS:  # transição do slide anterior para o atual
        a = ease(local / TRANS)
        img.paste(Image.blend(slides[i - 1], atual, a), (0, y0))
    else:
        img.paste(atual, (0, y0))
    # progresso
    d = ImageDraw.Draw(img)
    yb = y0 + 1350 + 70
    passo = 46
    x0 = (W - passo * (n - 1)) // 2
    for k in range(n):
        r = 11 if k == i else 8
        d.ellipse([x0 + k * passo - r, yb - r, x0 + k * passo + r, yb + r], fill=AMARELO if k == i else (60, 78, 104))
    msg = "Salve e compartilhe" if i == n - 1 else "Continue assistindo"
    fm = f.get("BarlowCondensed_700Bold", 40)
    d.text(((W - d.textlength(msg, font=fm)) / 2, yb + 34), msg, font=fm, fill=NEVOA)
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fontes", type=Path, required=True)
    ap.add_argument("--slides", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--segundos", type=float, default=4.0, help="tempo de cada slide")
    a = ap.parse_args()
    arquivos = sorted(a.slides.glob("slide-*.png"), key=lambda p: int(p.stem.split("-")[1]))
    if not arquivos:
        raise SystemExit(f"Nenhum slide-N.png em {a.slides}")
    f = Fontes(a.fontes)
    slides = [Image.open(p).convert("RGB").resize((1080, 1350), Image.LANCZOS) for p in arquivos]
    base, _ = fundo(f, len(slides))
    dur = a.segundos * len(slides) + 0.5
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-an",
         "-movflags", "+faststart", str(a.saida)],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin
    for k in range(int(dur * FPS)):
        proc.stdin.write(quadro(base, slides, k / FPS, a.segundos, f).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"{a.saida.name}: {len(slides)} slides, {dur:.1f}s, sem áudio")


if __name__ == "__main__":
    main()
