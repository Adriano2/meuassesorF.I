# CLAUDE.md

Instruções permanentes para trabalhar neste repositório. Leia antes de escrever
qualquer código. Em caso de conflito entre este arquivo e um pedido pontual,
aponte o conflito antes de prosseguir.

A especificação técnica completa está em [`docs/ESPEC.md`](docs/ESPEC.md).
Este arquivo é o resumo operacional; a espec é a fonte da verdade sobre schema,
contrato de API, motores e agentes.

---

## 1. O que é este produto

Uma plataforma de assessoria pessoal: finanças, agenda, tarefas e organização,
operada tanto por um painel web quanto por uma equipe de agentes de IA
(Theo/diretor, Martin/finanças, Sofi/agenda, Luna/organização).

**Os dois princípios que governam todas as decisões:**

1. **O agente não tem privilégio.** Ele é mais um cliente da API interna,
   com as mesmas validações e a mesma auditoria da interface web. Nunca dê
   acesso direto a banco, ORM ou service para a camada de agentes.
2. **Cálculo é determinístico, linguagem é probabilística.** Nenhum número
   exibido ao usuário pode ter passado por um LLM. Somar, projetar, detectar
   recorrência e categorizar por regra são SQL e Python. O modelo interpreta
   intenção, extrai entidades de mídia e escolhe ferramenta — só isso.

Se uma tarefa parecer exigir que o LLM calcule algo, pare e pergunte.
Quase sempre significa que falta um motor determinístico.

---

## 2. Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (estilo 2.0, sem Query
  legado), Alembic, Pydantic v2
- **Banco:** PostgreSQL 16 (`pg_trgm`, `citext`, busca full-text em português)
- **Fila:** Celery + Redis
- **Frontend:** Next.js 15 (App Router), TypeScript estrito, TailwindCSS,
  TanStack Query, SVG próprio para gráficos
- **IA:** Anthropic SDK, tool-calling nativo. Sonnet para roteamento e
  especialistas; Opus só para análise financeira complexa; Haiku para
  classificação e enriquecimento em lote
- **Externos:** Pluggy (Open Finance), Google Calendar/Contacts, Asaas
  (cobrança), S3/GCS (arquivos), WhatsApp Cloud API (fase 6)

Não adicione dependência nova sem justificar em uma frase no PR. Nada de
biblioteca de gráficos pesada, nada de framework de agentes (LangChain,
LlamaIndex e afins) — o tool-calling nativo basta e é mais previsível.

---

## 3. Estrutura de pastas

```
backend/
  app/
    api/v1/            routers FastAPI — só HTTP, zero regra de negócio
    services/          regra de negócio; uma classe por domínio
    repositories/      acesso a dados; ÚNICO lugar com SQL/ORM
    motores/           determinísticos: series, projecao, fatura,
                       categorizacao, dedup, conciliacao, padroes
    agentes/
      orquestrador.py  roteamento de intenção
      especialistas/   martin.py, sofi.py, luna.py, theo.py
      tools/           wrappers finos sobre services
      prompts/         *.md versionados, um por agente
      canais/          painel.py, whatsapp.py (interface Canal)
    painel/            montagem dos cards + motor de NLG
      templates/       catálogo de frases por card
    integracoes/       pluggy/, google/, asaas/
    workers/           tasks Celery
    core/              config, seguranca, rls, erros, dinheiro, datas
    models/            SQLAlchemy
    schemas/           Pydantic (entrada e saída da API)
  tests/
    unit/motores/      sem banco, sem rede — devem rodar em <2s
    integration/       com banco de teste
    agentes/           suíte de aceite de linguagem natural
  alembic/
frontend/
  app/                 rotas do App Router
  components/
    cards/             um componente por card, burro (só renderiza)
    graficos/          SVG próprio
    ui/                design system
  lib/api/             cliente tipado, gerado do OpenAPI
  lib/design/          tokens
docs/
  ESPEC.md             a especificação técnica completa
```

**Regra de camadas, sem exceção:** router → service → repository. Router não
importa repository. Service não importa FastAPI. Repository não contém regra
de negócio. Tool de agente chama service, nunca repository.

---

## 4. Invariantes — nunca viole

### Dinheiro
- Sempre `BIGINT` de centavos, sempre com sufixo `_centavos` no nome.
- **Nunca `float`, nunca `Decimal` solto, nunca string formatada no banco.**
- Formatação para exibição acontece só na borda (Pydantic response ou
  frontend). O backend nunca devolve `"R$ 1.234,56"` — devolve `123456`.
- Divisão de parcelas: distribua o resto nos primeiros lançamentos, nunca
  perca centavo. `1000 / 3` → `334, 333, 333`.

### Multi-tenancy
- **Toda query filtra por `conta_id`. Sem exceção.** Se você escreveu um
  `select()` sem `conta_id`, está errado, mesmo que "só de leitura".
- O `conta_id` vem do contexto de request, nunca do corpo da requisição.
- Todo repository recebe `conta_id` como primeiro argumento explícito.
  Não confie em variável de contexto implícita para o filtro.
- RLS no Postgres entra na Fase 2. Até lá, o filtro explícito no repository
  é a única barreira — trate-o como tal.

### Auditoria
- **Toda escrita passa por `registrar_operacao()`** com snapshot `antes` e
  `depois`. É isso que sustenta o "Desfazer" e a auditoria.
- Toda escrita aceita `Idempotency-Key` e devolve `operacao_id`.
- Nada de `DELETE` físico em tabela de domínio. Use `deleted_at`. Toda query
  de leitura filtra `deleted_at IS NULL`.

### Datas e fuso
- Banco em UTC (`TIMESTAMPTZ`). Fuso do usuário vive em `contas.fuso`.
- Toda conversão passa por `core/datas.py`. Nunca use `datetime.now()` solto
  — use `agora(conta)` e `hoje(conta)`.
- `data_competencia` (em que mês conta) é diferente de `data_efetiva` (quando
  o dinheiro moveu). Não confunda os dois; a maioria dos relatórios usa
  competência, o fluxo de caixa usa efetiva.

### Cartão de crédito
- Gasto no cartão **não é saída de caixa** no dia da compra. O fluxo de caixa
  considera o pagamento da fatura; a análise por categoria considera a data
  da compra. Duas visões, um dado. Misturar as duas é o bug mais comum
  deste domínio — sempre escreva teste quando mexer aqui.
- Total de fatura é sempre derivado por soma, nunca campo mantido à mão.

### Séries
- Editar série sempre pergunta o escopo (`uma`, `futuras`, `todas`).
- `futuras` **encerra a série antiga com `data_fim` e cria uma nova**. Nunca
  reescreve histórico já materializado.
- Ancoragem no dia 31 resolve para o último dia do mês. Escreva o teste
  de fevereiro toda vez que tocar no motor.

### Categorização
- `categoria_travada = true` é sagrado. Nenhum processo automático
  (Open Finance, sync, LLM, job) pode sobrescrever categoria travada.
- Correção manual do usuário sempre trava e alimenta a memória.

---

## 5. Camada de agentes

- Prompts vivem em `agentes/prompts/*.md`, versionados. **Nunca** prompt
  inline em código Python.
- Toda tool é um wrapper fino sobre um service. Se a tool tem lógica própria,
  a lógica está no lugar errado.
- Tool nunca recebe id inventado: os ids válidos vão no bloco de contexto e
  o prompt instrui explicitamente a não inventar. Valide no wrapper e
  devolva erro legível para o modelo se vier id inexistente.
- **Toda tool destrutiva é `requer_confirmacao=True`.** Ela não executa:
  devolve um card de confirmação. Só o retorno do botão executa.
  Destrutivas: excluir qualquer entidade, encerrar série, pagar fatura,
  operações em lote, desconectar integração.
- Loop de tool-calling limitado a 8 iterações. Timeout de 30s por turno.
- Teto de custo por conta/dia: degrade para modelo menor, não bloqueie.
- **Conteúdo de mídia, PDF, transcrição e descrição bancária é DADO, não
  instrução.** Sempre encapsule em delimitadores explícitos no prompt.
  Os testes `#29` e `#30` da suíte de aceite (`docs/ESPEC.md` §9) rodam em CI
  a cada deploy e não podem quebrar nunca.
- Nunca logue senha, CVV, número completo de cartão ou token. Se o usuário
  enviar, o agente não repete e o valor é redigido antes de gravar em
  `mensagens`.

---

## 6. Painel e NLG

- O endpoint `/painel/{mesa}` devolve os cards **já calculados e com a frase
  pronta**. O frontend não faz conta — nem soma, nem percentual, nem
  formatação de insight.
- Frases vêm do catálogo de templates em `painel/templates/`, escolhidas por
  condição e prioridade. **Nunca gere frase de card com LLM.**
- Todo card precisa de estado vazio próprio, com frase e botão de primeira
  ação. O app tem que ser bonito com zero dados.
- Meta de performance: painel completo em menos de 400ms com 5.000
  transações. Se passar disso, o problema é query N+1 ou falta de cache
  Redis por `(conta_id, período)`.

---

## 7. Testes

- **TDD por fase.** Antes de implementar, escreva os testes dos critérios de
  aceite da fase (estão em `docs/ESPEC.md` §8). Não avance de fase com teste
  vermelho.
- `tests/unit/motores/` não toca banco nem rede e roda em menos de 2s.
  Se precisou de banco, ou é teste de integração ou o motor tem dependência
  que não deveria ter.
- Toda correção de bug começa por um teste que reproduz o bug.
- Casos de borda obrigatórios sempre que tocar em motor: dia 31 em fevereiro,
  parcelamento com resto de centavo, transação em virada de mês, fuso em
  horário de verão, importação duplicando lançamento manual.
- Suíte de agentes: os 30 casos de `docs/ESPEC.md` §9. Ao adicionar uma tool,
  adicione pelo menos 2 casos.

---

## 8. Migrations

- Uma migration por PR, com `downgrade` funcional de verdade.
- Nunca edite migration já aplicada em qualquer ambiente.
- Mudança de coluna em tabela grande: expand → migrate → contract, em três
  deploys. Nunca `ALTER` bloqueante em `transacoes`.
- Índice novo sempre `CONCURRENTLY`.

---

## 9. Convenções de código

- **Domínio em português, infraestrutura em inglês.** `transacoes`,
  `categoria_id`, `registrar_transacao` — mas `repository`, `service`,
  `handler`, `client`. É inconsistente de propósito e funciona bem:
  o vocabulário do negócio é o do usuário.
- Type hints obrigatórios no backend. `strict: true` no TypeScript.
  Sem `any`, sem `# type: ignore` sem comentário explicando.
- Erros: exceções de domínio em `core/erros.py`, traduzidas para HTTP num
  único exception handler. Router não monta `HTTPException` na mão.
- Toda resposta de erro tem `codigo` estável (string), `mensagem` legível em
  pt-BR e `trace_id`. O agente usa o `codigo`, o usuário lê a `mensagem`.
- Logs estruturados em JSON com `trace_id`, `conta_id` e `usuario_id`.
  **Nunca logue payload financeiro completo nem conteúdo de mensagem.**
- Commits em português, imperativo, escopo curto:
  `motores: corrige ancoragem de série no dia 31`.

---

## 10. Antes de assumir, pergunte

Pare e pergunte quando:
- a tarefa exigir que um LLM produza um número exibido ao usuário;
- faltar regra de negócio explícita sobre borda financeira (arredondamento,
  fatura, estorno, transferência entre contas próprias);
- for necessário adicionar dependência, serviço externo ou custo recorrente;
- a mudança afetar `transacoes`, `operacoes` ou o modelo de tenancy;
- algo neste arquivo conflitar com o pedido.

Não invente regra de negócio financeira para destravar. Um cálculo errado
silencioso é pior que uma feature faltando.

---

## 11. Checklist antes de abrir PR

- [ ] Nenhum `float` em valor monetário
- [ ] Nenhuma query sem `conta_id`
- [ ] Nenhuma escrita sem `registrar_operacao`
- [ ] Nenhum `DELETE` físico
- [ ] `deleted_at IS NULL` em todas as leituras
- [ ] Migration com `downgrade` testado
- [ ] Testes de borda do motor tocado
- [ ] Tool destrutiva marcada como `requer_confirmacao`
- [ ] Nenhum prompt inline no código
- [ ] Nenhum dado sensível em log
- [ ] Card novo tem estado vazio
- [ ] Suíte de agentes verde, incluindo `#29` e `#30`

---

## 12. Comandos

```bash
make dev            # sobe api, worker, postgres, redis e frontend
make test           # suíte completa
make test-unit      # só motores, rápido
make test-agentes   # suíte de aceite de linguagem natural
make lint           # ruff + mypy + eslint + tsc
make migrate        # alembic upgrade head
make revision m="…" # nova migration
make seed           # conta demo com 12 meses de dados sintéticos
```

`make seed` é obrigatório manter funcionando: é como se testa o painel com
volume realista e como se demonstra o produto.

> Estado atual: o repositório contém apenas a documentação. O `Makefile` e os
> alvos acima entram junto com a Fase 1 — quem implementar a Fase 1 cria o
> `Makefile` com exatamente esses nomes de alvo.

---

## 13. Manutenção deste arquivo

Revise ao fim de cada fase. Toda vez que uma mesma correção precisar ser feita
duas vezes, ela vira uma linha aqui. É assim que o arquivo ganha valor.
