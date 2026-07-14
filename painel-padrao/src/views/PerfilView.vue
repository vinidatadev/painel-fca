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
.loading-text { color: #888; text-align: center; padding: 2rem; }
.section-title { font-size: .85rem; font-weight: 700; text-transform: uppercase; color: #6b7280; letter-spacing: .4px; margin-bottom: 1rem; }

.avatar-section { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.avatar-area { display: flex; flex-direction: column; align-items: center; gap: .6rem; }
.avatar-actions { display: flex; flex-direction: column; gap: .4rem; align-items: center; }
.user-info-block { flex: 1; }
.user-info-block h2 { font-size: 1.2rem; font-weight: 700; margin-bottom: .35rem; }
.user-info-block .email { font-size: .82rem; color: #9ca3af; margin-top: .25rem; }
.chip { display: inline-block; background: #eff6ff; color: #1d4ed8; border-radius: 20px; padding: .15rem .6rem; font-size: .75rem; font-weight: 600; margin-right: .35rem; }
.chip-role { background: #fef3c7; color: #92400e; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem 1rem; }
.success-msg { color: #059669; font-size: .875rem; margin-top: .5rem; }

/* Notificações */
.notif-desc { font-size: .85rem; color: #6b7280; margin-bottom: 1rem; }
.notif-list { display: flex; flex-direction: column; gap: .15rem; }
.notif-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: .85rem .75rem; border-radius: 8px; cursor: pointer; transition: background .15s;
}
.notif-item:hover { background: #f9fafb; }
.notif-info { display: flex; align-items: center; gap: .75rem; }
.notif-icon { font-size: 1.3rem; }
.notif-info strong { font-size: .9rem; display: block; }
.notif-info p { font-size: .78rem; color: #9ca3af; margin: 0; }

/* Toggle switch */
.toggle-wrap { flex-shrink: 0; }
.toggle {
  appearance: none; width: 44px; height: 24px; background: #d1d5db;
  border-radius: 12px; cursor: pointer; position: relative; transition: background .2s;
}
.toggle::before {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; background: #fff; border-radius: 50%;
  transition: transform .2s; box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.toggle:checked { background: #1a56db; }
.toggle:checked::before { transform: translateX(20px); }
.toggle:disabled { opacity: .4; cursor: not-allowed; }

/* Som */
.som-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: .75rem;
}
.som-card {
  display: flex; flex-direction: column; align-items: center; gap: .4rem;
  padding: .85rem .5rem; border-radius: 10px; border: 2px solid #e5e7eb;
  cursor: pointer; transition: border-color .2s, background .2s; position: relative;
}
.som-card:hover { background: #f0f7ff; border-color: #93c5fd; }
.som-card--ativo { border-color: #1a56db; background: #eff6ff; }
.som-icon { font-size: 1.6rem; }
.som-label { font-size: .75rem; font-weight: 600; color: #374151; }
.btn-preview {
  position: absolute; bottom: 6px; right: 6px;
  background: #1a56db; color: #fff; border: none; border-radius: 50%;
  width: 20px; height: 20px; font-size: .65rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity .15s;
}
.som-card:hover .btn-preview { opacity: 1; }
.som-card--ativo .btn-preview { opacity: 0.7; }

@media (max-width: 480px) {
  .som-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
