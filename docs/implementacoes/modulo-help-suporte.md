# Implementações — Módulo de Help / Suporte

## 1. Visão geral

Módulo completo de tickets de suporte interno, com fluxo separado para usuários comuns e admins.

- Usuário comum: abre tickets (título + descrição obrigatórios, até 5 anexos) e vê **somente os seus próprios**
- Admin: painel com **todos os tickets**, pode responder e alterar status
- Respostas e mudanças de status propagadas em **tempo real** via WebSocket

---

## 2. Backend

### 2.1 Modelos — `backend/models.py`

Dois novos modelos adicionados ao final do arquivo:

```python
class HelpTicket(Base):
    __tablename__ = "help_tickets"
    id, titulo, descricao, anexo_keys (TEXT[]), status, created_by, created_at, updated_at
    relationships: criado_por (User), mensagens (HelpMensagem)

class HelpMensagem(Base):
    __tablename__ = "help_mensagens"
    id, ticket_id (FK), texto, autor_id (FK), created_at
    relationships: ticket (HelpTicket), autor (User)
```

`status` pode ser: `aberto` | `em_andamento` | `resolvido` | `fechado`

`anexo_keys` é um array de `TEXT` (object keys do MinIO), suportando até 5 anexos por ticket.

### 2.2 Rota — `backend/routes/help.py`

| Método | Endpoint | Acesso | Descrição |
|--------|----------|--------|-----------|
| `POST` | `/api/help/` | todos | Cria ticket |
| `GET` | `/api/help/` | todos | Lista (admin = todos, user = próprios) |
| `GET` | `/api/help/{id}` | todos | Detalhe (user só vê o próprio) |
| `POST` | `/api/help/{id}/mensagens` | todos | Adiciona mensagem/resposta |
| `PATCH` | `/api/help/{id}/status` | admin | Atualiza status |

Regras de negócio:
- Admin que responde um ticket `aberto` → status muda automaticamente para `em_andamento`
- Máximo de 5 `anexo_keys` por ticket (validado no backend)
- URLs pré-assinadas (1 hora) geradas no momento do GET, campo `is_image` detectado pela extensão

### 2.3 Registro em `backend/main.py`

```python
from routes.help import router as help_router
app.include_router(help_router, prefix="/api")
```

Migration executada no lifespan do app:

```sql
-- Garante a coluna (nova instalação)
ALTER TABLE help_tickets ADD COLUMN IF NOT EXISTS anexo_keys TEXT[];

-- Bloco seguro: migra coluna legada `anexo_key` → `anexo_keys` apenas se existir
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'help_tickets' AND column_name = 'anexo_key'
    ) THEN
        UPDATE help_tickets
           SET anexo_keys = ARRAY[anexo_key]
         WHERE anexo_key IS NOT NULL AND anexo_keys IS NULL;
        ALTER TABLE help_tickets DROP COLUMN anexo_key;
    END IF;
END$$;
```

---

## 3. Frontend

### 3.1 API client — `src/api.js`

Novo objeto `api.help` adicionado:

```js
help: {
  list: ()           => GET  /api/help/
  get: (id)          => GET  /api/help/{id}
  create: (data)     => POST /api/help/          { titulo, descricao, anexo_keys[] }
  responder: (id, texto) => POST /api/help/{id}/mensagens
  status: (id, status)   => PATCH /api/help/{id}/status
}
```

### 3.2 View do usuário — `src/views/HelpView.vue`

Funcionalidades:
- Lista dos próprios tickets com thumbnail inline de imagens
- Modal de criação com:
  - Campos título e descrição (obrigatórios)
  - **Drop zone** — clique, arraste ou solte arquivos
  - **Ctrl+V** — cola print/screenshot diretamente como anexo
  - **Preview imediato** — imagens mostram thumb 72×72, PDFs mostram ícone com nome
  - Upload paralelo e imediato por arquivo; botão bloqueado enquanto há uploads em andamento
  - Remoção individual de cada arquivo antes de enviar
- Detalhe do ticket com grid de anexos clicáveis e histórico de mensagens
- Usuário pode adicionar mensagens em tickets abertos/em andamento
- Atualização automática via WebSocket (`help_ticket_novo`, `help_ticket_atualizado`)

### 3.3 Painel admin — `src/views/AdminHelpView.vue`

Funcionalidades:
- Tabela com todos os tickets: título, usuário, status, data de abertura, qtd de respostas
- Filtro por status + busca por título (reativo, sem requisição extra)
- Modal de detalhe com:
  - Grid de anexos (imagens com preview, docs com link)
  - Histórico de mensagens com destaque visual para respostas do suporte
  - Campo de resposta
  - Dropdown de status inline (muda ao selecionar, chama PATCH imediatamente)
- Atualização automática via WebSocket

### 3.4 Rotas — `src/router.js`

```js
{ path: '/help',       component: HelpView }       // usuários
{ path: '/admin/help', component: AdminHelpView }   // admins
```

### 3.5 Navbar — `src/App.vue`

```html
<!-- aparece só para não-admins -->
<RouterLink v-if="user.role !== 'admin'" to="/help">Suporte</RouterLink>

<!-- aparece só para admins -->
<RouterLink v-if="user.role === 'admin'" to="/admin/help">Help</RouterLink>
```

---

## 4. Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---------|------|-------------|
| `backend/models.py` | modificado | +`HelpTicket`, +`HelpMensagem` |
| `backend/routes/help.py` | criado | rota completa do módulo |
| `backend/main.py` | modificado | import + include do router, migration no lifespan |
| `src/api.js` | modificado | +`api.help` |
| `src/router.js` | modificado | +`/help`, +`/admin/help` |
| `src/App.vue` | modificado | links na navbar por role |
| `src/views/HelpView.vue` | criado | view do usuário |
| `src/views/AdminHelpView.vue` | criado | painel admin |
