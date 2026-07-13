# API — Sistema FCA

Backend: Python (FastAPI) · Autenticação: JWT Bearer

---

## Convenções

- Todas as rotas (exceto `/auth/login`) exigem header `Authorization: Bearer <token>`
- Respostas de erro seguem o padrão `{ "detail": "mensagem" }`
- Datas em ISO 8601: `2025-07-09T14:30:00Z`
- IDs em UUID v4

---

## Auth

### `POST /auth/login`
Autentica o usuário e retorna o token JWT.

**Body:**
```json
{
  "email": "usuario@empresa.com",
  "password": "senha123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "João Silva",
    "email": "joao@empresa.com",
    "company": "ACI_MATRIZ",
    "sector": "Expedição",
    "role": "user"
  }
}
```

**Erros:** `401` credenciais inválidas · `403` usuário inativo

---

### `GET /auth/me`
Retorna os dados do usuário logado a partir do token.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "João Silva",
  "email": "joao@empresa.com",
  "company": "ACI_MATRIZ",
  "sector": "Expedição",
  "matricula": "12345",
  "turno": "A",
  "role": "user"
}
```

---

## Usuários (somente admin)

### `GET /usuarios`
Lista todos os usuários.

**Query params:** `company` · `sector` · `active` (bool) · `page` · `page_size`

**Response 200:**
```json
{
  "total": 42,
  "page": 1,
  "items": [
    {
      "id": "uuid",
      "name": "João Silva",
      "email": "joao@empresa.com",
      "company": "ACI_MATRIZ",
      "sector": "Expedição",
      "role": "user",
      "matricula": "12345",
      "turno": "A",
      "active": true,
      "created_at": "2025-01-10T08:00:00Z"
    }
  ]
}
```

---

### `POST /usuarios`
Cria um novo usuário.

**Body:**
```json
{
  "name": "Maria Souza",
  "email": "maria@empresa.com",
  "password": "senha_segura",
  "company": "SINOBRAS",
  "sector": "MEP",
  "role": "user",
  "matricula": "67890",
  "turno": "B"
}
```

**Response 201:** objeto do usuário criado (sem `password_hash`)

**Erros:** `400` email já cadastrado · `422` combinação empresa/setor inválida

---

### `GET /usuarios/{id}`
Retorna um usuário pelo ID.

**Response 200:** objeto completo do usuário

**Erros:** `404` não encontrado

---

### `PUT /usuarios/{id}`
Atualiza dados do usuário.

**Body:** qualquer subconjunto dos campos de criação (exceto email)

**Response 200:** objeto atualizado

---

### `PATCH /usuarios/{id}/desativar`
Desativa o usuário (soft delete — `active = false`).

**Response 200:** `{ "active": false }`

---

## FCAs

### `GET /fcas`
Lista FCAs visíveis ao usuário logado.

- Usuário comum: apenas FCAs onde abriu ou tem/teve etapa na fila (setor + empresa)
- Admin: todos

**Query params:** `status` · `company` · `sector` · `area_causadora` · `data_inicio` · `data_fim` · `page` · `page_size`

**Response 200:**
```json
{
  "total": 15,
  "page": 1,
  "items": [
    {
      "id": "uuid",
      "cod_fca": "FCA-2025-0042",
      "causa": "Material indisponível",
      "area_causadora": "MEP",
      "empresa_causadora": "ACI_MATRIZ",
      "setor_solicitante": "Expedição",
      "empresa_solicitante": "ACI_MATRIZ",
      "uf": "CE",
      "numero_remessa": 83139570,
      "status": "em_andamento",
      "etapa_atual": {
        "setor": "ACL",
        "empresa": "ACI_MATRIZ",
        "order_index": 2
      },
      "created_at": "2025-07-09T10:00:00Z"
    }
  ]
}
```

---

### `POST /fcas`
Abre um novo FCA.

Setor e empresa do solicitante são extraídos do token JWT — não enviados no body.

**Body:**
```json
{
  "causa": "Material indisponível",
  "area_causadora": "MEP",
  "empresa_causadora": "ACI_MATRIZ",
  "acao": "Confere o estoque e a programação do item junto com PCP",
  "uf": "CE",
  "numero_remessa": 83139570,
  "detalhe": "Item sem estoque para carregamento",
  "anexo_url": "uploads/evidencia.jpg"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "cod_fca": "FCA-2025-0042",
  "status": "aberto",
  "etapas": [
    {
      "id": "uuid",
      "order_index": 1,
      "setor": "MEP",
      "empresa": "ACI_MATRIZ",
      "status": "pendente"
    }
  ]
}
```

**Erros:** `422` combinação área causadora/empresa inválida · `403` setor não pode abrir FCA (Produção)

---

### `GET /fcas/{id}`
Retorna o FCA completo com histórico de etapas.

**Response 200:**
```json
{
  "id": "uuid",
  "cod_fca": "FCA-2025-0042",
  "causa": "Material indisponível",
  "acao": "Confere o estoque e a programação do item junto com PCP",
  "uf": "CE",
  "numero_remessa": 83139570,
  "detalhe": "Item sem estoque para carregamento",
  "anexo_url": "uploads/evidencia.jpg",
  "setor_solicitante": "Expedição",
  "empresa_solicitante": "ACI_MATRIZ",
  "area_causadora": "MEP",
  "empresa_causadora": "ACI_MATRIZ",
  "status": "em_andamento",
  "created_by": { "id": "uuid", "name": "João Silva" },
  "created_at": "2025-07-09T10:00:00Z",
  "etapas": [
    {
      "id": "uuid",
      "order_index": 1,
      "setor": "MEP",
      "empresa": "ACI_MATRIZ",
      "status": "concluido",
      "problema_solucionado": false,
      "devolutiva": "Sem estoque disponível, encaminhando para ACL retirar de rota",
      "respondido_por": { "id": "uuid", "name": "Carlos MEP" },
      "entered_at": "2025-07-09T10:05:00Z",
      "concluded_at": "2025-07-09T11:30:00Z"
    },
    {
      "id": "uuid",
      "order_index": 2,
      "setor": "ACL",
      "empresa": "ACI_MATRIZ",
      "status": "pendente",
      "problema_solucionado": null,
      "devolutiva": null,
      "respondido_por": null,
      "entered_at": "2025-07-09T11:30:00Z",
      "concluded_at": null
    }
  ]
}
```

**Erros:** `403` usuário sem acesso a este FCA · `404` não encontrado

---

### `POST /fcas/{id}/responder`
Responde a etapa atual do FCA. Só pode ser chamado pelo usuário cujo setor/empresa bate com a etapa ativa.

**Body — sem encaminhamento:**
```json
{
  "problema_solucionado": true,
  "devolutiva": "Carga ajustada conforme solicitado",
  "encaminhar": []
}
```

**Body — com encaminhamento:**
```json
{
  "problema_solucionado": false,
  "devolutiva": "Sem estoque, precisa retirar de rota e cancelar remessa",
  "encaminhar": [
    { "setor": "ACL", "empresa": "ACI_MATRIZ" },
    { "setor": "Customer_Service", "empresa": "ACC" }
  ]
}
```

**Response 200:**
```json
{
  "fca_status": "em_andamento",
  "etapa_concluida": { "order_index": 1, "setor": "MEP" },
  "proxima_etapa": { "order_index": 2, "setor": "ACL", "empresa": "ACI_MATRIZ" }
}
```

Quando a fila se esgota:
```json
{
  "fca_status": "aguardando_devolutiva",
  "etapa_concluida": { "order_index": 3, "setor": "Customer_Service" },
  "proxima_etapa": null
}
```

**Erros:** `403` não é a vez do setor do usuário · `409` etapa já concluída · `422` encaminhamento com combinação inválida

---

## Dashboard

### `GET /dashboard`
Retorna os dados agregados para o dashboard do usuário logado.

**Response 200:**
```json
{
  "minha_fila": {
    "total": 3,
    "itens": [ /* lista resumida de FCAs pendentes para o setor */ ]
  },
  "acompanhamento": {
    "abertos": 5,
    "em_andamento": 8,
    "aguardando_devolutiva": 2,
    "encerrados": 47
  }
}
```

---

## Upload

Arquivos são armazenados no **MinIO** (object storage compatível com S3). O backend nunca serve o arquivo diretamente — gera uma URL pré-assinada com expiração para acesso temporário seguro.

Bucket padrão: `fca-anexos`  
Estrutura de path: `{ano}/{mes}/{dia}/{uuid}_{nome_original}`  
Ex: `2025/07/09/a1b2c3_evidencia.jpg`

---

### `POST /upload`
Faz upload de um anexo. Deve ser chamado antes de criar o FCA — retorna a `object_key` para ser enviada no campo `anexo_url` do `POST /fcas`.

**Body:** `multipart/form-data` com campo `file`

**Response 201:**
```json
{
  "object_key": "2025/07/09/a1b2c3_evidencia.jpg",
  "filename": "evidencia.jpg",
  "size_bytes": 204800,
  "content_type": "image/jpeg"
}
```

**Erros:** `413` arquivo maior que 20MB · `415` tipo não permitido (aceito: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`)

---

### `GET /upload/{object_key}/url`
Gera uma URL pré-assinada temporária para visualizar ou baixar o anexo.

Usado pelo frontend ao abrir o detalhe do FCA — nunca expõe credenciais do MinIO ao cliente.

**Response 200:**
```json
{
  "url": "http://minio:9000/fca-anexos/2025/07/09/a1b2c3_evidencia.jpg?X-Amz-Signature=...",
  "expires_in_seconds": 3600
}
```

**Erros:** `404` objeto não encontrado no MinIO
