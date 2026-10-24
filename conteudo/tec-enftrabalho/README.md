# @tec.enftrabalho — conteúdo para Instagram

Material do perfil @tec.enftrabalho (Enfermagem do Trabalho, Segurança do Trabalho e Bombeiro Civil).
Não faz parte da plataforma; fica aqui só para versionar os geradores.

| Arquivo | O que faz |
|---|---|
| `quiz.json` | Perguntas do Quiz 5s, com texto de tela, texto de narração e fonte normativa |
| `gerar_quiz.py` | Renderiza os Reels 1080×1920 com narração em pt-BR, contagem de 5 s e resposta. `--estilo tema` gera a versão com ilustração, cartão de pergunta e caixa verde de resposta (fundo branco) |
| `gerar_logo.py` | Gera os PNGs finais do logo (selo escolhido: perfil, transparente e horizontal) |
| `gerar_carrossel.py` | Gera os slides dos carrosséis (1080×1350, fundo branco) a partir de `carrosseis.json`, no mesmo estilo dos quizzes |
| `amostras_voz.py` | Gera a mesma frase em 4 vozes femininas Chirp 3 HD para escolher |
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

## Voz neural (Google Chirp 3 HD, pt-BR)

```bash
export GOOGLE_TTS_API_KEY=...   # chave da API Cloud Text-to-Speech; nunca vai para o repositório
python3 amostras_voz.py --saida ./amostras
python3 gerar_quiz.py --fontes ./fontes --saida ./videos --estilo tema --voz google:Vindemiatrix
```

Cada trecho fica em cache (`~/.cache/tec-enftrabalho-tts`), então refazer um vídeo não gera nova cobrança.

## Voz gravada pelo titular do perfil

`roteiro-gravacao.md` traz os 4 trechos de cada quiz em linguagem falada. Grave cada trecho em um arquivo
e nomeie `{id}-{n}.m4a` (1 pergunta, 2 alternativas, 3 resposta, 4 fechamento). Aceita m4a, mp3, wav, aac, ogg e 3gp.

```bash
python3 gerar_quiz.py --fontes ./fontes --saida ./videos --estilo tema --audios ./gravacoes
```

O gerador corta o silêncio das pontas, nivela o volume (-16 LUFS) e ajusta a duração do vídeo ao áudio.
Se faltar algum arquivo, ele lista os nomes e não gera nada.

## Voz do Gemini (chave do Google AI Studio)

```bash
export GEMINI_API_KEY=...        # chave do AI Studio; nunca vai para o repositório
python3 amostras_voz.py --saida ./amostras            # compara 4 vozes femininas
python3 gerar_quiz.py --fontes ./fontes --saida ./videos --estilo tema --voz gemini:Achernar
```

O modelo padrão é `gemini-2.5-flash-preview-tts`; para trocar, defina `GEMINI_TTS_MODEL`. A faixa grátis limita pedidos
por minuto, então o gerador espera e tenta de novo quando recebe HTTP 429. Cada trecho fica em cache.
