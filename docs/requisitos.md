# Requisitos do Sistema FCA

## 1. Visão Geral

Sistema web para gerenciamento do ciclo de vida de FCAs (Ficha de Correção de Ação), substituindo o fluxo atual no Pipefy. Cada FCA percorre uma fila dinâmica de setores responsáveis pelo tratamento, com visibilidade e ações restritas por usuário/setor.

Stack: Vue.js (frontend) · Python (backend) · PostgreSQL (banco) · MinIO (object storage para anexos)

---

## 2. Empresas e Setores

### Empresas
| Sigla | Nome Completo |
|-------|---------------|
| ACI_MATRIZ | Aço Cearense Industrial - Matriz |
| ACI_FILIAL | Aço Cearense Industrial - Filial |
| SINOBRAS | SINOBRAS |
| ACC | Aço Cearense Comercial |

### Setores por Empresa
| Setor | ACI Matriz | ACI Filial | SINOBRAS | ACC |
|-------|:---:|:---:|:---:|:---:|
| ACL | ✅ | ✅ | ✅ | ❌ |
| PCP | ✅ | ✅ | ✅ | ❌ |
| Qualidade | ✅ | ✅ | ✅ | ❌ |
| MEP | ✅ | ✅ | ✅ | ❌ |
| Expedição | ✅ | ✅ | ✅ | ❌ |
| Produção | ✅ | ✅ | ✅ | ❌ |
| Comercial | ❌ | ❌ | ❌ | ✅ |
| Customer Service | ❌ | ❌ | ❌ | ✅ |

**Regras fixas de negócio:**
- `ACC` só possui Comercial e Customer Service
- `Produção` é exclusivamente área causadora — não abre FCA e não recebe devolutiva
- `Comercial` existe apenas na ACC e não recebe devolutiva
- `Customer Service` administra o sistema, pode abrir FCA e recebe devolutiva

---

## 3. Usuários e Acesso

### Cadastro do Usuário
Feito pelo administrador (Customer Service). Campos:

| Campo | Tipo | Observação |
|-------|------|------------|
| Nome | Texto | |
| Email | Texto | usado como login |
| Senha | Texto | hash bcrypt |
| Empresa | Lista | vínculo fixo |
| Setor | Lista | vínculo fixo, filtrado pela empresa |
| Matrícula | Número | |
| Turno | Lista (A/B/C/D) | |
| Papel | Enum | `admin` ou `user` |

> Matrícula e Turno ficam no perfil do usuário — não são campos do formulário de abertura do FCA.

### Regras de Visibilidade
- Cada usuário vê **apenas FCAs onde seu setor/empresa está na fila de tratamento atual ou já passou**
- O solicitante vê o FCA que abriu do início ao fim
- `admin` (Customer Service) vê todos os FCAs de todas as empresas/setores
- Um usuário **não vê e não interage** com FCAs de outros setores/empresas

### Autenticação
- Login via email + senha
- JWT com expiração configurável
- Nome e email vêm do token — não são campos de formulário

---

## 4. Formulário de Abertura do FCA

Preenchido pelo solicitante autenticado. Empresa e Setor do solicitante são preenchidos automaticamente pelo perfil do usuário logado.

| Campo | Tipo | Opções / Observação |
|-------|------|---------------------|
| Causa do FCA | Lista | Carro com problema mecânico / Excesso de PBT / Formatação da carga / Material indisponível / Material obstruído / Material oxidado / Pedido fora do padrão / Peso fardo 1 tonelada / Divergência de peso |
| Área Causadora | Lista | ACL / Comercial / MEP / PCP / Qualidade / Expedição / Produção |
| Empresa do Causador | Lista | ACI - Matriz / ACI - Filial / ACC / SINOBRAS — filtrada pelas regras do setor |
| Ação | Lista | Ajustar a carga / Analisar e atuar junto com comercial / Atuar junto com comercial / Avaliar o material / Bloquear os fardos / Confere o estoque e programação / Sinalizar o time comercial / Desobstruir material / Corrigir peso |
| UF | Lista | Todos os estados brasileiros |
| Número da Remessa | Número | |
| Detalhe / Observação | Texto livre | |
| Anexo / Evidência | Arquivo | |

**Preenchidos automaticamente (do usuário logado):**
- Setor Solicitante
- Empresa do Solicitante

**Validações:**
- Combinações inválidas de Área Causadora + Empresa do Causador devem ser bloqueadas (ex: ACL + ACC)
- Produção não pode ser Setor Solicitante

---

## 5. Lógica Central — Fila de Setores

### Conceito
O FCA não tem mais "fases fixas". Em vez disso, possui uma **fila de etapas** — uma lista ordenada de setores que devem tratar o FCA antes da devolutiva ao solicitante.

Na abertura, a fila começa com **um único setor**: o derivado da triagem automática (Área Causadora + Empresa do Causador).

Durante o tratamento, qualquer setor da fila pode **adicionar novos setores ao final da fila** antes de concluir sua etapa. Isso substitui o antigo "Encaminha para outra área".

### Estrutura de uma Etapa
Cada etapa da fila contém:
- Setor responsável
- Empresa do setor
- Status: `pendente` | `em_andamento` | `concluido`
- Resposta preenchida pelo responsável (quando concluída)
- Timestamps de entrada e conclusão

### Triagem Automática (abertura)
Ao criar o FCA, o sistema monta a fila inicial com base em:

```
Área Causadora + Empresa do Causador → Setor responsável da etapa 1
```

Mesma tabela de mapeamento do fluxo atual (ACL+ACI Matriz → ACL Matriz, etc.).

---

## 6. Fluxo Detalhado

### Etapa 1 — Abertura
1. Usuário autenticado preenche o formulário
2. Sistema preenche Setor Solicitante e Empresa do Solicitante pelo perfil
3. FCA criado com status `aberto` e fila inicializada com o setor derivado da triagem
4. E-mail de notificação disparado ao setor responsável da etapa 1

### Etapa 2 — Tratamento pelo Setor Atual
O setor que está no topo da fila (etapa `pendente` mais antiga) acessa o FCA e vê:

**Preview somente leitura:**
- Todos os dados da abertura
- Histórico de etapas já concluídas (setor, devolutiva, timestamp)

**Formulário de resposta:**
| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| Problema Solucionado? | Sim / Não | Sim |
| Detalhe / Devolutiva da Tratativa | Texto livre | Sim |
| Encaminhar para outro(s) setor(es)? | Sim / Não | Sim |

Se "Encaminhar para outro(s) setor(es)?" = **Sim**, o usuário pode adicionar **uma ou mais entradas** na fila, cada uma com:
| Campo | Tipo |
|-------|------|
| Setor de destino | Lista |
| Empresa do setor | Lista |

> A ordem das entradas adicionadas define a ordem de tratamento.

### Etapa 3 — Roteamento pós-resposta

**Cenário A — Sem encaminhamento:**
1. Etapa atual marcada como `concluida`
2. Sistema verifica se há próxima etapa na fila
   - Se **sim**: próxima etapa vai para `pendente`, e-mail disparado ao próximo setor
   - Se **não**: FCA vai para `aguardando_devolutiva`, e-mail de devolutiva disparado ao solicitante

**Cenário B — Com encaminhamento:**
1. Etapa atual marcada como `concluida`
2. Novos setores adicionados ao final da fila com status `pendente`
3. Próximo setor da fila recebe notificação por e-mail
4. Ciclo se repete (Etapa 2)

> "Problema Solucionado? = Não" não bloqueia o fluxo — o FCA segue normalmente. A resposta fica registrada no histórico e é incluída no e-mail de devolutiva.

### Etapa 4 — Devolutiva ao Solicitante
Quando a fila se esgota, o e-mail de devolutiva é disparado ao setor solicitante com o consolidado de todas as etapas.

---

## 7. Notificações por E-mail

### E-mail de Abertura (dispara ao setor responsável da etapa atual)
```
Assunto: Novo FCA Registrado - [Área Causadora] - [UF]  ← UF apenas para ACL

Corpo:
CodFCA, Causa, Setor Responsável, Área Causadora, Ação, UF,
Empresa, Número da Remessa, Detalhe/Observação, GT/DT

Link para acessar e tratar o FCA no sistema
```

### E-mail de Devolutiva (dispara ao solicitante ao fim da fila)
```
Assunto: FCA Respondido - [Área Causadora] - [CodFCA]

Corpo:
Resultado consolidado de todas as etapas (setor, Problema Solucionado, Devolutiva)
Dados completos do registro original
```

---

## 8. Estados do FCA

| Status | Descrição |
|--------|-----------|
| `aberto` | Fila iniciada, aguardando tratamento do primeiro setor |
| `em_andamento` | Pelo menos uma etapa concluída, ainda há pendentes na fila |
| `aguardando_devolutiva` | Fila esgotada, e-mail de retorno disparado |
| `encerrado` | Solicitante confirmou ciência (ou timeout configurável) |

---

## 9. Páginas do Sistema

### Autenticação
- `/login` — email + senha

### Dashboard (pós-login)
- `/dashboard` — visão geral dos FCAs visíveis ao usuário logado

  Exibe dois grupos de cards/indicadores:
  - **Minha Fila** — FCAs em que é a vez do meu setor agir (etapa pendente/em andamento)
  - **Acompanhamento** — FCAs que meu setor abriu ou já tratou, com andamento atual

  Indicadores rápidos: total abertos · em andamento · aguardando devolutiva · encerrados

  Filtros: status · empresa · data de abertura

### FCAs
- `/fca` — listagem completa
  - Colunas: CodFCA · Causa · Setor solicitante · Área causadora · Empresa · Status atual · Setor atual da fila · Data abertura
  - Usuário vê apenas FCAs do seu setor/empresa (abertos por ele ou com etapa na fila)
  - Admin vê tudo
  - Filtros: status · setor · empresa · data

- `/fca/novo` — formulário de abertura
  - Restrito a setores que podem abrir FCA (não disponível para Produção)
  - Setor e empresa preenchidos automaticamente do perfil

- `/fca/:id` — detalhe e tratamento do FCA
  
  Esta é a tela principal do fluxo. Dividida em seções:

  **Seção 1 — Dados da Abertura** (somente leitura)
  Todos os campos do formulário original: causa, ação, UF, remessa, detalhe, anexo, setor/empresa solicitante e causadora.

  **Seção 2 — Linha do Tempo / Histórico de Etapas**
  Lista cronológica de todas as etapas já concluídas e a etapa atual, mostrando para cada uma:
  - Setor + Empresa responsável
  - Data de entrada e conclusão
  - Problema Solucionado? (Sim/Não)
  - Devolutiva preenchida pelo responsável
  - Nome do usuário que respondeu

  > Visível para todos que têm acesso ao FCA — solicitante, setores que já passaram e admin.
  > É aqui que o Customer Service lê o que o MEP devolveu antes de preencher a própria etapa.

  **Seção 3 — Formulário de Resposta** (visível apenas quando é a vez do setor do usuário logado)
  - Problema Solucionado? (Sim/Não)
  - Detalhe / Devolutiva da Tratativa (texto livre)
  - Encaminhar para outro(s) setor(es)? (Sim/Não)
    - Se Sim: lista dinâmica para adicionar pares Setor + Empresa na ordem desejada

  **Seção 4 — Status da Fila** (somente leitura)
  Próximos setores aguardando na fila (setor + empresa), sem mostrar as devolutivas futuras — apenas o que ainda está pendente.

### Administração (somente admin)
- `/admin/usuarios` — listagem de usuários com filtro por empresa/setor/status
- `/admin/usuarios/novo` — cadastro de novo usuário
- `/admin/usuarios/:id` — edição e desativação do usuário

---

## 10. Regras de Negócio Consolidadas

1. Setor Solicitante e Empresa do Solicitante são herdados do usuário logado — não são campos editáveis no formulário
2. Nome, email, matrícula e turno vêm do perfil do usuário — não são campos do FCA
3. A triagem automática usa Área Causadora + Empresa do Causador para montar a etapa inicial da fila
4. Qualquer setor pode encaminhar para N setores adicionais, que entram no final da fila na ordem definida
5. A devolutiva só ocorre quando a fila está completamente vazia (sem etapas pendentes)
6. "Problema Solucionado = Não" não bloqueia o fluxo — registra e segue
7. Produção nunca é Setor Solicitante e não recebe devolutiva
8. Comercial (ACC) não recebe devolutiva
9. ACC só possui Comercial e Customer Service — combinações inválidas bloqueadas na UI e no backend
10. O campo UF aparece no assunto do e-mail apenas para etapas cujo setor responsável é ACL
11. Todo o histórico de etapas (setor, resposta, timestamps) é persistido e visível no detalhe do FCA
12. Usuários só visualizam e interagem com FCAs onde seu setor/empresa tem (ou teve) etapa na fila

---

## 11. Modelo de Dados

### `users`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID PK | |
| name | VARCHAR(100) | nome completo |
| email | VARCHAR(150) UNIQUE | login |
| password_hash | TEXT | bcrypt |
| company | VARCHAR(20) | enum: ACI_MATRIZ / ACI_FILIAL / SINOBRAS / ACC |
| sector | VARCHAR(30) | enum: ACL / PCP / Qualidade / MEP / Expedição / Produção / Comercial / Customer_Service |
| role | VARCHAR(10) | enum: admin / user |
| matricula | VARCHAR(20) | |
| turno | CHAR(1) | A / B / C / D |
| active | BOOLEAN | default true |
| created_at | TIMESTAMP | |

---

### `fcas`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID PK | |
| cod_fca | VARCHAR(20) UNIQUE | código gerado pelo sistema |
| causa | VARCHAR(100) | causa do FCA (lista fechada) |
| acao | VARCHAR(100) | ação definida (lista fechada) |
| uf | CHAR(2) | estado |
| numero_remessa | BIGINT | |
| detalhe | TEXT | observação livre |
| anexo_url | TEXT | object key no MinIO (ex: `2025/07/09/uuid_evidencia.jpg`) |
| setor_solicitante | VARCHAR(30) | herdado do usuário que abriu |
| empresa_solicitante | VARCHAR(20) | herdado do usuário que abriu |
| area_causadora | VARCHAR(30) | definido no formulário |
| empresa_causadora | VARCHAR(20) | definido no formulário |
| status | VARCHAR(25) | aberto / em_andamento / aguardando_devolutiva / encerrado |
| created_by | UUID FK → users.id | usuário que abriu |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | atualizado a cada mudança de status |

---

### `fca_etapas` (fila de tratamento)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID PK | |
| fca_id | UUID FK → fcas.id | |
| order_index | INTEGER | posição na fila, começa em 1, incrementa a cada encaminhamento |
| setor | VARCHAR(30) | setor responsável por esta etapa |
| empresa | VARCHAR(20) | empresa do setor responsável |
| status | VARCHAR(15) | pendente / em_andamento / concluido |
| problema_solucionado | BOOLEAN | null até ser respondido |
| devolutiva | TEXT | resposta do responsável, null até ser respondido |
| respondido_por | UUID FK → users.id | null até ser respondido |
| entered_at | TIMESTAMP | quando a etapa ficou ativa (status → em_andamento) |
| concluded_at | TIMESTAMP | quando foi concluída |

> A etapa "ativa" em um dado momento é a de menor `order_index` com status `pendente` ou `em_andamento`.
> Quando um setor encaminha para outros, as novas etapas entram com `order_index` sequencial a partir do maior existente.

---

### Relacionamentos
```
users ──< fcas          (created_by)
fcas  ──< fca_etapas    (fca_id)
users ──< fca_etapas    (respondido_por)
```

### Visibilidade (query base por usuário)
```sql
-- FCAs visíveis para um usuário não-admin:
SELECT DISTINCT f.*
FROM fcas f
LEFT JOIN fca_etapas e ON e.fca_id = f.id
WHERE f.created_by = :user_id          -- abriu o FCA
   OR (
     e.setor   = :user_sector AND
     e.empresa = :user_company         -- tem ou teve etapa na fila
   )
```
