# Relatório de Auditoria de Segurança — Sistema FCA

**Projeto:** Sistema FCA — Plataforma Python/FastAPI (async), PostgreSQL 16, MinIO, Azure AD (OAuth2) e Docker Compose.
**Stack:** FastAPI + SQLAlchemy async + bcrypt + JWT (HS256/RS256) + slowapi + boto3 + openpyxl + Uvicorn + Nginx + Vue 3.
**Auditor:** Especialista Sênior em AppSec / Auditoria de Código.
**Status:** Todas as vulnerabilidades identificadas foram corrigidas.

---

## Sumário Executivo

Foram identificadas e corrigidas **15 vulnerabilidades** distribuídas em três níveis de criticidade:

| Severidade | Quantidade | Status |
|------------|------------|--------|
| CRÍTICA    | 5          | Corrigidas |
| ALTA       | 4          | Corrigidas |
| MÉDIA      | 5          | Corrigidas |
| **Total**  | **15**     | **100%** |

Nenhuma infecção por SQL Injection foi encontrada (todas as queries usam SQLAlchemy ORM parametrizado).

---

## Vulnerabilidades Críticas (C-1 a C-5)

### C-1 — WebSocket sem autenticação (Bypass total de auth / Impersonificação)
**Arquivos:** `backend/auth.py`, `backend/main.py`, `src/api.js`, `src/App.vue`

**Problema:** O endpoint `/ws` aceitava `user_id` como query param e não validava o JWT. Qualquer pessoa que conhecesse o UUID de um usuário podia conectarse no lugar dele e receber notificações/eventos privados.

**Correção:**
- Centralizada a função `authenticate_token(token, db)` em `auth.py` — mesma lógica de validação para HTTP e WebSocket (HS256 local ou RS256 Azure AD).
- `main.py`: o WebSocket agora exige `?token=<JWT>`, valida o token **antes** de `ws.accept()`, e registra o socket com `str(user.id)` extraído do payload — nunca confia em `user_id` vindo da URL. Em falha, rejeita com `WS_1008_POLICY_VIOLATION`.
- `require_user()` refatorado para reaproveitar `authenticate_token`, eliminando duplicação.
- Frontend (`src/App.vue` + `src/api.js`): `connectWs()` agora busca o JWT via `getToken()` e envia `/ws?token=<JWT>` (codificado), em vez de `user_id`.

### C-2 — IDOR em Presigned URLs (acesso arbitrário a arquivos de outros setores/empresas)
**Arquivo:** `backend/routes/upload.py`

**Problema:** Qualquer usuário autenticado podia gerar URL pré-assinada para qualquer `object_key` do bucket MinIO — anexos de FCAs de outros setores/empresas, avatares alheios, etc.

**Correção:** Criada `_pode_acessar_key(object_key, current, db)` — autorização **fail-closed** antes de assinar a URL:
1. **Avatar**: liberado só se a key contiver `avatars/{user_id}` correspondente (regex valida o UUID logo após `avatars/`).
2. **Anexo de FCA**: busca o(s) FCA(s) dono(s) da key em `anexo_urls`/`anexo_url` e aplica `_can_view` (mesma regra RBAC/multi-tenancy das rotas de FCA).
3. **Anexo de Help Ticket**: só admin ou `created_by` do ticket.
4. **Objeto sem referência no banco**: 403 (fail-closed).
- O endpoint passou a exigir `Depends(get_db)` e retornar 403 em caso de acesso negado.

### C-3 — Travas de primeiro acesso (must_change_password / onboarding) não aplicadas na API
**Arquivo:** `backend/auth.py`

**Problema:** As travas existiam apenas no frontend (router/App.vue). Um usuário recém-criado podia usar o token de login para chamar diretamente qualquer endpoint REST/WS ignorando troca de senha e onboarding.

**Correção:** Em `require_user()`, após validar o token, aplicadas duas travas rígidas:
- **Trava 1 (must_change_password)**: 403 (`X-Reason: must_change_password`) para contas locais com flag true, exceto em `/api/auth/me` e `/api/auth/change-password`.
- **Trava 2 (onboarding)**: 403 (`X-Reason: onboarding_incompleto`) para não-admins com `onboarding_completed=False`, exceto em `/api/auth/me` e prefixos `/api/onboarding` e `/api/perfil`.

### C-4 — Segredos padrão/fracos e fallbacks hardcoded
**Arquivos:** `backend/auth.py`, `backend/storage.py`, `backend/onboarding_storage.py`, `docker-compose.yml`, `*.env.example`

**Problema:** `.env` versionado no disco com `admin:admin`, `JWT_SECRET` placeholder e `minioadmin/minioadmin`; fallbacks hardcoded de credenciais nos módulos Python e no compose.

**Correção:**
- `auth.py`: `raise RuntimeError` no startup se `JWT_SECRET` vazio, for placeholder conhecido ou `<16` caracteres. Valida `AZURE_TENANT_ID` e `AZURE_CLIENT_ID` não nulos.
- `storage.py` e `onboarding_storage.py`: removidos os fallbacks `minioadmin`; `raise RuntimeError` se `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` ausentes.
- `docker-compose.yml`: `MINIO_USER`/`MINIO_PASSWORD` e `DB_USER`/`DB_PASSWORD`/`DB_NAME` usam `${VAR:? mensagem}` (erro explícito se não definidas).
- `.env.example` atualizados para sinalizar as variáveis agora obrigatórias.

### C-5 — Setup do primeiro admin sem rate-limit
**Arquivo:** `backend/routes/auth.py`

**Problema:** `/auth/setup` criava o primeiro admin master sem `@limiter.limit`, expondo a rota a brute-force antes do primeiro admin existir.

**Correção:** Adicionado `@limiter.limit("3/hour")` a `/auth/setup` (3 tentativas/hora/IP).

---

## Vulnerabilidades Altas (A-2 a A-5)

### A-2 — Race condition na geração do cod_fca
**Arquivos:** `backend/routes/fcas.py`, `backend/main.py`

**Problema:** `_get_seq()` usava `count()+1` — aberturas concorrentes podiam gerar o mesmo `cod_fca`.

**Correção:**
- `_get_seq(db, year)` agora acquire **advisory lock transitório** do PostgreSQL (`pg_advisory_xact_key`) por ano, serializando contagem+inserção.
- Contagem filtrada por `FCA.cod_fca.like('FCA-{ano}-%')` (eficiente).
- Migração idempotente em `main.py` cria a constraint `UNIQUE (cod_fca)` (`uq_fcas_cod_fca`) — barreira final de integridade.

### A-3 — Validação e sanitização de uploads (MinIO)
**Arquivos:** `backend/storage.py`, `backend/routes/upload.py`, `backend/routes/perfil.py`

**Problema:** Validação por Content-Type (spoofável); leitura integral em memória antes do check de tamanho (DoS por RAM); filename não sanitizado (path traversal dentro do bucket).

**Correção:**
- `storage.sanitize_filename`: extrai basename, remove `../`,`/`,`\\`, bytes nulos, chars de controle, limita a 100 chars.
- `storage.validate_extension`: allowlist de extensões (`.jpg`,`.jpeg`,`.png`,`.webp`,`.pdf`).
- `storage.upload_file` com parâmetro `prefix` (controlado pelo servidor, não sanitizado) para preservar `avatars/{user_id}`.
- `upload.py` e `perfil.py`: checam `file.size` declarado **antes** de ler; depois lêem em chunks de 1 MB interrompendo no limite; validam **magic bytes** (JPEG/PNG/WEBP/PDF) — não confiam só no Content-Type.

### A-4 — CORS com allow_methods=["*"] + credentials
**Arquivo:** `backend/main.py`

**Problema:** `allow_credentials=True` combinado com `allow_methods=["*"]` enfraquece a política.

**Correção:** Substituído `["*"]` por `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` (explícitos).

### A-5 — Troca de senha sem exigir senha atual
**Arquivos:** `backend/routes/auth.py`, `src/api.js`, `src/views/ChangePasswordView.vue`

**Problema:** `/auth/change-password` aceitava só o token + nova senha — permitia consolidação de acesso sem reautenticação em sessão compartilhada/token roubado.

**Correção:**
- `ChangePasswordRequest` agora exige `senha_atual` (mín. 1 char) + `nova_senha`.
- Backend faz `verify_password(senha_atual, hash)` antes de redefinir — 400 se incorreta.
- Frontend: `api.auth.changePassword(senha_atual, nova_senha)` e a view ganhou campo "Senha atual" com toggle e `autocomplete=current-password`.

---

## Vulnerabilidades Médias (M-1 a M-5)

### M-1 — Verificação explícita de algoritmo JWT
**Arquivo:** `backend/auth.py`

**Problema:** Não havia rejeição explícita de `alg=none` ou algoritmos não permitidos.

**Correção:** `authenticate_token` define `ALLOWED_ALGS = {"HS256","RS256"}` e rejeita antes de decodificar: `alg` vazio/`none` → AuthError; `alg` fora da allowlist → AuthError com o algoritmo informado.

### M-2 — Logs e telemetria de falhas de autenticação
**Arquivos:** `backend/auth.py`, `backend/routes/auth.py`

**Problema:** Falhas de auth/RBAC não eram logadas, dificultando detecção de brute-force/varredura.

**Correção:** Adicionados `logger.warning`/`logger.exception` estruturados com `ip`, `user`, `rota`, `razao` em:
- `authenticate_token`: header ilegível, alg inválido, token local/azure inválido/expirado, sem e-mail, usuário inativo/inexistente.
- `require_user`: RBAC admin negado, must_change_password, onboarding_incompleto.
- `/auth/login`: credenciais inválidas (ip + email).

### M-3 — Limite de volume em exportações CSV/XLSX
**Arquivo:** `backend/routes/fcas.py`

**Problema:** `export_fcas` montava workbook/CSV inteiro em memória sem limite — DoS de memória em export de histórico grande.

**Correção:** `MAX_EXPORT_ROWS = 10000`. Se excedido → 422 pedindo para refinar filtros, antes de montar o arquivo.

### M-4 — Tratamento e log de exceções
**Arquivos:** `backend/routes/fcas.py`, `backend/routes/help.py`, `backend/routes/notifications.py`

**Problema:** `except Exception: pass` e `except Exception as e: raise HTTPException(500)` mascaravam a causa raiz.

**Correção:**
- `export_fcas`: `except HTTPException: raise` primeiro; depois `except Exception` com `logger.exception(...)` antes do 500 (informando formato e total).
- E-mail de abertura/devolutiva em `fcas.py`: `pass` → `logger.exception` com `cod_fca`.
- `_resolve_anexos` (help.py) e comunicado (notifications.py): silenciados → `logger.exception` com a key.
- Loggers criados nos três módulos onde não existiam.

### M-5 — Isolamento de redes no Docker Compose
**Arquivos:** `docker-compose.yml`, `nginx.conf`, `nginx.local.conf`, `.env`, `backend/.env`, `.env.example`

**Problema:** MinIO e backend expostos no host; sem healthchecks de MinIO/backend; sem networks isoladas.

**Correção:**
- Duas networks bridge: `backend_net` (db, minio, backend) e `frontend_net` (frontend, backend).
- **MinIO**: `ports` → `expose` (9000/9001 só internos); healthcheck `mc ready local`.
- **db**: `ports` removido, agora `expose: 5432`; healthcheck sem fallbacks.
- **backend**: `ports: 8000` removido, agora `expose`; healthcheck via `GET /health`; `depends_on` aguarda db **e** minio.
- **Nginx** (`nginx.conf` e `nginx.local.conf`): adicionados `location /api/` e `location /ws` → `proxy_pass http://backend:8000` (com upgrade WebSocket). Única entrada pública: porta 80.
- `VITE_API_URL` aponta para `http://localhost` (Nginx), e `.env` raiz recebeu `MINIO_USER`/`MINIO_PASSWORD`.
- `backend/.env` alinhado com as credenciais do compose e `JWT_SECRET` trocado por segredo forte.

---

## Confirmações (o que já estava correto)

- **SQL Injection:** Todas as queries usam SQLAlchemy ORM `select().where()` parametrizado. O único `sqlalchemy.text()` é em `main.py` para migrações internas com strings fixas (sem input externo) — sem risco.
- **RBAC/FCA isolation nas rotas de FCA:** `_can_view`, `list_fcas`, `responder_fca`, `encerrar`, audit/reabrir/reatribuir/cancelar respeitam setor+empresa juntos; admin vê tudo; cancelados invisíveis para não-admin. Sem IDOR de leitura nessas rotas.
- **Regra "Produção não abre FCA":** `routes/fcas.py` verifica `current["sector"] == "Producao"` e `SECTORS_CAN_OPEN` (não contém Producao) — hardcoded consistente com `business.py`.
- **Rate limiting de /auth/login:** `@limiter.limit("10/minute")` por IP (`get_remote_address`).
- **Azure JWKS TTL 1h:** `auth.py` (`_JWKS_TTL=3600`).
- **Expiração JWT 8h:** `auth.py` (`JWT_EXPIRE_H=8`).
- **help.py / notifications.py** isolados por `created_by`/`user_id`.
- **CSP/X-Frame-Options/nosniff** no nginx.conf.

---

## Follow-up pós-auditoria (correções de runtime aplicadas após validação)

### F-1 — Bug na geração do `cod_fca` (advisory lock com nome de função incorreto)
**Arquivo:** `backend/routes/fcas.py`

**Problema:** A correção A-2 chamava `pg_advisory_xact_key(...)` — função **inexistente** no PostgreSQL (o nome correto é `pg_advisory_xact_lock`, com "L"). O asyncpg ainda falhava ao tipar parâmetros `:k`/`:y` como `unknown`, gerando `UndefinedFunctionError`. Resultado: todo `POST /api/fcas/` ia a 500 — impossível abrir FCA.

**Correção:**
- Nome corrigido para `pg_advisory_xact_lock`.
- Parâmetros inlined (`{LOCK_KEY}`, `{year}`) — ambos controlados pelo servidor (constante hex + `datetime.now().year`), sem input externo, portanto inline-seguros (mesmo critério já validado em "Confirmações" para `text()`).
- A lógica do advisory lock por ano e a constraint `UNIQUE(cod_fca)` permanecem intactas — sem race condition.

### F-2 — Anexos/imagens quebrados após M-5 (presigned URL persistida + MinIO interno)
**Arquivos:** `backend/routes/notifications.py`, `backend/models.py`, `backend/main.py`, `nginx.local.conf`, `docker-compose.yml`

**Problema:** A correção M-5 fechou a porta pública do MinIO (`ports`→`expose`, único entrada = porta 80). Mas o design prévio de comunicados persistia a **presigned URL inteira** no banco (`Notificacao.imagem_url`). Essas URLs (a) **expiram** e (b) quebram quando o endpoint do MinIO muda — exatamente o que ocorreu: notificações antigas apontavam para `http://localhost:9000/...Signature=minioadmin...`, que agora dá `ERR_CONNECTION_REFUSED`/rejeição de credencial.

**Correção (preservando M-5 — MinIO permanece interno):**
- `models.py`/`main.py`: nova coluna `notificacoes.imagem_key` (object_key). Migração idempotente limpa presigned URLs velhas (`imagem_url` com `Signature` → `NULL`).
- `routes/notifications.py`: comunicados agora guardam a **object_key**; a URL é resolvida sob demanda em `GET /notifications/` via `storage.get_presigned_url` → nunca mais expira/quebra.
- `nginx.local.conf`: adicionado reverse proxy `location ~ ^/(fca-anexos|fca-arquivos)/ → http://minio:9000` com `Host: minio:9000` (necessário para validar a assinatura SigV2 gerada pelo backend). CSP ajustada para remover `http://localhost:9000` (não mais necessário).
- `docker-compose.yml`: MinIO adicionado à `frontend_net` (continua **sem** `ports` no host — só o Nginx o alcança pela rede interna).

### F-3 — Fetch fantasma para `/api/fcas/undefined` (422) após criar FCA
**Arquivo:** `src/views/FcaDetalheView.vue`

**Problema:** `registerWsListener` (App.vue) é um slot único compartilhado. Ao sair de `FcaDetalheView` para `FcaNovoView`, o listener `_onWsUpdate` antigo **não era desregistrado**. O backend faz broadcast `fca_updated` **antes** de devolver o HTTP da criação; esse WS event chegava primeiro e disparava o listener stale, que lia `route.params.id` = `undefined` (rota `/fca/novo` não tem `:id`) → `GET /api/fcas/undefined` → 422. Inofensivo (o detail carrega depois normalmente), mas poluía o console.

**Correção:**
- `onUnmounted(() => registerWsListener?.(null))` — limpa o listener ao desmontar.
- Guard defensivo em `loadFca()`: `if (!route.params.id) return` antes de chamar a API.

---

## Operação pós-correção

### Variáveis agora obrigatórias (sem fallback inseguro)

**Raiz `.env`** (compose):
- `DB_USER`, `DB_PASSWORD`, `DB_NAME` (Postgres)
- `MINIO_USER`, `MINIO_PASSWORD` (MinIO root)
- `VITE_AZURE_*`, `VITE_API_URL` (build do frontend)

**`backend/.env`**:
- `DATABASE_URL`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `JWT_SECRET` (≥16 chars, não placeholder)
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` (devem casar com `MINIO_USER`/`MINIO_PASSWORD` do compose)

### Geração de segredo forte para JWT_SECRET
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Comandos Docker
```powershell
# Recriar everything (necessário após mudar VITE_API_URL ou Dockerfile/nginx)
docker compose up -d --build

# Apenas recriar o frontend após alterar .env do Vite
docker compose up -d --build frontend

# Verificar saúde
docker compose ps
curl http://localhost/health        # Nginx -> backend
curl http://localhost/api/auth/setup/status
```

### Observações finais
- Após qualquer alteração em `VITE_*` ou em `Dockerfile`/`nginx*.conf`, reconstrua a imagem do frontend (`--build frontend`).
- O Nginx agora é o único ponto público (porta 80); MinIO/db/backend só são acessíveis dentro das redes internas do compose.
- Para produção, gere credenciais fortes para `DB_*` e `MINIO_*` (não use os valores de exemplo).