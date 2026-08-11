# meuassesorF.I

Plataforma de assessoria pessoal — finanças, agenda, tarefas e organização —
operada por um painel web e por uma equipe de agentes de IA
(Theo/diretor, Martin/finanças, Sofi/agenda, Luna/organização).

**Estado atual: documentação.** Ainda não há código. A Fase 1 é a próxima etapa.

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

## Roadmap

1. **Fundação** — schema, auth, CRUD financeiro
2. **Motores** — séries, projeção, fatura, categorização, RLS
3. **Painel** — `/painel/{mesa}` com cards prontos do servidor + NLG
4. **Open Finance** — Pluggy, staging, dedup, conciliação
5. **Agentes** — roteador, especialistas, tools, operações reversíveis, chat SSE
6. **WhatsApp** — adaptador de canal, botões, mídia
7. **Agenda, organização e billing**

Critérios de aceite de cada fase em [`docs/ESPEC.md` §8](docs/ESPEC.md).

## Como começar a Fase 1

Abra uma sessão do Claude Code na raiz do repositório e peça **apenas a Fase 1**,
com os testes dos critérios de aceite escritos antes da implementação. O
`CLAUDE.md` já carrega as invariantes (dinheiro em centavos, `conta_id` em toda
query, `registrar_operacao` em toda escrita, soft delete) — não é preciso repetir
nada disso no prompt.
