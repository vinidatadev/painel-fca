# Sistema FCA — Documentação de Apresentação

> Versão 2.0 · Julho 2026

---

## O que é o Sistema FCA?

O Sistema FCA é uma plataforma web desenvolvida para gerenciar o ciclo de vida de **Fichas de Correção de Ação (FCA)**, substituindo o fluxo anterior no Pipefy. Ele centraliza a abertura, o tratamento e o encerramento de não-conformidades entre os setores das empresas do grupo, com rastreabilidade completa e controle de acesso por setor/empresa.

---

## Empresas e Setores Suportados

| Empresa | Setores |
|---|---|
| ACI Matriz | ACL, PCP, Qualidade, MEP, Expedição, Produção |
| ACI Filial | ACL, PCP, Qualidade, MEP, Expedição, Produção |
| SINOBRAS | ACL, PCP, Qualidade, MEP, Expedição, Produção |
| ACC | Comercial, Customer Service |

> Customer Service (ACC) é o setor administrador do sistema.

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Frontend | Vue.js 3 + Vite + Chart.js |
| Backend | Python / FastAPI (async) |
| Banco de Dados | PostgreSQL 16 |
| Armazenamento de Arquivos | MinIO (compatível S3) |
| Autenticação Corporativa | Microsoft Azure AD (OAuth2) |
| Infraestrutura | Docker Compose + Nginx |
| Comunicação em Tempo Real | WebSocket |

---

## Funcionalidades Principais

### 1. Ciclo de Vida do FCA

Cada FCA percorre um fluxo de estados bem definido:

```
Aberto → Em Andamento → Aguardando Devolutiva → Encerrado
```

A grande diferença deste sistema para processos tradicionais é a **fila dinâmica de etapas**: ao criar um FCA, o sistema determina automaticamente qual setor deve tratar primeiro, com base na área causadora e na empresa. Cada setor pode, ao responder, encaminhar o FCA para setores adicionais — a fila cresce conforme necessário.

---

### 2. Abertura de FCA

Campos do formulário:

- Causa (lista configurável: Material oxidado, Excesso de PBT, etc.)
- Área Causadora e Empresa do Causador (com validação de combinações válidas)
- Ação necessária
- UF, Número(s) de Remessa
- Detalhe / Observação (texto livre)
- Anexos / Evidências (múltiplos arquivos)

Empresa e setor do solicitante são preenchidos automaticamente pelo perfil do usuário logado. Regras de negócio são validadas no backend — combinações inválidas de empresa+setor são bloqueadas.

---

### 3. Tratamento e Fluxo

Quando chega a vez de um setor:

- O responsável recebe notificação em tempo real
- Visualiza todos os dados da abertura e o histórico de etapas anteriores
- Responde informando: **Problema Solucionado (Sim/Não)** + **Devolutiva** + **Encaminhamentos** (se necessário)
- O sistema avança para o próximo setor da fila ou encerra o FCA

---

### 4. Dashboard

Cada usuário tem uma visão personalizada ao entrar no sistema:

- **KPIs** em tempo real: Abertos, Em Andamento, Aguardando Devolutiva, Encerrados, Atrasados
- **Minha Fila**: lista dos FCAs que aguardam ação do seu setor/empresa
- **Gráficos**: série temporal (semana/mês) e ranking das top 5 áreas causadoras
- Atualização automática via WebSocket — sem precisar recarregar a página

---

### 5. Listagem e Filtros

- Filtros por: status, área causadora, intervalo de datas, busca por código/causa
- Chips visuais de filtros ativos
- Paginação por 20 itens
- **Exportação para Excel e CSV** com um clique

---

### 6. SLA (Service Level Agreement)

- Cada setor/empresa tem um prazo configurável para responder
- Prazos podem ser definidos em minutos, horas ou dias
- Hierarquia de regras: Global → Por Empresa → Por Setor+Empresa
- Badge visual na listagem e na timeline mostrando se está no prazo ou atrasado
- **Encerramento automático**: FCAs em "Aguardando Devolutiva" há mais de 72h (configurável) são encerrados pelo sistema

---

### 7. Notificações

Os usuários recebem alertas por múltiplos canais, configuráveis por preferência:

- **In-app** (painel de notificações no topo da tela, tempo real via WebSocket)
- **E-mail**
- **SMS**
- **Som** (4 opções de alerta sonoro)

Eventos que geram notificação: criação de FCA, atualização de etapa, comentários internos, novos tickets de suporte, comunicados do administrador.

---

### 8. Comentários Internos

Thread de comentários em cada FCA, visível apenas para os setores envolvidos. Permite troca de informações sem alterar o fluxo oficial de etapas.

---

### 9. Módulo de Suporte (Help)

Usuários podem abrir tickets de suporte diretamente no sistema. Admins visualizam e respondem todos os tickets. Suporte a múltiplos anexos e histórico de mensagens.

---

### 10. Onboarding

Novos usuários são direcionados obrigatoriamente para assistir aos vídeos de treinamento antes de acessar o sistema. O progresso é rastreado individualmente. O admin gerencia quais vídeos estão disponíveis.

---

### 11. Painel Administrativo (Customer Service)

Funcionalidades exclusivas do administrador:

- **Gestão de Usuários**: criação, edição, desativação, configuração de permissões
- **Configuração de SLA**: regras por empresa e setor
- **Configuração de Listas**: editar causas, ações e UFs disponíveis no formulário
- **Comunicados**: envio de notificações em broadcast para todos os usuários
- **Relatórios / BI**: exportação e análise histórica de FCAs (com controle de acesso por flag)
- **Ações sobre FCAs**: reabrir, reatribuir etapa, cancelar
- **Logs de Auditoria**: histórico imutável de todas as ações realizadas no sistema
- **Gestão de Tickets de Suporte**
- **Gestão de Onboarding**: upload e organização de vídeos de treinamento

---

## Segurança

### Autenticação

- **Dual Auth**: Login local (email + senha com bcrypt) **ou** login corporativo via **Microsoft Azure AD** (OAuth2 / RS256)
- **JWT**: Tokens com expiração configurável (padrão 8 horas). Certificados Azure cacheados com TTL de 1 hora
- **Primeiro acesso**: Usuário é forçado a trocar a senha antes de acessar qualquer funcionalidade
- **Onboarding obrigatório**: Além da senha, o onboarding deve ser concluído antes do acesso pleno

### Controle de Acesso

- **RBAC (Role-Based)**: papéis `admin` e `user` com permissões distintas
- **Isolamento por setor/empresa**: Cada usuário enxerga apenas os FCAs onde seu setor está ou esteve na fila. Nenhum dado de outro setor ou empresa é visível
- **Produção bloqueada**: O setor Produção não pode abrir FCA (regra de negócio hardcoded no backend)
- **Validação de combinações**: Combinações inválidas de empresa+setor são rejeitadas na API, não apenas no frontend
- **Usuários inativos**: `is_active = False` impede qualquer acesso sem necessidade de excluir o registro

### Rate Limiting

- Limitação de taxa de requisições por IP/usuário via **slowapi**
- Proteção contra ataques de força bruta nos endpoints de autenticação

### Proteção de Dados

- **Senhas**: Nunca armazenadas em texto claro — hash bcrypt com salt
- **ORM com queries parametrizadas**: SQLAlchemy previne SQL Injection
- **Soft delete**: Dados não são deletados fisicamente, preservando rastreabilidade
- **Variáveis sensíveis em `.env`**: Segredos (JWT_SECRET, credenciais do banco, Azure) nunca estão no código-fonte

### Armazenamento Seguro de Arquivos

- Arquivos armazenados no MinIO com chave UUID (`/ano/mes/dia/uuid_filename`)
- Downloads via **Presigned URLs** com expiração — nunca exposição direta
- **Limpeza automática**: Job a cada 1 hora remove arquivos sem referência no banco com mais de 2 horas

### Auditoria

- Tabela `audit_logs` **imutável**: registra todas as ações relevantes (criação, resposta, encerramento, timeout, ações admin)
- Rastreabilidade completa: usuário, ação, detalhe e timestamp em cada registro
- Visível para o admin no detalhe de cada FCA

### Infraestrutura

- Comunicação preparada para **HTTPS** via Nginx
- **WebSocket autenticado**: conexão vinculada ao `user_id`
- **CORS**: whitelist de origens permitidas configurável
- Arquitetura **stateless** (JWT): sem sessões no servidor, facilitando escalonamento

---

## Arquitetura em Resumo

```
┌────────────────────────────┐
│  Frontend — Vue.js 3 (SPA) │
│  Nginx (proxy reverso)     │
└────────────┬───────────────┘
             │ REST API + WebSocket
             ▼
┌────────────────────────────┐
│  Backend — FastAPI (async) │
│  13 módulos de rotas       │
└──────┬─────────┬───────────┘
       │         │
       ▼         ▼
  PostgreSQL   MinIO
  (dados)    (arquivos)
       │
       ▼
  Azure AD (auth corporativa)
  SMTP (e-mail)
```

O backend expõe 13 grupos de rotas REST (auth, users, fcas, dashboard, upload, sla, perfil, help, admin, notifications, bi, onboarding, opcoes) e um endpoint WebSocket para atualizações em tempo real.

---

## Perfis de Acesso

| Perfil | Pode abrir FCA | Vê FCAs | Responde etapas | Acesso admin |
|---|:---:|---|:---:|:---:|
| Usuário (setor operacional) | ✅ (exceto Produção) | Apenas do seu setor/empresa | ✅ (quando é sua vez) | ❌ |
| Admin (Customer Service) | ✅ | Todos | ✅ | ✅ |

---

## Jobs em Background

O sistema executa tarefas automáticas sem intervenção manual:

- **Timeout de FCAs**: a cada hora, encerra FCAs travados em "Aguardando Devolutiva" por mais de 72h (configurável)
- **Limpeza de arquivos órfãos**: a cada hora, remove do MinIO arquivos sem referência no banco com mais de 2 horas

---

## Implantação

O sistema roda inteiramente via **Docker Compose** com 4 containers:

```
postgres    → banco de dados
minio       → armazenamento de arquivos
backend     → API FastAPI
frontend    → Vue.js servido pelo Nginx
```

Toda a configuração de ambiente (URLs, credenciais, segredos) é feita via arquivos `.env`, sem necessidade de alterar código.
