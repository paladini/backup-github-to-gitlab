# GitHub → GitLab Backup

**Vision:** Script CLI que clona todos os repositórios de um usuário GitHub e os replica no GitLab, respeitando visibilidade (privado permanece privado), usando SSH keys já configuradas em ambas as plataformas.

**For:** Usuário individual que quer backup/espelho dos seus repos do GitHub no GitLab.

**Solves:** Dependência exclusiva do GitHub como única plataforma de hospedagem de código; risco de perda de acesso a repos privados caso a conta seja suspensa ou o serviço fique indisponível.

## Goals

- **G1**: Replicar 100% dos repos pessoais do GitHub para o GitLab mantendo visibilidade correta (privado→privado, público→público) — zero vazamentos de código privado.
- **G2**: Script idempotente — pode ser re-executado sem duplicar repos ou sobrescrever dados; repos já existentes no GitLab recebem apenas um push incremental.
- **G3** *(Phase 2)*: Sincronização automática — mudanças no GitHub propagam para o GitLab sem intervenção manual.

## Tech Stack

**Core:**

- Linguagem: Python 3.11+
- Runtime: Windows 10 (PowerShell), também compatível com Linux/macOS
- Dependências de sistema: `git` CLI no PATH

**Key dependencies:**

- `PyGithub` — GitHub REST API (listar repos, obter visibilidade, metadados)
- `python-gitlab` — GitLab REST API (criar repos, configurar mirror)
- `python-dotenv` — carregamento de tokens de `.env`
- `rich` — output colorido com barra de progresso no terminal
- `PyYAML` — arquivo de configuração `config.yaml`

## Scope

**v1 inclui:**

- Listagem de todos os repos pessoais do GitHub (públicos + privados + forks, configurável)
- Clonagem via SSH, branch por branch, incluindo todas as tags
- Criação automática dos repos no GitLab com a mesma visibilidade
- Push completo (todos os branches + tags) para o GitLab
- Modo idempotente: repos existentes no GitLab recebem push incremental
- `--dry-run` para inspecionar o que seria feito sem executar
- `--filter` para fazer backup de um subset de repos por nome/padrão glob
- Log detalhado por repo com status (success / skip / error)

**v2 inclui (phase 2):**

- Configuração automática de pull mirror no GitLab (via API)
- Nota: GitLab Pull Mirror requer GitLab Premium para repos privados
- Alternativa free: geração de `mirror.yml` (GitHub Action) para push automático

**Explicitamente fora do escopo:**

- Backup de wikis, issues, PRs, comentários ou projetos
- Backup de repositórios de organizações (repos org são opcionais via `--include-orgs`)
- Migração de GitHub Packages, Actions secrets ou ambientes de CI
- Interface gráfica (GUI)
- Suporte a GitLab auto-hospedado com certificados SSL customizados (apenas GitLab.com na v1)

## Constraints

- **Segurança**: Um repo privado no GitHub NUNCA pode ser criado como público no GitLab. O script deve falhar explicitamente se não conseguir determinar a visibilidade de um repo.
- **Autenticação**: SSH keys para operações git; API tokens para listar/criar repos. Tokens ficam em `.env`, nunca commitados.
- **Windows-first**: deve rodar em PowerShell no Windows 10; `git` deve estar no PATH.
- **Rate limiting**: GitHub tem limite de 5000 req/hora (com token autenticado). O script deve respeitar esse limite.
