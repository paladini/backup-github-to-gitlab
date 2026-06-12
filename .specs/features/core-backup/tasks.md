# Core Backup — Tasks

**Design**: `.specs/features/core-backup/design.md`
**Status**: Done

---

## Execution Plan

### Phase 1: Foundation (Sequential)

Scaffolding e models que tudo mais depende.

```
T1 → T2 → T3
```

### Phase 2: Clients & Ops (Parallel)

Três componentes independentes entre si, todos dependem apenas de T2 (models).

```
T3 complete, então:
    ├── T4 [P]  (GithubClient)
    ├── T5 [P]  (GitlabClient)
    └── T6 [P]  (GitOps)
```

### Phase 3: Orquestração & CLI (Sequential)

Integra tudo. T7 depende de T4+T5+T6. T8 depende de T7.

```
T4, T5, T6 complete, então:
T7 → T8
```

---

## Task Breakdown

### T1: Scaffolding do projeto

**What**: Criar estrutura de diretórios, arquivos de configuração de exemplo e dependências
**Where**: `backup.py`, `requirements.txt`, `config.example.yaml`, `.env.example`, `.gitignore`, `src/__init__.py`
**Depends on**: None
**Reuses**: N/A
**Requirement**: BKP-09

**Tools**:
- MCP: filesystem (Write/Edit)
- Skill: NONE

**Done when**:
- [ ] `requirements.txt` com: `PyGithub>=2.3`, `python-gitlab>=4.4`, `python-dotenv>=1.0`, `rich>=13.7`, `PyYAML>=6.0`
- [ ] `config.example.yaml` com todas as chaves documentadas e valores de exemplo
- [ ] `.env.example` com `GITHUB_TOKEN=` e `GITLAB_TOKEN=`, incluindo comentários que especificam os escopos necessários: GitHub=`repo`, GitLab=`api`
- [ ] `.gitignore` ignora: `.env`, `config.yaml`, `tmp/`, `__pycache__/`, `*.pyc`, `.venv/`
- [ ] `src/__init__.py` vazio (cria o package)
- [ ] `backup.py` vazio com `if __name__ == "__main__": pass`

**Tests**: none
**Gate**: verificação manual de arquivos

**Commit**: `chore: scaffold project structure`

---

### T2: Data models (src/models.py)

**What**: Definir os dataclasses `RepoInfo`, `BackupResult` e `Config`
**Where**: `src/models.py`
**Depends on**: T1
**Reuses**: N/A
**Requirement**: BKP-01, BKP-02, BKP-03, BKP-04

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] `RepoInfo` tem: `name`, `full_name`, `ssh_url`, `is_private`, `is_fork`, `is_archived`, `description`, `default_branch`
- [ ] `BackupResult` tem: `repo_name`, `status: Literal["success","skip","error","dry_run"]`, `message`
- [ ] `Config` tem todos os campos do design (usernames, tokens, flags, paths)
- [ ] Todos os campos têm type hints corretos
- [ ] `python -c "from src.models import RepoInfo, BackupResult, Config; print('OK')"` passa

**Tests**: none
**Gate**: `python -c "from src.models import RepoInfo, BackupResult, Config"`

**Commit**: `feat: add core data models`

---

### T3: Módulo de configuração (src/config.py)

**What**: Implementar `load_config()` e `validate_config()` que leem `config.yaml` + `.env`
**Where**: `src/config.py`
**Depends on**: T2
**Reuses**: `src/models.Config`
**Requirement**: BKP-09, BKP-10

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] `load_config(config_path, overrides)` lê YAML e aplica overrides (valores CLI têm precedência)
- [ ] `load_dotenv()` é chamado antes de ler tokens; tokens lidos de `os.environ`
- [ ] `validate_config()` lança `ConfigError` (exceção customizada) se `github_token` ou `gitlab_token` estiver vazio
- [ ] `validate_config()` lança `ConfigError` se `config.yaml` não existe, com mensagem `"Crie config.yaml a partir de config.example.yaml"`
- [ ] `python -c "from src.config import load_config, validate_config"` passa
- [ ] Teste manual: remover `.env` → rodar `validate_config` → mensagem de erro clara aparece

**Tests**: none (sem test framework definido ainda — validação manual)
**Gate**: `python -c "from src.config import load_config, validate_config"`

**Commit**: `feat: add config loading with validation`

---

### T4: GitHub client (src/github_client.py) [P]

**What**: Implementar `GithubClient` que lista repos pessoais do usuário via PyGithub
**Where**: `src/github_client.py`
**Depends on**: T3
**Reuses**: `src/models.RepoInfo`
**Requirement**: BKP-01, BKP-14, BKP-15

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] `GithubClient(token, username)` instancia sem erros
- [ ] `list_repos(include_forks, include_archived)` retorna `list[RepoInfo]`
- [ ] Repos privados são incluídos (autenticado com token)
- [ ] `include_forks=False` exclui repos onde `repo.fork == True`
- [ ] `include_archived=False` exclui repos onde `repo.archived == True`
- [ ] Cada `RepoInfo.ssh_url` usa formato `git@github.com:user/repo.git`
- [ ] `python -c "from src.github_client import GithubClient"` passa

**Tests**: none (requer token real — validação manual ou mock)
**Gate**: `python -c "from src.github_client import GithubClient"`

**Commit**: `feat: add GitHub client for listing repositories`

---

### T5: GitLab client (src/gitlab_client.py) [P]

**What**: Implementar `GitlabClient` com `repo_exists`, `create_repo` e `get_ssh_url`
**Where**: `src/gitlab_client.py`
**Depends on**: T3
**Reuses**: `src/models.RepoInfo`
**Requirement**: BKP-02, BKP-03, BKP-04, BKP-07, BKP-20

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] `GitlabClient(token, username, gitlab_url)` instancia sem erros
- [ ] `repo_exists(name)` retorna `True` se repo existe para o usuário autenticado, `False` caso contrário
- [ ] `create_repo(repo: RepoInfo)` cria repo com `visibility = "private" if repo.is_private else "public"` — sem lógica alternativa
- [ ] `create_repo()` copia `description` do repo GitHub
- [ ] `create_repo()` retorna `project.ssh_url_to_repo` da resposta da API — **não** constrói a URL localmente
- [ ] `get_ssh_url(name)` consulta a API GitLab pelo projeto e retorna `project.ssh_url_to_repo` — **não** constrói `git@gitlab.com:username/name.git`
- [ ] `python -c "from src.gitlab_client import GitlabClient"` passa

**Tests**: none (requer token real — validação manual)
**Gate**: `python -c "from src.gitlab_client import GitlabClient"`

**Commit**: `feat: add GitLab client for repo creation`

---

### T6: Operações Git (src/git_ops.py) [P]

**What**: Implementar `GitOps` com clone bare (--mirror), push (--mirror) e cleanup
**Where**: `src/git_ops.py`
**Depends on**: T3
**Reuses**: N/A (apenas subprocess + pathlib + stat)
**Requirement**: BKP-05, BKP-08, BKP-17, BKP-18

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] `GitOps(temp_dir, verbose)` cria `temp_dir` se não existir
- [ ] `clone(github_ssh_url, repo_name)` executa `git clone --mirror <url> <temp_dir>/<repo_name>.git` com `GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"` no env do subprocess
- [ ] `push(clone_path, gitlab_ssh_url)` executa `git push --mirror <gitlab_url>` com o mesmo `GIT_SSH_COMMAND`
- [ ] `cleanup(clone_path)` usa `shutil.rmtree(path, onerror=_handle_readonly)` onde `_handle_readonly` faz `os.chmod(path, stat.S_IWRITE)` antes de retentativa — necessário para Windows
- [ ] Em modo `verbose=True`, stdout/stderr do git são impressos; em False, silenciosos salvo erro
- [ ] Exceção customizada `GitOpsError` é lançada (não silenciada) em caso de exit code != 0
- [ ] `python -c "from src.git_ops import GitOps"` passa

**Tests**: none (requer git + SSH configurado — validação manual com repo de teste)
**Gate**: `python -c "from src.git_ops import GitOps"`

**Commit**: `feat: add git operations (mirror clone and push)`

---

### T7: Orquestrador BackupRunner (src/backup_runner.py)

**What**: Implementar `BackupRunner.run()` que coordena o fluxo completo para todos os repos
**Where**: `src/backup_runner.py`
**Depends on**: T4, T5, T6
**Reuses**: todos os módulos `src/`
**Requirement**: BKP-06, BKP-07, BKP-08, BKP-11, BKP-12, BKP-19

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] `BackupRunner(config, github, gitlab, git_ops)` instancia sem erros
- [ ] `run()` itera sobre `github.list_repos()` e chama `_backup_repo()` para cada um
- [ ] `_backup_repo()` fluxo: `repo_exists?` → se não: `create_repo()` → `clone()` → `push()`; se sim: `clone()` → `push()`
- [ ] `_backup_repo()` usa `try/finally`: `clone_path = None` antes do try; `cleanup(clone_path)` no finally se `clone_path is not None` — garante sem temp dirs órfãos mesmo em erros
- [ ] Quando `config.dry_run=True`, `_backup_repo()` retorna `BackupResult(status="dry_run")` sem executar nenhuma operação de escrita (o finally não chama cleanup pois clone_path permanece None)
- [ ] Erros em `_backup_repo()` são capturados no `except` e retornam `BackupResult(status="error", message=str(e))` sem propagar (script continua para o próximo repo; finally ainda executa)
- [ ] `run()` exibe barra de progresso `rich.progress.Progress` com nome do repo atual
- [ ] `run()` retorna `list[BackupResult]` completa
- [ ] `python -c "from src.backup_runner import BackupRunner"` passa

**Tests**: none (integração — validação manual com conta de teste)
**Gate**: `python -c "from src.backup_runner import BackupRunner"`

**Commit**: `feat: add BackupRunner orchestration`

---

### T8: CLI entry point e relatório final (backup.py)

**What**: Implementar `main()` com argparse, composição de dependências, chamada ao runner e relatório final
**Where**: `backup.py`
**Depends on**: T7
**Reuses**: todos os módulos `src/`, `rich.table`
**Requirement**: BKP-06, BKP-11, BKP-12, BKP-13, BKP-16

**Tools**:
- MCP: filesystem
- Skill: NONE

**Done when**:
- [ ] Args implementados: `--dry-run`, `--filter <pattern>`, `--verbose`, `--include-forks`, `--include-archived`, `--config <path>`
- [ ] `load_config()` + `validate_config()` chamados antes de qualquer operação; erros de config encerram com `sys.exit(1)` e mensagem clara
- [ ] `--filter` aplica glob com `fnmatch.fnmatch(repo.name, pattern)` antes de passar ao runner
- [ ] Relatório final usa `rich.table.Table` com colunas: `Repo`, `Status`, `Detalhes`
- [ ] Linha de rodapé: `X copiados • Y pulados • Z erros`
- [ ] `--dry-run` exibe `[DRY RUN] Nenhuma operação foi executada.` ao final
- [ ] `python backup.py --help` mostra todos os flags com descrições
- [ ] `python backup.py --dry-run` funciona sem erros (com config.yaml e .env válidos)

**Tests**: none (e2e manual)
**Gate**: `python backup.py --help`

**Commit**: `feat: add CLI entry point with report`

---

## Parallel Execution Map

```
Phase 1 (Sequential — Foundation):
  T1 ──→ T2 ──→ T3

Phase 2 (Parallel — Clients & Ops):
  T3 complete, então:
    ├── T4 [P]  GithubClient
    ├── T5 [P]  GitlabClient
    └── T6 [P]  GitOps

Phase 3 (Sequential — Integration):
  T4 + T5 + T6 complete, então:
    T7 ──→ T8
```

---

## Task Granularity Check

| Task | Scope | Status |
|------|-------|--------|
| T1: Scaffolding | Múltiplos arquivos de config | ✅ Coeso (todos são setup inicial) |
| T2: Data models | 3 dataclasses em 1 arquivo | ✅ Coeso (1 responsabilidade: models) |
| T3: Config module | 2 funções em 1 arquivo | ✅ Coeso (1 responsabilidade: config) |
| T4: GithubClient | 1 classe, 1 arquivo | ✅ Granular |
| T5: GitlabClient | 1 classe, 1 arquivo | ✅ Granular |
| T6: GitOps | 1 classe, 1 arquivo | ✅ Granular |
| T7: BackupRunner | 1 classe, 1 arquivo | ✅ Granular |
| T8: CLI + relatório | 1 entry point + argparse + rich table | ✅ Coeso (ponto de entrada único) |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
|------|-------------------|---------------|--------|
| T1 | None | T1 é início | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 [P] | T3 | T3 → T4 | ✅ Match |
| T5 [P] | T3 | T3 → T5 | ✅ Match |
| T6 [P] | T3 | T3 → T6 | ✅ Match |
| T7 | T4, T5, T6 | T4+T5+T6 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |

---

## Test Co-location Validation

Projeto greenfield sem TESTING.md definido. Todas as tasks são marcadas como `Tests: none` por consenso: o projeto não tem test framework configurado na v1 (CLIs de integração que dependem de contas reais em serviços externos têm custo de setup de mocks alto). A validação é feita manualmente com contas de teste reais.

| Task | Code Layer | Requires | Task Says | Status |
|------|------------|----------|-----------|--------|
| T2 | Data models | none | none | ✅ OK |
| T3 | Config loading | none | none | ✅ OK |
| T4 | API client | none | none | ✅ OK |
| T5 | API client | none | none | ✅ OK |
| T6 | Git subprocess | none | none | ✅ OK |
| T7 | Orchestration | none | none | ✅ OK |
| T8 | CLI entry point | none | none | ✅ OK |

> **Nota**: Para v2, considerar adicionar testes com mocks de PyGithub e python-gitlab para CI/CD.

---

## Requirement Traceability (atualizada)

| Requirement ID | Story | Tasks | Status |
|----------------|-------|-------|--------|
| BKP-01 | Listar repos GitHub autenticado | T4 | Pending |
| BKP-02 | Privado → privado (fail-safe) | T5 | Pending |
| BKP-03 | Público → público | T5 | Pending |
| BKP-04 | Visibilidade desconhecida → privado | T5 | Pending |
| BKP-05 | Push de todos branches e tags | T6 | Pending |
| BKP-06 | Relatório final | T7, T8 | Pending |
| BKP-07 | Re-exec não duplica repos | T5, T7 | Pending |
| BKP-08 | Re-exec atualizado → SKIP | T6, T7 | Pending |
| BKP-09 | Config via config.yaml + .env | T1, T3 | Pending |
| BKP-10 | Falha imediata sem token | T3, T8 | Pending |
| BKP-11 | dry-run lista sem escrever | T7, T8 | Pending |
| BKP-12 | dry-run não executa operações | T7, T8 | Pending |
| BKP-13 | --filter por glob | T8 | Pending |
| BKP-14 | include_forks configurável | T4 | Pending |
| BKP-15 | include_archived configurável | T4 | Pending |
| BKP-16 | --verbose logging detalhado | T6, T8 | Pending |
| BKP-17 | SSH StrictHostKeyChecking accept-new | T6 | Pending |
| BKP-18 | Windows rmtree lida com read-only | T6 | Pending |
| BKP-19 | Cleanup em finally (sem temp dirs órfãos) | T7 | Pending |
| BKP-20 | SSH URL lida da resposta da API GitLab | T5 | Pending |

**Coverage:** 20 total, 20 mapeados a tasks ✅
