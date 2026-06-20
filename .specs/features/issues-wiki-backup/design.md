# Issues & Wiki Backup — Design

## Architecture Overview

O feature é implementado como uma extensão não-destrutiva do sistema existente. Nenhum arquivo existente é modificado estruturalmente — apenas novas classes/métodos são adicionados onde necessário.

```
backup.py (CLI)
    └── BackupRunner.run()
            ├── [existing] _backup_repo(repo)   ← código git (inalterado)
            ├── [new]      _backup_wiki(repo)    ← wiki git clone+push
            └── [new]      _migrate_issues(repo) ← issues API migration

src/
├── models.py           ← + IssueData, CommentData, LabelData, MilestoneData
├── config.py           ← + backup_wiki, backup_issues em Config
├── github_client.py    ← + list_issues(), list_issue_comments(), list_labels(), list_milestones()
├── gitlab_client.py    ← + create_issue(), close_issue(), list_issues_markers(),
│                            create_label(), create_milestone(), list_labels(),
│                            list_milestones(), add_issue_comment()
├── git_ops.py          ← + clone_wiki(), push_wiki()  (ou reutiliza clone/push existentes)
├── backup_runner.py    ← + _backup_wiki(), _migrate_issues(), updated run()
└── [new] issue_migrator.py  ← orquestra a migração de issues de um repo
```

## New Data Models (`src/models.py`)

```python
@dataclass
class LabelData:
    name: str
    color: str       # hex sem '#', ex: "d73a4a"
    description: str

@dataclass
class MilestoneData:
    github_number: int
    title: str
    description: str
    state: Literal["open", "closed"]
    due_date: str | None  # "YYYY-MM-DD" ou None

@dataclass
class CommentData:
    author: str
    created_at: str   # ISO 8601
    body: str

@dataclass
class IssueData:
    github_number: int
    title: str
    body: str         # pode ser None → normalizado para ""
    state: Literal["open", "closed"]
    author: str
    created_at: str   # ISO 8601
    labels: list[str]
    milestone_number: int | None
    comments: list[CommentData]
```

## Config Changes (`src/config.py` + `src/models.py`)

Adicionar ao dataclass `Config`:
```python
backup_wiki: bool = False
backup_issues: bool = False
```

Em `config.py`, ler os novos campos com `.get()` e default `False` para retrocompatibilidade.

## Wiki Backup Design

Wiki é um repositório git separado. A estratégia é idêntica ao backup de código:

```
GitHub wiki SSH URL: git@github.com:{owner}/{repo}.wiki.git
GitLab wiki SSH URL: git@gitlab.com:{owner}/{repo}.wiki.git
```

**Fluxo:**
1. Tentar `git clone --mirror {github_wiki_url}` em diretório temporário
2. Se falhar (exit code não-zero) → wiki não existe ou está vazia → pular silenciosamente
3. Configurar remote GitLab e fazer `git push --mirror`
4. Cleanup do diretório temporário

**Implementação:** `GitOps` ganha dois métodos auxiliares, ou reutiliza `clone()` e `push()` diretamente passando as URLs de wiki.

**Reutilização:** `clone()` e `push()` em `git_ops.py` já aceitam URLs SSH arbitrárias — os métodos de wiki podem chamar os mesmos métodos, apenas com URLs diferentes. Não precisamos de novos métodos se as URLs de wiki forem construídas corretamente.

**Detecção de "sem wiki":** `git clone` de um repo com wiki vazia retorna exit code não-zero com mensagem `warning: You appear to have cloned an empty repository.` ou similar. O handler existente de erro de clone já captura isso — basta interceptar e tratar como skip em vez de error.

## Issues Migration Design

### Componente: `IssueMigrator` (`src/issue_migrator.py`)

Responsável por migrar todas as issues de um único repositório. Orquestra:
1. Sync de labels
2. Sync de milestones
3. Leitura de issues GitLab existentes (para idempotência)
4. Migração de issues novas (com comentários)

```python
class IssueMigrator:
    def __init__(self, github: GithubClient, gitlab: GitlabClient, verbose: bool): ...
    
    def migrate(self, repo_name: str, gitlab_project_id: int, dry_run: bool) -> IssueMigratorResult: ...
    
    def _sync_labels(self, repo_name: str, gitlab_project_id: int) -> dict[str, int]: ...
    # returns: {label_name: gitlab_label_id}
    
    def _sync_milestones(self, repo_name: str, gitlab_project_id: int) -> dict[int, int]: ...
    # returns: {github_milestone_number: gitlab_milestone_id}
    
    def _get_migrated_ids(self, gitlab_project_id: int) -> set[int]: ...
    # returns: set of already-migrated github issue numbers
    
    def _migrate_issue(self, issue: IssueData, gitlab_project_id: int,
                       label_map: dict[str, int], milestone_map: dict[int, int]) -> None: ...
```

### Idempotência

O marcador `<!-- github-issue-id: {N} -->` é inserido ao final do corpo de cada issue migrada. Para detectar issues já migradas:

```python
def _get_migrated_ids(self, gitlab_project_id: int) -> set[int]:
    # Lista TODAS as issues do projeto GitLab (paginado)
    # Para cada uma, procura re.search(r'<!-- github-issue-id: (\d+) -->', body)
    # Retorna set dos números encontrados
```

Isso requer apenas leitura (sem escrita) e é executado uma única vez por repo antes da migração.

### Formato do corpo da issue migrada

```markdown
> 🔄 Migrado do GitHub — originalmente reportado por @{author} em {YYYY-MM-DD}

{corpo original}

<!-- github-issue-id: {N} -->
```

### Formato do comentário migrado

```markdown
> 🔄 @{author} em {YYYY-MM-DD HH:MM UTC}

{corpo original do comentário}
```

### Fluxo de migração de uma issue

```
1. Criar issue no GitLab (título + corpo formatado + labels + milestone_id)
2. Se issue.state == "closed": fechar via PUT /projects/:id/issues/:iid {state_event: "close"}
3. Para cada comentário em ordem: POST /projects/:id/issues/:iid/notes {body: ...}
```

### IssueMigratorResult

```python
@dataclass
class IssueMigratorResult:
    repo_name: str
    created: int
    skipped: int
    errors: int
```

## BackupRunner Changes

`BackupRunner.run()` chama os novos métodos após o backup de código:

```python
for repo in repos:
    result = self._backup_repo(repo)       # existing
    results.append(result)
    
    if self._config.backup_wiki:
        wiki_result = self._backup_wiki(repo)
        wiki_results.append(wiki_result)
    
    if self._config.backup_issues:
        gitlab_project = self._gitlab.get_project(repo.name)  # retorna None se não existe
        if gitlab_project is None:
            # repo não foi backupeado ainda
            log warning and skip
        else:
            issue_result = self._issue_migrator.migrate(
                repo.name, gitlab_project.id, self._config.dry_run
            )
            issue_results.append(issue_result)
```

O relatório final em `backup.py` é estendido para exibir as seções Wiki e Issues.

## GithubClient Extensions

Novos métodos:
```python
def get_wiki_ssh_url(self, repo_name: str) -> str:
    # Constrói: git@github.com:{github_username}/{repo_name}.wiki.git
    # Não faz chamada de API — só constrói a URL

def list_issues(self, repo_name: str) -> list[IssueData]:
    # GET /repos/{owner}/{repo}/issues?state=all&per_page=100 (paginado)
    # Filtra: ignora items com 'pull_request' key
    # Para cada issue, chama list_issue_comments() para buscar comentários
    # Retorna lista ordenada por issue.number ASC

def list_issue_comments(self, repo_name: str, issue_number: int) -> list[CommentData]:
    # GET /repos/{owner}/{repo}/issues/{number}/comments?per_page=100 (paginado)

def list_labels(self, repo_name: str) -> list[LabelData]:
    # GET /repos/{owner}/{repo}/labels?per_page=100 (paginado)

def list_milestones(self, repo_name: str) -> list[MilestoneData]:
    # GET /repos/{owner}/{repo}/milestones?state=all&per_page=100
```

**Rate limiting:** Os métodos novos já usam PyGithub (que tem rate-limit handler built-in via `github.RateLimitExceededException`) — o mecanismo existente em `GithubClient` cobre todos os novos métodos automaticamente.

## GitlabClient Extensions

Novos métodos:
```python
def get_project_id(self, repo_name: str) -> int | None:
    # Retorna o ID interno do projeto GitLab, ou None se não existe

def list_issues_markers(self, project_id: int) -> set[int]:
    # Lista TODAS as issues do projeto, extrai github-issue-id via regex

def list_labels(self, project_id: int) -> list[str]:
    # Retorna nomes das labels existentes

def create_label(self, project_id: int, label: LabelData) -> None:
    # POST /projects/:id/labels — skip se já existe (409 Conflict)

def list_milestones(self, project_id: int) -> dict[str, int]:
    # Retorna {title: gitlab_milestone_id}

def create_milestone(self, project_id: int, milestone: MilestoneData) -> int:
    # POST /projects/:id/milestones — retorna ID criado

def close_milestone(self, project_id: int, milestone_id: int) -> None:
    # PUT /projects/:id/milestones/:id {state_event: "close"}

def create_issue(self, project_id: int, title: str, body: str,
                  label_names: list[str], milestone_id: int | None) -> int:
    # POST /projects/:id/issues — retorna iid (internal issue id)

def close_issue(self, project_id: int, issue_iid: int) -> None:
    # PUT /projects/:id/issues/:iid {state_event: "close"}

def add_issue_comment(self, project_id: int, issue_iid: int, body: str) -> None:
    # POST /projects/:id/issues/:iid/notes
```

**Rate limiting:** Os novos métodos são decorados/wrapped pelo mecanismo existente de retry HTTP 429 em `GitlabClient`.

## Sequência completa para um repo com issues

```
1. github.list_labels(repo)          → LabelData[]
2. gitlab.list_labels(project_id)    → existing names set
3. Para cada label ausente: gitlab.create_label(...)

4. github.list_milestones(repo)      → MilestoneData[]
5. gitlab.list_milestones(project_id) → {title: id}
6. Para cada milestone ausente: gitlab.create_milestone(...) → id
   Se fechado: gitlab.close_milestone(...)
7. milestone_map = {github_number: gitlab_id}

8. gitlab.list_issues_markers(project_id) → migrated_ids set

9. github.list_issues(repo)          → IssueData[] (inclui comentários)
10. Para cada issue NÃO em migrated_ids:
    a. gitlab.create_issue(title, formatted_body, labels, milestone_id) → iid
    b. Se state=="closed": gitlab.close_issue(iid)
    c. Para cada comment: gitlab.add_issue_comment(iid, formatted_comment)
```

## Considerações de Performance

- Repos com muitas issues (>200) e comentários podem levar vários minutos por repo
- A progress bar existente (rich) deve ser atualizada para mostrar progresso dentro do repo (opcional)
- O custo de `list_issues_markers()` (listar todas as issues GitLab) cresce linearmente com re-runs — aceitável para o caso de uso de backup pessoal
- Wiki backup é muito rápido (uma operação git por repo)

## Arquivos a Criar/Modificar

| Arquivo | Ação |
|---------|------|
| `src/models.py` | Adicionar IssueData, CommentData, LabelData, MilestoneData, IssueMigratorResult |
| `src/config.py` | Adicionar backup_wiki, backup_issues a Config |
| `src/github_client.py` | Adicionar list_issues, list_issue_comments, list_labels, list_milestones, get_wiki_ssh_url |
| `src/gitlab_client.py` | Adicionar get_project_id, list_issues_markers, list_labels, create_label, list_milestones, create_milestone, close_milestone, create_issue, close_issue, add_issue_comment |
| `src/issue_migrator.py` | Criar — IssueMigrator class |
| `src/backup_runner.py` | Adicionar _backup_wiki, _migrate_issues, atualizar run() e relatório |
| `backup.py` | Atualizar relatório final para wiki/issues |
| `config.example.yaml` | Adicionar backup_wiki e backup_issues (comentados, default false) |
