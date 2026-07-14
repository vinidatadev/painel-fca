<template>
  <div>
    <div class="page-header">
      <h1>Novo FCA</h1>
      <RouterLink to="/fca" class="btn btn-secondary btn-sm">← Voltar</RouterLink>
    </div>

    <div class="card">
      <div v-if="loadingOpcoes" class="loading-text">Carregando opções...</div>

      <form v-else @submit.prevent="submit">
        <!-- Info do solicitante (readonly) -->
        <div class="info-row" v-if="user">
          <span class="info-chip">Setor solicitante: <strong>{{ user.sector }}</strong></span>
          <span class="info-chip">Empresa: <strong>{{ user.company }}</strong></span>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label>Causa do FCA *</label>
            <select v-model="form.causa" required>
              <option value="">Selecione...</option>
              <option v-for="c in opcoes.causas" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>Área Causadora *</label>
            <select v-model="form.area_causadora" required @change="form.empresa_causadora = ''">
              <option value="">Selecione...</option>
              <option v-for="s in areasDisponiveis" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>Empresa do Causador *</label>
            <select v-model="form.empresa_causadora" required :disabled="!form.area_causadora">
              <option value="">Selecione...</option>
              <option v-for="e in empresasParaArea" :key="e" :value="e">{{ e }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>Ação *</label>
            <select v-model="form.acao" required>
              <option value="">Selecione...</option>
              <option v-for="a in opcoes.acoes" :key="a" :value="a">{{ a }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>UF *</label>
            <select v-model="form.uf" required>
              <option value="">Selecione...</option>
              <option v-for="u in opcoes.ufs" :key="u" :value="u">{{ u }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>Número(s) da Remessa</label>
            <div class="remessas-list">
              <div v-for="(_, i) in form.remessas" :key="i" class="remessa-row">
                <input
                  v-model.number="form.remessas[i]"
                  type="number"
                  placeholder="Ex: 83139570"
                  class="remessa-input"
                />
                <button type="button" class="btn btn-danger btn-sm" @click="removeRemessa(i)" v-if="form.remessas.length > 1">✕</button>
              </div>
              <button type="button" class="btn btn-secondary btn-sm" @click="addRemessa" style="align-self:flex-start">
                + Adicionar remessa
              </button>
            </div>
          </div>
        </div>

        <div class="form-group" style="margin-top:.75rem">
          <label>Detalhe / Observação</label>
          <textarea v-model="form.detalhe" placeholder="Descreva o problema com mais detalhes..." rows="3"></textarea>
        </div>

        <div class="form-group">
          <label>Anexos / Evidências <small>(JPEG, PNG, PDF — máx 20 MB cada · até 5 · ou cole com Ctrl+V)</small></label>
          <div
            class="drop-zone"
            :class="{ 'drag-over': isDragging }"
            @click="$refs.fileInput.click()"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="onDrop"
          >
            <span v-if="pendingFiles.length === 0">Clique, arraste ou cole (Ctrl+V) para adicionar</span>
            <span v-else>+ Adicionar mais</span>
          </div>
          <input ref="fileInput" type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf" class="hidden-input" @change="onFileChange" />
          <div v-if="pendingFiles.length" class="previews">
            <div v-for="(f, i) in pendingFiles" :key="i" class="preview-item">
              <img v-if="f.preview" :src="f.preview" class="preview-thumb" />
              <div v-else class="preview-doc"><span class="doc-icon">📄</span><span class="doc-name">{{ f.file.name }}</span></div>
              <div class="preview-info">
                <span class="preview-name">{{ f.file.name }}</span>
                <span v-if="f.uploading" class="hint-upload">Enviando...</span>
                <span v-else-if="f.key" class="hint-ok">✓</span>
                <span v-else-if="f.error" class="hint-err">{{ f.error }}</span>
              </div>
              <button type="button" class="remove-btn" @click.stop="removeFile(i)">×</button>
            </div>
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <div style="display:flex;gap:.75rem;margin-top:1.25rem">
          <button class="btn btn-primary" type="submit" :disabled="submitting || isUploading">
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

// Cada item: { file, preview, key, uploading, error }
const pendingFiles = ref([])
const isUploading = computed(() => pendingFiles.value.some(f => f.uploading))

const form = ref({
  causa: '', area_causadora: '', empresa_causadora: '',
  acao: '', uf: '', remessas: [null], detalhe: ''
})

function addRemessa() { form.value.remessas.push(null) }
function removeRemessa(i) { form.value.remessas.splice(i, 1) }

// ── Anexos ────────────────────────────────────────────────────────────────────
function onFileChange(e) {
  Array.from(e.target.files).forEach(addFile)
  e.target.value = ''
}
function onDrop(e) {
  isDragging.value = false
  Array.from(e.dataTransfer.files).forEach(addFile)
}
function addFile(file) {
  if (pendingFiles.value.length >= 5) { error.value = 'Máximo de 5 anexos por FCA.'; return }
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
  ACL:              ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  PCP:              ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Qualidade:        ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  MEP:              ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Expedicao:        ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Producao:         ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Comercial:        ['ACC'],
  Customer_Service: ['ACC'],
}

// Mapeamento triagem: area+empresa → setor destino (espelho do backend)
const TRIAGEM = {
  'ACL_ACI_MATRIZ': ['ACL', 'ACI_MATRIZ'],
  'ACL_ACI_FILIAL': ['ACL', 'ACI_FILIAL'],
  'ACL_SINOBRAS':   ['ACL', 'SINOBRAS'],
  'Comercial_ACC':  ['Comercial', 'ACC'],
  'PCP_ACI_MATRIZ': ['PCP', 'ACI_MATRIZ'],
  'PCP_ACI_FILIAL': ['PCP', 'ACI_FILIAL'],
  'PCP_SINOBRAS':   ['PCP', 'SINOBRAS'],
  'Qualidade_ACI_MATRIZ': ['Qualidade', 'ACI_MATRIZ'],
  'Qualidade_ACI_FILIAL': ['Qualidade', 'ACI_FILIAL'],
  'Qualidade_SINOBRAS':   ['Qualidade', 'SINOBRAS'],
  'MEP_ACI_MATRIZ': ['MEP', 'ACI_MATRIZ'],
  'MEP_ACI_FILIAL': ['MEP', 'ACI_FILIAL'],
  'MEP_SINOBRAS':   ['MEP', 'SINOBRAS'],
  'Expedicao_ACI_MATRIZ': ['Expedicao', 'ACI_MATRIZ'],
  'Expedicao_ACI_FILIAL': ['Expedicao', 'ACI_FILIAL'],
  'Expedicao_SINOBRAS':   ['Expedicao', 'SINOBRAS'],
  'Customer_Service_ACC': ['Customer_Service', 'ACC'],
  'Producao_ACI_MATRIZ':  ['Producao', 'ACI_MATRIZ'],
  'Producao_ACI_FILIAL':  ['Producao', 'ACI_FILIAL'],
  'Producao_SINOBRAS':    ['Producao', 'SINOBRAS'],
}

const areasDisponiveis = computed(() => {
  return Object.keys(AREA_EMPRESAS).filter(area => {
    const empresas = AREA_EMPRESAS[area] || []
    // Mantém a área só se restar ao menos uma empresa válida
    return empresas.some(empresa => {
      const key = `${area}_${empresa}`
      const destino = TRIAGEM[key]
      if (!destino) return true
      return !(destino[0] === user.value?.sector && destino[1] === user.value?.company)
    })
  })
})

// Empresas disponíveis para a área selecionada, excluindo combinações que resultam no próprio setor
const empresasParaArea = computed(() => {
  if (!form.value.area_causadora) return []
  const todas = AREA_EMPRESAS[form.value.area_causadora] || []
  return todas.filter(empresa => {
    const key = `${form.value.area_causadora}_${empresa}`
    const destino = TRIAGEM[key]
    if (!destino) return true
    // Remove se o destino é o próprio setor+empresa do usuário
    return !(destino[0] === user.value?.sector && destino[1] === user.value?.company)
  })
})

async function submit() {
  error.value = ''
  if (isUploading.value) { error.value = 'Aguarde os uploads terminarem.'; return }
  const failed = pendingFiles.value.filter(f => f.error)
  if (failed.length) { error.value = 'Alguns arquivos falharam. Remova-os antes de enviar.'; return }
  submitting.value = true
  try {
    const anexo_urls = pendingFiles.value.filter(f => f.key).map(f => f.key)
    const payload = {
      ...form.value,
      remessas: form.value.remessas.filter(r => r !== null && r !== '' && !isNaN(r)),
      anexo_urls,
    }
    const res = await api.fcas.create(payload)
    router.push(`/fca/${res.id}`)
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  window.addEventListener('paste', onPaste)
  try {
    opcoes.value = await api.opcoes.get()
  } catch (e) {
    error.value = 'Erro ao carregar opções: ' + e.message
  } finally {
    loadingOpcoes.value = false
  }
})
onUnmounted(() => { window.removeEventListener('paste', onPaste) })
</script>

<style scoped>
.info-row { display: flex; gap: .75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.info-chip { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: .35rem .75rem; font-size: .82rem; color: #1d4ed8; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem 1rem; }
.loading-text { color: #888; padding: 1.5rem; text-align: center; }
.text-muted { color: #9ca3af; font-size: .8rem; }
.text-green { color: #059669; font-size: .8rem; }

.remessas-list { display: flex; flex-direction: column; gap: .4rem; }
.remessa-row { display: flex; gap: .4rem; align-items: center; }
.remessa-input { flex: 1; padding: .5rem .75rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: .9rem; }

/* ── Drop zone e previews ── */
.drop-zone {
  border: 2px dashed #cbd5e1; border-radius: 8px; padding: .8rem 1rem;
  text-align: center; cursor: pointer; color: #64748b; font-size: .9rem;
  transition: border-color .15s, background .15s; user-select: none; margin-top: .25rem;
}
.drop-zone:hover, .drag-over { border-color: #3b82f6; background: #eff6ff; }
.hidden-input { display: none; }

.previews { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: .6rem; }
.preview-item {
  position: relative; display: flex; flex-direction: column; align-items: center;
  width: 90px; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 8px; padding: .4rem; gap: .25rem;
}
.preview-thumb { width: 72px; height: 72px; object-fit: cover; border-radius: 5px; }
.preview-doc { display: flex; flex-direction: column; align-items: center; gap: .2rem; width: 72px; height: 72px; justify-content: center; }
.doc-icon { font-size: 1.8rem; }
.doc-name { font-size: .65rem; word-break: break-all; text-align: center; color: #64748b; }
.preview-info { width: 100%; text-align: center; }
.preview-name { font-size: .65rem; word-break: break-all; color: #64748b; display: block; }
.hint-upload { font-size: .72rem; color: #64748b; display: block; }
.hint-ok { font-size: .72rem; color: #16a34a; display: block; }
.hint-err { font-size: .72rem; color: #ef4444; display: block; }
.remove-btn {
  position: absolute; top: -7px; right: -7px; width: 20px; height: 20px;
  background: #ef4444; color: #fff; border: none; border-radius: 50%;
  font-size: .8rem; cursor: pointer; display: flex; align-items: center; justify-content: center;
  line-height: 1;
}

@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
