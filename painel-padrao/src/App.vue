<template>
  <div v-if="loading" class="app-loading">
    <div class="loading-spinner"></div>
  </div>

  <template v-else>
    <!-- Troca de senha obrigatória no primeiro acesso -->
    <div v-if="user && user.must_change_password" class="login-wrapper">
      <ChangePasswordView @done="onPasswordChanged" />
    </div>

    <!-- Onboarding obrigatório (apenas não-admin) -->
    <div v-else-if="user && !user.onboarding_completed && user.role !== 'admin'" class="login-wrapper">
      <OnboardingView @done="onOnboardingDone" />
    </div>

    <div v-else-if="!user" class="login-wrapper">
      <LoginView @login="onLogin" />
    </div>

    <div v-else class="app-shell" :class="{ 'sidebar-is-collapsed': sidebarCollapsed }">
      <!-- Skip link acessibilidade -->
      <a href="#main-content" class="skip-link">Ir para o conteúdo principal</a>

      <!-- Overlay mobile (fora da sidebar, dentro do app-shell) -->
      <Transition name="fade-overlay">
        <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false"></div>
      </Transition>

      <!-- Botão flutuante para colapsar/expandir sidebar (sempre visível) -->
      <button
        class="sidebar-toggle-btn"
        @click="sidebarCollapsed = !sidebarCollapsed"
        :aria-label="sidebarCollapsed ? 'Expandir menu' : 'Recolher menu'"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path :d="sidebarCollapsed ? 'M5 3l4 4-4 4' : 'M9 3L5 7l4 4'" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <!-- Sidebar -->
      <aside
        class="sidebar"
        :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-open': sidebarOpen }"
        aria-label="Navegação principal"
      >
        <!-- Logo -->
        <div class="sidebar-logo">
          <div class="sidebar-logo-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="var(--color-primary-500)"/>
              <path d="M7 14h14M7 9h9M7 19h11" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <span class="sidebar-logo-text">Sistema FCA</span>
        </div>

        <!-- Nav items -->
        <nav class="sidebar-nav">
          <div class="sidebar-section">
            <span class="sidebar-section-label">Principal</span>
            <RouterLink class="sidebar-item" to="/dashboard" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Dashboard' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="2" width="6" height="6" rx="1.5" fill="currentColor" opacity=".8"/><rect x="10" y="2" width="6" height="6" rx="1.5" fill="currentColor" opacity=".5"/><rect x="2" y="10" width="6" height="6" rx="1.5" fill="currentColor" opacity=".5"/><rect x="10" y="10" width="6" height="6" rx="1.5" fill="currentColor" opacity=".8"/></svg>
              </span>
              <span class="sidebar-item-label">Dashboard</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Dashboard</span>
            </RouterLink>
            <RouterLink class="sidebar-item" to="/fca" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'FCAs' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 3h12a1 1 0 011 1v10a1 1 0 01-1 1H3a1 1 0 01-1-1V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5" fill="none"/><path d="M5 7h8M5 10h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">FCAs</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">FCAs</span>
            </RouterLink>
            <RouterLink v-if="canOpenFca" class="sidebar-item sidebar-item-new" to="/fca/novo" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Novo FCA' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M9 6v6M6 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Novo FCA</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Novo FCA</span>
            </RouterLink>
            <RouterLink v-if="user.role !== 'admin'" class="sidebar-item" to="/help" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Suporte' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M9 13v.5M9 10.5a2 2 0 10-2-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Suporte</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Suporte</span>
            </RouterLink>
          </div>

          <div v-if="user.acesso_relatorio && user.role !== 'admin'" class="sidebar-section">
            <span class="sidebar-section-label">Relatórios</span>
            <RouterLink class="sidebar-item" to="/admin/relatorio" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Relatório' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 2h7l3 3v11H4V2z" stroke="currentColor" stroke-width="1.5"/><path d="M11 2v3h3M6 8h6M6 11h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Relatório</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Relatório</span>
            </RouterLink>
          </div>

          <div v-if="user.role === 'admin'" class="sidebar-section">
            <span class="sidebar-section-label">Administração</span>
            <RouterLink class="sidebar-item" to="/admin/usuarios" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Usuários' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 15c0-3.314 2.686-6 6-6s6 2.686 6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Usuários</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Usuários</span>
            </RouterLink>
            <RouterLink class="sidebar-item" to="/admin/sla" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'SLA' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M9 5v4l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">SLA</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">SLA</span>
            </RouterLink>
            <RouterLink v-if="user?.role === 'admin' || user?.acesso_relatorio" class="sidebar-item" to="/admin/relatorio" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Relatório' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 2h7l3 3v11H4V2z" stroke="currentColor" stroke-width="1.5"/><path d="M11 2v3h3M6 8h6M6 11h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Relatório</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Relatório</span>
            </RouterLink>
            <RouterLink class="sidebar-item" to="/admin/help" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Help Admin' : undefined">              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M2 4a1 1 0 011-1h12a1 1 0 011 1v8a1 1 0 01-1 1H5l-3 2V4z" stroke="currentColor" stroke-width="1.5"/></svg>
              </span>
              <span class="sidebar-item-label">Help Admin</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Help Admin</span>
            </RouterLink>
            <RouterLink class="sidebar-item" to="/admin/comunicados" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Comunicados' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M2 5a1 1 0 011-1h12a1 1 0 011 1v7a1 1 0 01-1 1H5l-3 2V5z" stroke="currentColor" stroke-width="1.5" fill="none"/><path d="M6 8h6M6 11h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Comunicados</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Comunicados</span>
            </RouterLink>
            <RouterLink class="sidebar-item" to="/admin/config" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Configurações' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M9 2v1.5M9 14.5V16M2 9h1.5M14.5 9H16M4.1 4.1l1.1 1.1M12.8 12.8l1.1 1.1M12.8 5.2l1.1-1.1M4.1 13.9l1.1-1.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </span>
              <span class="sidebar-item-label">Configurações</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Configurações</span>
            </RouterLink>
            <RouterLink class="sidebar-item" to="/admin/onboarding" @click="sidebarOpen = false" :aria-label="sidebarCollapsed ? 'Onboarding' : undefined">
              <span class="sidebar-item-icon">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="4" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M7.5 7.5l4 2-4 2V7.5z" fill="currentColor" opacity=".7"/></svg>
              </span>
              <span class="sidebar-item-label">Onboarding</span>
              <span v-if="sidebarCollapsed" class="sidebar-tooltip">Onboarding</span>
            </RouterLink>
          </div>
        </nav>

        <!-- User section no bottom -->
        <div class="sidebar-bottom">
          <RouterLink to="/perfil" class="sidebar-user" @click="sidebarOpen = false">
            <UserAvatar :name="user.name" :avatarUrl="avatarUrl" :size="32" />
            <div class="sidebar-user-info">
              <span class="sidebar-user-name">{{ user.name }}</span>
              <span class="sidebar-user-meta">{{ user.sector }} · {{ user.company }}</span>
            </div>
            <span v-if="sidebarCollapsed" class="sidebar-tooltip">{{ user.name }}</span>
          </RouterLink>
          <button class="sidebar-logout" @click="onLogout" :aria-label="sidebarCollapsed ? 'Sair' : undefined">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 14H3a1 1 0 01-1-1V3a1 1 0 011-1h3M11 11l3-3-3-3M14 8H6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span class="sidebar-item-label">Sair</span>
            <span v-if="sidebarCollapsed" class="sidebar-tooltip">Sair</span>
          </button>
        </div>
      </aside>

      <!-- Área principal -->
      <div class="main-area">
        <!-- Topbar -->
        <header class="topbar">
          <button class="topbar-hamburger" @click="sidebarOpen = !sidebarOpen" aria-label="Abrir menu">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <div class="topbar-title">{{ routeTitle }}</div>
          <div class="topbar-right">
            <div class="topbar-search">
              <svg class="topbar-search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              <input type="text" placeholder="Buscar…" class="topbar-search-input" />
            </div>
            <button
              class="topbar-notif"
              :class="{ 'has-badge': unreadNotif > 0 }"
              aria-label="Notificações"
              @click="notifPanelOpen = !notifPanelOpen"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 2a6 6 0 00-6 6v3l-1.5 2h15L16 11V8a6 6 0 00-6-6zM8 16a2 2 0 004 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              <span v-if="unreadNotif > 0" class="notif-badge">{{ unreadNotif > 9 ? '9+' : unreadNotif }}</span>
            </button>
            <NotificationPanel
              v-if="notifPanelOpen"
              ref="notifPanelRef"
              @close="notifPanelOpen = false"
              @update:unread="unreadNotif = $event"
            />
            <RouterLink to="/perfil" class="topbar-avatar">
              <UserAvatar :name="user.name" :avatarUrl="avatarUrl" :size="32" />
            </RouterLink>
          </div>
        </header>

        <!-- Conteúdo -->
        <main class="content" id="main-content">
          <RouterView :key="$route.fullPath" :user="user" />
        </main>

        <footer class="version-bar">FCA System v2.0</footer>
      </div>
    </div>
  </template>
</template>

<script setup>
import { ref, computed, inject, onMounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { clearLocalToken, api, getLocalToken } from './api'
import LoginView from './views/LoginView.vue'
import ChangePasswordView from './views/ChangePasswordView.vue'
import OnboardingView from './views/OnboardingView.vue'
import UserAvatar from './components/UserAvatar.vue'
import NotificationPanel from './components/NotificationPanel.vue'

const msal   = inject('msal')
const router = useRouter()
const route  = useRoute()
const user   = ref(null)
const loading = ref(true)
const sidebarCollapsed = ref(false)
const sidebarOpen = ref(false)

provide('user', user)

const ROUTE_TITLES = {
  '/dashboard': 'Dashboard',
  '/fca': 'FCAs',
  '/fca/novo': 'Novo FCA',
  '/help': 'Suporte',
  '/perfil': 'Perfil',
  '/admin/usuarios': 'Usuários',
  '/admin/sla': 'SLA',
  '/admin/config': 'Configurações',
  '/admin/comunicados': 'Comunicados',
  '/admin/help': 'Help Admin',
  '/admin/relatorio': 'Relatório',
  '/admin/onboarding': 'Onboarding',
}
const routeTitle = computed(() => {
  const path = route.path
  if (path.startsWith('/fca/') && path !== '/fca/novo') return 'Detalhe do FCA'
  if (path.startsWith('/admin/usuarios/')) return 'Editar Usuário'
  return ROUTE_TITLES[path] || 'Sistema FCA'
})

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

// ── Notificações ─────────────────────────────────────────────────────────────
const notifCount = ref(0)
const unreadNotif = ref(0)
const notifPanelOpen = ref(false)
const notifPanelRef = ref(null)
const BASE_TITLE = 'Sistema FCA'

function updateTitle() {
  document.title = notifCount.value > 0 ? `(${notifCount.value}) 🔔 ${BASE_TITLE}` : BASE_TITLE
}
function resetNotifCount() { notifCount.value = 0; updateTitle() }
if (typeof window !== 'undefined') window.addEventListener('focus', resetNotifCount)

const _audioEls = {}
function _initAudio() {
  for (const id of ['som1', 'som2', 'som3', 'som4']) {
    const el = new Audio(`/sounds/${id}.wav`)
    el.preload = 'auto'; el.volume = 0.7; _audioEls[id] = el
  }
}
if (typeof window !== 'undefined') _initAudio()

function playSound(tipo) {
  const el = _audioEls[tipo]
  if (!el) return
  el.currentTime = 0
  el.play().catch(() => {})
}

function dispararNotificacao() {
  const som = user.value?.notif_som ?? 'som1'
  const push = user.value?.notif_push ?? true
  if (som !== 'none') playSound(som)
  if (push && document.hidden) { notifCount.value++; updateTitle() }
}

provide('dispararNotificacao', dispararNotificacao)
provide('playSound', playSound)
provide('reloadUser', async () => {
  try {
    const me = await api.auth.me().catch(() => null)
    if (me && user.value) user.value = { ...user.value, ...me }
  } catch { /* silencioso */ }
})

// ── WebSocket ─────────────────────────────────────────────────────────────────
const wsListener = ref(null)
provide('registerWsListener', (fn) => { wsListener.value = fn })

let _ws = null
let _wsTimer = null

function connectWs() {
  if (!user.value) return
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const url = base.replace(/^http/, 'ws') + `/ws?user_id=${user.value.id}`
  _ws = new WebSocket(url)
  _ws.onmessage = (ev) => {
    let event = null; let destinatarios = []
    try { const p = JSON.parse(ev.data); event = p.event; destinatarios = p.destinatarios || [] }
    catch { event = ev.data }
    if (event === 'fca_updated') {
      if (user.value && destinatarios.length > 0) {
        const ok = destinatarios.some(d => d.setor === user.value.sector && d.empresa === user.value.company)
        if (ok) dispararNotificacao()
      }
      if (wsListener.value) wsListener.value('fca_updated')
    } else if (event === 'nova_notificacao') {
      unreadNotif.value++
      dispararNotificacao()
      if (notifPanelRef.value) notifPanelRef.value.load()
    } else if (event) {
      if (wsListener.value) wsListener.value(event)
    }
  }
  _ws.onclose = () => { _wsTimer = setTimeout(connectWs, 3000) }
  _ws.onerror = () => _ws.close()
}

const canOpenFca = computed(() => {
  if (!user.value) return false
  return !['Producao'].includes(user.value.sector)
})

async function _afterLogin(me) {
  await loadAvatar(me.avatar_url)
  connectWs()
  try {
    const c = await api.notifications.unreadCount()
    unreadNotif.value = c.count ?? 0
  } catch { /* silencioso */ }
}

onMounted(async () => {
  const localToken = getLocalToken()
  if (localToken) {
    try {
      const payload = JSON.parse(atob(localToken.split('.')[1]))
      if (payload.exp && payload.exp * 1000 > Date.now()) {
        const me = await api.auth.me().catch(() => null)
        if (me) {
          user.value = { ...me, provider: 'local' }
          loading.value = false
          await _afterLogin(me)
          if (router.currentRoute.value.path === '/login' || router.currentRoute.value.path === '/') router.replace('/dashboard')
          return
        }
      }
    } catch { /* token malformado */ }
    clearLocalToken()
  }
  try {
    const response = await msal.handleRedirectPromise()
    const account = response?.account || msal.getAllAccounts()[0]
    if (account) {
      const me = await api.auth.me().catch(() => null)
      if (me) {
        user.value = { ...me, provider: 'microsoft' }
        loading.value = false
        await _afterLogin(me)
        router.replace('/dashboard')
        return
      }
    }
  } catch { /* sem sessão */ }
  loading.value = false
})

async function onLogin(userData) {
  user.value = userData
  await _afterLogin(userData)
  router.replace('/dashboard')
}

async function onPasswordChanged() {
  if (user.value) user.value.must_change_password = false
  // Atualiza dados do usuário
  try {
    const me = await api.auth.me().catch(() => null)
    if (me) user.value = { ...user.value, ...me }
  } catch { /* silencioso */ }
}

async function onOnboardingDone() {
  if (user.value) user.value.onboarding_completed = true
  router.replace('/dashboard')
}

async function onLogout() {
  clearLocalToken()
  if (user.value?.provider === 'microsoft') await msal.logoutRedirect()
  user.value = null
  router.replace('/login')
}
</script>


<style>
/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-family-base);
  background: var(--color-neutral-100);
  color: var(--color-neutral-900);
  font-size: var(--font-size-base);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { line-height: 1.25; }
h1 { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); }
h2 { font-size: var(--font-size-xl); font-weight: var(--font-weight-semibold); }
h3 { font-size: var(--font-size-lg); font-weight: var(--font-weight-semibold); }

/* ── Skip link ── */
.skip-link {
  position: absolute; left: -9999px; top: var(--space-2); z-index: 9999;
  background: var(--color-primary-700); color: #fff; padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); text-decoration: none;
}
.skip-link:focus { left: var(--space-2); }

/* ── Loading ── */
.app-loading {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: var(--color-neutral-50);
}
.loading-spinner {
  width: 36px; height: 36px; border: 3px solid var(--color-primary-100);
  border-top-color: var(--color-primary-500); border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── App Shell ── */
.app-shell { display: flex; min-height: 100vh; }

/* ── Sidebar ── */
.sidebar {
  position: fixed; left: 0; top: 0; height: 100vh;
  width: var(--sidebar-width);
  background: #fff;
  border-right: 1px solid var(--color-neutral-200);
  display: flex; flex-direction: column;
  transition: width var(--transition-base);
  z-index: 200;
  overflow: hidden;
}
.sidebar-collapsed { width: var(--sidebar-width-collapsed); }

.sidebar-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 199;
}
.fade-overlay-enter-active, .fade-overlay-leave-active { transition: opacity var(--transition-base); }
.fade-overlay-enter-from, .fade-overlay-leave-to { opacity: 0; }

/* Logo */
.sidebar-logo {
  position: relative;
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--color-neutral-100);
  min-height: 60px; overflow: visible;
}
.sidebar-logo-icon { flex-shrink: 0; }
.sidebar-logo-text {
  font-size: var(--font-size-base); font-weight: var(--font-weight-bold);
  color: var(--color-primary-700); white-space: nowrap; flex: 1;
  transition: opacity var(--transition-base);
}

/* Nav */
.sidebar-nav { flex: 1; overflow-y: auto; padding: var(--space-3) 0; }
.sidebar-section { margin-bottom: var(--space-3); }
.sidebar-section-label {
  display: block; padding: var(--space-2) var(--space-4) var(--space-1);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-400); text-transform: uppercase; letter-spacing: .06em;
  white-space: nowrap; overflow: hidden;
}
.sidebar-collapsed .sidebar-section-label { opacity: 0; height: 0; padding: 0; margin: 0; }

.sidebar-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  border-radius: 0; cursor: pointer; font-size: var(--font-size-sm);
  color: var(--color-neutral-600); text-decoration: none;
  transition: background var(--transition-fast), color var(--transition-fast);
  position: relative; white-space: nowrap;
}
.sidebar-item:hover { background: var(--color-neutral-50); color: var(--color-primary-700); }
.sidebar-item.router-link-active {
  background: var(--color-primary-50); color: var(--color-primary-700);
  font-weight: var(--font-weight-semibold);
}
.sidebar-item.router-link-active .sidebar-item-icon { color: var(--color-primary-500); }
.sidebar-item-icon { flex-shrink: 0; display: flex; align-items: center; justify-content: center; width: 20px; height: 20px; }
.sidebar-item-label { flex: 1; transition: opacity var(--transition-base), max-width var(--transition-base); max-width: 200px; overflow: hidden; }
.sidebar-item-new .sidebar-item-icon { color: var(--color-primary-500); }

/* Collapsed states — apenas escondem labels, os ícones ficam clicáveis */
.sidebar-collapsed .sidebar-item-label,
.sidebar-collapsed .sidebar-user-info,
.sidebar-collapsed .sidebar-logo-text { opacity: 0; max-width: 0; }
.sidebar-collapsed .sidebar-logout span:not(.sidebar-tooltip) { opacity: 0; max-width: 0; overflow: hidden; }
.sidebar-collapsed .sidebar-section-label { opacity: 0; height: 0; padding: 0; margin: 0; }
.sidebar-collapsed .sidebar-item {
  justify-content: center;
  padding: var(--space-3) var(--space-2);
  gap: 0;
}
.sidebar-collapsed .sidebar-logo { justify-content: center; gap: 0; padding: var(--space-4) var(--space-2); }
.sidebar-collapsed .sidebar-user { justify-content: center; gap: 0; }
.sidebar-collapsed .sidebar-logout { justify-content: center; gap: 0; }

/* Botão flutuante de toggle — sempre visível na borda da sidebar */
.sidebar-toggle-btn {
  position: fixed;
  top: 20px;
  left: calc(var(--sidebar-width) - 14px);
  width: 28px; height: 28px; border-radius: 50%;
  background: #fff; border: 1.5px solid var(--color-neutral-200);
  box-shadow: var(--shadow-md);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: var(--color-neutral-500);
  z-index: 210;
  transition: left var(--transition-base), color var(--transition-fast), border-color var(--transition-fast);
}
.sidebar-toggle-btn:hover { color: var(--color-primary-500); border-color: var(--color-primary-300); }
.sidebar-is-collapsed .sidebar-toggle-btn { left: calc(var(--sidebar-width-collapsed) - 14px); }

/* Tooltips */
.sidebar-tooltip {
  display: none;
  position: absolute; left: calc(100% + 8px); top: 50%;
  transform: translateY(-50%);
  background: var(--color-neutral-900); color: #fff;
  font-size: var(--font-size-xs); padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm); white-space: nowrap; pointer-events: none;
  z-index: 300;
}
.sidebar-collapsed .sidebar-item:hover .sidebar-tooltip,
.sidebar-collapsed .sidebar-user:hover .sidebar-tooltip,
.sidebar-collapsed .sidebar-logout:hover .sidebar-tooltip { display: block; }

/* Bottom user section */
.sidebar-bottom {
  border-top: 1px solid var(--color-neutral-200);
  padding: var(--space-3) var(--space-2);
  display: flex; flex-direction: column; gap: var(--space-1);
}
.sidebar-user {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-2); border-radius: var(--radius-md);
  text-decoration: none; cursor: pointer; position: relative;
  transition: background var(--transition-fast);
}
.sidebar-user:hover { background: var(--color-neutral-50); }
.sidebar-user-info { flex: 1; min-width: 0; }
.sidebar-user-name {
  display: block; font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-800); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sidebar-user-meta {
  display: block; font-size: var(--font-size-xs); color: var(--color-neutral-500);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sidebar-logout {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-2); border-radius: var(--radius-md);
  background: none; border: none; cursor: pointer; font-size: var(--font-size-sm);
  color: var(--color-neutral-500); width: 100%;
  transition: background var(--transition-fast), color var(--transition-fast);
  position: relative;
}
.sidebar-logout:hover { background: var(--color-danger-bg); color: var(--color-danger-text); }

/* ── Main area ── */
.main-area {
  flex: 1; display: flex; flex-direction: column;
  margin-left: var(--sidebar-width);
  transition: margin-left var(--transition-base);
  min-width: 0;
}
.sidebar-is-collapsed .main-area { margin-left: var(--sidebar-width-collapsed); }

/* ── Topbar ── */
.topbar {
  position: sticky; top: 0; z-index: 100;
  height: var(--topbar-height);
  background: #fff;
  border-bottom: 1px solid var(--color-neutral-200);
  box-shadow: var(--shadow-sm);
  display: flex; align-items: center; gap: var(--space-4);
  padding: 0 var(--space-6);
}
.topbar-hamburger {
  display: none; background: none; border: none; cursor: pointer;
  color: var(--color-neutral-500); padding: var(--space-1); border-radius: var(--radius-sm);
}
.topbar-title {
  font-size: var(--font-size-base); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-800); flex: 1;
}
.topbar-right { display: flex; align-items: center; gap: var(--space-3); }

.topbar-search {
  position: relative; display: flex; align-items: center;
}
.topbar-search-icon {
  position: absolute; left: var(--space-3); color: var(--color-neutral-400); pointer-events: none;
}
.topbar-search-input {
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-7);
  border: 1px solid var(--color-neutral-200); border-radius: var(--radius-full);
  font-size: var(--font-size-sm); background: var(--color-neutral-50);
  color: var(--color-neutral-800); outline: none; width: 200px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast), width var(--transition-base);
}
.topbar-search-input:focus {
  border-color: var(--color-primary-300); background: #fff;
  box-shadow: 0 0 0 3px var(--color-primary-100); width: 260px;
}
.topbar-search-input::placeholder { color: var(--color-neutral-400); }

.topbar-notif {
  position: relative; display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: var(--radius-md);
  color: var(--color-neutral-500); text-decoration: none;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.topbar-notif:hover { background: var(--color-neutral-100); color: var(--color-neutral-700); }
.notif-badge {
  position: absolute; top: 3px; right: 3px;
  background: var(--color-danger); color: #fff;
  font-size: 10px; font-weight: var(--font-weight-bold);
  min-width: 16px; height: 16px; border-radius: var(--radius-full);
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px; line-height: 1;
}
.topbar-avatar { border-radius: var(--radius-full); cursor: pointer; text-decoration: none; }

/* ── Content ── */
.content {
  flex: 1; padding: var(--space-6);
  max-width: 1200px; width: 100%;
}

.version-bar {
  padding: var(--space-2) var(--space-6);
  text-align: right; font-size: var(--font-size-xs);
  color: var(--color-neutral-300); border-top: 1px solid var(--color-neutral-100);
}

/* ── Utilitários globais ── */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-5); border: none; border-radius: var(--radius-md);
  cursor: pointer; font-size: var(--font-size-sm); font-weight: var(--font-weight-medium);
  font-family: var(--font-family-base);
  transition: opacity var(--transition-base), box-shadow var(--transition-base), transform var(--transition-fast), background var(--transition-fast);
  text-decoration: none; white-space: nowrap; line-height: 1;
}
.btn:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.btn:active:not(:disabled) { transform: translateY(0); box-shadow: none; }
.btn:focus-visible { outline: 2px solid var(--color-primary-500); outline-offset: 2px; }
.btn:disabled { opacity: .45; cursor: not-allowed; transform: none; box-shadow: none; }

.btn-primary   { background: var(--color-primary-700); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--color-primary-900); }
.btn-secondary { background: var(--color-neutral-100); color: var(--color-neutral-700); }
.btn-secondary:hover:not(:disabled) { background: var(--color-neutral-200); }
.btn-ghost     { background: transparent; color: var(--color-neutral-600); }
.btn-ghost:hover:not(:disabled) { background: var(--color-neutral-100); }
.btn-danger    { background: var(--color-danger); color: #fff; }
.btn-danger:hover:not(:disabled) { background: var(--color-danger-text); }
.btn-outline   { background: transparent; border: 1.5px solid var(--color-primary-500); color: var(--color-primary-700); }
.btn-outline:hover:not(:disabled) { background: var(--color-primary-50); }
.btn-success   { background: var(--color-success); color: #fff; }
.btn-success:hover:not(:disabled) { background: var(--color-success-text); }
.btn-warning   { background: var(--color-warning); color: #fff; }
.btn-warning:hover:not(:disabled) { background: #b45309; }

.btn-sm  { padding: var(--space-1) var(--space-3); font-size: var(--font-size-xs); }
.btn-lg  { padding: var(--space-3) var(--space-7); font-size: var(--font-size-base); }

/* Cards */
.card {
  background: #fff; border-radius: var(--radius-lg);
  padding: var(--space-5); box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}
.card-interactive { cursor: pointer; transition: box-shadow var(--transition-base), transform var(--transition-base); }
.card-interactive:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

/* Badges */
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px var(--space-3); border-radius: var(--radius-full);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); line-height: 1.4;
}
.badge::before { content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.badge-aberto               { background: var(--color-info-bg);    color: var(--color-info-text); }
.badge-em_andamento         { background: var(--color-warning-bg); color: var(--color-warning-text); }
.badge-aguardando_devolutiva { background: var(--color-purple-bg);  color: var(--color-purple-text); }
.badge-encerrado            { background: var(--color-success-bg); color: var(--color-success-text); }
.badge-cancelado            { background: var(--color-neutral-100); color: var(--color-neutral-500); text-decoration: line-through; }

/* Form groups */
.form-group { display: flex; flex-direction: column; gap: var(--space-1); }
.form-group label { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-neutral-700); }
.form-group input,
.form-group select,
.form-group textarea {
  padding: var(--space-2) var(--space-3);
  border: 1.5px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--font-size-sm);
  color: var(--color-neutral-900); background: #fff;
  font-family: var(--font-family-base); outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}
.form-group textarea { resize: vertical; min-height: 80px; }
.form-group input.input-error,
.form-group select.input-error { border-color: var(--color-danger); }

/* Skeleton */
@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
.skeleton {
  background: linear-gradient(90deg, var(--color-neutral-200) 25%, var(--color-neutral-100) 50%, var(--color-neutral-200) 75%);
  background-size: 800px 100%;
  animation: shimmer 1.5s infinite linear;
  border-radius: var(--radius-sm);
}
.skeleton-text  { height: 1rem; border-radius: var(--radius-sm); }
.skeleton-rect  { border-radius: var(--radius-md); }
.skeleton-avatar { width: 40px; height: 40px; border-radius: var(--radius-full); }

/* Misc */
.error-msg  { color: var(--color-danger-text); font-size: var(--font-size-sm); margin-top: var(--space-1); }
.empty-state { color: var(--color-neutral-400); font-size: var(--font-size-sm); padding: var(--space-6) 0; text-align: center; }
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-6);
}
.page-header h1 { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); color: var(--color-neutral-900); }
.section-title {
  font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: .06em;
  display: flex; align-items: center; gap: var(--space-2); margin: 0;
}

/* Animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fade-in-up { animation: fadeInUp var(--transition-slow) ease forwards; }

/* ── Responsivo ── */
@media (max-width: 1024px) {
  :root { --sidebar-width: var(--sidebar-width-collapsed); }
  .sidebar-item-label, .sidebar-user-info, .sidebar-logo-text { opacity: 0; max-width: 0; overflow: hidden; }
  .sidebar-logout span:not(.sidebar-tooltip) { opacity: 0; max-width: 0; overflow: hidden; }
  .sidebar-section-label { opacity: 0; height: 0; padding: 0; }
  .sidebar-item { justify-content: center; padding: var(--space-3) var(--space-2); gap: 0; }
  .sidebar-logo { justify-content: center; gap: 0; padding: var(--space-4) var(--space-2); }
  .sidebar-user { justify-content: center; gap: 0; }
  .sidebar-logout { justify-content: center; gap: 0; }
  .sidebar-item:hover .sidebar-tooltip,
  .sidebar-user:hover .sidebar-tooltip,
  .sidebar-logout:hover .sidebar-tooltip { display: block; }
  .sidebar-toggle-btn { left: calc(var(--sidebar-width-collapsed) - 14px); }
}
@media (max-width: 768px) {
  .topbar-hamburger { display: flex; }
  .topbar-search { display: none; }
  .sidebar-toggle-btn { display: none; }
  .sidebar {
    transform: translateX(-100%);
    transition: transform var(--transition-base);
    width: var(--sidebar-width) !important;
  }
  .sidebar-open {
    transform: translateX(0);
    width: var(--sidebar-width) !important;
  }
  /* Restaura tudo no mobile drawer */
  .sidebar-item-label, .sidebar-user-info, .sidebar-logo-text { opacity: 1 !important; max-width: 200px !important; }
  .sidebar-logout span:not(.sidebar-tooltip) { opacity: 1 !important; max-width: 200px !important; }
  .sidebar-section-label { opacity: 1 !important; height: auto !important; padding: var(--space-2) var(--space-4) var(--space-1) !important; }
  .sidebar-item { justify-content: flex-start !important; padding: var(--space-2) var(--space-4) !important; gap: var(--space-3) !important; }
  .sidebar-logo { justify-content: flex-start !important; gap: var(--space-3) !important; padding: var(--space-4) !important; }
  .sidebar-user { justify-content: flex-start !important; gap: var(--space-3) !important; }
  .sidebar-logout { justify-content: flex-start !important; gap: var(--space-3) !important; }
  .main-area { margin-left: 0 !important; }
  .content { padding: var(--space-4); }
}
</style>
