<template>
  <div style="max-width:600px">
    <div class="page-header">
      <h1>Meu Perfil</h1>
    </div>

    <div v-if="loading" class="loading-text">Carregando...</div>

    <template v-else>
      <!-- Avatar -->
      <div class="card avatar-section">
        <div class="avatar-area">
          <UserAvatar :name="perfil.name" :avatarUrl="avatarUrl" :size="80" />
          <div class="avatar-actions">
            <label class="btn btn-outline btn-sm" style="cursor:pointer">
              {{ uploadingAvatar ? 'Enviando...' : '📷 Alterar foto' }}
              <input type="file" accept="image/jpeg,image/png,image/webp" @change="onAvatar" style="display:none" />
            </label>
            <button v-if="perfil.avatar_url" class="btn btn-danger btn-sm" @click="removerAvatar">Remover</button>
          </div>
        </div>
        <div class="user-info-block">
          <h2>{{ perfil.name }}</h2>
          <span class="chip">{{ perfil.sector }} · {{ perfil.company }}</span>
          <span class="chip chip-role">{{ perfil.role }}</span>
          <p class="email">{{ perfil.email }}</p>
        </div>
      </div>

      <!-- Dados editáveis -->
      <div class="card" style="margin-top:1rem">
        <h3 class="section-title">Informações</h3>
        <form @submit.prevent="salvar">
          <div class="form-grid">
            <div class="form-group">
              <label>Matrícula</label>
              <input v-model="form.matricula" type="text" placeholder="Número de matrícula" />
            </div>
            <div class="form-group">
              <label>Turno</label>
              <select v-model="form.turno">
                <option value="">—</option>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="D">D</option>
              </select>
            </div>
            <div class="form-group" style="grid-column:1/-1">
              <label>Telefone / WhatsApp</label>
              <input v-model="form.telefone" type="tel" placeholder="(00) 00000-0000" />
            </div>
          </div>

          <p v-if="successInfo" class="success-msg">{{ successInfo }}</p>
          <p v-if="errorInfo" class="error-msg">{{ errorInfo }}</p>

          <button class="btn btn-primary" type="submit" :disabled="salvando" style="margin-top:.75rem">
            {{ salvando ? 'Salvando...' : 'Salvar' }}
          </button>
        </form>
      </div>

      <!-- Notificações -->
      <div class="card" style="margin-top:1rem">
        <h3 class="section-title">Notificações</h3>
        <p class="notif-desc">Escolha como quer ser avisado quando um FCA chegar no seu setor.</p>

        <div class="notif-list">
          <label class="notif-item">
            <div class="notif-info">
              <span class="notif-icon">✉️</span>
              <div>
                <strong>E-mail</strong>
                <p>Receba por e-mail quando um FCA precisar da sua ação</p>
              </div>
            </div>
            <div class="toggle-wrap">
              <input type="checkbox" v-model="form.notif_email" class="toggle" @change="salvarNotif" />
            </div>
          </label>

          <label class="notif-item">
            <div class="notif-info">
              <span class="notif-icon">📱</span>
              <div>
                <strong>SMS / Telefone</strong>
                <p>Receba por SMS (requer telefone cadastrado)</p>
              </div>
            </div>
            <div class="toggle-wrap">
              <input type="checkbox" v-model="form.notif_sms" class="toggle" @change="salvarNotif" :disabled="!form.telefone" />
            </div>
          </label>

          <label class="notif-item">
            <div class="notif-info">
              <span class="notif-icon">🔔</span>
              <div>
                <strong>Badge na aba do navegador</strong>
                <p>Mostra contador na aba quando chegar FCA e você não estiver olhando</p>
              </div>
            </div>
            <div class="toggle-wrap">
              <input type="checkbox" v-model="form.notif_push" class="toggle" @change="salvarNotif" />
            </div>
          </label>
        </div>
      </div>

      <!-- Som de notificação -->
      <div class="card" style="margin-top:1rem">
        <h3 class="section-title">Som de notificação</h3>
        <p class="notif-desc">Escolha o som que toca quando um novo FCA chegar (funciona mesmo com a aba em segundo plano).</p>

        <div class="som-grid">
          <div
            v-for="opt in somOpcoes"
            :key="opt.value"
            class="som-card"
            :class="{ 'som-card--ativo': form.notif_som === opt.value }"
            @click="selecionarSom(opt.value)"
          >
            <span class="som-icon">{{ opt.icon }}</span>
            <span class="som-label">{{ opt.label }}</span>
            <button
              v-if="opt.value !== 'none'"
              class="btn-preview"
              type="button"
              @click.stop="previewSom(opt.value)"
              title="Ouvir"
            >▶</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api'
import UserAvatar from '../components/UserAvatar.vue'

const userRef = inject('user')
const reloadAvatar = inject('reloadAvatar')
const reloadUser   = inject('reloadUser')
const playSound    = inject('playSound')

const perfil  = ref(null)
const loading = ref(true)
const salvando = ref(false)
const uploadingAvatar = ref(false)
const successInfo = ref('')
const errorInfo   = ref('')

const somOpcoes = [
  { value: 'none', icon: '🔕', label: 'Nenhum' },
  { value: 'som1', icon: '💬', label: 'Mensagem' },
  { value: 'som2', icon: '📨', label: 'Alerta' },
  { value: 'som3', icon: '🔔', label: 'Sino' },
  { value: 'som4', icon: '⚡', label: 'Urgente' },
]

const form = ref({
  matricula: '', turno: '', telefone: '',
  notif_email: true, notif_sms: false, notif_push: true,
  notif_som: 'som1',
})

// URL pré-assinada do avatar
const avatarUrl = ref(null)
async function loadAvatarUrl() {
  if (perfil.value?.avatar_url) {
    try {
      const res = await api.upload.url(perfil.value.avatar_url)
      avatarUrl.value = res.url
    } catch { avatarUrl.value = null }
  } else {
    avatarUrl.value = null
  }
}

onMounted(async () => {
  try {
    perfil.value = await api.perfil.get()
    form.value = {
      matricula:   perfil.value.matricula  || '',
      turno:       perfil.value.turno      || '',
      telefone:    perfil.value.telefone   || '',
      notif_email: perfil.value.notif_email,
      notif_sms:   perfil.value.notif_sms,
      notif_push:  perfil.value.notif_push,
      notif_som:   perfil.value.notif_som  || 'som1',
    }
    await loadAvatarUrl()
  } finally {
    loading.value = false
  }
})

async function salvar() {
  successInfo.value = ''
  errorInfo.value = ''
  salvando.value = true
  try {
    const res = await api.perfil.update({
      matricula: form.value.matricula || null,
      turno:     form.value.turno     || null,
      telefone:  form.value.telefone  || null,
    })
    perfil.value = res
    // Atualiza o user global (matricula/turno não afetam o token mas mantem consistência)
    successInfo.value = 'Salvo com sucesso!'
    setTimeout(() => successInfo.value = '', 3000)
  } catch (e) {
    errorInfo.value = e.message
  } finally {
    salvando.value = false
  }
}

async function salvarNotif() {
  try {
    await api.perfil.update({
      notif_email: form.value.notif_email,
      notif_sms:   form.value.notif_sms,
      notif_push:  form.value.notif_push,
      notif_som:   form.value.notif_som,
    })
    // Atualiza o user global para que o som reativo funcione imediatamente
    if (userRef) userRef.value = { ...userRef.value, notif_push: form.value.notif_push, notif_som: form.value.notif_som }
  } catch (e) {
    console.error(e)
  }
}

function previewSom(tipo) {
  playSound?.(tipo)
}

async function selecionarSom(valor) {
  form.value.notif_som = valor
  if (valor !== 'none') previewSom(valor)
  await salvarNotif()
}

async function onAvatar(e) {
  const file = e.target.files[0]
  if (!file) return
  uploadingAvatar.value = true
  try {
    perfil.value = await api.perfil.uploadAvatar(file)
    await loadAvatarUrl()
    reloadAvatar?.(perfil.value.avatar_url)
    // Atualiza o user global se injetado
    if (userRef) userRef.value = { ...userRef.value }
  } catch (err) {
    alert(err.message)
  } finally {
    uploadingAvatar.value = false
    e.target.value = ''
  }
}

async function removerAvatar() {
  if (!confirm('Remover foto?')) return
  try {
    perfil.value = await api.perfil.deleteAvatar()
    avatarUrl.value = null
    reloadAvatar?.(null)
  } catch (e) {
    alert(e.message)
  }
}
</script>

<style scoped>
.section-title { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); text-transform: uppercase; color: var(--color-neutral-500); letter-spacing: .06em; margin-bottom: var(--space-4); }

.avatar-section { display: flex; align-items: center; gap: var(--space-6); flex-wrap: wrap; }
.avatar-area { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.avatar-actions { display: flex; flex-direction: column; gap: var(--space-2); align-items: center; }
.user-info-block { flex: 1; }
.user-info-block h2 { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); margin-bottom: var(--space-2); }
.user-info-block .email { font-size: var(--font-size-xs); color: var(--color-neutral-400); margin-top: var(--space-1); }
.chip { display: inline-block; background: var(--color-primary-100); color: var(--color-primary-700); border-radius: var(--radius-full); padding: 2px var(--space-3); font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); margin-right: var(--space-1); }
.chip-role { background: var(--color-warning-bg); color: var(--color-warning-text); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3) var(--space-5); }
.success-msg { color: var(--color-success-text); font-size: var(--font-size-sm); margin-top: var(--space-2); background: var(--color-success-bg); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); }

/* Notificações */
.notif-desc { font-size: var(--font-size-sm); color: var(--color-neutral-500); margin-bottom: var(--space-4); }
.notif-list { display: flex; flex-direction: column; }
.notif-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) var(--space-2); border-radius: var(--radius-md);
  cursor: pointer; transition: background var(--transition-fast);
}
.notif-item:hover { background: var(--color-neutral-50); }
.notif-info { display: flex; align-items: center; gap: var(--space-3); }
.notif-icon { font-size: 1.3rem; }
.notif-info strong { font-size: var(--font-size-sm); display: block; color: var(--color-neutral-800); }
.notif-info p { font-size: var(--font-size-xs); color: var(--color-neutral-400); margin: 0; }

/* Toggle switch */
.toggle-wrap { flex-shrink: 0; }
.toggle {
  appearance: none; width: 44px; height: 24px; background: var(--color-neutral-300);
  border-radius: 12px; cursor: pointer; position: relative; transition: background var(--transition-base);
}
.toggle::before {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; background: #fff; border-radius: 50%;
  transition: transform var(--transition-base); box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.toggle:checked { background: var(--color-primary-700); }
.toggle:checked::before { transform: translateX(20px); }
.toggle:disabled { opacity: .4; cursor: not-allowed; }

/* Som */
.som-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); }
.som-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-1);
  padding: var(--space-4) var(--space-2); border-radius: var(--radius-lg);
  border: 2px solid var(--color-neutral-200); cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast); position: relative;
}
.som-card:hover { background: var(--color-primary-50); border-color: var(--color-primary-300); }
.som-card--ativo { border-color: var(--color-primary-500); background: var(--color-primary-50); }
.som-icon { font-size: 1.6rem; }
.som-label { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-neutral-700); }
.btn-preview {
  position: absolute; bottom: 6px; right: 6px;
  background: var(--color-primary-500); color: #fff; border: none; border-radius: 50%;
  width: 20px; height: 20px; font-size: .6rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity var(--transition-fast);
}
.som-card:hover .btn-preview { opacity: 1; }
.som-card--ativo .btn-preview { opacity: .7; }

@media (max-width: 480px) { .som-grid { grid-template-columns: repeat(3, 1fr); } .form-grid { grid-template-columns: 1fr; } }
</style>
