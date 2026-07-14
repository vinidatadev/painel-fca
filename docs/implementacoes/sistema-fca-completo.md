# Implementações — Sistema FCA Completo

Documentação de todas as funcionalidades implementadas para o sistema FCA (Ficha de Correção de Ação), construído sobre o projeto base de login seguro com autenticação local e Microsoft.

---

## 1. Arquitetura Geral

**Stack:**
- Frontend: Vue 3 + Vue Router + Vite
- Backend: Python / FastAPI (async)
- Banco: PostgreSQL (via SQLAlchemy asyncpg)
- Storage: MinIO (S3-compatível)
- Auth: JWT local (HS256) + Azure AD / Microsoft (RS256)

**Estrutura de containers (docker-compose):**
- `frontend` — Vue buildado + nginx
- `backend` — FastAPI + Uvicorn
- `db` — PostgreSQL 16
- `minio` — object storage para anexos e avatares

---

## 2. Modelo de Dados

### `users`
Expandido com campos de negócio:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| company | VARCHAR(20) | ACI_MATRIZ / ACI_FILIAL / SINOBRAS / ACC |
| sector | VARCHAR(30) | ACL / PCP / Qualidade / MEP / Expedicao / Producao / Comercial / Customer_Service |
| role | VARCHAR(10) | admin / user |
| matricula | VARCHAR(20) | matrícula funcional |
| turno | CHAR(1) | A / B / C / D |
| telefone | VARCHAR(20) | para notificações SMS |
| avatar_url | TEXT | object key no MinIO |
| notif_email | BOOLEAN | flag de notificação por e-mail |
| notif_sms | BOOLEAN | flag de notificação por SMS |
| notif_push | BOOLEAN | flag de notificação na página |

### `fcas`
FCA principal com fila de etapas dinâmica.

| Campo relevante | Descrição |
|-----------------|-----------|
| cod_fca | FCA-{ano}-{seq:04d} gerado automaticamente |
| remessas | ARRAY(BIGINT) — lista de remessas |
| status | aberto / em_andamento / aguardando_devolutiva / encerrado |

### `fca_etapas`
Fila ordenada de tratamento.

| Campo relevante | Descrição |
|-----------------|-----------|
| order_index | posição na fila, incrementa a cada encaminhamento |
| status | pendente / em_andamento / concluido |
| sla_deadline | TIMESTAMP — deadline calculado pela regra de SLA |

### `opcoes_lista`
Listas configuráveis pelo admin (causas, ações, UFs). Suporta ativação/desativação sem quebrar histórico.

### `sla_regras`
Regras de prazo por escopo.

| Campo | Descrição |
|-------|-----------|
| empresa | NULL = global |
| setor | NULL = toda a empresa |
| valor | número (ex: 4) |
| unidade | minuto / hora / dia |
| prazo_minutos | calculado na criação |

---

## 3. Backend — Rotas Implementadas

### Auth (`/api/auth`)
- `POST /login` — autenticação local com JWT
- `GET /me` — dados completos do usuário logado
- `POST /setup` — cria o primeiro admin (bloqueado após primeiro uso)
- `GET /setup/status` — verifica se o setup está disponível

### Usuários (`/api/usuarios`) — somente admin
- CRUD completo com validação empresa×setor
- Suporte a `auth_provider: local | microsoft`
- Soft delete via `PATCH /{id}/desativar`

### FCAs (`/api/fcas`)
- `GET /` — listagem com filtros e paginação, filtrada por visibilidade
- `POST /` — abertura com triagem automática e validação de setor próprio
- `GET /{id}` — detalhe completo com etapas
- `POST /{id}/responder` — responde a etapa atual, suporta encaminhamentos em cascata
- `POST /{id}/encerrar` — solicitante confirma ciência (aguardando_devolutiva → encerrado)

**Regras de visibilidade:**
- admin vê todos
- user vê FCAs onde `setor_solicitante+empresa_solicitante` bate com o seu, ou onde tem/teve etapa na fila

**Validações:**
- Produção não pode abrir FCA
- Não pode abrir FCA para o próprio setor/empresa
- Combinações inválidas empresa×setor bloqueadas

### Dashboard (`/api/dashboard`)
- Minha fila (etapas pendentes/em andamento do setor)
- Contadores por status (abertos, em andamento, aguardando devolutiva, encerrados)

### Upload (`/api/upload`)
- `POST /` — upload de arquivo para MinIO, retorna `object_key`
- `GET /{object_key}/url` — gera URL pré-assinada temporária (1h)
- URL pública substitui host interno `minio:9000` pelo `MINIO_PUBLIC_URL` configurado no .env

### Opções (`/api/opcoes`)
- `GET /` — listas ativas para formulários (causas, ações, UFs + empresas/setores estáticos)
- `GET /admin` — todas as opções incluindo inativas (admin)
- CRUD completo para causas, ações, UFs com soft delete

### SLA (`/api/sla`) — somente admin
- CRUD de regras de prazo por escopo (global → empresa → setor+empresa)
- Hierarquia de busca: mais específico tem prioridade

### Perfil (`/api/perfil`)
- `GET /` — dados do usuário logado
- `PATCH /` — atualiza matrícula, turno, telefone e flags de notificação
- `POST /avatar` — upload de foto de perfil
- `DELETE /avatar` — remove foto

---

## 4. Lógica de Negócio

### Triagem automática
Ao criar um FCA, o sistema lê `area_causadora + empresa_causadora` e monta a primeira etapa da fila usando a tabela `TRIAGEM` em `business.py`.

### Fila dinâmica
- Etapa ativa = menor `order_index` com status `pendente` ou `em_andamento`
- Ao responder, o responsável pode encaminhar para N setores adicionais
- Novos setores entram no final da fila com `order_index` sequencial
- Quando a fila esgota → status `aguardando_devolutiva` + e-mail de devolutiva

### SLA
Ao criar cada etapa, busca a regra de SLA na hierarquia:
1. Setor + empresa específicos
2. Toda a empresa
3. Global

Salva `sla_deadline = entered_at + prazo_minutos` na etapa. O frontend calcula e exibe o badge em tempo real, atualizando a cada 30 segundos.

### Remessas múltiplas
Campo `remessas` é um `ARRAY(BIGINT)` no PostgreSQL. O frontend renderiza campos dinâmicos com `+` / `✕`.

---

## 5. Frontend — Páginas e Componentes

### Páginas
| Rota | Descrição |
|------|-----------|
| `/dashboard` | Minha fila + indicadores de status |
| `/fca` | Listagem com filtros por status, área causadora e data |
| `/fca/novo` | Formulário de abertura com validação de setor próprio |
| `/fca/:id` | Detalhe: dados, histórico de etapas, formulário de resposta, fila pendente, encerramento |
| `/perfil` | Avatar, matrícula, turno, telefone, flags de notificação |
| `/admin/usuarios` | CRUD de usuários com filtros |
| `/admin/usuarios/novo` e `/:id` | Formulário de usuário com tipo de login (local/Microsoft) |
| `/admin/sla` | CRUD de regras de SLA com preview de prazo |
| `/admin/config` | Gestão de causas, ações e UFs (listas configuráveis) |

### Componentes
| Arquivo | Descrição |
|---------|-----------|
| `SlaBadge.vue` | Badge animado de SLA: "⏱ Vence em 3h" ou "⚠ Atrasado 2min", atualiza a cada 30s |
| `UserAvatar.vue` | Exibe foto ou bolinha com iniciais em cor determinística pelo nome |

### Sessão persistente
Token local armazenado em `localStorage` (persiste entre abas). MSAL configurado com `cacheLocation: 'localStorage'` para o mesmo comportamento com login Microsoft.

---

## 6. E-mails

Configurados via variáveis de ambiente (`SMTP_HOST`, `SMTP_USER`, etc). Se `SMTP_HOST` estiver vazio, apenas loga no console sem enviar — comportamento padrão para desenvolvimento.

**Tipos de e-mail:**
- **Abertura** — disparado ao setor responsável da etapa 1 (ou próxima após encaminhamento). Para etapas ACL, inclui a UF no assunto.
- **Devolutiva** — disparado ao setor solicitante quando a fila esgota, com histórico consolidado de todas as etapas.

**Configuração por setor** via variáveis de ambiente:
```
EMAIL_SECTOR_Expedicao_ACI_MATRIZ=expedicao-matriz@empresa.com
EMAIL_SECTOR_Customer_Service_ACC=cs@empresa.com
```

---

## 7. Variáveis de Ambiente Relevantes

### `backend/.env`
```env
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET=...
JWT_EXPIRE_H=8
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=fca-anexos
MINIO_PUBLIC_URL=http://localhost:9000
FRONTEND_URL=http://localhost
SMTP_HOST=              # vazio = e-mails apenas logados
EMAIL_FROM=noreply@fca.local
```

---

## 8. Primeiro Acesso

1. `docker compose up --build`
2. Acesse `http://localhost`
3. O formulário "Primeira vez?" aparece automaticamente quando o banco está vazio
4. Crie o admin (Customer Service / ACC)
5. Acesse `/admin/usuarios` para criar os demais usuários
6. Acesse `/admin/sla` para configurar os prazos de resposta
7. Acesse `/admin/config` para personalizar causas, ações e UFs

---

## 9. Recriar Banco (quando há mudanças no schema)

O SQLAlchemy usa `create_all` que não altera tabelas existentes. Para aplicar mudanças de schema em desenvolvimento:

```bash
docker compose down -v   # apaga volumes (banco + MinIO)
docker compose up --build
```
