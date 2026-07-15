<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="login-logo-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <path d="M7 14h14M7 9h9M7 19h11" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="logo">Sistema FCA</div>
        <p class="subtitle">Ficha de Correção de Ação</p>
      </div>

      <button class="btn-ms" @click="loginMicrosoft" :disabled="loading === 'ms'">
        <img src="https://learn.microsoft.com/en-us/azure/active-directory/develop/media/howto-add-branding-in-apps/ms-symbollockup_mssymbol_19.svg" alt="Microsoft" />
        {{ loading === 'ms' ? 'Entrando...' : 'Entrar com Microsoft' }}
      </button>

      <div class="divider"><span>ou</span></div>

      <form @submit.prevent="loginLocal">
        <div class="form-field">
          <label>E-mail</label>
          <input v-model="email" type="email" placeholder="seu@email.com" autocomplete="email" required />
        </div>
        <div class="form-field">
          <label>Senha</label>
          <input v-model="password" type="password" placeholder="••••••••" autocomplete="current-password" required />
        </div>
        <button class="btn-submit" type="submit" :disabled="loading === 'local'">
          {{ loading === 'local' ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>

      <p v-if="error" class="error-msg" role="alert">{{ error }}</p>

      <div v-if="showSetup" class="setup-box">
        <p>Primeira vez? Configure o administrador:</p>
        <form @submit.prevent="doSetup">
          <input v-model="setupName" type="text" placeholder="Nome completo" required />
          <input v-model="setupEmail" type="email" placeholder="E-mail" required />
          <input v-model="setupPassword" type="password" placeholder="Senha (mín. 8 caracteres)" required minlength="8" />
          <button class="btn-submit" type="submit">Criar Administrador</button>
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
  background: linear-gradient(135deg, var(--color-primary-50) 0%, #e0e7ff 100%);
  font-family: var(--font-family-base);
}
.login-card {
  background: #fff; border-radius: var(--radius-xl); padding: var(--space-8) var(--space-7);
  box-shadow: var(--shadow-lg); text-align: center; max-width: 400px; width: 100%;
  border: 1px solid var(--color-neutral-100);
}
.login-brand { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); margin-bottom: var(--space-7); }
.login-logo-icon {
  width: 52px; height: 52px; background: var(--color-primary-500); border-radius: var(--radius-lg);
  display: flex; align-items: center; justify-content: center;
}
.logo { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-primary-700); }
.subtitle { font-size: var(--font-size-sm); color: var(--color-neutral-400); }

.btn-ms {
  display: flex; align-items: center; justify-content: center; gap: var(--space-3);
  width: 100%; padding: var(--space-3) var(--space-5);
  background: #fff; border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); font-weight: var(--font-weight-medium);
  cursor: pointer; transition: box-shadow var(--transition-base), border-color var(--transition-base);
  color: var(--color-neutral-800); font-family: var(--font-family-base);
}
.btn-ms:hover:not(:disabled) { box-shadow: var(--shadow-md); border-color: var(--color-primary-300); }
.btn-ms:disabled { opacity: .5; cursor: not-allowed; }
.btn-ms img { width: 20px; }

.divider { display: flex; align-items: center; gap: var(--space-3); margin: var(--space-5) 0; color: var(--color-neutral-300); font-size: var(--font-size-xs); }
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--color-neutral-200); }

form { display: flex; flex-direction: column; gap: var(--space-3); text-align: left; }
.form-field { display: flex; flex-direction: column; gap: var(--space-1); }
.form-field label { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-neutral-700); }
.form-field input {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); outline: none;
  width: 100%; font-family: var(--font-family-base); transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.form-field input:focus { border-color: var(--color-primary-500); box-shadow: 0 0 0 3px var(--color-primary-100); }
.btn-submit {
  width: 100%; padding: var(--space-3); background: var(--color-primary-700); color: #fff;
  border: none; border-radius: var(--radius-md); font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold); cursor: pointer; font-family: var(--font-family-base);
  transition: background var(--transition-fast), box-shadow var(--transition-base);
  margin-top: var(--space-1);
}
.btn-submit:hover:not(:disabled) { background: var(--color-primary-900); box-shadow: var(--shadow-md); }
.btn-submit:disabled { opacity: .5; cursor: not-allowed; }

.error-msg { color: var(--color-danger-text); font-size: var(--font-size-sm); margin-top: var(--space-3); background: var(--color-danger-bg); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); }

.setup-box { margin-top: var(--space-5); padding: var(--space-4); background: var(--color-success-bg); border-radius: var(--radius-md); text-align: left; }
.setup-box p { color: var(--color-success-text); font-weight: var(--font-weight-semibold); font-size: var(--font-size-sm); margin-bottom: var(--space-3); }
.setup-box form { display: flex; flex-direction: column; gap: var(--space-2); }
.setup-box input { padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-300); border-radius: var(--radius-md); font-size: var(--font-size-sm); outline: none; font-family: var(--font-family-base); }
.setup-box input:focus { border-color: var(--color-primary-500); }
</style>
