# Core Backup — Specification

## Problem Statement

O usuário tem dezenas de repositórios no GitHub (públicos e privados) e quer uma cópia de segurança no GitLab. Sem automação, cada repo exigiria criação manual no GitLab + configuração de remote + push — processo tedioso, propenso a erro humano (especialmente no mapeamento de visibilidade privado→privado). O risco de acidentalmente tornar um repo privado público é o principal perigo.

## Goals

- [ ] Replicar todos os repos pessoais do GitHub para o GitLab sem intervenção manual por repo
- [ ] Garantir que repos privados no GitHub SEMPRE sejam privados no GitLab (zero exceções)
- [ ] Script idempotente: re-executar não duplica repos nem sobrescreve histórico no GitLab
- [ ] Usuário consegue verificar o que será feito antes de executar (`--dry-run`)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backup de issues, PRs, comentários | Fora do escopo de v1; requer API separada por plataforma |
| Repos de organizações | Risco de vazar código de org; deixado para v2 com flag explícita |
| Wikis dos repositórios | São repos git separados; escopo amplia significativamente |
| Migração de CI/CD (Actions, GitLab CI) | Sintaxe incompatível entre plataformas |
| Arquivamento automático no GitLab | API suporta, mas aumenta complexidade; v2 |
| GitLab self-hosted com SSL customizado | Apenas GitLab.com na v1 |

---

## User Stories

### P1: Backup inicial completo ⭐ MVP

**User Story**: Como usuário com conta no GitHub e GitLab, quero executar um único comando que copie todos os meus repos do GitHub para o GitLab, respeitando visibilidade, para ter uma cópia de segurança operacional.

**Why P1**: É o core value do projeto. Sem isso, nada funciona.

**Acceptance Criteria**:

1. WHEN o usuário executa `python backup.py` THEN o sistema SHALL listar todos os repos pessoais do GitHub (públicos e privados) via API autenticada
2. WHEN um repo do GitHub é privado THEN o sistema SHALL criar o repo correspondente no GitLab como **privado** sem exceção
3. WHEN um repo do GitHub é público THEN o sistema SHALL criar o repo correspondente no GitLab como **público**
4. WHEN o sistema não consegue determinar a visibilidade de um repo THEN o sistema SHALL criar como **privado** no GitLab e logar um aviso
5. WHEN o repo é clonado via SSH THEN o sistema SHALL fazer push de **todos os branches** e **todas as tags** para o GitLab
6. WHEN o backup de todos os repos é concluído THEN o sistema SHALL exibir um relatório: `X repos copiados, Y pulados, Z erros`

**Independent Test**: Criar um repo privado de teste no GitHub → rodar o script → verificar que o repo existe no GitLab como **privado** com todos os branches.

---

### P1: Modo idempotente (re-execução segura) ⭐ MVP

**User Story**: Como usuário, quero poder re-executar o script sem criar repos duplicados no GitLab nem corromper repos que já foram copiados.

**Why P1**: Sem idempotência, re-executar o script a cada semana quebraria repos no GitLab.

**Acceptance Criteria**:

1. WHEN o script é executado e um repo GitLab com o mesmo nome já existe THEN o sistema SHALL fazer push incremental (apenas novos commits/branches/tags) sem recriar o repo
2. WHEN o GitLab já tem o repo e o histórico está atualizado THEN o sistema SHALL pular o push e logar `[SKIP] repo-name: already up to date`
3. WHEN o script é executado duas vezes seguidas sem mudanças nos repos THEN o segundo resultado SHALL ser idêntico ao primeiro (sem erros, sem duplicatas)

**Independent Test**: Rodar o script duas vezes; o segundo run deve mostrar todos os repos como `[SKIP]`.

---

### P1: Configuração via arquivo + variáveis de ambiente ⭐ MVP

**User Story**: Como usuário, quero configurar nomes de usuário, tokens e opções em um arquivo de configuração, sem hardcodar nada no script.

**Why P1**: Tokens não podem ser hardcodados; usernames diferentes (GitHub vs GitLab) precisam ser configuráveis.

**Acceptance Criteria**:

1. WHEN o usuário copia `config.example.yaml` para `config.yaml` e define seus usernames THEN o sistema SHALL usar esses valores
2. WHEN o usuário define `GITHUB_TOKEN` e `GITLAB_TOKEN` no arquivo `.env` THEN o sistema SHALL carregá-los automaticamente sem expô-los em logs
3. WHEN `config.yaml` não existe THEN o sistema SHALL exibir erro claro com instrução de como criar o arquivo
4. WHEN `GITHUB_TOKEN` ou `GITLAB_TOKEN` não está definido THEN o sistema SHALL falhar imediatamente com mensagem explicativa antes de fazer qualquer operação

**Independent Test**: Remover o `.env` → rodar o script → verificar que falha com mensagem útil antes de qualquer chamada de API.

---

### P1: Dry-run para pré-visualização ⭐ MVP

**User Story**: Como usuário, quero executar `python backup.py --dry-run` para ver exatamente o que o script faria sem executar nenhuma operação real.

**Why P1**: Essencial para ganhar confiança antes da primeira execução em produção.

**Acceptance Criteria**:

1. WHEN `--dry-run` é passado THEN o sistema SHALL listar todos os repos encontrados no GitHub com suas visibilidades
2. WHEN `--dry-run` é passado THEN o sistema SHALL indicar para cada repo se seria criado, atualizado ou pulado no GitLab
3. WHEN `--dry-run` é passado THEN o sistema SHALL NÃO executar nenhuma operação de escrita: nenhuma criação de repo, nenhum clone, nenhum push
4. WHEN `--dry-run` é passado THEN o sistema SHALL exibir `[DRY RUN] Nenhuma operação foi executada.` ao final

**Independent Test**: Rodar com `--dry-run` → confirmar que nenhum novo repo aparece no GitLab.

---

### P2: Filtro por nome/padrão

**User Story**: Como usuário, quero fazer backup de apenas um subset dos meus repos usando um filtro por nome.

**Why P2**: Útil para testar com um repo específico antes de rodar em tudo, e para excluir repos que não precisam de backup.

**Acceptance Criteria**:

1. WHEN `--filter "myproject-*"` é passado THEN o sistema SHALL processar apenas repos cujo nome satisfaz o padrão glob
2. WHEN `--filter` corresponde a zero repos THEN o sistema SHALL logar aviso e encerrar sem erro
3. WHEN nenhum `--filter` é passado THEN o sistema SHALL processar todos os repos

**Independent Test**: `--filter "test-*"` em uma conta com repos `test-foo`, `test-bar`, `myproject` → apenas os dois primeiros são processados.

---

### P2: Forks e repos arquivados configuráveis

**User Story**: Como usuário, quero controlar se forks e repos arquivados são incluídos no backup.

**Why P2**: Forks são frequentemente mirrors de projetos de terceiros; incluir por padrão pode ser indesejado.

**Acceptance Criteria**:

1. WHEN `include_forks: false` está no `config.yaml` (padrão) THEN o sistema SHALL pular repos que são forks
2. WHEN `include_forks: true` THEN o sistema SHALL incluir forks no backup
3. WHEN `include_archived: false` THEN o sistema SHALL pular repos arquivados do GitHub
4. WHEN `include_archived: true` (padrão) THEN o sistema SHALL incluir repos arquivados

**Independent Test**: Configurar `include_forks: false` → verificar que forks são pulados no log.

---

### P3: Verbose logging

**User Story**: Como usuário, quero o flag `--verbose` para ver logs detalhados de cada operação (clone, push, etc.) para debugar problemas.

**Why P3**: Útil para diagnóstico mas não essencial para o funcionamento.

**Acceptance Criteria**:

1. WHEN `--verbose` é passado THEN o sistema SHALL logar cada comando git executado e sua saída
2. WHEN um erro ocorre em modo verbose THEN o sistema SHALL exibir o traceback completo
3. WHEN `--verbose` NÃO é passado THEN o sistema SHALL exibir apenas progresso resumido e erros

---

## Edge Cases

- WHEN o GitHub retorna rate limit (HTTP 429) THEN o sistema SHALL aguardar o tempo indicado pelo header `X-RateLimit-Reset` e tentar novamente
- WHEN o GitLab retorna rate limit THEN o sistema SHALL aguardar 60 segundos e tentar novamente (GitLab não expõe header de reset)
- WHEN um repo no GitLab com mesmo nome já existe mas pertence a outro namespace THEN o sistema SHALL logar erro e pular (não sobrescrever)
- WHEN o clone SSH falha (timeout, SSH key não reconhecida) THEN o sistema SHALL registrar o repo como erro e continuar com os demais
- WHEN o diretório temporário de clone não tem espaço em disco THEN o sistema SHALL falhar com mensagem clara indicando o caminho e tamanho disponível
- WHEN um repo tem zero commits (vazio) no GitHub THEN o sistema SHALL criar o repo no GitLab mas pular o push (não há o que copiar)
- WHEN o nome do repo no GitHub contém caracteres inválidos para GitLab THEN o sistema SHALL sanitizar o nome (substituir caracteres inválidos por `-`) e logar o mapeamento
- WHEN o script é executado pela primeira vez em uma máquina nova THEN o sistema SHALL aceitar automaticamente a autenticidade do host SSH (`StrictHostKeyChecking=accept-new`) em vez de travar esperando input interativo
- WHEN a remoção do diretório temporário falha no Windows devido a arquivos read-only do `.git` THEN o sistema SHALL usar handler que remove o atributo read-only e tenta novamente, sem deixar diretórios órfãos
- WHEN o clone ou push de um repo falha com exceção THEN o sistema SHALL remover o diretório temporário no bloco `finally` (mesmo em caso de erro), garantindo que `./tmp/` não acumule clones abandonados
- WHEN o GitLab sanitiza o nome do repo e gera um `path` diferente do `name` THEN a SSH URL usada no push SHALL ser lida da resposta da API de criação (campo `ssh_url_to_repo`), não construída localmente a partir do nome

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|----------------|-------|-------|--------|
| BKP-01 | P1: Listar repos GitHub autenticado | T4 | Verified |
| BKP-02 | P1: Visibilidade privado → privado (fail-safe) | T5 | Verified |
| BKP-03 | P1: Visibilidade público → público | T5 | Verified |
| BKP-04 | P1: Visibilidade desconhecida → privado + aviso | T5 | Verified |
| BKP-05 | P1: Push de todos os branches e tags | T6 | Verified |
| BKP-06 | P1: Relatório final (copiados/pulados/erros) | T7, T8 | Verified |
| BKP-07 | P1: Re-exec não duplica repos | T5, T7 | Verified |
| BKP-08 | P1: Re-exec atualizado → SKIP | T6, T7 | Verified |
| BKP-09 | P1: Config via config.yaml + .env | T1, T3 | Verified |
| BKP-10 | P1: Falha imediata sem token | T3, T8 | Verified |
| BKP-11 | P1: dry-run lista sem escrever | T7, T8 | Verified |
| BKP-12 | P1: dry-run não executa operações | T7, T8 | Verified |
| BKP-13 | P2: --filter por glob | T8 | Verified |
| BKP-14 | P2: include_forks configurável | T4 | Verified |
| BKP-15 | P2: include_archived configurável | T4 | Verified |
| BKP-16 | P3: --verbose logging detalhado | T6, T8 | Verified |
| BKP-17 | P1: SSH StrictHostKeyChecking accept-new (não travar) | T6 | Verified |
| BKP-18 | P1: Windows rmtree lida com arquivos read-only do .git | T6 | Verified |
| BKP-19 | P1: Cleanup do temp dir em finally (sem vazar em erro) | T7 | Verified |
| BKP-20 | P1: SSH URL do GitLab lida da resposta da API, não construída | T5 | Verified |

**Coverage:** 20 total, 0 mapeados a tasks, 20 unmapeados ⚠️

---

## Success Criteria

- [ ] Usuário executa `python backup.py` e todos os repos pessoais do GitHub aparecem no GitLab
- [ ] Zero repos privados criados como públicos no GitLab
- [ ] Re-execução 24h depois não causa erros nem duplicatas
- [ ] `--dry-run` mostra o plano correto sem alterar nada
- [ ] Script termina em < 5 minutos para um usuário com até 50 repos
