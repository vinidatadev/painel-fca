<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Suporte / Help</h1>
      <button class="btn btn-primary" @click="openForm">+ Nova Solicitação</button>
    </div>

    <!-- Modal novo ticket -->
    <div v-if="showForm" class="modal-overlay" @click.self="cancelForm">
      <div class="modal-box" @paste.stop="onPaste">
        <h2>Nova Solicitação</h2>
        <div class="form-group">
          <label>Título <span class="req">*</span></label>
          <input v-model="form.titulo" maxlength="200" placeholder="Resumo do problema" />
        </div>
        <div class="form-group">
          <label>Descrição <span class="req">*</span></label>
          <textarea v-model="form.descricao" rows="5" placeholder="Descreva com detalhes..."></textarea>
        </div>

        <!-- Área de anexos -->
        <div class="form-group">
          <label>
            Anexos
            <small>(JPEG, PNG, PDF — máx 20 MB cada · até 5 · ou cole com Ctrl+V)</small>
          </label>
          <div
            class="drop-zone"
            :class="{ 'drag-over': isDragging }"
            @click="$refs.fileInput.click()"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="onDrop"
          >
            <span v-if="pendingFiles.length === 0">
              Clique, arraste ou cole (Ctrl+V) para adicionar
            </span>
            <span v-else>+ Adicionar mais</span>
          </div>
          <input ref="fileInput" type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf" class="hidden-input" @change="onFileChange" />

          <!-- Previews -->
          <div v-if="pendingFiles.length" class="previews">
            <div v-for="(f, i) in pendingFiles" :key="i" class="preview-item">
              <img v-if="f.preview" :src="f.preview" class="preview-thumb" :title="f.file.name" />
              <div v-else class="preview-doc">
                <span class="doc-icon">📄</span>
                <span class="doc-name">{{ f.file.name }}</span>
              </div>
              <div class="preview-info">
                <span class="preview-name">{{ f.file.name }}</span>
                <span v-if="f.uploading" class="hint">Enviando...</span>
                <span v-else-if="f.key" class="hint success">✓</span>
                <span v-else-if="f.error" class="hint error">{{ f.error }}</span>
              </div>
              <button class="remove-btn" @click.stop="removeFile(i)" title="Remover">×</button>
            </div>
          </div>
        </div>

        <p v-if="formErr" class="err">{{ formErr }}</p>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="cancelForm">Cancelar</button>
          <button class="btn btn-primary" :disabled="saving || isUploading" @click="submitForm">
            {{ saving ? 'Enviando...' : isUploading ? 'Aguardando uploads...' : 'Enviar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Lista de tickets -->
    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="tickets.length === 0" class="empty">Nenhuma solicitação encontrada.</div>
    <div v-else class="tickets-list">
      <div
        v-for="t in tickets"
        :key="t.id"
        class="ticket-card"
        @click="openTicket(t)"
      >
        <div class="ticket-header">
          <span class="ticket-title">{{ t.titulo }}</span>
          <span class="badge" :class="badgeClass(t.status)">{{ labelStatus(t.status) }}</span>
        </div>
        <p class="ticket-desc">{{ t.descricao.slice(0, 120) }}{{ t.descricao.length > 120 ? '...' : '' }}</p>
        <!-- Thumbs inline na lista se houver imagens -->
        <div v-if="t.anexos.some(a => a.is_image)" class="inline-thumbs">
          <img
            v-for="a in t.anexos.filter(a => a.is_image).slice(0, 3)"
            :key="a.key"
            :src="a.url"
            class="inline-thumb"
          />
          <span v-if="t.anexos.filter(a => a.is_image).length > 3" class="more-thumbs">
            +{{ t.anexos.filter(a => a.is_image).length - 3 }}
          </span>
        </div>
        <small class="ticket-meta">
          Aberto em {{ fmtDate(t.created_at) }} · {{ t.mensagens.length }} resposta(s)
          <span v-if="t.anexos.length"> · 📎 {{ t.anexos.length }} anexo(s)</span>
        </small>
      </div>
    </div>

    <!-- Detalhe do ticket -->
    <div v-if="selected" class="modal-overlay" @click.self="selected = null">
      <div class="modal-box modal-lg">
        <div class="detalhe-header">
          <h2>{{ selected.titulo }}</h2>
          <span class="badge" :class="badgeClass(selected.status)">{{ labelStatus(selected.status) }}</span>
        </div>
        <p class="detalhe-desc">{{ selected.descricao }}</p>

        <!-- Anexos do ticket -->
        <div v-if="selected.anexos.length" class="anexos-grid">
          <a v-for="a in selected.anexos" :key="a.key" :href="a.url" target="_blank" class="anexo-item">
            <img v-if="a.is_image" :src="a.url" class="anexo-thumb" />
            <div v-else class="anexo-doc">📄 <span>{{ a.key.split('/').pop() }}</span></div>
          </a>
        </div>

        <div class="mensagens">
          <div v-for="m in selected.mensagens" :key="m.id" class="mensagem" :class="{ admin: m.autor.role === 'admin' }">
            <div class="msg-author">{{ m.autor.name }} <small>{{ m.autor.role === 'admin' ? '(Suporte)' : '' }}</small></div>
            <div class="msg-text">{{ m.texto }}</div>
            <div class="msg-date">{{ fmtDate(m.created_at) }}</div>
          </div>
          <div v-if="selected.mensagens.length === 0" class="empty-msg">Aguardando resposta do suporte.</div>
        </div>

        <div v-if="!['resolvido','fechado'].includes(selected.status)" class="reply-box">
          <textarea v-model="replyText" rows="3" placeholder="Adicionar informação..."></textarea>
          <button class="btn btn-primary btn-sm" :disabled="!replyText.trim() || sendingReply" @click="sendReply">
            {{ sendingReply ? 'Enviando...' : 'Enviar' }}
          </button>
        </div>
        <button class="btn btn-outline btn-sm mt" @click="selected = null">Fechar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

const registerWsListener = inject('registerWsListener')

const tickets    = ref([])
const loading    = ref(false)
const showForm   = ref(false)
const saving     = ref(false)
const formErr    = ref('')
const isDragging = ref(false)
const selected   = ref(null)
const replyText  = ref('')
const sendingReply = ref(false)
const fileInput  = ref(null)

// Cada item: { file, preview (dataURL|null), key (object_key após upload), uploading, error }
const pendingFiles = ref([])

const isUploading = computed(() => pendingFiles.value.some(f => f.uploading))

const form = ref({ titulo: '', descricao: '' })

// ── Carregamento ──────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try { tickets.value = await api.help.list() }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}

onMounted(() => {
  load()
  registerWsListener?.((evt) => {
    if (evt === 'help_ticket_atualizado' || evt === 'help_ticket_novo') load()
  })
  window.addEventListener('paste', onGlobalPaste)
})

onUnmounted(() => {
  window.removeEventListener('paste', onGlobalPaste)
})

// ── Paste global (Ctrl+V fora do modal também captura) ───────────────────────
function onGlobalPaste(e) {
  if (showForm.value) handlePasteEvent(e)
}

function onPaste(e) {
  handlePasteEvent(e)
}

function handlePasteEvent(e) {
  const items = Array.from(e.clipboardData?.items || [])
  const imageItem = items.find(i => i.type.startsWith('image/'))
  if (!imageItem) return
  e.preventDefault()
  const file = imageItem.getAsFile()
  if (file) addFile(new File([file], `paste_${Date.now()}.png`, { type: file.type }))
}

// ── File handling ─────────────────────────────────────────────────────────────
function onFileChange(e) {
  Array.from(e.target.files).forEach(addFile)
  e.target.value = ''
}

function onDrop(e) {
  isDragging.value = false
  Array.from(e.dataTransfer.files).forEach(addFile)
}

function addFile(file) {
  if (pendingFiles.value.length >= 5) {
    formErr.value = 'Máximo de 5 anexos por ticket.'
    return
  }
  const entry = { file, preview: null, key: null, uploading: true, error: null }
  pendingFiles.value.push(entry)
  const idx = pendingFiles.value.length - 1

  // Preview imediato para imagens
  if (file.type.startsWith('image/')) {
    const reader = new FileReader()
    reader.onload = e => { pendingFiles.value[idx].preview = e.target.result }
    reader.readAsDataURL(file)
  }

  // Upload imediato
  api.upload.file(file)
    .then(res => { pendingFiles.value[idx].key = res.object_key })
    .catch(err => { pendingFiles.value[idx].error = err.message })
    .finally(() => { pendingFiles.value[idx].uploading = false })
}

function removeFile(i) {
  pendingFiles.value.splice(i, 1)
}

// ── Form ──────────────────────────────────────────────────────────────────────
function openForm() {
  showForm.value = true
  formErr.value = ''
}

async function submitForm() {
  formErr.value = ''
  if (!form.value.titulo.trim()) { formErr.value = 'Título obrigatório'; return }
  if (!form.value.descricao.trim()) { formErr.value = 'Descrição obrigatória'; return }
  if (isUploading.value) { formErr.value = 'Aguarde os uploads terminarem.'; return }

  const failedUploads = pendingFiles.value.filter(f => f.error)
  if (failedUploads.length) { formErr.value = 'Alguns arquivos falharam no upload. Remova-os antes de enviar.'; return }

  saving.value = true
  try {
    const anexo_keys = pendingFiles.value.filter(f => f.key).map(f => f.key)
    await api.help.create({ ...form.value, anexo_keys })
    cancelForm()
    await load()
  } catch (e) {
    formErr.value = e.message
  } finally {
    saving.value = false
  }
}

function cancelForm() {
  showForm.value = false
  form.value = { titulo: '', descricao: '' }
  pendingFiles.value = []
  formErr.value = ''
}

// ── Detalhe ───────────────────────────────────────────────────────────────────
async function openTicket(t) {
  try {
    selected.value = await api.help.get(t.id)
    replyText.value = ''
  } catch (e) { console.error(e) }
}

async function sendReply() {
  if (!replyText.value.trim()) return
  sendingReply.value = true
  try {
    await api.help.responder(selected.value.id, replyText.value)
    replyText.value = ''
    selected.value = await api.help.get(selected.value.id)
    await load()
  } catch (e) { console.error(e) }
  finally { sendingReply.value = false }
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', resolvido: 'Resolvido', fechado: 'Fechado' }[s] || s
}
function badgeClass(s) {
  return { aberto: 'badge-warning', em_andamento: 'badge-info', resolvido: 'badge-success', fechado: 'badge-neutral' }[s] || ''
}
function fmtDate(iso) {
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.page-container { max-width: 860px; margin: 0 auto; padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.page-header h1 { font-size: 1.4rem; font-weight: 600; }

/* ── Tickets list ── */
.tickets-list { display: flex; flex-direction: column; gap: .75rem; }
.ticket-card {
  background: var(--card-bg, #fff); border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px; padding: 1rem 1.2rem; cursor: pointer; transition: box-shadow .15s;
}
.ticket-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.ticket-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: .3rem; }
.ticket-title { font-weight: 600; }
.ticket-desc { color: var(--text-muted, #64748b); font-size: .9rem; margin: .3rem 0; }
.ticket-meta { color: var(--text-muted, #64748b); font-size: .78rem; }
.inline-thumbs { display: flex; gap: .35rem; margin: .4rem 0; align-items: center; }
.inline-thumb { width: 48px; height: 48px; object-fit: cover; border-radius: 5px; border: 1px solid var(--border, #e2e8f0); }
.more-thumbs { font-size: .8rem; color: var(--text-muted, #64748b); }

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed var(--border, #cbd5e1); border-radius: 8px;
  padding: .8rem 1rem; text-align: center; cursor: pointer;
  color: var(--text-muted, #64748b); font-size: .9rem; transition: border-color .15s, background .15s;
  user-select: none;
}
.drop-zone:hover, .drag-over { border-color: var(--primary, #3b82f6); background: #eff6ff; }
.hidden-input { display: none; }

/* ── Previews ── */
.previews { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: .6rem; }
.preview-item {
  position: relative; display: flex; flex-direction: column; align-items: center;
  width: 90px; background: var(--bg-subtle, #f8fafc);
  border: 1px solid var(--border, #e2e8f0); border-radius: 8px; padding: .4rem;
  gap: .25rem;
}
.preview-thumb { width: 72px; height: 72px; object-fit: cover; border-radius: 5px; }
.preview-doc { display: flex; flex-direction: column; align-items: center; gap: .2rem; width: 72px; height: 72px; justify-content: center; }
.doc-icon { font-size: 1.8rem; }
.doc-name { font-size: .65rem; word-break: break-all; text-align: center; color: var(--text-muted, #64748b); }
.preview-info { width: 100%; text-align: center; }
.preview-name { font-size: .65rem; word-break: break-all; color: var(--text-muted, #64748b); display: block; }
.remove-btn {
  position: absolute; top: -7px; right: -7px; width: 20px; height: 20px;
  background: #ef4444; color: #fff; border: none; border-radius: 50%;
  font-size: .8rem; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center;
}

/* ── Anexos grid no detalhe ── */
.anexos-grid { display: flex; flex-wrap: wrap; gap: .6rem; margin-bottom: 1rem; }
.anexo-item { text-decoration: none; display: block; }
.anexo-thumb {
  width: 100px; height: 100px; object-fit: cover; border-radius: 7px;
  border: 1px solid var(--border, #e2e8f0); transition: opacity .15s;
}
.anexo-thumb:hover { opacity: .85; }
.anexo-doc {
  display: flex; align-items: center; gap: .35rem; padding: .5rem .75rem;
  background: var(--bg-subtle, #f1f5f9); border-radius: 7px; font-size: .85rem;
  color: var(--text, #334155);
}
.anexo-doc span { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: var(--card-bg, #fff); border-radius: 10px;
  padding: 1.8rem; width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto;
}
.modal-lg { max-width: 720px; }
.modal-box h2 { margin-bottom: 1rem; font-size: 1.2rem; font-weight: 600; }
.modal-actions { display: flex; gap: .75rem; justify-content: flex-end; margin-top: 1rem; }

.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: .3rem; font-size: .9rem; font-weight: 500; }
.form-group input, .form-group textarea {
  width: 100%; padding: .5rem .75rem; border: 1px solid var(--border, #cbd5e1);
  border-radius: 6px; font-size: .95rem; background: var(--input-bg, #f8fafc);
}
.form-group textarea { resize: vertical; }
.req { color: #ef4444; }
.hint { font-size: .75rem; display: block; }
.hint.success { color: #16a34a; }
.hint.error { color: #ef4444; }
.err { color: #ef4444; font-size: .85rem; margin: .5rem 0; }
.empty, .loading { text-align: center; color: var(--text-muted, #64748b); padding: 2rem; }

/* ── Detalhe ── */
.detalhe-header { display: flex; gap: .75rem; align-items: center; flex-wrap: wrap; margin-bottom: .75rem; }
.detalhe-desc { margin-bottom: .75rem; white-space: pre-wrap; }
.mensagens { display: flex; flex-direction: column; gap: .6rem; margin: 1rem 0; }
.mensagem { background: var(--bg-subtle, #f1f5f9); border-radius: 8px; padding: .7rem 1rem; }
.mensagem.admin { background: #eff6ff; border-left: 3px solid #3b82f6; }
.msg-author { font-weight: 600; font-size: .85rem; margin-bottom: .2rem; }
.msg-author small { color: #3b82f6; }
.msg-text { white-space: pre-wrap; font-size: .92rem; }
.msg-date { color: var(--text-muted, #94a3b8); font-size: .75rem; margin-top: .3rem; }
.empty-msg { color: var(--text-muted, #64748b); font-style: italic; font-size: .9rem; }
.reply-box { display: flex; flex-direction: column; gap: .5rem; margin-top: .75rem; }
.reply-box textarea {
  width: 100%; padding: .5rem .75rem; border: 1px solid var(--border, #cbd5e1);
  border-radius: 6px; font-size: .9rem; resize: vertical;
}
.btn-sm { font-size: .85rem; padding: .35rem .85rem; align-self: flex-end; }
.mt { margin-top: 1rem; }

.badge-warning { background: #fef9c3; color: #854d0e; }
.badge-info    { background: #dbeafe; color: #1d4ed8; }
.badge-success { background: #dcfce7; color: #15803d; }
.badge-neutral { background: #f1f5f9; color: #475569; }
</style>
