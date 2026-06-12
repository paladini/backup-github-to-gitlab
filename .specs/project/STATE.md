# Project State

## Decisions

| ID  | Decision | Rationale | Date |
|-----|----------|-----------|------|
| D01 | Python 3.11+ como linguagem | Melhor ecossistema para APIs (PyGithub, python-gitlab) e operações Git. Roda nativamente no Windows. | 2026-06-12 |
| D02 | SSH para operações git, API token para listagem/criação | SSH keys já estão configuradas em ambas as plataformas; tokens de API são necessários para criar repos e obter metadados de privados | 2026-06-12 |
| D03 | Bare clone (`--mirror`) ao invés de clone normal | `git clone --mirror` captura todos os branches e tags sem precisar iterá-los manualmente | 2026-06-12 |
| D04 | Visibilidade: fail-safe por padrão | Se a API retornar visibilidade desconhecida, o script cria como PRIVADO no GitLab, nunca como público | 2026-06-12 |
| D05 | Phase 2: documentar ambas as opções (GitLab Premium Pull Mirror + GitHub Actions) | GitLab Pull Mirror requer Premium para repos privados; GitHub Actions é free mas precisa de workflow em cada repo | 2026-06-12 |
| D06 | Scope v1: apenas repos pessoais, não org | Simplifica a v1 e evita riscos de vazar código de organização. Orgs adicionados via flag na v2. | 2026-06-12 |
| D07 | SSH StrictHostKeyChecking=accept-new via GIT_SSH_COMMAND | Sem isso o script trava em primeira execução aguardando input interativo; `accept-new` é mais seguro que `no` (ainda valida hosts conhecidos) | 2026-06-12 |
| D08 | shutil.rmtree com onerror handler no Windows | .git dirs têm arquivos read-only no Windows; rmtree vanilla lança PermissionError garantido | 2026-06-12 |
| D09 | GitLab SSH URL lida de project.ssh_url_to_repo (API) | GitLab pode normalizar path de formas imprevisíveis; construir URL localmente produziria erros silenciosos em repos com nomes especiais | 2026-06-12 |
| D10 | cleanup() em try/finally em _backup_repo() | Garante que ./tmp/ não acumule clones abandonados independente do tipo de falha | 2026-06-12 |

## Blockers

_Nenhum no momento._

## Open Questions

| ID  | Question | Context |
|-----|----------|---------|
| OQ1 | GitLab tem o mesmo namespace disponível para os repos? | Se um repo `paladini/foo` já existe no GitLab por outra razão, o script deve criar `paladini/foo-github-backup` ou falhar? |
| OQ2 | Repositórios arquivados devem ser arquivados também no GitLab? | A API do GitLab suporta arquivar repos. Isso seria ideal mas está fora do escopo da v1. |

## Lessons Learned

_Será preenchido durante a implementação._

## Deferred Ideas

- Migração de issues/PRs via API (muito complexo para v1, mas APIs existem)
- Suporte a LFS (Git Large File Storage) — clonar com LFS ativo
- Dashboard web para ver status dos mirrors
