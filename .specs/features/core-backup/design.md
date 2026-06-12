# Core Backup — Design

**Spec**: `.specs/features/core-backup/spec.md`
**Status**: Draft

---

## Architecture Overview

O script é um CLI Python com 5 componentes independentes orquestrados por um `BackupRunner`. Cada componente tem responsabilidade única e pode ser testado isoladamente.

```
┌─────────────────────────────────────────────────────┐
│                   backup.py (CLI)                    │
│              argparse + entry point                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│               BackupRunner (orquestrador)            │
│   Para cada repo: clone → create_gitlab → push      │
└───┬───────────────┬───────────────┬─────────────────┘
    │               │               │
    ▼               ▼               ▼
┌────────┐   ┌───────────┐   ┌──────────┐
│ GitHub │   │  GitLab   │   │  GitOps  │
│ Client │   │  Client   │   │  (git)   │
└────────┘   └───────────┘   └──────────┘
    │               │               │
    │ PyGithub      │ python-gitlab  │ subprocess git
    │ API token     │ API token      │ SSH key
    ▼               ▼               ▼
 GitHub API     GitLab API     git clone/push
                               (temp dir)

┌─────────────────────────────────────────────────────┐
│              Config (carregado no início)            │
│         config.yaml + .env → dataclass Config       │
└─────────────────────────────────────────────────────┘
```

**Fluxo de execução por repo:**

```
1. GithubClient.list_repos()          → lista [RepoInfo]
2. Para cada RepoInfo:
   a. GitlabClient.repo_exists()?     → sim: ir para (d), não: ir para (b)
   b. GitlabClient.create_repo()      → cria com visibilidade correta
   c. GitOps.clone(github_ssh_url)    → bare clone em temp dir
   d. GitOps.push(gitlab_ssh_url)     → force-push todos branches+tags
   e. GitOps.cleanup()                → rm -rf temp dir
3. BackupRunner.report()              → imprime tabela de resultados
```

---

## Code Reuse Analysis

### Existing Components to Leverage

Projeto greenfield — sem código existente. Mas reutilizamos patterns de bibliotecas bem estabelecidas.

| Library | How to Use |
|---------|------------|
| `PyGithub` | `Github(token).get_user().get_repos()` para listar todos os repos |
| `python-gitlab` | `gl.projects.create({'name': ..., 'visibility': ...})` |
| `rich.progress` | `Progress()` context manager para barra de progresso |
| `python-dotenv` | `load_dotenv()` antes de `os.environ.get()` |

### Integration Points

| System | Integration Method | Token Scope Necessário |
|--------|--------------------|-----------------------|
| GitHub API | Token no header `Authorization: token ...` via PyGithub | `repo` (para listar repos privados) |
| GitLab API | Token no header `PRIVATE-TOKEN` via python-gitlab | `api` (para criar projetos) |
| Git (SSH) | Subprocess `git` com `GIT_SSH_COMMAND` configurado | SSH key registrada em ambas as plataformas |

> **Nota de setup**: O `config.example.yaml` e `.env.example` devem documentar explicitamente quais escopos criar ao gerar os tokens. Usuários frequentemente geram tokens com escopo insuficiente na primeira tentativa.

---

## Data Models

### RepoInfo

Representa um repo GitHub como retornado pela API, normalizado para uso interno.

```python
@dataclass
class RepoInfo:
    name: str           # "my-project"
    full_name: str      # "paladini/my-project"
    ssh_url: str        # "git@github.com:paladini/my-project.git"
    is_private: bool    # True = privado, False = público
    is_fork: bool       # True = é fork de outro repo
    is_archived: bool   # True = arquivado no GitHub
    description: str    # Pode ser vazio
    default_branch: str # "main" ou "master"
```

### BackupResult

Resultado do backup de um único repo.

```python
@dataclass
class BackupResult:
    repo_name: str
    status: Literal["success", "skip", "error", "dry_run"]
    message: str        # Detalhes do status
```

### Config

Configuração carregada do `config.yaml` + `.env`.

```python
@dataclass
class Config:
    github_username: str
    github_token: str        # De .env: GITHUB_TOKEN
    gitlab_username: str
    gitlab_token: str        # De .env: GITLAB_TOKEN
    gitlab_url: str          # Default: "https://gitlab.com"
    include_forks: bool      # Default: False
    include_archived: bool   # Default: True
    temp_dir: str            # Default: "./tmp"
    dry_run: bool            # Default: False
    filter_pattern: str      # Default: "*" (todos)
    verbose: bool            # Default: False
```

---

## Components

### `src/config.py` — Configuração

- **Purpose**: Carrega e valida configuração de `config.yaml` + `.env`
- **Location**: `src/config.py`
- **Interfaces**:
  - `load_config(config_path: str, overrides: dict) -> Config` — lê yaml + dotenv, aplica overrides de CLI
  - `validate_config(config: Config) -> None` — lança `ConfigError` se campos obrigatórios faltam
- **Dependencies**: `python-dotenv`, `PyYAML`
- **Reuses**: nada (foundation)

### `src/github_client.py` — GitHub API

- **Purpose**: Lista todos os repos do usuário GitHub com metadados de visibilidade
- **Location**: `src/github_client.py`
- **Interfaces**:
  - `GithubClient(token: str, username: str)`
  - `list_repos(include_forks: bool, include_archived: bool) -> list[RepoInfo]` — retorna todos os repos pessoais, respeita filtros
- **Dependencies**: `PyGithub`
- **Reuses**: `RepoInfo` dataclass de `src/models.py`
- **Notes**: Autentica com token para ver repos privados. Lida com paginação automática via PyGithub.

### `src/gitlab_client.py` — GitLab API

- **Purpose**: Cria e consulta repos no GitLab com visibilidade correta
- **Location**: `src/gitlab_client.py`
- **Interfaces**:
  - `GitlabClient(token: str, username: str, gitlab_url: str)`
  - `repo_exists(name: str) -> bool`
  - `create_repo(repo: RepoInfo) -> str` — retorna `project.ssh_url_to_repo` lido da resposta da API (nunca construído localmente)
  - `get_ssh_url(name: str) -> str` — para repos já existentes: consulta a API pelo `path` e retorna `ssh_url_to_repo`
- **Dependencies**: `python-gitlab`
- **Reuses**: `RepoInfo` dataclass
- **Security**: `visibility` é derivada APENAS de `repo.is_private` — nunca de input externo. Se `is_private=True` → `"private"`. Se `is_private=False` → `"public"`. Sem lógica alternativa.
- **Notes**: O GitLab pode normalizar o `name` em um `path` diferente (ex: `"my project"` → `path="my-project"`). Por isso a SSH URL **deve** vir de `project.ssh_url_to_repo` na resposta, não de `f"git@gitlab.com:{username}/{name}.git"`. Construir a URL localmente produziria URLs erradas para qualquer repo com espaços ou chars especiais.

### `src/git_ops.py` — Operações Git

- **Purpose**: Clone bare do GitHub e push para GitLab via subprocess git
- **Location**: `src/git_ops.py`
- **Interfaces**:
  - `GitOps(temp_dir: str, verbose: bool)`
  - `clone(github_ssh_url: str, repo_name: str) -> Path` — clona em `temp_dir/repo_name.git`
  - `push(clone_path: Path, gitlab_ssh_url: str) -> None` — push `--mirror` para GitLab
  - `cleanup(clone_path: Path) -> None` — remove diretório temporário com handler para Windows read-only
- **Dependencies**: `subprocess` (built-in), `git` no PATH do sistema, `stat` (built-in)
- **Reuses**: nada
- **Notes**:
  - Usa `git clone --mirror` + `git push --mirror`. Não usa GitPython (desnecessário para operações simples).
  - **SSH StrictHostKeyChecking**: todos os comandos git passam `-c core.sshCommand="ssh -o StrictHostKeyChecking=accept-new"` via env var `GIT_SSH_COMMAND`. Sem isso, primeira execução em máquina nova trava aguardando input interativo do usuário.
  - **Windows rmtree**: `cleanup()` usa `onerror` handler que chama `stat.S_IWRITE` + `os.chmod` antes de retentativa. Arquivos `.git` no Windows têm atributo read-only; `shutil.rmtree` sem handler lança `PermissionError` garantido.
  - `cleanup()` é chamado **sempre** pelo `BackupRunner` em bloco `finally`, não dentro do fluxo normal.

### `src/backup_runner.py` — Orquestrador

- **Purpose**: Coordena o fluxo completo de backup para cada repo
- **Location**: `src/backup_runner.py`
- **Interfaces**:
  - `BackupRunner(config: Config, github: GithubClient, gitlab: GitlabClient, git_ops: GitOps)`
  - `run() -> list[BackupResult]` — executa o backup completo
  - `_backup_repo(repo: RepoInfo) -> BackupResult` — processa um único repo
- **Dependencies**: todos os outros módulos
- **Reuses**: `RepoInfo`, `BackupResult`, `Config`
- **Notes**: `_backup_repo()` usa `try/finally` para garantir `cleanup()` mesmo em caso de erro:
  ```python
  clone_path = None
  try:
      clone_path = git_ops.clone(...)
      git_ops.push(...)
      return BackupResult(status="success", ...)
  except Exception as e:
      return BackupResult(status="error", message=str(e))
  finally:
      if clone_path and clone_path.exists():
          git_ops.cleanup(clone_path)
  ```

### `src/models.py` — Data Models

- **Purpose**: Dataclasses compartilhadas entre módulos
- **Location**: `src/models.py`
- **Interfaces**: `RepoInfo`, `BackupResult`, `Config` (definidos acima)
- **Dependencies**: `dataclasses`, `typing` (built-ins)
- **Reuses**: nada

### `backup.py` — CLI Entry Point

- **Purpose**: Ponto de entrada, parseia args CLI, monta dependências, chama `BackupRunner.run()`
- **Location**: `backup.py` (raiz do projeto)
- **Interfaces**:
  - `main()` — entry point
  - Args: `--dry-run`, `--filter`, `--verbose`, `--include-forks`, `--include-archived`, `--config`
- **Dependencies**: `argparse` (built-in), `rich`, todos os módulos `src/`
- **Reuses**: nada

---

## Estrutura de Arquivos

```
backup-github-to-gitlab/
├── backup.py                    # CLI entry point
├── requirements.txt             # PyGithub, python-gitlab, python-dotenv, rich, PyYAML
├── config.example.yaml          # Template de configuração (commitado)
├── .env.example                 # Template de tokens (commitado)
├── .gitignore                   # ignora .env, config.yaml, tmp/
├── src/
│   ├── __init__.py
│   ├── models.py               # RepoInfo, BackupResult, Config
│   ├── config.py               # load_config, validate_config
│   ├── github_client.py        # GithubClient
│   ├── gitlab_client.py        # GitlabClient
│   ├── git_ops.py              # GitOps
│   └── backup_runner.py        # BackupRunner
└── .specs/                     # Documentação do projeto (este diretório)
```

---

## Known Limitations

| Limitação | Impacto | Workaround |
|-----------|---------|------------|
| Git LFS não suportado | Objetos LFS não são copiados via `--mirror`; repos com LFS terão histórico incompleto no GitLab | Documentar no README; usuário pode fazer clone LFS manualmente |
| Repos de organizações não incluídos | Apenas repos pessoais na v1 | `--include-orgs` planejado para v2 |
| GitLab Pull Mirror requer Premium para repos privados | Mirror automático via GitLab não funciona gratuitamente para privados | Alternativa: GitHub Actions (v2) |

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
|----------------|----------|-------------|
| `GITHUB_TOKEN` ausente | Falha imediata em `validate_config()` com mensagem clara | Script não inicia |
| `GITLAB_TOKEN` ausente | Falha imediata em `validate_config()` com mensagem clara | Script não inicia |
| SSH falha (repo individual) | `BackupResult(status="error")`, continua próximo repo | Repo aparece em erros no relatório |
| Rate limit GitHub (429) | Aguarda `X-RateLimit-Reset` header, retry automático | Pausa visível no terminal |
| Repo GitLab já existe | Pula criação, faz push incremental | `[SKIP create]` no log |
| Espaço em disco insuficiente | Exceção com path e espaço disponível | Script para, mensagem clara |
| Nome de repo inválido para GitLab | Sanitiza (substitui chars inválidos por `-`), loga mapeamento | Repo criado com nome sanitizado |
| Repo vazio (zero commits) | Cria repo no GitLab, pula push, loga `[SKIP push] empty repo` | Repo criado vazio no GitLab |
| SSH StrictHostKeyChecking (primeiro run) | `GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"` em todos os subprocessos git | Aceita host automaticamente sem input |
| rmtree PermissionError no Windows | `onerror` handler aplica `chmod` e retenta antes de propagar | Cleanup bem-sucedido no Windows |
| Clone/push falha com exceção | `finally` em `_backup_repo()` garante cleanup mesmo com erro | Sem temp dirs órfãos em `./tmp/` |
| Rate limit GitLab | Aguarda 60s fixo e retenta (sem header de reset no GitLab) | Pausa visível no terminal |

---

## Tech Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Clone strategy | `git clone --mirror` | Captura todos refs (branches, tags, stash) em um único comando |
| Push strategy | `git push --mirror` | Replica exatamente todos refs do clone no destino |
| Git via subprocess | subprocess direto | GitPython adiciona dependência e camada de abstração desnecessária para operações simples |
| Tokens em .env | python-dotenv | Padrão da indústria, evita hardcoding, fácil de usar em CI futuramente |
| Config em YAML | PyYAML | Mais legível que JSON para configs de usuário, sem ambiguidade de TOML |
| Temp dir para clones | `./tmp/` (configurável) | Usuário vê onde os dados temporários ficam; evita surpresas em diretórios do sistema |
| SSH StrictHostKeyChecking | `accept-new` via `GIT_SSH_COMMAND` | Evita hang interativo em primeira execução; mais seguro que `no` (ainda valida hosts conhecidos) |
| rmtree no Windows | `onerror` com chmod + retry | `shutil.rmtree` sem handler quebra garantidamente em `.git` dirs no Windows |
| GitLab SSH URL | Lida de `project.ssh_url_to_repo` (resposta API) | GitLab normaliza `path` de forma imprevisível; construir URL localmente produz erros silenciosos |
| Cleanup em finally | `try/finally` em `_backup_repo()` | Garante ausência de temp dirs órfãos independente do tipo de falha |

---

## Security Considerations

1. **Visibilidade**: A função `create_repo()` no `GitlabClient` aceita apenas `RepoInfo.is_private` para determinar visibilidade. Não existe path de código que crie um repo público a partir de um privado.

2. **Tokens**: Carregados via `os.environ` + dotenv. Nunca logados. O `.env` está no `.gitignore` desde o início.

3. **Validação de saída do git**: O subprocess captura stdout/stderr do git para log mas não executa nenhum output como código.

4. **Nomes de repos**: Sanitização antes de qualquer chamada de API para evitar path traversal ou injection via nomes de repos.
