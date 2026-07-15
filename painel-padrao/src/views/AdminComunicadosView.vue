<template>
  <div class="comunicados">
    <div class="page-header">
      <h1>Comunicados</h1>
      <button class="btn btn-primary" @click="abrirForm">+ Novo comunicado</button>
    </div>

    <!-- Modal de criação -->
    <Transition name="fade-overlay">
      <div v-if="showForm" class="modal-backdrop" @click.self="showForm = false">
        <div class="modal-box">
          <div class="modal-header">
            <span>Novo comunicado</span>
            <button class="modal-close" @click="showForm = false" aria-label="Fechar">✕</button>
          </div>

          <form class="modal-body" @submit.prevent="enviar">
            <div class="field">
              <label>Título *</label>
              <input v-model="form.titulo" maxlength="200" required class="input" />
            </div>

            <div class="field">
              <label>Mensagem</label>
              <textarea v-model="form.mensagem" rows="3" class="input"></textarea>
            </div>

            <div class="field">
              <label>Imagem (opcional)</label>
              <div v-if="imgPreview" class="img-preview-wrap">
                <img :src="imgPreview" class="img-preview" alt="Preview" />
                <button type="button" class="btn btn-ghost btn-sm" @click="removerImagem">Remover</button>
              </div>
              <input v-else type="file" accept="image/*" @change="onImagem" class="input-file" />
            </div>

            <div class="field">
              <label>Rota de destino (opcional)</label>
              <input v-model="form.link_rota" placeholder="ex: /fca, /help" class="input" />
              <span class="field-hint">Ao clicar na notificação, o usuário será redirecionado para esta rota.</span>
            </div>

            <div class="field">
              <label>Destinatários *</label>
              <div class="radio-group">
                <label class="radio-opt" v-for="op in destinatarioOps" :key="op.value">
                  <input type="radio" v-model="form.destino" :value="op.value" />
                  {{ op.label }}
                </label>
              </div>
            </div>

            <!-- Setor + Empresa -->
            <div v-if="form.destino === 'setor'" class="field-row">
              <div class="field">
                <label>Empresa *</label>
                <select v-model="form.empresa" class="input" required>
                  <option value="">Selecione</option>
                  <option v-for="e in empresas" :key="e" :value="e">{{ e }}</option>
                </select>
              </div>
              <div class="field">
                <label>Setor *</label>
                <select v-model="form.setor" class="input" required>
                  <option value="">Selecione</option>
                  <option v-for="s in setoresDaEmpresa" :key="s" :value="s">{{ s }}</option>
                </select>
              </div>
            </div>

            <!-- Usuário específico -->
            <div v-if="form.destino === 'usuario'" class="field">
              <label>Usuário *</label>
              <select v-model="form.user_id" class="input" required>
                <option value="">Selecione</option>
                <option v-for="u in usuarios" :key="u.id" :value="u.id">{{ u.name }} ({{ u.sector }} / {{ u.company }})</option>
              </select>
            </div>

            <div v-if="erro" class="alert alert-danger">{{ erro }}</div>

            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" @click="showForm = false">Cancelar</button>
              <button type="submit" class="btn btn-primary" :disabled="enviando">
                {{ enviando ? 'Enviando…' : 'Enviar comunicado' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Feedback -->
    <Transition name="fade-overlay">
      <div v-if="successMsg" class="toast-success">{{ successMsg }}</div>
    </Transition>

    <p class="page-hint">
      Comunicados são notificações manuais enviadas para todos, um setor/empresa ou um usuário específico.
      Aparecem no sino de notificações de cada destinatário em tempo real.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const SECTORS_BY_COMPANY = {
  ACI_MATRIZ: ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  ACI_FILIAL: ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  SINOBRAS:   ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  ACC:        ['Comercial', 'Customer_Service'],
}
const empresas = Object.keys(SECTORS_BY_COMPANY)

const destinatarioOps = [
  { value: 'todos',   label: 'Todos os usuários' },
  { value: 'setor',   label: 'Setor + Empresa' },
  { value: 'usuario', label: 'Usuário específico' },
]

const showForm  = ref(false)
const enviando  = ref(false)
const erro      = ref('')
const successMsg = ref('')
const usuarios  = ref([])
const imgKey    = ref(null)
const imgPreview = ref(null)

const form = ref(emptyForm())

function emptyForm() {
  return { titulo: '', mensagem: '', link_rota: '', destino: 'todos', empresa: '', setor: '', user_id: '' }
}

const setoresDaEmpresa = computed(() => SECTORS_BY_COMPANY[form.value.empresa] ?? [])

onMounted(async () => {
  try {
    const res = await api.usuarios.list({ ativo: true, limit: 500 })
    usuarios.value = res.items ?? res
  } catch { /* silencioso */ }
})

function abrirForm() {
  form.value = emptyForm()
  imgKey.value = null
  imgPreview.value = null
  erro.value = ''
  showForm.value = true
}

async function onImagem(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const res = await api.upload.file(file)
    imgKey.value = res.object_key
    imgPreview.value = URL.createObjectURL(file)
  } catch (err) {
    erro.value = 'Erro ao enviar imagem: ' + err.message
  }
}

function removerImagem() {
  imgKey.value = null
  imgPreview.value = null
}

async function enviar() {
  erro.value = ''
  enviando.value = true
  try {
    const payload = {
      titulo:    form.value.titulo,
      mensagem:  form.value.mensagem || null,
      link_rota: form.value.link_rota || null,
      destino:   form.value.destino,
      imagem_key: imgKey.value || null,
    }
    if (form.value.destino === 'setor') {
      payload.empresa = form.value.empresa
      payload.setor   = form.value.setor
    }
    if (form.value.destino === 'usuario') {
      payload.user_id = form.value.user_id
    }
    const res = await api.notifications.comunicado(payload)
    showForm.value = false
    successMsg.value = `Comunicado enviado para ${res.total} usuário(s).`
    setTimeout(() => { successMsg.value = '' }, 4000)
  } catch (err) {
    erro.value = err.message
  } finally {
    enviando.value = false
  }
}
</script>

<style scoped>
.comunicados { max-width: 720px; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-6);
}
.page-hint {
  margin-top: var(--space-4);
  font-size: var(--font-size-sm); color: var(--color-neutral-500);
  background: var(--color-neutral-50); border-radius: var(--radius-md);
  padding: var(--space-4); border-left: 3px solid var(--color-primary-300);
}

/* Modal */
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  z-index: 400; display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: #fff; border-radius: var(--radius-lg); width: 520px; max-width: 95vw;
  max-height: 92vh; overflow-y: auto; box-shadow: var(--shadow-lg);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--color-neutral-100);
  font-weight: 600; font-size: var(--font-size-base);
}
.modal-close {
  background: none; border: none; cursor: pointer; font-size: 16px;
  color: var(--color-neutral-400); line-height: 1;
}
.modal-close:hover { color: var(--color-neutral-700); }
.modal-body { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 8px; }

/* Fields */
.field { display: flex; flex-direction: column; gap: 4px; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field label { font-size: 13px; font-weight: 500; color: var(--color-neutral-700); }
.field-hint { font-size: 11px; color: var(--color-neutral-400); }
.input {
  padding: 8px 10px; border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: 14px; font-family: inherit;
  background: #fff; color: var(--color-neutral-800);
  outline: none; transition: border-color 0.15s;
}
.input:focus { border-color: var(--color-primary-400); box-shadow: 0 0 0 3px var(--color-primary-100); }
textarea.input { resize: vertical; }
.input-file { font-size: 13px; color: var(--color-neutral-600); }

.radio-group { display: flex; gap: 16px; flex-wrap: wrap; }
.radio-opt {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; cursor: pointer; color: var(--color-neutral-700);
}

/* Image preview */
.img-preview-wrap { display: flex; flex-direction: column; gap: 6px; }
.img-preview { width: 100%; max-height: 160px; object-fit: cover; border-radius: var(--radius-md); }

/* Alert */
.alert { padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; }
.alert-danger { background: var(--color-danger-bg, #fee2e2); color: var(--color-danger-text, #b91c1c); }

/* Toast */
.toast-success {
  position: fixed; bottom: 24px; right: 24px;
  background: var(--color-success, #16a34a); color: #fff;
  padding: 12px 20px; border-radius: var(--radius-md);
  font-size: 14px; box-shadow: var(--shadow-lg); z-index: 600;
  animation: notif-in 0.2s ease;
}
@keyframes notif-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.fade-overlay-enter-active, .fade-overlay-leave-active { transition: opacity 0.2s; }
.fade-overlay-enter-from, .fade-overlay-leave-to { opacity: 0; }
</style>
