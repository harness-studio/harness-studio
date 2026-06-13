# Runbook — continuar o dogfood no Claude Code

Estamos pós **Spec Lock**. A spec travável está em `.harness/engagements/skill-crawl/SPEC.md`.
Feature a implementar: o comando `hssd skill` (Crawl) — ver SPEC.md (24 AC).

## 0. Awareness antes de começar
- Há mudanças não commitadas no working tree (correções "erros bobos": `cli/hssd.py`, `README.md`,
  `CLI.md`, `GLOSSARY.md`, `cli/README.md`) + arquivos novos (`proposals/…`, `specs/overview.md`,
  `.harness/engagements/skill-crawl/…`). Rode `git status` / `git diff` e commite o que aprovar.
- Git LFS: os binários de `presentation/`/`assets/` podem aparecer modificados — trate à parte
  (`git lfs status`); não suba estado quebrado. Stage só o que for seu.
- Pré-requisito do gate TDD: o repo não tem testes ainda. `uv add --dev pytest` (o gate roda `uv run pytest`).

## 1. Montar o .claude/ (uma vez)
```bash
# da raiz do repo
uv tool install --editable .   # coloca `hssd` no PATH (ou use: python cli/hssd.py …)
hssd init                      # cria hssd.yaml, CLAUDE.md, e MONTA .claude/agents + skills + commands
```
`hssd init` é não-destrutivo e idempotente. É o que faz o Claude Code enxergar os subagentes e o
skill `harness-studio` (o maestro).

## 2A. Caminho recomendado — continuar o build pelo SPEC (maestro interativo)
Abra o Claude Code na pasta do repo e cole este prompt:

> Continue uma engagement do Harness Studio (dogfood). A spec travada está em
> `.harness/engagements/skill-crawl/SPEC.md` — leia. Estamos no P3, pós Spec Lock. Conduza como o
> processo governado manda (você é o maestro; maker ≠ checker):
> 1. **P3a Red** — como *test-author*: crie `tests/`, garanta pytest (`uv add --dev pytest`) e escreva
>    testes que cobrem TODOS os critérios de aceite da spec (clone a partir de um git fixture local com
>    `file://`, monkeypatch `Path.home`, limpe `GIT_CONFIG_GLOBAL/SYSTEM`). Rode `uv run pytest` e
>    confirme que FALHAM (red) antes de qualquer implementação.
> 2. **P3b Green** — implemente o `hssd skill` em `cli/hssd.py` conforme a spec (espelhe `cmd_template`;
>    adicione `SKILL_CATALOG`, o refactor `_load_catalog_file`, os helpers `_skill_*`, `cmd_skill` e o
>    subparser; o **BLOCK de colisão de nome** com skills blessed e a **restrição no `cmd_sync`**).
>    Rode `uv run pytest` até passar (green).
> 3. **P4** — rode os subagentes verificadores independentes (independent-verifier, completion-challenger,
>    test-adversary, regression-hunter) sobre o diff; conserte o que acharem (loop até secar). É feature
>    de CLI sem API/auth → pode pular o security-adversary.
> Guarde evidência em `.harness/engagements/skill-crawl/`. Me mostre o diff + a saída verde antes do merge.

## 2B. Alternativa — rodar a engine headless (terminal puro, sem Claude Code interativo)
```bash
uv add --dev pytest
hssd overview add specs/overview.md
hssd overview architect           # IA: rascunha docs/ADR.md (cole o design da nossa SPEC)
hssd architecture approve         # trava a arquitetura
hssd overview analyze && hssd overview split   # IA: plano → work items (LOC-n)
hssd sprint plan --goal "skill import (Crawl)"
hssd work list
hssd engage LOC-1 --no-security   # loop de 6 fases (--no-security: é feature de CLI)
```
Use 2B só em terminal puro/CI — NÃO dentro do Claude Code interativo (aninha `claude -p`).

## 3. Backend / auth
- Backend real (default): `HSSD_AGENT_BACKEND=claude` — precisa do `claude` logado na sua conta.
- Dry-run determinístico: `HSSD_AGENT_BACKEND=mock` (pro orquestrador, sem gastar tokens).

## 4. Quando passar verde + P4 secar
- Revise o diff, commite, e (no modelo da engine) `hssd work done <id>` / feche o sprint.
- Retro fix-the-harness: todo defeito que escapou vira um guard novo.
