# Implementações — Sistema de Notificações

## 1. Visão geral

Sistema completo de notificações em tempo real para novos FCAs: som ao receber um FCA direcionado ao setor do usuário, badge com contador no título da aba do navegador, e preferência de som configurável por usuário no perfil.

---

## 2. Backend — campo `notif_som` no modelo de usuário

### O que foi feito
Adicionado o campo `notif_som` (string, default `'som1'`) na tabela `users` para persistir a preferência de som de cada usuário.

### Arquivos modificados
- `backend/models.py` — novo campo `notif_som: Mapped[str]`
- `backend/routes/auth.py` — `MeResponse` e endpoint `/auth/me` passam a retornar `notif_push` e `notif_som`
- `backend/routes/perfil.py` — `PerfilOut`, `PerfilUpdate` e `_to_out` atualizados com `notif_som`; aceita valores `none | som1 | som2 | som3 | som4`
- `backend/main.py` — migração automática no startup via `ADD COLUMN IF NOT EXISTS` para bancos existentes
- `backend/migrations/add_notif_som.sql` — script SQL manual alternativo

---

## 3. Backend — broadcast com destinatários

### Problema
O broadcast do WebSocket era genérico (`"fca_updated"` para todos). Qualquer usuário com a tela aberta recebia som de notificação, mesmo que o FCA não fosse direcionado ao seu setor.

### Solução
O `ws_manager.broadcast` passou a aceitar uma lista de `destinatarios` (`[{"setor": str, "empresa": str}]`). O payload enviado pelo WebSocket mudou de texto puro para JSON:

```json
{ "event": "fca_updated", "destinatarios": [{"setor": "ACL", "empresa": "ACI_MATRIZ"}] }
```

Cada endpoint do backend passa os destinatários corretos:
- `POST /fcas/` → setor/empresa da etapa inicial (triagem)
- `POST /fcas/{id}/responder` → setores das etapas pendentes após a resposta
- `POST /fcas/{id}/encerrar` → lista vazia (ninguém precisa ser notificado)

### Arquivos modificados
- `backend/ws_manager.py` — `broadcast(event, destinatarios)` serializa para JSON
- `backend/routes/fcas.py` — todos os `manager.broadcast` passam os destinatários corretos

---

## 4. Frontend — lógica de notificação no App.vue

### O que foi feito
`App.vue` passou a interpretar o payload JSON do WebSocket e só dispara o som/badge se o usuário logado for um dos destinatários.

```js
const ehDestinatario = destinatarios.some(
  d => d.setor === user.value.sector && d.empresa === user.value.company
)
if (ehDestinatario) dispararNotificacao()
```

A função `dispararNotificacao` faz duas coisas:
1. Toca o som configurado no perfil do usuário (`notif_som`)
2. Incrementa o contador no título da aba se a aba estiver em segundo plano (`document.hidden`) e `notif_push` estiver ativo — ex: `(2) 🔔 Sistema FCA`

O contador é zerado automaticamente quando o usuário volta para a aba (`window focus`).

### Provides disponibilizados globalmente
| provide | uso |
|---|---|
| `dispararNotificacao` | views podem disparar notificação manualmente |
| `playSound(tipo)` | toca um som específico (usado no preview do perfil) |
| `reloadUser` | atualiza o objeto `user` global após salvar preferências |

---

## 5. Frontend — arquivos de som estáticos

### Problema
As abordagens anteriores (`AudioContext`, `data:` URLs) falhavam após F5 por restrições de autoplay do navegador. O Chrome bloqueia reprodução de áudio criada programaticamente antes de uma interação do usuário.

### Solução definitiva
Sons gerados como arquivos WAV reais em tempo de build e servidos pelo nginx como assets estáticos. O `App.vue` pré-carrega os 4 elementos `<audio>` ao inicializar a página — o navegador trata elementos de áudio pré-carregados diferente de áudio criado dinamicamente e não bloqueia o `.play()`.

### Como funciona o build
1. Script `scripts/gen-sounds.js` gera 4 arquivos WAV (PCM 16-bit, 22050 Hz) via síntese de tons puros em Node.js puro — sem dependências externas
2. O `Dockerfile` executa `npm run gen-sounds` antes do `npm run build`, então os arquivos entram no `dist/sounds/`
3. O nginx serve `/sounds/*.wav` normalmente com `media-src 'self'` no CSP

### Sons disponíveis
| ID | Descrição |
|---|---|
| `som1` | Dois bipes suaves (estilo WhatsApp) |
| `som2` | Tom crescente em três notas (estilo Telegram) |
| `som3` | Sino suave com harmônico |
| `som4` | Pulso duplo urgente |

### Arquivos criados/modificados
- `scripts/gen-sounds.js` — gerador dos WAV files
- `package.json` — script `gen-sounds` adicionado
- `Dockerfile` — executa `gen-sounds` antes do build
- `nginx.local.conf` — `media-src 'self'` adicionado ao CSP
- `nginx.conf` — `media-src 'self'` adicionado ao CSP

---

## 6. Frontend — seção de som no Perfil

### O que foi feito
Nova seção "Som de notificação" na `PerfilView.vue` com 5 opções em cards clicáveis:

| Valor | Ícone | Label |
|---|---|---|
| `none` | 🔕 | Nenhum |
| `som1` | 💬 | Mensagem |
| `som2` | 📨 | Alerta |
| `som3` | 🔔 | Sino |
| `som4` | ⚡ | Urgente |

Ao clicar em um card o som é tocado como preview imediatamente e a preferência é salva via `PATCH /api/perfil/`. O card selecionado fica destacado com borda azul. Cada card tem um botão `▶` de preview que aparece no hover.

A preferência salva é sincronizada com o objeto `user` global via `reloadUser`, garantindo que o som correto toque em tempo real sem precisar de F5.

### Arquivo modificado
- `src/views/PerfilView.vue`

---

## 7. Correção — redirect para `/fca/undefined` após criar FCA

### Problema
Após criar um FCA, o frontend redirecionava para `/fca/undefined` porque o campo `id` havia sido removido acidentalmente do `return` do endpoint `POST /api/fcas/`.

### Solução
Recolocado `"id": str(fca.id)` no dicionário de retorno do `create_fca`.

### Arquivo modificado
- `backend/routes/fcas.py`
