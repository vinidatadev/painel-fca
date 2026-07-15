<template>
  <div class="change-pw-wrapper">
    <div class="change-pw-card">
      <div class="change-pw-icon">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="12" fill="var(--color-primary-500)"/>
          <path d="M14 20h12M14 15h7M14 25h9" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
          <circle cx="28" cy="14" r="4" fill="#fff" fill-opacity=".2" stroke="#fff" stroke-width="1.5"/>
          <path d="M27 14h2M28 13v2" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>

      <h1 class="change-pw-title">Crie sua senha</h1>
      <p class="change-pw-sub">Este é seu primeiro acesso. Defina uma senha segura para continuar.</p>

      <form @submit.prevent="submit" class="change-pw-form">
        <div class="form-group">
          <label for="nova">Nova senha</label>
          <div class="pw-input-wrap">
            <input
              id="nova"
              v-model="nova"
              :type="showNova ? 'text' : 'password'"
              placeholder="Mínimo 8 caracteres"
              autocomplete="new-password"
              required
            />
            <button type="button" class="pw-toggle" @click="showNova = !showNova" tabindex="-1">
              <svg v-if="!showNova" width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M1 9s3-5.5 8-5.5S17 9 17 9s-3 5.5-8 5.5S1 9 1 9z" stroke="currentColor" stroke-width="1.5"/><circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.5"/></svg>
              <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M2 2l14 14M7.5 6.5A3 3 0 0112 11M4 5C2.5 6.5 1 9 1 9s3 5.5 8 5.5c1.8 0 3.4-.5 4.7-1.3M14.5 12.5C16 11 17 9 17 9s-3-5.5-8-5.5c-.7 0-1.3.1-2 .2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            </button>
          </div>
          <div class="pw-strength">
            <div class="pw-strength-bar" :class="strengthClass"></div>
            <span class="pw-strength-label">{{ strengthLabel }}</span>
          </div>
        </div>

        <div class="form-group">
          <label for="confirma">Confirmar senha</label>
          <div class="pw-input-wrap">
            <input
              id="confirma"
              v-model="confirma"
              :type="showConfirma ? 'text' : 'password'"
              placeholder="Repita a senha"
              autocomplete="new-password"
              required
            />
            <button type="button" class="pw-toggle" @click="showConfirma = !showConfirma" tabindex="-1">
              <svg v-if="!showConfirma" width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M1 9s3-5.5 8-5.5S17 9 17 9s-3 5.5-8 5.5S1 9 1 9z" stroke="currentColor" stroke-width="1.5"/><circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.5"/></svg>
              <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M2 2l14 14M7.5 6.5A3 3 0 0112 11M4 5C2.5 6.5 1 9 1 9s3 5.5 8 5.5c1.8 0 3.4-.5 4.7-1.3M14.5 12.5C16 11 17 9 17 9s-3-5.5-8-5.5c-.7 0-1.3.1-2 .2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            </button>
          </div>
          <p v-if="confirma && nova !== confirma" class="form-error">As senhas não coincidem.</p>
        </div>

        <p v-if="error" class="form-error">{{ error }}</p>

        <button type="submit" class="btn-primary" :disabled="loading || nova !== confirma || nova.length < 8">
          <span v-if="loading" class="btn-spinner"></span>
          <span v-else>Salvar e continuar</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api } from '../api.js'

const emit = defineEmits(['done'])

const nova = ref('')
const confirma = ref('')
const showNova = ref(false)
const showConfirma = ref(false)
const loading = ref(false)
const error = ref('')

const strength = computed(() => {
  const v = nova.value
  if (v.length < 8) return 0
  let score = 0
  if (v.length >= 12) score++
  if (/[A-Z]/.test(v)) score++
  if (/[0-9]/.test(v)) score++
  if (/[^A-Za-z0-9]/.test(v)) score++
  return score
})

const strengthClass = computed(() => ['weak', 'fair', 'good', 'strong', 'strong'][strength.value])
const strengthLabel = computed(() => {
  if (!nova.value) return ''
  return ['Muito fraca', 'Fraca', 'Razoável', 'Boa', 'Forte'][strength.value]
})

async function submit() {
  if (nova.value !== confirma.value) return
  loading.value = true
  error.value = ''
  try {
    await api.auth.changePassword(nova.value)
    emit('done')
  } catch (e) {
    error.value = e.message || 'Erro ao salvar senha.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-pw-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-primary);
  padding: 1.5rem;
}

.change-pw-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 420px;
  text-align: center;
}

.change-pw-icon {
  display: inline-flex;
  margin-bottom: 1.25rem;
}

.change-pw-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 0.4rem;
}

.change-pw-sub {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0 0 1.75rem;
  line-height: 1.5;
}

.change-pw-form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  text-align: left;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.pw-input-wrap {
  position: relative;
}

.pw-input-wrap input {
  width: 100%;
  padding: 0.65rem 2.5rem 0.65rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.95rem;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.pw-input-wrap input:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

.pw-toggle {
  position: absolute;
  right: 0.6rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-tertiary);
  padding: 0.2rem;
  display: flex;
}

.pw-strength {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.2rem;
}

.pw-strength-bar {
  height: 3px;
  border-radius: 2px;
  flex: 1;
  background: var(--color-border);
  transition: background 0.3s;
}

.pw-strength-bar.weak   { background: #ef4444; width: 25%; }
.pw-strength-bar.fair   { background: #f59e0b; width: 50%; }
.pw-strength-bar.good   { background: #3b82f6; width: 75%; }
.pw-strength-bar.strong { background: #22c55e; width: 100%; }

.pw-strength-label {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  min-width: 70px;
}

.form-error {
  font-size: 0.8rem;
  color: #ef4444;
  margin: 0;
}

.btn-primary {
  padding: 0.7rem 1.5rem;
  background: var(--color-primary-500);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
