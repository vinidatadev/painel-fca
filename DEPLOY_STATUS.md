# Status do Deploy - Sistema FCA

## Situação Atual
Sistema funcionando no servidor `<IP_SERVIDOR>` via Portainer com HTTPS (certificado autoassinado).

## Versões das Imagens Atuais
- **Frontend**: `frontend-app:v9` (última versão estável — notificações com setor)
- **Backend**: `backend-app:v5` (última versão estável — notificações com setor)

## Estrutura no Portainer
### Containers
- **frontend** — nginx com Vue.js buildado
  - Porta: `3003:443` (HTTPS) e `3080:80` (redirect HTTP→HTTPS)
  - Imagem: `frontend-app:v9`
  - Rede: `app-network`

- **backend** — FastAPI Python
  - Porta: `8003:8000` (interno, não exposto)
  - Imagem: `backend-app:v5`
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

### Frontend
```powershell
cd painel-padrao

docker build `
  --build-arg VITE_AZURE_CLIENT_ID=91d632dc-ddb3-4d01-a2cd-b1a4c6f8b056 `
  --build-arg VITE_AZURE_TENANT_ID=4f8fb8aa-7c76-4c81-82f5-24608f5a0b02 `
  --build-arg VITE_AZURE_REDIRECT_URI=https://<IP_SERVIDOR>:3003 `
  --build-arg VITE_API_URL="" `
  -t frontend-app:v9 .

docker save frontend-app:v9 -o frontend-v9.tar
```

### Backend
```powershell
cd painel-padrao\backend

docker build -t backend-app:v5 .

docker save backend-app:v5 -o backend-v5.tar
```

Depois importar os `.tar` no Portainer via **Images → Import** e atualizar os containers.

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
- `nginx.https.conf` — Configuração nginx com HTTPS e proxy
- `certs/nginx.crt` e `certs/nginx.key` — Certificado autoassinado
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
