<template>
  <div class="page-content">
    <div class="page-header">
      <h1 class="page-title">Onboarding</h1>
      <button class="btn-primary" @click="openModal()">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v6M5 8h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        Novo vídeo
      </button>
    </div>

    <p class="page-sub">Os usuários precisam assistir todos os vídeos ativos em ordem antes de acessar o sistema.</p>

    <!-- Empty state -->
    <div v-if="!loading && !videos.length" class="empty-state">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="4" y="10" width="40" height="28" rx="4" stroke="var(--color-text-tertiary)" stroke-width="1.8"/><path d="M20 18l10 6-10 6V18z" fill="var(--color-text-tertiary)"/></svg>
      <p>Nenhum vídeo cadastrado ainda.</p>
    </div>

    <!-- Lista de vídeos -->
    <div v-else class="video-list">
      <div
        v-for="(v, i) in videos"
        :key="v.id"
        class="video-card"
        :class="{ 'is-inactive': !v.ativo }"
      >
        <div class="video-order">{{ i + 1 }}</div>
        <div class="video-info">
          <span class="video-title">{{ v.titulo }}</span>
          <span class="video-desc" v-if="v.descricao">{{ v.descricao }}</span>
          <div class="video-meta">
            <span class="badge" :class="v.ativo ? 'badge-green' : 'badge-gray'">
              {{ v.ativo ? 'Ativo' : 'Inativo' }}
            </span>
            <span class="video-key">{{ v.video_key }}</span>
          </div>
        </div>
        <div class="video-actions">
          <button class="btn-icon" title="Mover para cima" :disabled="i === 0" @click="moveUp(i)">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 10l4-4 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <button class="btn-icon" title="Mover para baixo" :disabled="i === videos.length - 1" @click="moveDown(i)">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <button class="btn-icon" title="Editar" @click="openModal(v)">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M11 2l3 3-9 9H2v-3l9-9z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
          </button>
          <button class="btn-icon btn-danger" title="Excluir" @click="confirmDelete(v)">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4l1 9h4l1-9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal criar/editar -->
    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal" role="dialog" aria-modal="true">
          <div class="modal-header">
            <h2>{{ editing ? 'Editar vídeo' : 'Novo vídeo' }}</h2>
            <button class="btn-icon" @click="closeModal">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 4l10 10M14 4L4 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            </button>
          </div>

          <form @submit.prevent="saveVideo" class="modal-form">
            <div class="form-group">
              <label>Título *</label>
              <input v-model="form.titulo" type="text" required maxlength="200" placeholder="Ex: Bem-vindo ao sistema" />
            </div>
            <div class="form-group">
              <label>Descrição</label>
              <textarea v-model="form.descricao" rows="3" placeholder="Breve descrição do conteúdo do vídeo"></textarea>
            </div>
            <div class="form-group">
              <label>Ordem</label>
              <input v-model.number="form.ordem" type="number" min="0" />
            </div>
            <div class="form-group" v-if="!editing">
              <label>Arquivo de vídeo * <span class="label-hint">(MP4, WebM, OGG — máx. 500 MB)</span></label>
              <div class="file-drop" :class="{ 'has-file': form.file }" @dragover.prevent @drop.prevent="onDrop">
                <input type="file" accept="video/mp4,video/webm,video/ogg" @change="onFileChange" ref="fileInput" class="file-input" />
                <div class="file-drop-content" @click="fileInput.click()">
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none"><rect x="4" y="7" width="20" height="14" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M11 11l6 3-6 3V11z" fill="currentColor" opacity=".6"/></svg>
                  <span v-if="form.file">{{ form.file.name }}</span>
                  <span v-else>Clique ou arraste o vídeo aqui</span>
                </div>
              </div>
            </div>
            <div class="form-group" v-if="editing">
              <label>Status</label>
              <select v-model="form.ativo">
                <option :value="true">Ativo</option>
                <option :value="false">Inativo</option>
              </select>
            </div>

            <div class="upload-progress" v-if="uploading">
              <div class="upload-bar" :style="{ width: uploadPct + '%' }"></div>
              <span>Enviando... {{ uploadPct }}%</span>
            </div>

            <p v-if="formError" class="form-error">{{ formError }}</p>

            <div class="modal-footer">
              <button type="button" class="btn-secondary" @click="closeModal">Cancelar</button>
              <button type="submit" class="btn-primary" :disabled="saving || uploading">
                <span v-if="saving || uploading" class="btn-spinner"></span>
                <span v-else>{{ editing ? 'Salvar' : 'Enviar vídeo' }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Confirm delete -->
      <div v-if="deleteTarget" class="modal-backdrop" @click.self="deleteTarget = null">
        <div class="modal modal-sm" role="dialog">
          <div class="modal-header">
            <h2>Excluir vídeo</h2>
          </div>
          <p class="modal-body-text">Tem certeza que deseja excluir <strong>{{ deleteTarget.titulo }}</strong>? O arquivo será removido do armazenamento.</p>
          <div class="modal-footer">
            <button class="btn-secondary" @click="deleteTarget = null">Cancelar</button>
            <button class="btn-danger-solid" :disabled="deleting" @click="doDelete">
              <span v-if="deleting" class="btn-spinner"></span>
              <span v-else>Excluir</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const videos = ref([])
const loading = ref(false)
const modalOpen = ref(false)
const editing = ref(null)
const saving = ref(false)
const uploading = ref(false)
const uploadPct = ref(0)
const formError = ref('')
const deleteTarget = ref(null)
const deleting = ref(false)
const fileInput = ref(null)

const form = ref({ titulo: '', descricao: '', ordem: 0, ativo: true, file: null })

onMounted(load)

async function load() {
  loading.value = true
  try {
    videos.value = await api.onboarding.adminVideos()
  } finally {
    loading.value = false
  }
}

function openModal(v = null) {
  editing.value = v
  formError.value = ''
  if (v) {
    form.value = { titulo: v.titulo, descricao: v.descricao || '', ordem: v.ordem, ativo: v.ativo, file: null }
  } else {
    form.value = { titulo: '', descricao: '', ordem: videos.value.length, ativo: true, file: null }
  }
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
  editing.value = null
}

function onFileChange(e) {
  form.value.file = e.target.files[0] || null
}

function onDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f) form.value.file = f
}

async function saveVideo() {
  formError.value = ''
  saving.value = true
  try {
    if (editing.value) {
      const data = await api.onboarding.adminUpdate(editing.value.id, {
        titulo: form.value.titulo,
        descricao: form.value.descricao || null,
        ordem: form.value.ordem,
        ativo: form.value.ativo,
      })
      const idx = videos.value.findIndex(v => v.id === data.id)
      if (idx >= 0) videos.value[idx] = data
    } else {
      if (!form.value.file) { formError.value = 'Selecione um arquivo de vídeo.'; saving.value = false; return }
      const fd = new FormData()
      fd.append('titulo', form.value.titulo)
      fd.append('descricao', form.value.descricao || '')
      fd.append('ordem', String(form.value.ordem))
      fd.append('video', form.value.file)

      uploading.value = true
      uploadPct.value = 0

      // Usa XHR para acompanhar progresso
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        xhr.open('POST', `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/onboarding/admin/videos`)
        const token = localStorage.getItem('local_token')
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        xhr.upload.onprogress = (e) => {
          if (e.total) uploadPct.value = Math.round((e.loaded / e.total) * 100)
        }
        xhr.onload = () => {
          if (xhr.status === 201) resolve(JSON.parse(xhr.responseText))
          else {
            try { reject(new Error(JSON.parse(xhr.responseText).detail || 'Erro ao enviar')) }
            catch { reject(new Error('Erro ao enviar vídeo')) }
          }
        }
        xhr.onerror = () => reject(new Error('Erro de rede'))
        xhr.send(fd)
      })

      uploading.value = false
      videos.value.push(data)
    }
    closeModal()
  } catch (e) {
    formError.value = e.message || 'Erro ao salvar.'
    uploading.value = false
  } finally {
    saving.value = false
  }
}

async function moveUp(i) {
  if (i === 0) return
  ;[videos.value[i], videos.value[i - 1]] = [videos.value[i - 1], videos.value[i]]
  await reorder()
}

async function moveDown(i) {
  if (i >= videos.value.length - 1) return
  ;[videos.value[i], videos.value[i + 1]] = [videos.value[i + 1], videos.value[i]]
  await reorder()
}

async function reorder() {
  const body = videos.value.map((v, i) => ({ id: v.id, ordem: i }))
  await api.onboarding.adminReorder(body)
  videos.value.forEach((v, i) => { v.ordem = i })
}

function confirmDelete(v) {
  deleteTarget.value = v
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.onboarding.adminDelete(deleteTarget.value.id)
    videos.value = videos.value.filter(v => v.id !== deleteTarget.value.id)
    deleteTarget.value = null
  } catch (e) {
    alert(e.message || 'Erro ao excluir.')
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.page-content { padding: 1.5rem; max-width: 900px; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.page-title { font-size: 1.3rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.page-sub { font-size: 0.84rem; color: var(--color-text-secondary); margin: 0 0 1.5rem; }

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-tertiary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9rem;
}

.video-list { display: flex; flex-direction: column; gap: 0.75rem; }

.video-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  transition: opacity 0.2s;
}

.video-card.is-inactive { opacity: 0.55; }

.video-order {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary-50, rgba(99,102,241,0.1));
  color: var(--color-primary-500);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.video-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.video-title { font-size: 0.95rem; font-weight: 600; color: var(--color-text-primary); }
.video-desc { font-size: 0.82rem; color: var(--color-text-secondary); }
.video-meta { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.video-key { font-size: 0.72rem; color: var(--color-text-tertiary); font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300px; }

.badge {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 20px;
  font-size: 0.72rem;
  font-weight: 600;
}
.badge-green { background: rgba(34,197,94,0.12); color: #16a34a; }
.badge-gray  { background: rgba(100,100,100,0.1); color: var(--color-text-tertiary); }

.video-actions { display: flex; gap: 0.25rem; flex-shrink: 0; }

.btn-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: background 0.15s, color 0.15s;
}
.btn-icon:hover:not(:disabled) { background: var(--color-bg-primary); color: var(--color-text-primary); }
.btn-icon:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-icon.btn-danger:hover { color: #ef4444; border-color: #ef4444; }

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  padding: 1rem;
  backdrop-filter: blur(1px);
}

.modal {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-sm { max-width: 380px; }

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem 0;
}

.modal-header h2 { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }

.modal-form { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 1rem; }

.form-group { display: flex; flex-direction: column; gap: 0.3rem; }
.form-group label { font-size: 0.8rem; font-weight: 500; color: var(--color-text-secondary); }
.label-hint { color: var(--color-text-tertiary); font-weight: 400; }

.form-group input,
.form-group textarea,
.form-group select {
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.15s;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus { outline: none; border-color: var(--color-primary-500); }

/* File drop */
.file-drop {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  transition: border-color 0.15s;
}
.file-drop:hover, .file-drop.has-file { border-color: var(--color-primary-500); }
.file-input { display: none; }
.file-drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

/* Upload progress */
.upload-progress {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}
.upload-bar {
  height: 4px;
  background: var(--color-primary-500);
  border-radius: 2px;
  transition: width 0.3s;
}

.form-error { font-size: 0.8rem; color: #ef4444; margin: 0; }

.modal-body-text { padding: 0.75rem 1.5rem; color: var(--color-text-secondary); font-size: 0.9rem; line-height: 1.5; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0 1.5rem 1.5rem;
}

.btn-primary {
  padding: 0.6rem 1.1rem;
  background: var(--color-primary-500);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: opacity 0.15s;
}
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-secondary {
  padding: 0.6rem 1.1rem;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: var(--color-bg-primary); }

.btn-danger-solid {
  padding: 0.6rem 1.1rem;
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.btn-danger-solid:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
