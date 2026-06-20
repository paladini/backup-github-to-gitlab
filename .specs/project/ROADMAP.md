# Roadmap

**Current Milestone:** M1 — Core Backup
**Status:** Complete

---

## M1 — Core Backup (v1)

**Goal:** Script funcional que clona todos os repos pessoais do GitHub e os cria/atualiza no GitLab com visibilidade correta.
**Target:** Pronto para uso assim que as tasks de M1 forem concluídas.

### Features

**Configuração & Autenticação** — COMPLETE

- Arquivo `config.yaml` com usernames GitHub/GitLab e opções
- `.env` para tokens de API (nunca commitados)
- Validação de pré-requisitos: `git` no PATH, SSH acessível a ambas as plataformas
- Suporte a nomes de usuário diferentes (GitHub: `paladini`, GitLab: `paladini` ou outro)

**Listagem de Repositórios GitHub** — COMPLETE

- Listar todos os repos pessoais autenticados (inclui privados)
- Capturar: nome, visibilidade, URL SSH, descrição, se é fork
- Filtros configuráveis: `include_forks`, `include_archived`, `--filter` por glob

**Criação de Repositórios GitLab** — COMPLETE

- Criar repo no GitLab com mesmo nome e visibilidade do GitHub
- Se repo já existe: pular criação, apenas sincronizar código
- Copiar descrição do repo
- Fail-safe: nunca criar repo público se o original for privado

**Operações Git (Clone + Push)** — COMPLETE

- Clonar repo do GitHub via SSH (bare clone: todos os branches + tags)
- Configurar remote `gitlab` no clone local
- Push de todos os branches e tags para o GitLab
- Limpeza do diretório temporário após push bem-sucedido

**CLI e Relatório** — COMPLETE

- Flags: `--dry-run`, `--filter <pattern>`, `--verbose`, `--include-forks`, `--include-archived`
- Barra de progresso com `rich`
- Relatório final: repos processados / pulados / com erro

---

## M1.5 — Issues & Wiki Backup

**Goal:** Estender o backup para cobrir wikis (repositórios git separados) e issues (com labels, milestones, comentários), opt-in via config.yaml.

### Features

**Wiki Backup** — IN PROGRESS

- Clone + push do repositório wiki (git@github.com/user/repo.wiki.git → GitLab wiki)
- Idempotente: push --mirror é incremental
- Skip silencioso quando repo não tem wiki
- Habilitado via `backup_wiki: true` em config.yaml

**Issues Migration** — IN PROGRESS

- Listar issues do GitHub (state=all, excluir PRs)
- Sync de labels e milestones antes das issues
- Criar issues no GitLab com cabeçalho de atribuição (autor original + data)
- Migrar comentários em ordem cronológica
- Idempotente via marcador `<!-- github-issue-id: N -->` no corpo
- Habilitado via `backup_issues: true` em config.yaml

**Limitações documentadas:**

- Timestamps originais não são preservados (limitação da API GitLab sem admin)
- Autorias originais não são preservadas (mesmo motivo)
- Pull Requests não são migrados

**Spec:** `.specs/features/issues-wiki-backup/`

---

## M2 — Sincronização Automática (v2)

**Goal:** Mudanças no GitHub propagam automaticamente para o GitLab sem re-executar o script manualmente.

### Features

**GitLab Pull Mirror (Premium)** — PLANNED

- Configurar pull mirror via API do GitLab por repo
- Intervalo: horário ou diário
- Documentação clara do requisito GitLab Premium para repos privados

**GitHub Actions Push Mirror (Free)** — PLANNED

- Gerar arquivo `.github/workflows/gitlab-mirror.yml` para cada repo
- Workflow faz push para GitLab em cada push ao branch principal
- Funciona sem GitLab Premium

**Cron / Task Scheduler** — PLANNED

- Instruções para agendar o script no Windows Task Scheduler
- Comando de re-sync incremental (só repos com diferenças)

---

## Considerações Futuras

- Suporte a repositórios de organizações (`--include-orgs`)
- GitLab self-hosted como destino
- ~~Backup de wikis~~ → M1.5
- Notificações por email/Slack ao completar o backup
