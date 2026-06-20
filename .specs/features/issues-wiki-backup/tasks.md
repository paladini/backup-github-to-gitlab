# Issues & Wiki Backup — Tasks

## Overview

| ID | Title | Depends | [P] | Status |
|----|-------|---------|-----|--------|
| T-IW1 | Extend models + config | — | | Planned |
| T-IW2 | Extend GithubClient (wiki + issues) | T-IW1 | | Planned |
| T-IW3 | Extend GitlabClient (wiki + issues) | T-IW1 | | Planned |
| T-IW4 | Implement IssueMigrator | T-IW2, T-IW3 | | Planned |
| T-IW5 | Extend BackupRunner + relatório | T-IW4 | | Planned |
| T-IW6 | Update config.example.yaml + docs | T-IW1 | | Planned |
| T-IW7 | Integration test + gate check | T-IW5 | | Planned |

Note: T-IW2 e T-IW3 podem ser implementadas em paralelo [P] depois que T-IW1 estiver completa.

---

## T-IW1 — Extend models + config

**What:** Adicionar novos data models e campos de configuração.

**Where:**
- `src/models.py` — adicionar `LabelData`, `MilestoneData`, `CommentData`, `IssueData`, `IssueMigratorResult`
- `src/config.py` — adicionar `backup_wiki: bool` e `backup_issues: bool` ao `Config` dataclass e ao loader

**Depends on:** —

**Reuses:** Estrutura existente de `Config` dataclass

**Done when:**
- [ ] `LabelData`, `MilestoneData`, `CommentData`, `IssueData`, `IssueMigratorResult` presentes em `models.py`
- [ ] `Config` tem `backup_wiki: bool = False` e `backup_issues: bool = False`
- [ ] `config.py` lê `backup_wiki` e `backup_issues` de `config.yaml` com `.get(..., False)` (retrocompatível)
- [ ] `python -c "from src.models import IssueData; print(IssueData)"` não lança erro

**Tests:** Nenhum teste unitário necessário para dataclasses puras. A retrocompatibilidade é verificada rodando o script com um `config.yaml` sem os novos campos.

**Gate:** `python backup.py --dry-run` ainda funciona sem os novos campos no config.yaml

---

## T-IW2 — Extend GithubClient (wiki + issues)

**What:** Adicionar métodos para buscar labels, milestones, issues (com comentários) e construir URL de wiki.

**Where:** `src/github_client.py`

**Depends on:** T-IW1 (modelos)

**Reuses:** Mecanismo de retry existente para RateLimitExceededException, padrão de paginação existente

**Novos métodos:**

```python
def get_wiki_ssh_url(self, repo_name: str) -> str:
    # Constrói git@github.com:{username}/{repo_name}.wiki.git

def list_labels(self, repo_name: str) -> list[LabelData]:
    # GET /repos/{owner}/{repo}/labels — paginado (per_page=100)

def list_milestones(self, repo_name: str) -> list[MilestoneData]:
    # GET /repos/{owner}/{repo}/milestones?state=all — paginado

def list_issue_comments(self, repo_name: str, issue_number: int) -> list[CommentData]:
    # GET /repos/{owner}/{repo}/issues/{number}/comments — paginado

def list_issues(self, repo_name: str) -> list[IssueData]:
    # GET /repos/{owner}/{repo}/issues?state=all — paginado
    # Filtra: skip items com 'pull_request' key
    # Para cada issue, chama list_issue_comments()
    # Ordena por issue.number ASC
```

**Done when:**
- [ ] Todos os 5 métodos implementados
- [ ] `list_issues` filtra PRs corretamente (item sem `pull_request` key ou com `pull_request == None`)
- [ ] `list_issues` faz paginação (while `len(page) == 100: fetch next page`)
- [ ] Comentários são buscados por issue e associados ao `IssueData.comments`
- [ ] `get_wiki_ssh_url` retorna URL correta para `repo_name="foo"` → `"git@github.com:{user}/foo.wiki.git"`

**Tests:** Verificação manual: rodar `python -c "from src.github_client import GithubClient"` sem erro de import. Teste real requer token configurado — coberto em T-IW7.

**Gate:** Imports sem erro

---

## T-IW3 — Extend GitlabClient (wiki + issues) [P com T-IW2]

**What:** Adicionar métodos para criar labels, milestones, issues, comentários e ler estado atual do projeto.

**Where:** `src/gitlab_client.py`

**Depends on:** T-IW1 (modelos)

**Reuses:** Mecanismo de retry existente para HTTP 429

**Novos métodos:**

```python
def get_project_id(self, repo_name: str) -> int | None:
    # Usa self._gl.projects.get(f"{gitlab_username}/{repo_name}")
    # Retorna project.id ou None se não encontrado

def list_issues_markers(self, project_id: int) -> set[int]:
    # Lista todas as issues do projeto (paginado, all=True)
    # Para cada issue, extrai github-issue-id via:
    #   re.search(r'<!-- github-issue-id: (\d+) -->', issue.description or "")
    # Retorna set de ints

def list_labels(self, project_id: int) -> set[str]:
    # Retorna set de nomes de labels existentes

def create_label(self, project_id: int, label: LabelData) -> None:
    # POST — skip silencioso em caso de 409 (já existe)
    # Cor deve incluir '#': f"#{label.color}"

def list_milestones(self, project_id: int) -> dict[str, int]:
    # Retorna {title: milestone_id}

def create_milestone(self, project_id: int, ms: MilestoneData) -> int:
    # POST — retorna milestone.id

def close_milestone(self, project_id: int, milestone_id: int) -> None:
    # PUT com state_event="close"

def create_issue(self, project_id: int, title: str, body: str,
                  label_names: list[str], milestone_id: int | None) -> int:
    # POST /projects/:id/issues — retorna issue.iid

def close_issue(self, project_id: int, issue_iid: int) -> None:
    # PUT /projects/:id/issues/:iid com state_event="close"

def add_issue_comment(self, project_id: int, issue_iid: int, body: str) -> None:
    # POST /projects/:id/issues/:iid/notes
```

**Done when:**
- [ ] Todos os 10 métodos implementados
- [ ] `list_issues_markers` usa paginação (`all=True` ou loop com `page`)
- [ ] `create_label` não lança exceção em caso de label duplicada
- [ ] `get_project_id` retorna `None` (não lança) para repo inexistente

**Tests:** Import test; integração em T-IW7.

**Gate:** Imports sem erro

---

## T-IW4 — Implement IssueMigrator

**What:** Criar `src/issue_migrator.py` com a classe `IssueMigrator` que orquestra a migração completa de issues de um repositório.

**Where:** `src/issue_migrator.py` (arquivo novo)

**Depends on:** T-IW2, T-IW3

**Lógica principal:**

```python
class IssueMigrator:
    def __init__(self, github: GithubClient, gitlab: GitlabClient, verbose: bool): ...

    def migrate(self, repo_name: str, project_id: int, dry_run: bool) -> IssueMigratorResult:
        # 1. Sync labels
        # 2. Sync milestones → milestone_map
        # 3. Get migrated IDs set
        # 4. List GitHub issues
        # 5. Dry run: return counts without creating
        # 6. For each issue not in migrated IDs:
        #    a. Format body
        #    b. create_issue → iid
        #    c. If closed: close_issue
        #    d. For each comment: format + add_issue_comment
        # 7. Return IssueMigratorResult

    def _format_issue_body(self, issue: IssueData) -> str:
        # > 🔄 Migrado do GitHub — originalmente reportado por @{author} em {YYYY-MM-DD}
        # 
        # {body}
        #
        # <!-- github-issue-id: {N} -->

    def _format_comment_body(self, comment: CommentData) -> str:
        # > 🔄 @{author} em {YYYY-MM-DD HH:MM UTC}
        #
        # {body}

    def _sync_labels(...) -> None: ...
    def _sync_milestones(...) -> dict[int, int]: ...
    def _get_migrated_ids(...) -> set[int]: ...
```

**Done when:**
- [ ] Arquivo `src/issue_migrator.py` criado com `IssueMigrator`
- [ ] `_format_issue_body` inclui cabeçalho + corpo + marcador `<!-- github-issue-id: N -->`
- [ ] `_format_comment_body` inclui cabeçalho de atribuição
- [ ] Labels são sincronizadas antes das issues
- [ ] Milestones são sincronizados antes das issues
- [ ] Issues já migradas são puladas (idempotência via `_get_migrated_ids`)
- [ ] Issues individuais que falham são logadas e não abortam o resto (`try/except` por issue)
- [ ] `dry_run=True` retorna contagem sem criar nada

**Tests:** Import test; integração em T-IW7.

**Gate:** `python -c "from src.issue_migrator import IssueMigrator"` sem erro

---

## T-IW5 — Extend BackupRunner + relatório

**What:** Integrar wiki backup e issue migration no `BackupRunner.run()`, e atualizar o relatório final.

**Where:** `src/backup_runner.py` e `backup.py`

**Depends on:** T-IW4

**Mudanças em `BackupRunner`:**

1. Injetar `IssueMigrator` no construtor (opcional, pode ser `None` quando issues estão desabilitadas)
2. `run()` chama `_backup_wiki(repo)` após `_backup_repo(repo)` quando `config.backup_wiki`
3. `run()` chama `_migrate_issues(repo)` quando `config.backup_issues`
4. `run()` retorna uma estrutura de resultado estendida ou usa listas separadas

**`_backup_wiki(repo: RepoInfo) -> BackupResult`:**
```python
# Constrói wiki SSH URLs (GitHub + GitLab)
# Tenta clone via git_ops.clone(wiki_github_url)
# Se falhar com WikiNotFoundError (exit != 0): return status="skip", message="no wiki"
# Push para GitLab wiki URL
# Cleanup
# Return status="success"
```

**`_migrate_issues(repo: RepoInfo) -> IssueMigratorResult | None`:**
```python
# project_id = gitlab.get_project_id(repo.name)
# if project_id is None: log warning, return None
# return issue_migrator.migrate(repo.name, project_id, config.dry_run)
```

**Relatório final em `backup.py`:**
```
Repos  : X success, Y skip, Z error
Wikis  : X success, Y skip (no wiki), Z error   ← quando backup_wiki: true
Issues : X created, Y already migrated, Z error  ← quando backup_issues: true
```

**Done when:**
- [ ] `BackupRunner.run()` chama wiki backup quando `config.backup_wiki`
- [ ] `BackupRunner.run()` chama issue migration quando `config.backup_issues`
- [ ] Wiki "not found" (clone fail) → status `"skip"`, não `"error"`
- [ ] Relatório final exibe seções Wiki/Issues apenas quando habilitados
- [ ] `--dry-run` mostra ações de wiki e counts de issues sem executar
- [ ] `backup.py` instancia `IssueMigrator` e o injeta no `BackupRunner` quando `config.backup_issues`

**Tests:** Coberto em T-IW7.

**Gate:** `python backup.py --dry-run` com `backup_wiki: false` e `backup_issues: false` no config mostra relatório original sem novas seções

---

## T-IW6 — Update config.example.yaml + docs [P com T-IW2/T-IW3]

**What:** Atualizar arquivos de documentação e exemplo de configuração.

**Where:** `config.example.yaml`, `README.md`

**Depends on:** T-IW1

**Done when:**
- [ ] `config.example.yaml` tem seção com `backup_wiki: false` e `backup_issues: false` (comentados com explicação)
- [ ] `README.md` tem seção "Issues & Wiki Backup" explicando as limitações (timestamps, autores) e como habilitar

**Gate:** `config.example.yaml` é válido YAML

---

## T-IW7 — Integration test + gate check

**What:** Verificar que o feature funciona end-to-end com um repositório de teste.

**Where:** Teste manual com token real

**Depends on:** T-IW5

**Passos de verificação:**

```bash
# 1. Habilitar features no config.yaml
#    backup_wiki: true
#    backup_issues: true

# 2. Rodar dry-run primeiro
python backup.py --dry-run --filter "test-*"
# Esperado: mostra wiki action e issue count para repos de teste

# 3. Rodar backup real com filtro
python backup.py --filter "test-*"
# Esperado: relatório com Repos/Wikis/Issues

# 4. Verificar no GitLab:
#    - Wiki do repo de teste tem conteúdo
#    - Issues aparecem com cabeçalho de atribuição
#    - Labels e milestones existem no projeto

# 5. Rodar novamente (idempotência)
python backup.py --filter "test-*"
# Esperado: Issues: 0 created, N already migrated, 0 error
#           Wiki: success (git push --mirror é idempotente)
```

**Done when:**
- [ ] dry-run mostra contagens corretas sem criar nada
- [ ] Backup real cria wiki e issues no GitLab
- [ ] Re-run não duplica issues
- [ ] Relatório final exibe as 3 seções (Repos / Wikis / Issues)
- [ ] Logs são limpos: sem stack traces para repos sem wiki

**Gate:** Todos os 5 passos acima passam sem erro

---

## Requirement Coverage

| Requirement | Task |
|-------------|------|
| WIKI-01 | T-IW5 |
| WIKI-02 | T-IW5 |
| WIKI-03 | T-IW5 |
| WIKI-04 | T-IW1 |
| WIKI-05 | T-IW5 |
| WIKI-06 | T-IW5 |
| ISS-01 | T-IW2 |
| ISS-02 | T-IW4 |
| ISS-03 | T-IW4 |
| ISS-04 | T-IW4 |
| ISS-05 | T-IW1 |
| ISS-06 | T-IW4 |
| ISS-07 | T-IW4 |
| ISS-08 | T-IW4 |
| ISS-09 | T-IW4 |
| ISS-10 | T-IW4 |
| ISS-11 | T-IW4 |
| ISS-12 | T-IW2 |
| ISS-13 | T-IW4 |
| ISS-14 | T-IW5 |
| ISS-15 | T-IW5 |
| ISS-E1 | T-IW2 (reuso) |
| ISS-E2 | T-IW3 (reuso) |
| ISS-E3 | T-IW2 |
| ISS-E5 | T-IW4 |
