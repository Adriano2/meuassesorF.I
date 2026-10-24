"""Gera as ilustrações dos carrosséis ilustrados com o Gemini (modelo de imagem), usando as referências da titular.

Uso (precisa de GEMINI_API_KEY, a chave do Google AI Studio):
    python3 gerar_ilustracoes.py --saida ./ilustracoes [--so primeiros-socorros] [--slide 3]

Referências (ficam em referencias/, fora do git porque o repositório é público):
    ref-foto.jpg            foto da titular, para manter o rosto
    ref-estilo-rosto.png    quadro de capa da série aprovada (rosto e traço)
    ref-estilo.png          quadro de cena da série aprovada (cenário, cores, enquadramento)

As imagens saem SEM texto: títulos, balões e cartões são desenhados depois por gerar_carrossel_ilustrado.py,
com as fontes da marca, para não haver erro de português dentro da arte.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).parent
ESTILO = (
    "Semi-realistic digital comic illustration with professional finish: clean defined ink outlines, cinematic lighting, "
    "detailed shading, rich realistic professional environments with coherent workers and equipment. "
    "Match exactly the art style, line work, rendering and color palette of the style reference images "
    "(predominantly navy blue, yellow, white, and green for health and prevention elements). "
    "PROTAGONIST (must be recognizable and identical in every image): she must look like the woman in the photo reference "
    "(image 1), which has priority over the faces in the style references. A Brazilian woman in her late twenties with a "
    "full, rounded face and soft cheeks, fair skin with a warm rosy blush, thick, well-defined arched dark brown eyebrows, "
    "green-gray almond eyes with defined lashes, full lips, small pearl stud earrings, light brown hair with ash-blonde "
    "highlights pulled into a loose high bun with soft loose strands framing the face, and a curvy, fuller figure. "
    "Do not slim her face or body and do not make her look like a generic model. Default outfit: white short-sleeved "
    "nursing uniform with a small plain green cross patch, stethoscope. Keep her face, hair and proportions consistent. "
"Correct anatomy (hands with five fingers), correct and realistic safety equipment. "
    "Vertical 4:5 single image, one scene only (never a grid, comic page or multiple panels). "
    "IMPORTANT: NO text, NO letters, NO numbers, NO logos, NO speech bubbles and NO captions anywhere in the image, "
    "including uniforms, patches, signs, screens, labels and clipboards: leave them blank. Titles and dialogue are added "
    "later by the designer, so keep the empty areas described in the scene clean. No frames or borders."
)


def _parte_imagem(caminho: Path) -> dict:
    mime = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(caminho.read_bytes()).decode()}}


def gerar_imagem(cena: str, refs: list[Path], destino: Path) -> None:
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise SystemExit("Defina GEMINI_API_KEY (chave do Google AI Studio).")
    modelo = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    corpo = {
        "contents": [{"parts": [_parte_imagem(r) for r in refs] + [{"text": f"Image 1 is the photo reference of the protagonist. All the other images are approved artworks of the same series: copy their style and their version of the protagonist, but ignore any text in them.\n{ESTILO}\n\nScene: {cena}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "4:5"}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": chave},
    )
    for tentativa in range(4):  # a faixa grátis limita pedidos por minuto
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                resp = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and tentativa < 3:
                time.sleep(25 * (tentativa + 1))
                continue
            raise SystemExit(f"Gemini recusou o pedido (HTTP {e.code}): {e.read().decode()[:400]}")
    for parte in resp.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        dados = parte.get("inlineData") or parte.get("inline_data")
        if dados:
            destino.write_bytes(base64.b64decode(dados["data"]))
            return
    raise SystemExit(f"Resposta sem imagem (pode ter sido bloqueada): {json.dumps(resp)[:400]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--refs", type=Path, default=AQUI / "referencias")
    ap.add_argument("--so", help="gera só este carrossel")
    ap.add_argument("--slide", type=int, help="gera só este slide (1, 2, ...)")
    a = ap.parse_args()
    refs = [a.refs / "ref-foto.jpg", a.refs / "ref-estilo-rosto.png", a.refs / "ref-estilo.png"]
    extras = sorted(a.refs.glob("ref-extra-*"))[:2]  # outras artes aprovadas da série (mais referência de rosto e traço)
    falta = [r.name for r in refs if not r.exists()]
    refs += extras
    if falta:
        raise SystemExit(f"Faltam as referências em {a.refs}: {', '.join(falta)}")
    for c in json.loads((AQUI / "carrosseis_ilustrados.json").read_text(encoding="utf-8")):
        if a.so and c["id"] != a.so:
            continue
        pasta = a.saida / c["id"]
        pasta.mkdir(parents=True, exist_ok=True)
        for n, s in enumerate(c["slides"], 1):
            if a.slide and n != a.slide:
                continue
            destino = pasta / f"arte-{n}.png"
            marca = pasta / f".arte-{n}.sha"
            h = hashlib.sha1(s["cena"].encode()).hexdigest()
            if destino.exists() and marca.exists() and marca.read_text() == h:
                print(f"{c['id']} slide {n}: já gerado")
                continue
            gerar_imagem(s["cena"], refs, destino)
            marca.write_text(h)
            print(f"{c['id']} slide {n}: ok")


if __name__ == "__main__":
    main()
