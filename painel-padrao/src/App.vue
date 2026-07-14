<template>
  <div v-if="loading" class="app-loading">Carregando...</div>

  <template v-else>
    <div v-if="!user" class="login-wrapper">
      <LoginView @login="onLogin" />
    </div>

    <div v-else class="app-shell">
      <header class="navbar">
        <RouterLink class="logo" to="/dashboard">Sistema FCA</RouterLink>
        <nav class="nav-links">
          <RouterLink class="nav-btn" to="/dashboard">Dashboard</RouterLink>
          <RouterLink class="nav-btn" to="/fca">FCAs</RouterLink>
          <RouterLink v-if="canOpenFca" class="nav-btn" to="/fca/novo">+ Novo FCA</RouterLink>
          <RouterLink v-if="user.role === 'admin'" class="nav-btn" to="/admin/usuarios">Usuários</RouterLink>
          <RouterLink v-if="user.role === 'admin'" class="nav-btn" to="/admin/sla">SLA</RouterLink>
          <RouterLink v-if="user.role === 'admin'" class="nav-btn" to="/admin/config">Configurações</RouterLink>
          <RouterLink v-if="user.role === 'admin'" class="nav-btn" to="/admin/help">Help</RouterLink>
          <RouterLink v-if="user.role !== 'admin'" class="nav-btn" to="/help">Suporte</RouterLink>
        </nav>
        <div class="nav-right">
          <RouterLink to="/perfil" class="user-chip">
            <UserAvatar :name="user.name" :avatarUrl="avatarUrl" :size="30" />
            <span class="user-info">
              {{ user.name }}
              <small>{{ user.sector }} · {{ user.company }}</small>
            </span>
          </RouterLink>
          <button class="btn btn-outline" @click="onLogout">Sair</button>
        </div>
      </header>

      <main class="content">
        <RouterView :key="$route.fullPath" :user="user" />
      </main>

      <footer class="version-bar">FCA System v2.0</footer>
    </div>
  </template>
</template>

<script setup>
import { ref, computed, inject, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { clearLocalToken, api, getLocalToken } from './api'
import LoginView from './views/LoginView.vue'
import UserAvatar from './components/UserAvatar.vue'

const msal   = inject('msal')
const router = useRouter()
const user   = ref(null)
const loading = ref(true)

// Disponibiliza o usuário para todas as views filhas
provide('user', user)

// ── Avatar URL global ───────────────────────────────────────────────────────
const avatarUrl = ref(null)
async function loadAvatar(avatarKey) {
  if (!avatarKey) { avatarUrl.value = null; return }
  try {
    const res = await api.upload.url(avatarKey)
    avatarUrl.value = res.url
  } catch { avatarUrl.value = null }
}
provide('reloadAvatar', (key) => loadAvatar(key))

// ── Sistema de notificações ─────────────────────────────────────────────────
const notifCount = ref(0)
const BASE_TITLE = 'Sistema FCA'

function updateTitle() {
  document.title = notifCount.value > 0
    ? `(${notifCount.value}) 🔔 ${BASE_TITLE}`
    : BASE_TITLE
}

function resetNotifCount() {
  notifCount.value = 0
  updateTitle()
}

if (typeof window !== 'undefined') {
  window.addEventListener('focus', resetNotifCount)
}

// Pré-carrega os elementos de áudio uma vez — o navegador não bloqueia .play()
// em elementos que já foram carregados durante a sessão
const _audioEls = {}
function _initAudio() {
  for (const id of ['som1', 'som2', 'som3', 'som4']) {
    const el = new Audio(`/sounds/${id}.wav`)
    el.preload = 'auto'
    el.volume = 0.7
    _audioEls[id] = el
  }
}
if (typeof window !== 'undefined') _initAudio()

function playSound(tipo) {
  const el = _audioEls[tipo]
  if (!el) return
  // Reinicia se já estava tocando
  el.currentTime = 0
  el.play().catch(() => {})
}

function dispararNotificacao() {
  const som = user.value?.notif_som ?? 'som1'
  const push = user.value?.notif_push ?? true

  if (som !== 'none') playSound(som)

  if (push && document.hidden) {
    notifCount.value++
    updateTitle()
  }
}

// Disponibiliza para views que queiram disparar manualmente (ex: toast)
provide('dispararNotificacao', dispararNotificacao)
provide('playSound', playSound)
// Permite que PerfilView atualize o user global (ex: notif_som)
provide('reloadUser', async () => {
  try {
    const me = await api.auth.me().catch(() => null)
    if (me && user.value) user.value = { ...user.value, ...me }
  } catch { /* silencioso */ }
})
// ────────────────────────────────────────────────────────────────────────────

// Callback registrado pela view ativa para reagir a eventos em tempo real
const wsListener = ref(null)
provide('registerWsListener', (fn) => { wsListener.value = fn })

let _ws = null
let _wsTimer = null

function connectWs() {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const url = base.replace(/^http/, 'ws') + '/ws'
  _ws = new WebSocket(url)

  _ws.onmessage = (ev) => {
    let event = null
    let destinatarios = []
    try {
      const parsed = JSON.parse(ev.data)
      event = parsed.event
      destinatarios = parsed.destinatarios || []
    } catch {
      // fallback para mensagens antigas em texto puro
      event = ev.data
    }

    if (event === 'fca_updated') {
      // Só notifica se o usuário logado for um dos destinatários
      if (user.value && destinatarios.length > 0) {
        const ehDestinatario = destinatarios.some(
          d => d.setor === user.value.sector && d.empresa === user.value.company
        )
        if (ehDestinatario) dispararNotificacao()
      }

      if (wsListener.value) wsListener.value('fca_updated')
    }

    // Repassa qualquer outro evento (help, etc.) para o listener ativo
    if (event && event !== 'fca_updated') {
      if (wsListener.value) wsListener.value(event)
    }
  }

  _ws.onclose = () => { _wsTimer = setTimeout(connectWs, 3000) }
  _ws.onerror = () => _ws.close()
}
// ────────────────────────────────────────────────────────────────────────────

const canOpenFca = computed(() => {
  if (!user.value) return false
  const blocked = ['Producao']
  return !blocked.includes(user.value.sector)
})

onMounted(async () => {
  connectWs()
  // Tenta restaurar sessão local
  const localToken = getLocalToken()
  if (localToken) {
    try {
      const payload = JSON.parse(atob(localToken.split('.')[1]))
      if (payload.exp && payload.exp * 1000 > Date.now()) {
        const me = await api.auth.me().catch(() => null)
        if (me) {
          user.value = { ...me, provider: 'local' }
          loading.value = false
          await loadAvatar(me.avatar_url)
          if (router.currentRoute.value.path === '/login' || router.currentRoute.value.path === '/') {
            router.replace('/dashboard')
          }
          return
        }
      }
    } catch { /* token malformado */ }
    clearLocalToken()
  }

  // Tenta restaurar sessão Microsoft (incluindo redirect de volta do Azure)
  try {
    const response = await msal.handleRedirectPromise()
    const account = response?.account || msal.getAllAccounts()[0]
    if (account) {
      const me = await api.auth.me().catch(() => null)
      if (me) {
        user.value = { ...me, provider: 'microsoft' }
        loading.value = false
        await loadAvatar(me.avatar_url)
        router.replace('/dashboard')
        return
      }
    }
  } catch { /* sem sessão */ }

  loading.value = false
})

async function onLogin(userData) {
  user.value = userData
  await loadAvatar(userData.avatar_url)
  router.replace('/dashboard')
}

async function onLogout() {
  clearLocalToken()
  if (user.value?.provider === 'microsoft') {
    await msal.logoutRedirect()
  }
  user.value = null
  router.replace('/login')
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f2f5; color: #1a1a2e; }

.app-loading {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; font-size: 1rem; color: #888;
}

.app-shell { min-height: 100vh; display: flex; flex-direction: column; }

.navbar {
  display: flex; align-items: center; padding: .75rem 2rem;
  background: #fff; border-bottom: 1px solid #e0e4ec;
  box-shadow: 0 1px 4px rgba(0,0,0,.06); gap: 1.5rem; position: sticky; top: 0; z-index: 100;
}
.logo {
  font-size: 1rem; font-weight: 700; color: #1a56db;
  text-decoration: none; white-space: nowrap;
}
.nav-links { display: flex; gap: .2rem; flex: 1; }
.nav-btn {
  background: none; border: none; padding: .4rem .85rem; border-radius: 6px;
  cursor: pointer; font-size: .875rem; color: #555; text-decoration: none;
  transition: background .15s, color .15s; white-space: nowrap;
}
.nav-btn:hover { background: #eff6ff; color: #1a56db; }
.nav-btn.router-link-active { background: #dbeafe; color: #1a56db; font-weight: 600; }
.nav-right { display: flex; align-items: center; gap: 1rem; margin-left: auto; }
.user-chip {
  display: flex; align-items: center; gap: .5rem; text-decoration: none;
  padding: .3rem .6rem; border-radius: 8px; transition: background .15s;
}
.user-chip:hover { background: #f0f7ff; }
.user-info { font-size: .8rem; color: #555; display: flex; flex-direction: column; align-items: flex-start; }
.user-info small { color: #888; font-size: .72rem; }

.content { max-width: 1100px; width: 100%; margin: 1.5rem auto; padding: 0 1.25rem; flex: 1; }

.version-bar {
  padding: .4rem 2rem; text-align: right; font-size: .7rem;
  color: #ccc; border-top: 1px solid #eee; background: #fff;
}

/* utilitários globais */
.btn { padding: .45rem 1.1rem; border: none; border-radius: 6px; cursor: pointer; font-size: .875rem; font-weight: 500; transition: opacity .2s; }
.btn:hover:not(:disabled) { opacity: .85; }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-primary { background: #1a56db; color: #fff; }
.btn-secondary { background: #e5e7eb; color: #374151; }
.btn-danger { background: #dc2626; color: #fff; }
.btn-outline { background: transparent; border: 1px solid #1a56db; color: #1a56db; }
.btn-sm { padding: .3rem .75rem; font-size: .8rem; }

.card { background: #fff; border-radius: 10px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
.badge { display: inline-block; padding: .2rem .6rem; border-radius: 20px; font-size: .75rem; font-weight: 600; }
.badge-aberto { background: #dbeafe; color: #1d4ed8; }
.badge-em_andamento { background: #fef3c7; color: #92400e; }
.badge-aguardando_devolutiva { background: #ede9fe; color: #6d28d9; }
.badge-encerrado { background: #d1fae5; color: #065f46; }

.form-group { display: flex; flex-direction: column; gap: .35rem; }
.form-group label { font-size: .85rem; font-weight: 500; color: #374151; }
.form-group input, .form-group select, .form-group textarea {
  padding: .5rem .75rem; border: 1px solid #d1d5db; border-radius: 6px;
  font-size: .9rem; outline: none; background: #fff; font-family: inherit;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: #1a56db; }
.form-group textarea { resize: vertical; min-height: 80px; }

.error-msg { color: #dc2626; font-size: .85rem; margin-top: .25rem; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.page-header h1 { font-size: 1.3rem; font-weight: 700; }
</style>
