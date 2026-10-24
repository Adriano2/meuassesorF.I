# @tec.enftrabalho — conteúdo para Instagram

Material do perfil @tec.enftrabalho (Enfermagem do Trabalho, Segurança do Trabalho e Bombeiro Civil).
Não faz parte da plataforma; fica aqui só para versionar os geradores.

| Arquivo | O que faz |
|---|---|
| `quiz.json` | Perguntas do Quiz 5s, com texto de tela, texto de narração e fonte normativa |
| `gerar_quiz.py` | Renderiza os Reels 1080×1920 com narração em pt-BR, contagem de 5 s e resposta |
| `gerar_logo.py` | Gera os PNGs do logo (perfil e horizontal) |
| `opcoes_logo.py` | Gera os quatro conceitos de logo e a prancha comparativa em `logo-opcoes/` |

## Dependências

```bash
apt-get install -y espeak-ng mbrola mbrola-br3 ffmpeg
pip install pillow numpy
# fontes Barlow e Barlow Condensed (OFL), por exemplo:
npm pack @expo-google-fonts/barlow @expo-google-fonts/barlow-condensed
```

## Uso

```bash
python3 gerar_quiz.py --fontes ./fontes --saida ./videos                 # fundo escuro
python3 gerar_quiz.py --fontes ./fontes --saida ./videos --fundo branco  # fundo branco
python3 gerar_quiz.py --fontes ./fontes --saida ./videos --so q01-pgr-nr1
python3 opcoes_logo.py --fontes ./fontes --saida ./logo-opcoes
```

Antes de publicar uma pergunta nova, confira a norma citada em `explicacao`.
