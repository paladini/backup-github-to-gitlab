# Issues & Wiki Backup — Specification

## Problem Statement

O backup atual copia apenas o código Git (branches + tags). Wikis e Issues ficam exclusivamente no GitHub — se a conta for suspensa ou o GitHub ficar indisponível, toda a documentação e histórico de rastreamento de bugs/features se perde. Este feature estende o backup para cobrir esses dois artefatos adicionais.

**Limitações conhecidas da migração de issues (documentar explicitamente ao usuário):**
- Timestamps originais não podem ser preservados: a API do GitLab não permite definir `created_at` sem token de administrador. Todas as issues migradas terão a data da migração.
- Autorias originais não podem ser preservadas: todas as issues e comentários aparecerão como criados pelo token owner no GitLab. O autor original é registrado no corpo da issue/comentário.
- Pull Requests do GitHub NÃO são migrados (são um artefato específico do GitHub; equivalentes no GitLab são Merge Requests com semântica diferente).

---

## Goals

- **G1**: Wikis de repositórios GitHub são copiadas para os wikis correspondentes no GitLab como operação git (clone + push), preservando todo o histórico de commits da wiki.
- **G2**: Issues (exceto PRs) são migradas do GitHub para o GitLab com título, corpo, labels, milestone, estado (open/closed) e comentários preservados na medida do possível.
- **G3**: Ambos os features são opt-in via `config.yaml`; repositórios sem wiki ou sem issues não geram ruído ou erros.
- **G4**: Operação idempotente — re-executar o script não duplica wikis nem issues já migradas.

---

## Out of Scope

| Artefato | Motivo |
|----------|--------|
| Pull Requests | Semântica incompatível com GitLab MRs; alta complexidade; deixado para futura análise |
| Anexos de issues (imagens, arquivos) | GitHub hospeda em CDN próprio; não há API de migração de blobs |
| Reações emoji em issues/comentários | Baixíssimo valor; API adicional por item |
| Mapeamento de @mentions entre plataformas | Nomes de usuário podem diferir; risco de menção errada |
| Preservação de timestamps originais | API GitLab requer token de admin; fora do alcance do script |
| Preservação de autorias originais | Mesma limitação de admin |
| Arquivamento de milestones fechados no GitLab | API suporta, mas é detalhe de baixa prioridade |
| Issues de repositórios de organizações | Org repos estão fora do escopo até `--include-orgs` ser implementado |

---

## User Stories

### WIKI-P1: Backup de wiki via git ⭐ MVP

**User Story**: Como usuário, quero que a wiki de cada repositório GitHub seja copiada para o wiki correspondente no GitLab, para não perder documentação.

**Why P1**: Wikis contêm documentação que não está no código; perdê-las é tão sério quanto perder o código.

**Acceptance Criteria**:

1. WHEN `backup_wiki: true` está em `config.yaml` AND um repo GitHub tem wiki com conteúdo THEN o sistema SHALL clonar a wiki (repo git separado em `{ssh_url_base}/{repo}.wiki.git`) e fazer push para o wiki GitLab correspondente
2. WHEN o repo GitHub não tem wiki habilitada ou a wiki está vazia THEN o sistema SHALL pular silenciosamente (sem erro, sem warning ruidoso)
3. WHEN a wiki já existe no GitLab THEN o sistema SHALL fazer push incremental (idempotente), sem recriar nem sobrescrever
4. WHEN `backup_wiki: false` (padrão) THEN o sistema SHALL pular o backup de wikis em todos os repos
5. WHEN o push de wiki falha THEN o sistema SHALL registrar o repo como `wiki_error` no relatório e continuar com os demais repos

---

### WIKI-P2: Wiki incluída no dry-run

**Why P2**: Consistência com o comportamento do backup de código.

**Acceptance Criteria**:

1. WHEN `--dry-run` AND `backup_wiki: true` THEN o sistema SHALL indicar para cada repo se a wiki seria copiada ou pulada, sem executar operação

---

### ISS-P1: Migração de issues (título, corpo, estado) ⭐ MVP

**User Story**: Como usuário, quero que todas as issues (abertas e fechadas) dos meus repos GitHub sejam criadas no GitLab correspondente, para não perder o histórico de bugs e features.

**Why P1**: Issues documentam decisões e histórico de bugs; perder isso é uma lacuna crítica de backup.

**Acceptance Criteria**:

1. WHEN `backup_issues: true` está em `config.yaml` THEN o sistema SHALL buscar todas as issues do repo GitHub (state=all), excluindo Pull Requests
2. WHEN uma issue GitHub está aberta THEN a issue GitLab correspondente SHALL ser criada como aberta
3. WHEN uma issue GitHub está fechada THEN a issue GitLab correspondente SHALL ser criada e fechada imediatamente após
4. O corpo de cada issue migrada SHALL conter um cabeçalho de atribuição: `> 🔄 Migrado do GitHub — originalmente reportado por @{autor} em {YYYY-MM-DD}`
5. O corpo de cada issue migrada SHALL conter ao final um marcador oculto: `<!-- github-issue-id: {N} -->` (usado para idempotência)
6. WHEN `backup_issues: false` (padrão) THEN o sistema SHALL pular a migração de issues em todos os repos

---

### ISS-P1: Idempotência de issues ⭐ MVP

**Why P1**: Re-executar o script não pode criar issues duplicadas no GitLab.

**Acceptance Criteria**:

1. WHEN o script é re-executado THEN o sistema SHALL listar todas as issues existentes no GitLab do projeto e extrair os `github-issue-id` dos seus corpos
2. WHEN uma issue GitHub já tem um `github-issue-id` correspondente no GitLab THEN o sistema SHALL pular essa issue (sem criar duplicata)
3. WHEN issues novas foram criadas no GitHub desde o último run THEN apenas as novas SHALL ser migradas

---

### ISS-P1: Migração de labels ⭐ MVP

**Why P1**: Sem labels, issues perdem sua categorização — são menos úteis para triagem.

**Acceptance Criteria**:

1. WHEN migrating issues THEN o sistema SHALL primeiro listar todas as labels do repo GitHub e criar as ausentes no projeto GitLab correspondente
2. WHEN uma label com o mesmo nome já existe no GitLab THEN o sistema SHALL pular a criação (sem erro)
3. A cor da label SHALL ser preservada (formato `#RRGGBB`)
4. A descrição da label SHALL ser preservada (se existir)

---

### ISS-P2: Migração de milestones

**Why P2**: Milestones agrupam issues por versão/sprint — perder essa estrutura reduz a utilidade do backup.

**Acceptance Criteria**:

1. WHEN migrating issues AND um repo GitHub tem milestones THEN o sistema SHALL criar os milestones ausentes no projeto GitLab antes de migrar as issues
2. WHEN um milestone GitHub está fechado THEN o milestone GitLab SHALL ser criado e fechado
3. WHEN uma milestone com o mesmo título já existe no GitLab THEN o sistema SHALL reutilizá-la (sem duplicata)
4. Issues migradas SHALL ter o milestone GitLab correspondente atribuído (quando o original tinha milestone)

---

### ISS-P2: Migração de comentários

**Why P2**: Comentários contêm contexto de debugging, decisões e conversas — perder isso reduz significativamente o valor do backup de issues.

**Acceptance Criteria**:

1. WHEN migrating an issue THEN o sistema SHALL migrar todos os comentários da issue em ordem cronológica
2. O corpo de cada comentário migrado SHALL conter: `> 🔄 @{autor} em {YYYY-MM-DD HH:MM UTC}\n\n{corpo original}`
3. WHEN uma issue já existe no GitLab (idempotência) THEN comentários NÃO serão re-migrados (a issue inteira é pulada)

---

### ISS-P3: Issues no dry-run

**Acceptance Criteria**:

1. WHEN `--dry-run` AND `backup_issues: true` THEN o sistema SHALL exibir para cada repo: total de issues no GitHub, quantas já estão migradas, quantas seriam criadas
2. WHEN `--dry-run` THEN nenhuma issue, label, milestone ou comentário SHALL ser criado

---

## Edge Cases

- **(WIKI-E1)** WHEN o clone da wiki GitHub falha com exit code não-zero (wiki URL retorna erro git, indicando wiki vazia ou desabilitada) THEN o sistema SHALL tratar como "sem wiki" e pular silenciosamente
- **(WIKI-E2)** WHEN o push da wiki para GitLab falha THEN o sistema SHALL registrar o erro no relatório final sem interromper o backup dos demais repos
- **(ISS-E1)** WHEN a API do GitHub retorna rate limit durante listagem de issues ou comentários THEN o sistema SHALL reutilizar o mecanismo existente de retry com espera (BKP-21)
- **(ISS-E2)** WHEN a API do GitLab retorna rate limit (429) durante criação de issues/labels/milestones THEN o sistema SHALL reutilizar o mecanismo existente de retry (BKP-22)
- **(ISS-E3)** WHEN um repo GitHub tem mais de 100 issues THEN o sistema SHALL paginar a API (per_page=100) e processar todas as páginas
- **(ISS-E4)** WHEN uma issue GitHub tem corpo nulo (null) THEN o sistema SHALL usar string vazia como corpo, adicionando apenas o cabeçalho de atribuição
- **(ISS-E5)** WHEN a criação de uma issue falha no GitLab THEN o sistema SHALL logar o erro e continuar com a próxima issue (não aborta o repo inteiro)
- **(ISS-E6)** WHEN `backup_issues: true` AND o projeto não tem issues no GitHub THEN o sistema SHALL pular silenciosamente sem erro
- **(ISS-E7)** WHEN o repo GitLab correspondente não existe (código não foi backupeado ainda) THEN o sistema SHALL pular o backup de issues com aviso

---

## Config Changes

```yaml
# config.yaml — novos campos opcionais
backup_wiki: false      # default: false (opt-in)
backup_issues: false    # default: false (opt-in)
```

Ambos os campos são **opcionais** — se ausentes, tratados como `false`. O script não deve falhar se campos antigos de `config.yaml` não tiverem esses campos (retrocompatibilidade).

---

## CLI Changes

Sem novas flags CLI — as opções são gerenciadas via `config.yaml`. O relatório final deve incluir contadores de wiki e issues quando habilitados:

```
Repos  : 12 success, 0 skip, 0 error
Wikis  : 8 success, 3 skip (no wiki), 1 error
Issues : 47 created, 12 already migrated, 0 error
```

---

## Requirement Traceability

| ID | Story | Phase | Status |
|----|-------|-------|--------|
| WIKI-01 | Wiki backup via git clone+push quando habilitado | T-WIKI | Planned |
| WIKI-02 | Pular repo sem wiki (silencioso) | T-WIKI | Planned |
| WIKI-03 | Wiki push idempotente | T-WIKI | Planned |
| WIKI-04 | Wiki desabilitada por padrão (opt-in) | T-CONFIG | Planned |
| WIKI-05 | Wiki error não interrompe demais repos | T-RUNNER | Planned |
| WIKI-06 | dry-run mostra ação de wiki | T-RUNNER | Planned |
| ISS-01 | Listar issues GitHub (state=all, excluir PRs) | T-ISS-CLIENT | Planned |
| ISS-02 | Criar issue GitLab com título e corpo + cabeçalho | T-ISS-MIGRATOR | Planned |
| ISS-03 | Fechar issue GitLab quando original está fechada | T-ISS-MIGRATOR | Planned |
| ISS-04 | Marcador `<!-- github-issue-id: N -->` no corpo | T-ISS-MIGRATOR | Planned |
| ISS-05 | Issues desabilitadas por padrão (opt-in) | T-CONFIG | Planned |
| ISS-06 | Idempotência: ler issues GitLab existentes antes de migrar | T-ISS-MIGRATOR | Planned |
| ISS-07 | Pular issues já migradas (github-issue-id presente) | T-ISS-MIGRATOR | Planned |
| ISS-08 | Sync de labels (criar ausentes, preservar cor+desc) | T-ISS-MIGRATOR | Planned |
| ISS-09 | Sync de milestones (criar ausentes, fechar se fechados) | T-ISS-MIGRATOR | Planned |
| ISS-10 | Atribuir milestone GitLab correto à issue migrada | T-ISS-MIGRATOR | Planned |
| ISS-11 | Migrar comentários em ordem cronológica | T-ISS-MIGRATOR | Planned |
| ISS-12 | Paginação de issues (per_page=100) | T-ISS-CLIENT | Planned |
| ISS-13 | Corpo nulo → string vazia + cabeçalho | T-ISS-MIGRATOR | Planned |
| ISS-14 | Issue GitLab não existe ainda → skip com aviso | T-RUNNER | Planned |
| ISS-15 | dry-run mostra contagem de issues por repo | T-RUNNER | Planned |
| ISS-E1 | Rate limit GitHub reutiliza mecanismo existente (BKP-21) | T-ISS-CLIENT | Planned |
| ISS-E2 | Rate limit GitLab reutiliza mecanismo existente (BKP-22) | T-ISS-MIGRATOR | Planned |
| ISS-E3 | Paginação issues >100 | T-ISS-CLIENT | Planned |
| ISS-E5 | Falha em issue individual não aborta o repo | T-ISS-MIGRATOR | Planned |

**Coverage:** 25 requirements, 25 mapeados a tasks ✅
