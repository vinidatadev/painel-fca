# Status do Deploy - Sistema FCA

## Situação Atual
Sistema funcionando no servidor `<IP_SERVIDOR>` via Portainer com HTTPS (certificado autoassinado).

## Versões das Imagens Atuais
- **Frontend**: `frontend-app:v10` (campos DT/Cod Material/Ordem de Venda + dashboard com colunas personalizáveis)
- **Backend**: `backend-app:v6` (campos extras no FCA + preferências de usuário)

## Estrutura no Portainer
### Containers
- **frontend** — nginx com Vue.js buildado
  - Porta: `3003:443` (HTTPS) e `3080:80` (redirect HTTP→HTTPS)
  - Imagem: `frontend-app:v10`
  - Rede: `app-network`

- **backend** — FastAPI Python
  - Porta: `8003:8000` (interno, não exposto)
  - Imagem: `backend-app:v6`
  - Rede: `app-network`
  - ENVs importantes (OBRIGATÓRIAS — o backend falha no startup se faltarem):
    - `JWT_SECRET`: segredo forte (mín. 16 chars, ex.: 64 hex)
    - `AZURE_TENANT_ID`: 4f8fb8aa-7c76-4c81-82f5-24608f5a0b02
    - `AZURE_CLIENT_ID`: 91d632dc-ddb3-4d01-a2cd-b1a4c6f8b056
    - `MINIO_ACCESS_KEY`: access key do MinIO do servidor
    - `MINIO_SECRET_KEY`: secret key do MinIO do servidor
    - `DATABASE_URL`: postgresql+asyncpg://admin:sua_senha_segura@<IP_SERVIDOR>:5432/meu_banco?sslmode=disable
    - `MINIO_ENDPOINT`: <IP_SERVIDOR>:9010
    - `MINIO_PUBLIC_URL`: https://<IP_SERVIDOR>:3003
    - `FRONTEND_URL`: https://<IP_SERVIDOR>:3003
    - `ALLOWED_ORIGINS`: https://<IP_SERVIDOR>:3003
    - `MINIO_BUCKET`: fca-anexos
    - Opcionais: SMTP_HOST/PORT/USER/PASS, FCA_TIMEOUT_HORAS (padrão 72)
  - Obs.: a imagem backend **não embute `.env`** — configure as ENVs acima no container.

### Stacks
- **minio-cs** — MinIO S3-compatible storage
  - Porta: 9010 (S3 API) e 9001 (console)
  
- **postgres-cs** — PostgreSQL 16
  - Porta: 5432

## Como Rebuildar as Imagens

> **Segurança:** as imagens agora usam `.dockerignore` e **não embutem `.env`**
> nem arquivos de credenciais. Todas as variáveis sensíveis são definidas
> **somente** nas ENVs do container no Portainer. Assim o `.tar` pode ser
> compartilhado/armazenado sem vazar segredos.

### 1. Frontend
```powershell
cd painel-padrao

docker build `
  --build-arg VITE_AZURE_CLIENT_ID=91d632dc-ddb3-4d01-a2cd-b1a4c6f8b056 `
  --build-arg VITE_AZURE_TENANT_ID=4f8fb8aa-7c76-4c81-82f5-24608f5a0b02 `
  --build-arg VITE_AZURE_REDIRECT_URI=https://<IP_SERVIDOR>:3003 `
  --build-arg VITE_API_URL="" `
  -t frontend-app:v10 .

docker save frontend-app:v10 -o frontend-v10.tar
```

### 2. Backend
```powershell
cd painel-padrao\backend

docker build -t backend-app:v6 .

docker save backend-app:v6 -o backend-v6.tar
```

### 3. Upload no Portainer
1. **Images → Import** → importar `frontend-v10.tar` e `backend-v6.tar`.
2. **Containers → backend** → imagem para `backend-app:v6` e conferir/definir as
   **ENVs obrigatórias** (ver lista na seção "Estrutura no Portainer").
3. **Containers → frontend** → imagem para `frontend-app:v10`.
4. Recreate/Reapply em ambos os containers.

### 4. Checklist de segurança (a cada deploy)
- [ ] Confirmar `JWT_SECRET`, `AZURE_*`, `MINIO_*`, `DATABASE_URL`, `ALLOWED_ORIGINS` no container backend
- [ ] Não commitar/exportar `.env`, `certs/`, `*.tar` no repositório
- [ ] Verificar logs do backend após o start (deve subir healthy)

## Funcionalidades Implementadas
✅ Login local (email/senha)  
✅ Login Microsoft (Azure AD SSO)  
✅ Gestão de FCAs  
✅ Sistema de notificações em tempo real (WebSocket)  
✅ Upload de anexos (MinIO via proxy nginx)  
✅ Onboarding de novos usuários  
✅ Administração de usuários  
✅ Troca de senha obrigatória (contas locais)  
✅ HTTPS com certificado autoassinado  
✅ CSP configurado corretamente  

## Issues Conhecidos
⚠️ Certificado autoassinado — Chrome não oferece salvar senha automaticamente  
⚠️ Sem vídeos de onboarding cadastrados — usuários pulam automaticamente  

## Próximos Passos (se necessário)
- [ ] Adicionar domínio e Let's Encrypt para certificado confiável
- [ ] Cadastrar vídeos de onboarding no admin
- [ ] Configurar backup automático do PostgreSQL e MinIO
- [ ] Monitoramento com logs centralizados

## Arquivos Importantes
- `nginx.https.conf` — Configuração nginx com HTTPS e proxy (⚠️ **não versionado** no git — contém IP do servidor; mantê-lo apenas no ambiente de deploy)
- `certs/nginx.crt` e `certs/nginx.key` — Certificado autoassinado (⚠️ **não versionados**)
- `.env` (raiz e `backend/`) — Segredos locais (⚠️ **nunca commitados** — protegidos por `.gitignore`)
- `src/api.js` — Cliente API (usa URLs relativas para proxy)
- `backend/auth.py` — Autenticação JWT local + Azure AD
- `backend/routes/` — Endpoints da API

## Comandos Úteis no Portainer Console

### Verificar logs do backend
Container backend → Logs (últimas 100 linhas)

### Testar conexão MinIO
```sh
curl http://<IP_SERVIDOR>:9010/minio/health/live
```

### Verificar nginx config
Container frontend → Console:
```sh
nginx -t
cat /etc/nginx/conf.d/default.conf
```

## Contato/Handoff
Código completo está em `painel-padrao/`.  
Sistema está **rodando e funcional** no ambiente de produção.
