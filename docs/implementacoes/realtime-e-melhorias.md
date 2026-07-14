# Implementações — Realtime, Ordenação e Correções

## 1. WebSocket — Atualizações em tempo real

### Problema
A lista de FCAs e o Dashboard só atualizavam com F5 manual.

### Solução
Implementado WebSocket global no `App.vue` que mantém uma conexão persistente com o backend. Quando qualquer FCA é criado ou atualizado, o backend faz broadcast para todos os clientes conectados, que recarregam os dados automaticamente.

### Arquivos criados/modificados
- `backend/ws_manager.py` — gerencia conexões WebSocket ativas e faz broadcast
- `backend/main.py` — expõe o endpoint `/ws` e importa o manager
- `backend/routes/fcas.py` — chama `manager.broadcast("fca_updated")` nos endpoints `POST /`, `POST /{id}/responder` e `POST /{id}/encerrar`
- `src/App.vue` — conecta no WebSocket ao montar, reconecta automaticamente em caso de queda (retry 3s), disponibiliza `registerWsListener` via `provide` para as views filhas
- `src/views/FcaListView.vue` — registra `load` como listener via `inject('registerWsListener')`
- `src/views/DashboardView.vue` — registra `load` como listener via `inject('registerWsListener')`

### Como funciona
1. `App.vue` abre conexão `ws://localhost:8000/ws` ao iniciar
2. Views que precisam de realtime chamam `registerWsListener(fn)` no `onMounted` e `registerWsListener(null)` no `onUnmounted`
3. Ao receber `"fca_updated"`, o App chama o listener ativo, que recarrega os dados da view

---

## 2. Ordenação da fila do Dashboard

### Problema
"Minha Fila" no Dashboard não tinha ordenação definida — o banco retornava em ordem arbitrária.

### Solução
Adicionado `.order_by(FCA.created_at.asc())` na query do `dashboard.py`, aplicado após o `if/else` de admin/usuário para cobrir os dois casos.

### Arquivo modificado
- `backend/routes/dashboard.py`

---

## 3. Upload de avatar — erro 413

### Problema
Fotos maiores eram rejeitadas com `413 Request Entity Too Large` pelo Uvicorn (h11).

### Solução
Adicionada a flag `--h11-max-incomplete-event-size 10485760` (10 MB) no comando de inicialização do Uvicorn. O backend ainda valida e rejeita arquivos acima de 2 MB com mensagem amigável (`MAX_AVATAR_SIZE` em `routes/perfil.py`).

### Arquivo modificado
- `backend/Dockerfile`

---

## 4. Avatar não exibindo após upload

### Problema
Dois bugs combinados impediam a exibição do avatar:
1. `PerfilView.vue` usava um `computed async` para buscar a URL pré-assinada — Vue não suporta computed assíncrono, então sempre retornava uma Promise não resolvida
2. `App.vue` passava `avatarUrl="null"` hardcoded para o `UserAvatar` no navbar

### Solução
- Removido o `computed async` do `PerfilView`, passando a usar o `avatarUrl` ref que já existia e era carregado corretamente via `loadAvatarUrl()`
- `App.vue` agora busca a URL pré-assinada ao restaurar a sessão (`loadAvatar`) e a disponibiliza via `avatarUrl` ref para o `UserAvatar` no navbar
- Adicionado `provide('reloadAvatar')` no App para que o `PerfilView` possa atualizar o avatar do navbar após trocar ou remover a foto

### Arquivos modificados
- `src/App.vue`
- `src/views/PerfilView.vue`

---

## 5. CSP bloqueando imagens do MinIO

### Problema
O nginx bloqueava imagens vindas de `http://localhost:9000` (MinIO) por violação de Content Security Policy.

### Solução
Adicionado `http://localhost:9000` ao `img-src` da CSP no nginx local.

### Arquivo modificado
- `nginx.local.conf`
