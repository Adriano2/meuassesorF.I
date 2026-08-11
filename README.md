# meuassesorF.I

Plataforma de assessoria pessoal — finanças, agenda, tarefas e organização —
operada por um painel web e por uma equipe de agentes de IA
(Theo/diretor, Martin/finanças, Sofi/agenda, Luna/organização).

**Estado atual: Fase 1 concluída** — schema, autenticação e CRUD financeiro, com
93 testes verdes. A Fase 2 (motores de série, projeção e categorização) é a
próxima etapa.

## Documentos

| Arquivo | O que é |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Regras permanentes de trabalho no repositório. Lido automaticamente pelo Claude Code em cada sessão. |
| [`docs/ESPEC.md`](docs/ESPEC.md) | Especificação técnica completa: análise do produto de referência, arquitetura, schema SQL, motores determinísticos, contrato de API, agentes e prompts, design system, roadmap, suíte de aceite dos agentes e motor de frases (NLG). |
| [`docs/index.html`](docs/index.html) | Resumo visual navegável da especificação. Página autocontida — abre offline no navegador e é o que o GitHub Pages publica. |

Publicado em **https://adriano2.github.io/meuassesorF.I/** (depende de Pages estar
ativo: *Settings → Pages → Deploy from a branch → `claude/claude-code-platform-analysis-g8narb` / `/docs`*).

## Os dois princípios

1. **O agente não tem privilégio.** Ele é mais um cliente da API interna, com as
   mesmas validações e a mesma auditoria da interface web.
2. **Cálculo é determinístico, linguagem é probabilística.** Nenhum número
   exibido ao usuário passa por um LLM. O modelo interpreta intenção, extrai
   entidades de mídia e escolhe ferramenta — só isso.

## Stack planejada

Backend Python 3.12 + FastAPI + SQLAlchemy 2.0 + PostgreSQL 16, fila Celery +
Redis, frontend Next.js 15 + TypeScript + TailwindCSS + TanStack Query, camada de
IA com o SDK da Anthropic e tool-calling nativo. Integrações: Pluggy
(Open Finance), Google Calendar/Contacts, Asaas, S3/GCS e WhatsApp Cloud API.

## Como rodar

```bash
docker compose up -d postgres     # ou um PostgreSQL 16 local
cp .env.example .env
make instalar
make migrate
make dev                          # API em http://localhost:8000/docs
make test                         # 93 testes
make lint                         # ruff + mypy
```

A suíte de integração exige PostgreSQL de verdade — o schema usa `citext`,
arrays, enums nativos e índices parciais, e testar contra SQLite daria falso
verde. Sem banco, os testes de integração são pulados e os de motor rodam.

## Roadmap

1. ~~**Fundação** — schema, auth, CRUD financeiro~~ ✅
2. **Motores** — séries, projeção, categorização, RLS
3. **Painel** — `/painel/{mesa}` com cards prontos do servidor + NLG
4. **Open Finance** — Pluggy, staging, dedup, conciliação
5. **Agentes** — roteador, especialistas, tools, operações reversíveis, chat SSE
6. **WhatsApp** — adaptador de canal, botões, mídia
7. **Agenda, organização e billing**

Critérios de aceite de cada fase em [`docs/ESPEC.md` §8](docs/ESPEC.md).

## O que a Fase 1 entregou

| Camada | Onde | O que tem |
|---|---|---|
| Motores | `backend/app/motores/` | ciclo de fatura: competência da compra, fechamento/vencimento, distribuição de parcelas |
| Núcleo | `backend/app/core/` | centavos sem perda de resto, fuso e ancoragem de dia, erros de domínio, JWT e bcrypt |
| Dados | `backend/app/models/`, `repositories/` | 12 tabelas, `conta_id` explícito em toda query, soft delete universal |
| Regra | `backend/app/services/` | categorias, contas, cartões, faturas, transações, `registrar_operacao` em toda escrita |
| HTTP | `backend/app/api/v1/` | 19 rotas, `Idempotency-Key`, `operacao_id` em toda resposta de escrita |

Critérios de aceite, todos cobertos por teste: criar transação, categoria, conta
e cartão pela API; multi-tenancy isolado; bordas de fatura passando.

**Duas decisões tomadas aqui que não estavam na espec** — ambas documentadas no
cabeçalho de `services/financas.py`: transação `realizado` em conta bancária move
`saldo_centavos` (compra no cartão não move — quem move é o pagamento da fatura);
e cada parcela de uma compra parcelada conta na competência da sua fatura,
enquanto a compra à vista mantém a data da compra.

## Como seguir para a Fase 2

Abra uma sessão do Claude Code na raiz e peça **apenas a Fase 2**, com os testes
dos critérios de aceite escritos antes. O `CLAUDE.md` já carrega as invariantes —
não é preciso repetir nada disso no prompt.
