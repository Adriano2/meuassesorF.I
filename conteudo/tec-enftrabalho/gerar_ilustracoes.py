"""Gera as ilustrações dos carrosséis ilustrados com o Gemini (modelo de imagem), usando as referências da titular.

Uso (precisa de GEMINI_API_KEY, a chave do Google AI Studio):
    python3 gerar_ilustracoes.py --saida ./ilustracoes [--so primeiros-socorros] [--slide 3]

Referências (ficam em referencias/, fora do git porque o repositório é público):
    ref-foto.jpg        foto da titular, para manter o rosto
    ref-ilustracao.png  ilustração de estilo, para manter o traço e as cores

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
    "Semi-realistic comic-book illustration with bold clean ink outlines, vivid saturated colors, detailed shading "
    "and cinematic lighting, matching the style, line work and palette of the second reference image. "
    "The woman must look like the person in the first reference photo: same face shape, light brown hair in a high bun, "
    "light eyes, fair skin. Portrait aspect ratio 4:5. "
    "IMPORTANT: the image must contain NO text, NO letters, NO numbers, NO logos and NO captions anywhere, "
    "including on uniforms, patches, signs, screens and clipboards (leave them blank). Do not add frames or borders."
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
        "contents": [{"parts": [_parte_imagem(r) for r in refs] + [{"text": f"{ESTILO}\n\nScene: {cena}"}]}],
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
    refs = [a.refs / "ref-foto.jpg", a.refs / "ref-ilustracao.png"]
    falta = [r.name for r in refs if not r.exists()]
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
