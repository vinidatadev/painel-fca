<template>
  <div>
    <div class="page-header">
      <h1>Suporte</h1>
      <button class="btn btn-primary" @click="openForm">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Nova Solicitação
      </button>
    </div>

    <!-- Modal novo ticket -->
    <div v-if="showForm" class="modal-overlay" @click.self="cancelForm">
      <div class="modal-box" @paste.stop="onPaste">
        <div class="modal-header">
          <h2>Nova Solicitação</h2>
          <button class="modal-close" @click="cancelForm" aria-label="Fechar">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 4l10 10M14 4L4 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="form-group">
          <label>Título <span class="req">*</span></label>
          <input v-model="form.titulo" maxlength="200" placeholder="Resumo do problema" />
        </div>
        <div class="form-group">
          <label>Descrição <span class="req">*</span></label>
          <textarea v-model="form.descricao" rows="5" placeholder="Descreva com detalhes..."></textarea>
        </div>
        <div class="form-group">
          <label>Anexos <small style="font-weight:400;color:var(--color-neutral-400)">(até 5 · JPEG, PNG, PDF · ou cole Ctrl+V)</small></label>
          <div class="drop-zone" :class="{ 'drag-over': isDragging }"
            @click="$refs.fileInput.click()"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="onDrop">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none"><path d="M14 18V10M10 14l4-4 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 22a5 5 0 010-10h1a6 6 0 1112 0h1a5 5 0 010 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
            <span>{{ pendingFiles.length === 0 ? 'Clique, arraste ou cole' : '+ Adicionar mais' }}</span>
          </div>
          <input ref="fileInput" type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf" class="hidden-input" @change="onFileChange" />
          <div v-if="pendingFiles.length" class="previews">
            <div v-for="(f, i) in pendingFiles" :key="i" class="preview-item">
              <div class="preview-media">
                <img v-if="f.preview" :src="f.preview" class="preview-thumb" />
                <div v-else class="preview-doc">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M12 2H6a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V8L12 2z" stroke="currentColor" stroke-width="1.5"/><path d="M12 2v6h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                  <span>{{ f.file.name.slice(0,12) }}</span>
                </div>
                <div class="preview-overlay" @click.stop="removeFile(i)">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
                </div>
              </div>
              <span v-if="f.uploading" class="status-dot uploading"></span>
              <span v-else-if="f.key" class="status-dot ok">✓</span>
              <span v-else-if="f.error" class="status-dot err">!</span>
            </div>
          </div>
        </div>
        <p v-if="formErr" class="error-msg">{{ formErr }}</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="cancelForm">Cancelar</button>
          <button class="btn btn-primary" :disabled="saving || isUploading" @click="submitForm">
            {{ saving ? 'Enviando...' : isUploading ? 'Aguardando uploads...' : 'Enviar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Lista -->
    <div v-if="loading" class="tickets-list">
      <div v-for="i in 3" :key="i" class="ticket-card">
        <div class="skeleton skeleton-text" style="width:60%;margin-bottom:8px"></div>
        <div class="skeleton skeleton-text" style="width:80%"></div>
      </div>
    </div>
    <div v-else-if="!tickets.length" class="empty-state-block">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none"><path d="M8 12a4 4 0 014-4h32a4 4 0 014 4v24a4 4 0 01-4 4H20l-8 6V12z" stroke="var(--color-neutral-300)" stroke-width="2"/></svg>
      <p>Nenhuma solicitação encontrada.</p>
      <button class="btn btn-primary btn-sm" @click="openForm">Criar solicitação</button>
    </div>
    <div v-else class="tickets-list">
      <div v-for="t in tickets" :key="t.id" class="ticket-card card-interactive" @click="openTicket(t)">
        <div class="ticket-header">
          <span class="ticket-title">{{ t.titulo }}</span>
          <span class="badge" :class="badgeClass(t.status)">{{ labelStatus(t.status) }}</span>
        </div>
        <p class="ticket-desc">{{ t.descricao.slice(0, 120) }}{{ t.descricao.length > 120 ? '...' : '' }}</p>
        <div v-if="t.anexos.some(a => a.is_image)" class="inline-thumbs">
          <img v-for="a in t.anexos.filter(a => a.is_image).slice(0, 3)" :key="a.key" :src="a.url" class="inline-thumb" />
          <span v-if="t.anexos.filter(a => a.is_image).length > 3" class="more-thumbs">+{{ t.anexos.filter(a => a.is_image).length - 3 }}</span>
        </div>
        <div class="ticket-footer">
          <small class="ticket-meta">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><circle cx="6" cy="6" r="5" stroke="currentColor" stroke-width="1.2"/><path d="M6 3v3l2 2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
            {{ fmtDate(t.created_at) }}
          </small>
          <small class="ticket-meta">{{ t.mensagens.length }} resposta(s)</small>
          <small v-if="t.anexos.length" class="ticket-meta">📎 {{ t.anexos.length }}</small>
        </div>
      </div>
    </div>

    <!-- Detalhe do ticket -->
    <div v-if="selected" class="modal-overlay" @click.self="selected = null">
      <div class="modal-box modal-lg">
        <div class="modal-header">
          <div class="detalhe-title-row">
            <h2>{{ selected.titulo }}</h2>
            <span class="badge" :class="badgeClass(selected.status)">{{ labelStatus(selected.status) }}</span>
          </div>
          <button class="modal-close" @click="selected = null">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 4l10 10M14 4L4 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
        <p class="detalhe-desc">{{ selected.descricao }}</p>
        <div v-if="selected.anexos.length" class="anexos-grid">
          <a v-for="a in selected.anexos" :key="a.key" :href="a.url" target="_blank" class="anexo-item">
            <img v-if="a.is_image" :src="a.url" class="anexo-thumb" />
            <div v-else class="anexo-doc">📄 <span>{{ a.key.split('/').pop() }}</span></div>
          </a>
        </div>
        <div class="mensagens">
          <div v-for="m in selected.mensagens" :key="m.id" class="mensagem" :class="{ admin: m.autor.role === 'admin' }">
            <div class="msg-avatar">{{ m.autor.name.charAt(0).toUpperCase() }}</div>
            <div class="msg-body">
              <div class="msg-header">
                <span class="msg-author">{{ m.autor.name }}</span>
                <span v-if="m.autor.role === 'admin'" class="msg-suporte">Suporte</span>
                <span class="msg-date">{{ fmtDate(m.created_at) }}</span>
              </div>
              <div class="msg-text">{{ m.texto }}</div>
            </div>
          </div>
          <p v-if="!selected.mensagens.length" class="msg-empty">Aguardando resposta do suporte.</p>
        </div>
        <div v-if="!['resolvido','fechado'].includes(selected.status)" class="reply-box">
          <textarea v-model="replyText" rows="3" placeholder="Adicionar informação..."></textarea>
          <div class="reply-actions">
            <button class="btn btn-primary btn-sm" :disabled="!replyText.trim() || sendingReply" @click="sendReply">
              {{ sendingReply ? 'Enviando...' : 'Enviar resposta' }}
            </button>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" style="margin-top:var(--space-4)" @click="selected = null">Fechar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

const registerWsListener = inject('registerWsListener')
const tickets = ref([]); const loading = ref(false); const showForm = ref(false)
const saving = ref(false); const formErr = ref(''); const isDragging = ref(false)
const selected = ref(null); const replyText = ref(''); const sendingReply = ref(false)
const fileInput = ref(null); const pendingFiles = ref([])
const isUploading = computed(() => pendingFiles.value.some(f => f.uploading))
const form = ref({ titulo: '', descricao: '' })

async function load() {
  loading.value = true
  try { tickets.value = await api.help.list() }
  catch (e) { console.error(e) } finally { loading.value = false }
}
onMounted(() => {
  load()
  registerWsListener?.((evt) => { if (['help_ticket_atualizado','help_ticket_novo'].includes(evt)) load() })
  window.addEventListener('paste', onGlobalPaste)
})
onUnmounted(() => window.removeEventListener('paste', onGlobalPaste))
function onGlobalPaste(e) { if (showForm.value) handlePasteEvent(e) }
function onPaste(e) { handlePasteEvent(e) }
function handlePasteEvent(e) {
  const img = Array.from(e.clipboardData?.items || []).find(i => i.type.startsWith('image/'))
  if (!img) return; e.preventDefault()
  const file = img.getAsFile()
  if (file) addFile(new File([file], `paste_${Date.now()}.png`, { type: file.type }))
}
function onFileChange(e) { Array.from(e.target.files).forEach(addFile); e.target.value = '' }
function onDrop(e) { isDragging.value = false; Array.from(e.dataTransfer.files).forEach(addFile) }
function addFile(file) {
  if (pendingFiles.value.length >= 5) { formErr.value = 'Máximo de 5 anexos.'; return }
  const entry = { file, preview: null, key: null, uploading: true, error: null }
  pendingFiles.value.push(entry)
  const idx = pendingFiles.value.length - 1
  if (file.type.startsWith('image/')) {
    const reader = new FileReader(); reader.onload = e => { pendingFiles.value[idx].preview = e.target.result }; reader.readAsDataURL(file)
  }
  api.upload.file(file).then(res => { pendingFiles.value[idx].key = res.object_key })
    .catch(err => { pendingFiles.value[idx].error = err.message }).finally(() => { pendingFiles.value[idx].uploading = false })
}
function removeFile(i) { pendingFiles.value.splice(i, 1) }
function openForm() { showForm.value = true; formErr.value = '' }
async function submitForm() {
  formErr.value = ''
  if (!form.value.titulo.trim()) { formErr.value = 'Título obrigatório'; return }
  if (!form.value.descricao.trim()) { formErr.value = 'Descrição obrigatória'; return }
  if (isUploading.value) { formErr.value = 'Aguarde os uploads.'; return }
  if (pendingFiles.value.filter(f => f.error).length) { formErr.value = 'Remova os arquivos com erro.'; return }
  saving.value = true
  try {
    await api.help.create({ ...form.value, anexo_keys: pendingFiles.value.filter(f => f.key).map(f => f.key) })
    cancelForm(); await load()
  } catch (e) { formErr.value = e.message } finally { saving.value = false }
}
function cancelForm() { showForm.value = false; form.value = { titulo: '', descricao: '' }; pendingFiles.value = []; formErr.value = '' }
async function openTicket(t) {
  try { selected.value = await api.help.get(t.id); replyText.value = '' }
  catch (e) { console.error(e) }
}
async function sendReply() {
  if (!replyText.value.trim()) return
  sendingReply.value = true
  try {
    await api.help.responder(selected.value.id, replyText.value)
    replyText.value = ''; selected.value = await api.help.get(selected.value.id); await load()
  } catch (e) { console.error(e) } finally { sendingReply.value = false }
}
function labelStatus(s) { return { aberto: 'Aberto', em_andamento: 'Em andamento', resolvido: 'Resolvido', fechado: 'Fechado' }[s] || s }
function badgeClass(s) { return { aberto: 'badge-aberto', em_andamento: 'badge-em_andamento', resolvido: 'badge-encerrado', fechado: 'badge-cancelado' }[s] || '' }
function fmtDate(iso) { return new Date(iso).toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }) }
</script>

<style scoped>
/* Tickets list */
.tickets-list { display: flex; flex-direction: column; gap: var(--space-3); }
.ticket-card {
  background: #fff; border: 1px solid var(--color-neutral-200); border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5); cursor: pointer;
  transition: box-shadow var(--transition-base), transform var(--transition-base), border-color var(--transition-base);
}
.ticket-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); border-color: var(--color-primary-300); }
.ticket-header { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-3); margin-bottom: var(--space-2); }
.ticket-title { font-weight: var(--font-weight-semibold); color: var(--color-neutral-800); font-size: var(--font-size-sm); }
.ticket-desc { color: var(--color-neutral-500); font-size: var(--font-size-sm); line-height: 1.5; margin-bottom: var(--space-2); }
.ticket-footer { display: flex; gap: var(--space-4); }
.ticket-meta { display: flex; align-items: center; gap: 4px; color: var(--color-neutral-400); font-size: var(--font-size-xs); }
.inline-thumbs { display: flex; gap: var(--space-1); margin-bottom: var(--space-2); }
.inline-thumb { width: 44px; height: 44px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--color-neutral-200); }
.more-thumbs { font-size: var(--font-size-xs); color: var(--color-neutral-400); display: flex; align-items: center; }

/* Empty */
.empty-state-block { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-12); text-align: center; color: var(--color-neutral-400); font-size: var(--font-size-sm); }

/* Drop zone */
.drop-zone {
  border: 2px dashed var(--color-neutral-300); border-radius: var(--radius-md);
  padding: var(--space-5); text-align: center; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  color: var(--color-neutral-400); font-size: var(--font-size-sm);
  transition: all var(--transition-base); background: var(--color-neutral-50);
}
.drop-zone:hover { border-color: var(--color-primary-300); background: var(--color-primary-50); color: var(--color-primary-600); }
.drag-over { border-color: var(--color-primary-500) !important; background: var(--color-primary-100) !important; }
.hidden-input { display: none; }
.previews { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); }
.preview-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.preview-media { position: relative; width: 64px; height: 64px; border-radius: var(--radius-md); overflow: hidden; background: var(--color-neutral-100); border: 1px solid var(--color-neutral-200); cursor: pointer; }
.preview-thumb { width: 100%; height: 100%; object-fit: cover; }
.preview-doc { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; color: var(--color-neutral-500); font-size: 9px; text-align: center; padding: 4px; }
.preview-overlay { position: absolute; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity var(--transition-fast); }
.preview-media:hover .preview-overlay { opacity: 1; }
.status-dot { font-size: var(--font-size-xs); }
.status-dot.ok { color: var(--color-success); }
.status-dot.err { color: var(--color-danger); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 500; padding: var(--space-4); }
.modal-box { background: #fff; border-radius: var(--radius-xl); padding: var(--space-6); width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.modal-lg { max-width: 720px; }
.modal-header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-5); }
.modal-header h2 { font-size: var(--font-size-lg); font-weight: var(--font-weight-semibold); margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; padding: var(--space-1); color: var(--color-neutral-400); border-radius: var(--radius-sm); transition: color var(--transition-fast), background var(--transition-fast); flex-shrink: 0; }
.modal-close:hover { background: var(--color-neutral-100); color: var(--color-neutral-700); }
.modal-actions { display: flex; gap: var(--space-3); justify-content: flex-end; margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--color-neutral-100); }
.form-group { margin-bottom: var(--space-4); }
.form-group label { display: block; margin-bottom: var(--space-1); font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-neutral-700); }
.form-group input, .form-group textarea {
  width: 100%; padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); font-family: var(--font-family-base);
  background: var(--color-neutral-50); outline: none; transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.form-group input:focus, .form-group textarea:focus { border-color: var(--color-primary-500); box-shadow: 0 0 0 3px var(--color-primary-100); background: #fff; }
.form-group textarea { resize: vertical; }
.req { color: var(--color-danger); }

/* Detalhe */
.detalhe-title-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.detalhe-desc { font-size: var(--font-size-sm); color: var(--color-neutral-700); margin-bottom: var(--space-4); white-space: pre-wrap; line-height: 1.6; }
.anexos-grid { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-4); }
.anexo-item { text-decoration: none; }
.anexo-thumb { width: 88px; height: 88px; object-fit: cover; border-radius: var(--radius-md); border: 1px solid var(--color-neutral-200); transition: opacity var(--transition-fast); }
.anexo-thumb:hover { opacity: .8; }
.anexo-doc { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--color-neutral-100); border-radius: var(--radius-md); font-size: var(--font-size-xs); color: var(--color-neutral-600); }
.mensagens { display: flex; flex-direction: column; gap: var(--space-3); margin: var(--space-4) 0; }
.mensagem { display: flex; gap: var(--space-3); align-items: flex-start; }
.msg-avatar {
  width: 32px; height: 32px; border-radius: var(--radius-full);
  background: var(--color-primary-100); color: var(--color-primary-700);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); flex-shrink: 0;
}
.mensagem.admin .msg-avatar { background: var(--color-warning-bg); color: var(--color-warning-text); }
.msg-body { flex: 1; background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); border-bottom-left-radius: 2px; padding: var(--space-3); }
.mensagem.admin .msg-body { background: var(--color-primary-50); border-color: var(--color-primary-100); border-bottom-left-radius: var(--radius-md); }
.msg-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); flex-wrap: wrap; }
.msg-author { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-neutral-800); }
.msg-suporte { font-size: var(--font-size-xs); background: var(--color-warning-bg); color: var(--color-warning-text); padding: 1px var(--space-2); border-radius: var(--radius-full); }
.msg-date { font-size: var(--font-size-xs); color: var(--color-neutral-400); margin-left: auto; }
.msg-text { font-size: var(--font-size-sm); color: var(--color-neutral-700); white-space: pre-wrap; line-height: 1.5; }
.msg-empty { font-size: var(--font-size-sm); color: var(--color-neutral-400); font-style: italic; text-align: center; padding: var(--space-4) 0; }
.reply-box { background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: var(--space-3); margin-top: var(--space-3); }
.reply-box textarea { width: 100%; border: 1.5px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); font-size: var(--font-size-sm); font-family: var(--font-family-base); resize: vertical; outline: none; transition: border-color var(--transition-fast); margin-bottom: var(--space-2); }
.reply-box textarea:focus { border-color: var(--color-primary-500); }
.reply-actions { display: flex; justify-content: flex-end; }
</style>
