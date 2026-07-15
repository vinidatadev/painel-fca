<template>
  <div>
    <div class="page-header">
      <h1>Novo FCA</h1>
      <RouterLink to="/fca" class="btn btn-secondary btn-sm">← Voltar</RouterLink>
    </div>

    <div class="card">
      <div v-if="loadingOpcoes" class="loading-center">
        <div class="loading-spinner"></div>
        <span>Carregando opções...</span>
      </div>

      <form v-else @submit.prevent="submit">
        <!-- Contexto do usuário -->
        <div v-if="user" class="user-context-card">
          <div class="user-context-icon">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 15c0-3.314 2.686-6 6-6s6 2.686 6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </div>
          <div class="user-context-grid">
            <div class="user-context-item">
              <span class="user-context-label">Setor solicitante</span>
              <span class="user-context-value">{{ user.sector }}</span>
            </div>
            <div class="user-context-item">
              <span class="user-context-label">Empresa</span>
              <span class="user-context-value">{{ user.company }}</span>
            </div>
          </div>
        </div>

        <!-- Seção 1: Identificação -->
        <div class="form-section">
          <div class="form-section-header">
            <span class="form-section-num">1</span>
            <h3 class="form-section-title">Identificação</h3>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label>Causa do FCA <span class="req">*</span></label>
              <select v-model="form.causa" required>
                <option value="">Selecione...</option>
                <option v-for="c in opcoes.causas" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Área Causadora <span class="req">*</span></label>
              <select v-model="form.area_causadora" required @change="form.empresa_causadora = ''">
                <option value="">Selecione...</option>
                <option v-for="s in areasDisponiveis" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Empresa do Causador <span class="req">*</span></label>
              <select v-model="form.empresa_causadora" required :disabled="!form.area_causadora">
                <option value="">Selecione...</option>
                <option v-for="e in empresasParaArea" :key="e" :value="e">{{ e }}</option>
              </select>
            </div>
          </div>
        </div>

        <hr class="section-divider" />

        <!-- Seção 2: Localização e Ação -->
        <div class="form-section">
          <div class="form-section-header">
            <span class="form-section-num">2</span>
            <h3 class="form-section-title">Localização e Ação</h3>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label>Ação <span class="req">*</span></label>
              <select v-model="form.acao" required>
                <option value="">Selecione...</option>
                <option v-for="a in opcoes.acoes" :key="a" :value="a">{{ a }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>UF <span class="req">*</span></label>
              <select v-model="form.uf" required>
                <option value="">Selecione...</option>
                <option v-for="u in opcoes.ufs" :key="u" :value="u">{{ u }}</option>
              </select>
            </div>
          </div>
        </div>

        <hr class="section-divider" />

        <!-- Seção 3: Remessas -->
        <div class="form-section">
          <div class="form-section-header">
            <span class="form-section-num">3</span>
            <h3 class="form-section-title">Remessas</h3>
          </div>
          <div class="remessas-list">
            <div v-for="(_, i) in form.remessas" :key="i" class="remessa-row">
              <div class="form-group" style="flex:1">
                <label v-if="i === 0">Número(s) da Remessa</label>
                <input v-model.number="form.remessas[i]" type="number" placeholder="Ex: 83139570" />
              </div>
              <button v-if="form.remessas.length > 1" type="button" class="btn btn-secondary btn-sm remessa-remove" @click="removeRemessa(i)" style="margin-top:auto">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              </button>
            </div>
            <button type="button" class="btn btn-ghost btn-sm add-remessa-btn" @click="addRemessa">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 2v8M2 6h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              Adicionar remessa
            </button>
          </div>
        </div>

        <hr class="section-divider" />

        <!-- Detalhe -->
        <div class="form-section">
          <div class="form-group">
            <label>Detalhe / Observação</label>
            <textarea v-model="form.detalhe" placeholder="Descreva o problema com mais detalhes..." rows="3"></textarea>
          </div>
        </div>

        <hr class="section-divider" />

        <!-- Seção 4: Evidências -->
        <div class="form-section">
          <div class="form-section-header">
            <span class="form-section-num">4</span>
            <h3 class="form-section-title">Evidências / Anexos</h3>
          </div>
          <p class="section-hint">JPEG, PNG, PDF — máx 20 MB cada · até 5 arquivos · ou cole com Ctrl+V</p>

          <div
            class="drop-zone"
            :class="{ 'drag-over': isDragging }"
            @click="$refs.fileInput.click()"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="onDrop"
          >
            <div class="drop-zone-content">
              <svg width="36" height="36" viewBox="0 0 36 36" fill="none"><path d="M18 24V12M12 18l6-6 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M6 28a6 6 0 010-12h2a8 8 0 1116 0h2a6 6 0 010 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              <p class="drop-zone-text">
                <span v-if="pendingFiles.length === 0">Clique, arraste ou cole (Ctrl+V) para adicionar</span>
                <span v-else>+ Adicionar mais arquivos</span>
              </p>
            </div>
          </div>

          <input ref="fileInput" type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf" class="hidden-input" @change="onFileChange" />

          <div v-if="pendingFiles.length" class="previews">
            <div v-for="(f, i) in pendingFiles" :key="i" class="preview-item">
              <div class="preview-media">
                <img v-if="f.preview" :src="f.preview" class="preview-thumb" />
                <div v-else class="preview-doc">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8L14 2z" stroke="currentColor" stroke-width="1.5"/><path d="M14 2v6h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                  <span class="doc-name">{{ f.file.name }}</span>
                </div>
                <div class="preview-overlay" @click.stop="removeFile(i)">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 5l6 6M11 5l-6 6" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
                </div>
              </div>
              <div class="preview-status">
                <span v-if="f.uploading" class="status-uploading">
                  <span class="skeleton skeleton-text" style="width:60px;height:8px"></span>
                </span>
                <span v-else-if="f.key" class="status-ok">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  Enviado
                </span>
                <span v-else-if="f.error" class="status-err">{{ f.error }}</span>
              </div>
            </div>
          </div>
        </div>

        <p v-if="error" class="error-msg" style="margin-top:var(--space-4)">{{ error }}</p>

        <!-- Submit -->
        <div class="submit-area">
          <button class="btn btn-primary" type="submit" :disabled="submitting || isUploading">
            <svg v-if="!submitting && !isUploading" width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7l4 4 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            {{ submitting ? 'Criando...' : isUploading ? 'Aguardando uploads...' : 'Criar FCA' }}
          </button>
          <RouterLink to="/fca" class="btn btn-secondary">Cancelar</RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const user = inject('user')

const opcoes = ref({ causas: [], acoes: [], ufs: [], empresas: [], setores_por_empresa: {} })
const loadingOpcoes = ref(true)
const submitting = ref(false)
const error = ref('')
const isDragging = ref(false)
const fileInput = ref(null)
const pendingFiles = ref([])
const isUploading = computed(() => pendingFiles.value.some(f => f.uploading))

const form = ref({ causa: '', area_causadora: '', empresa_causadora: '', acao: '', uf: '', remessas: [null], detalhe: '' })

function addRemessa() { form.value.remessas.push(null) }
function removeRemessa(i) { form.value.remessas.splice(i, 1) }

function onFileChange(e) { Array.from(e.target.files).forEach(addFile); e.target.value = '' }
function onDrop(e) { isDragging.value = false; Array.from(e.dataTransfer.files).forEach(addFile) }
function addFile(file) {
  if (pendingFiles.value.length >= 5) { error.value = 'Máximo de 5 anexos.'; return }
  const entry = { file, preview: null, key: null, uploading: true, error: null }
  pendingFiles.value.push(entry)
  const idx = pendingFiles.value.length - 1
  if (file.type.startsWith('image/')) {
    const reader = new FileReader()
    reader.onload = ev => { pendingFiles.value[idx].preview = ev.target.result }
    reader.readAsDataURL(file)
  }
  api.upload.file(file)
    .then(res => { pendingFiles.value[idx].key = res.object_key })
    .catch(err => { pendingFiles.value[idx].error = err.message })
    .finally(() => { pendingFiles.value[idx].uploading = false })
}
function removeFile(i) { pendingFiles.value.splice(i, 1) }
function onPaste(e) {
  const items = Array.from(e.clipboardData?.items || [])
  const img = items.find(i => i.type.startsWith('image/'))
  if (!img) return
  e.preventDefault()
  const file = img.getAsFile()
  if (file) addFile(new File([file], `paste_${Date.now()}.png`, { type: file.type }))
}

const AREA_EMPRESAS = {
  ACL: ['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'], PCP: ['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'],
  Qualidade: ['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'], MEP: ['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'],
  Expedicao: ['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'], Producao: ['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'],
  Comercial: ['ACC'], Customer_Service: ['ACC'],
}
const TRIAGEM = {
  'ACL_ACI_MATRIZ':['ACL','ACI_MATRIZ'],'ACL_ACI_FILIAL':['ACL','ACI_FILIAL'],'ACL_SINOBRAS':['ACL','SINOBRAS'],
  'Comercial_ACC':['Comercial','ACC'],'PCP_ACI_MATRIZ':['PCP','ACI_MATRIZ'],'PCP_ACI_FILIAL':['PCP','ACI_FILIAL'],
  'PCP_SINOBRAS':['PCP','SINOBRAS'],'Qualidade_ACI_MATRIZ':['Qualidade','ACI_MATRIZ'],'Qualidade_ACI_FILIAL':['Qualidade','ACI_FILIAL'],
  'Qualidade_SINOBRAS':['Qualidade','SINOBRAS'],'MEP_ACI_MATRIZ':['MEP','ACI_MATRIZ'],'MEP_ACI_FILIAL':['MEP','ACI_FILIAL'],
  'MEP_SINOBRAS':['MEP','SINOBRAS'],'Expedicao_ACI_MATRIZ':['Expedicao','ACI_MATRIZ'],'Expedicao_ACI_FILIAL':['Expedicao','ACI_FILIAL'],
  'Expedicao_SINOBRAS':['Expedicao','SINOBRAS'],'Customer_Service_ACC':['Customer_Service','ACC'],
  'Producao_ACI_MATRIZ':['Producao','ACI_MATRIZ'],'Producao_ACI_FILIAL':['Producao','ACI_FILIAL'],'Producao_SINOBRAS':['Producao','SINOBRAS'],
}
const areasDisponiveis = computed(() => Object.keys(AREA_EMPRESAS).filter(area =>
  (AREA_EMPRESAS[area] || []).some(empresa => {
    const destino = TRIAGEM[`${area}_${empresa}`]
    return !destino || !(destino[0] === user.value?.sector && destino[1] === user.value?.company)
  })
))
const empresasParaArea = computed(() => {
  if (!form.value.area_causadora) return []
  return (AREA_EMPRESAS[form.value.area_causadora] || []).filter(empresa => {
    const destino = TRIAGEM[`${form.value.area_causadora}_${empresa}`]
    return !destino || !(destino[0] === user.value?.sector && destino[1] === user.value?.company)
  })
})
async function submit() {
  error.value = ''
  if (isUploading.value) { error.value = 'Aguarde os uploads terminarem.'; return }
  if (pendingFiles.value.filter(f => f.error).length) { error.value = 'Remova os arquivos com erro.'; return }
  submitting.value = true
  try {
    const res = await api.fcas.create({
      ...form.value,
      remessas: form.value.remessas.filter(r => r !== null && r !== '' && !isNaN(r)),
      anexo_urls: pendingFiles.value.filter(f => f.key).map(f => f.key),
    })
    router.push(`/fca/${res.id}`)
  } catch (e) { error.value = e.message }
  finally { submitting.value = false }
}
onMounted(async () => {
  window.addEventListener('paste', onPaste)
  try { opcoes.value = await api.opcoes.get() }
  catch (e) { error.value = 'Erro ao carregar opções: ' + e.message }
  finally { loadingOpcoes.value = false }
})
onUnmounted(() => { window.removeEventListener('paste', onPaste) })
</script>

<style scoped>
.loading-center { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-8); color: var(--color-neutral-500); }
.loading-spinner { width: 32px; height: 32px; border: 3px solid var(--color-primary-100); border-top-color: var(--color-primary-500); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* User context card */
.user-context-card {
  display: flex; align-items: center; gap: var(--space-4);
  background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); margin-bottom: var(--space-5);
}
.user-context-icon { color: var(--color-primary-500); flex-shrink: 0; }
.user-context-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); flex: 1; }
.user-context-item { display: flex; flex-direction: column; gap: 2px; }
.user-context-label { font-size: var(--font-size-xs); color: var(--color-neutral-400); text-transform: uppercase; letter-spacing: .04em; }
.user-context-value { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-primary-700); }

/* Form sections */
.form-section { padding: var(--space-4) 0; }
.form-section:first-of-type { padding-top: 0; }
.form-section-header { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-4); }
.form-section-num {
  width: 24px; height: 24px; background: var(--color-primary-500); color: #fff;
  border-radius: var(--radius-full); display: flex; align-items: center; justify-content: center;
  font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); flex-shrink: 0;
}
.form-section-title { font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); color: var(--color-neutral-800); margin: 0; }
.section-divider { border: none; border-top: 1px solid var(--color-neutral-200); margin: 0; }
.section-hint { font-size: var(--font-size-xs); color: var(--color-neutral-400); margin-bottom: var(--space-3); margin-top: calc(-1 * var(--space-2)); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--space-3) var(--space-5); }

/* Remessas */
.remessas-list { display: flex; flex-direction: column; gap: var(--space-2); max-width: 400px; }
.remessa-row { display: flex; gap: var(--space-2); align-items: flex-end; }
.remessa-remove { align-self: flex-end; padding: var(--space-2); }
.add-remessa-btn { align-self: flex-start; margin-top: var(--space-1); color: var(--color-primary-600); }

/* Drop zone */
.drop-zone {
  border: 2px dashed var(--color-neutral-300); border-radius: var(--radius-lg);
  padding: var(--space-8); text-align: center; cursor: pointer;
  background: var(--color-neutral-50); transition: border-color var(--transition-base), background var(--transition-base), transform var(--transition-base);
  user-select: none;
}
.drop-zone:hover { border-color: var(--color-primary-300); background: var(--color-primary-50); }
.drag-over { border-color: var(--color-primary-500) !important; background: var(--color-primary-100) !important; transform: scale(1.01); }
.drop-zone-content { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); color: var(--color-neutral-400); }
.drop-zone-text { font-size: var(--font-size-sm); }
.hidden-input { display: none; }

/* Previews */
.previews { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-4); }
.preview-item { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); width: 96px; }
.preview-media { position: relative; width: 80px; height: 80px; border-radius: var(--radius-md); overflow: hidden; background: var(--color-neutral-100); border: 1px solid var(--color-neutral-200); cursor: pointer; }
.preview-thumb { width: 100%; height: 100%; object-fit: cover; }
.preview-doc { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; color: var(--color-neutral-500); }
.doc-name { font-size: 9px; word-break: break-all; text-align: center; color: var(--color-neutral-500); padding: 0 4px; }
.preview-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,.5);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity var(--transition-fast);
}
.preview-media:hover .preview-overlay { opacity: 1; }
.preview-status { text-align: center; width: 100%; }
.status-uploading { display: block; }
.status-ok { font-size: var(--font-size-xs); color: var(--color-success); display: flex; align-items: center; gap: 3px; justify-content: center; }
.status-err { font-size: var(--font-size-xs); color: var(--color-danger-text); display: block; text-align: center; }

/* Submit */
.submit-area {
  display: flex; gap: var(--space-3); align-items: center;
  margin-top: var(--space-6); padding-top: var(--space-5);
  border-top: 1px solid var(--color-neutral-200);
}
.req { color: var(--color-danger); }

@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr; }
  .user-context-grid { grid-template-columns: 1fr; }
  .submit-area { position: sticky; bottom: 0; background: #fff; margin: 0 calc(-1 * var(--space-5)); padding: var(--space-3) var(--space-5); box-shadow: 0 -4px 12px rgba(0,0,0,.08); }
}
</style>
