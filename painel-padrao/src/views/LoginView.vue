<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo">Sistema FCA</div>
      <p class="subtitle">Ficha de Correção de Ação</p>

      <button class="btn-ms" @click="loginMicrosoft" :disabled="loading === 'ms'">
        <img src="https://learn.microsoft.com/en-us/azure/active-directory/develop/media/howto-add-branding-in-apps/ms-symbollockup_mssymbol_19.svg" alt="Microsoft" />
        {{ loading === 'ms' ? 'Entrando...' : 'Entrar com Microsoft' }}
      </button>

      <div class="divider"><span>ou</span></div>

      <form @submit.prevent="loginLocal">
        <div class="form-group">
          <input v-model="email" type="email" placeholder="E-mail" autocomplete="email" required />
        </div>
        <div class="form-group">
          <input v-model="password" type="password" placeholder="Senha" autocomplete="current-password" required />
        </div>
        <button class="btn btn-primary" type="submit" :disabled="loading === 'local'" style="width:100%">
          {{ loading === 'local' ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>

      <p v-if="error" class="error-msg" role="alert">{{ error }}</p>

      <!-- Setup primeiro admin (só aparece se nenhum usuário existe) -->
      <div v-if="showSetup" class="setup-box">
        <p>Primeira vez? Configure o administrador:</p>
        <form @submit.prevent="doSetup" style="display:flex;flex-direction:column;gap:.5rem;margin-top:.5rem">
          <input v-model="setupName" type="text" placeholder="Nome completo" required />
          <input v-model="setupEmail" type="email" placeholder="E-mail" required />
          <input v-model="setupPassword" type="password" placeholder="Senha (mín. 8 caracteres)" required minlength="8" />
          <button class="btn btn-primary" type="submit">Criar Administrador</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { loginRequest } from '../authConfig'
import { api, saveLocalToken } from '../api'

const emit = defineEmits(['login'])
const msal = inject('msal')

const loading  = ref('')
const error    = ref('')
const email    = ref('')
const password = ref('')
const showSetup = ref(false)
const setupName = ref('')
const setupEmail = ref('')
const setupPassword = ref('')

onMounted(async () => {
  try {
    const res = await fetch(import.meta.env.VITE_API_URL + '/api/auth/setup/status')
    if (res.ok) {
      const data = await res.json()
      showSetup.value = data.setup_disponivel
    }
  } catch { /* ignore */ }
})

async function loginMicrosoft() {
  loading.value = 'ms'
  error.value = ''
  try {
    await msal.loginRedirect(loginRequest)
  } catch {
    error.value = 'Erro ao autenticar. Tente novamente.'
    loading.value = ''
  }
}

async function loginLocal() {
  loading.value = 'local'
  error.value = ''
  try {
    const res = await api.auth.login(email.value, password.value)
    saveLocalToken(res.access_token)
    emit('login', { ...res.user, provider: 'local' })
  } catch (e) {
    error.value = e.message || 'Credenciais inválidas'
  } finally {
    loading.value = ''
  }
}

async function doSetup() {
  loading.value = 'setup'
  error.value = ''
  try {
    const res = await api.auth.setup(setupEmail.value, setupName.value, setupPassword.value)
    saveLocalToken(res.access_token)
    emit('login', { ...res.user, provider: 'local' })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = ''
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #e0e7ff 100%);
}
.login-card {
  background: #fff; border-radius: 16px; padding: 2.5rem 2rem;
  box-shadow: 0 8px 32px rgba(0,0,0,.1); text-align: center; max-width: 380px; width: 100%;
}
.logo { font-size: 1.2rem; font-weight: 700; color: #1a56db; margin-bottom: .25rem; }
.subtitle { font-size: .82rem; color: #888; margin-bottom: 1.5rem; }

.btn-ms {
  display: flex; align-items: center; justify-content: center; gap: .6rem;
  width: 100%; padding: .75rem 1.25rem; background: #fff; border: 1px solid #ddd;
  border-radius: 8px; font-size: .9rem; font-weight: 500; cursor: pointer;
  transition: box-shadow .2s, border-color .2s; color: #1a1a2e;
}
.btn-ms:hover:not(:disabled) { box-shadow: 0 2px 12px rgba(26,86,219,.15); border-color: #1a56db; }
.btn-ms:disabled { opacity: .6; cursor: not-allowed; }
.btn-ms img { width: 20px; }

.divider { display: flex; align-items: center; gap: .6rem; margin: 1.1rem 0; color: #bbb; font-size: .82rem; }
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: #eee; }

form { display: flex; flex-direction: column; gap: .6rem; text-align: left; }
input { padding: .6rem .9rem; border: 1px solid #d1d5db; border-radius: 7px; font-size: .9rem; outline: none; width: 100%; }
input:focus { border-color: #1a56db; }

.error-msg { color: #dc2626; font-size: .82rem; margin-top: .75rem; }

.setup-box { margin-top: 1.25rem; padding: 1rem; background: #f0fdf4; border-radius: 8px; text-align: left; font-size: .82rem; }
.setup-box p { color: #065f46; font-weight: 600; margin-bottom: 0; }
</style>
