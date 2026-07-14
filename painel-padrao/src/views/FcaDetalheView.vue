<template>
  <div>
    <div class="page-header">
      <h1>{{ fca?.cod_fca || 'Carregando...' }}</h1>
      <RouterLink to="/fca" class="btn btn-secondary btn-sm">← Voltar</RouterLink>
    </div>

    <div v-if="loading" class="loading-text">Carregando...</div>
    <div v-else-if="!fca" class="card error-msg">FCA não encontrado ou sem permissão de acesso.</div>

    <template v-else>
      <!-- Seção 1: Dados da abertura -->
      <div class="card">
        <h2 class="section-title">Dados da Abertura</h2>
        <div class="detail-grid">
          <div class="detail-item"><label>Status</label><span :class="['badge', 'badge-' + fca.status]">{{ labelStatus(fca.status) }}</span></div>
          <div class="detail-item"><label>Data de Abertura</label><span>{{ formatDate(fca.created_at) }}</span></div>
          <div class="detail-item"><label>Aberto por</label><span>{{ fca.created_by.name }}</span></div>
          <div class="detail-item"><label>Setor Solicitante</label><span>{{ fca.setor_solicitante }} · {{ fca.empresa_solicitante }}</span></div>
          <div class="detail-item"><label>Área Causadora</label><span>{{ fca.area_causadora }} · {{ fca.empresa_causadora }}</span></div>
          <div class="detail-item"><label>Causa</label><span>{{ fca.causa }}</span></div>
          <div class="detail-item"><label>Ação</label><span>{{ fca.acao }}</span></div>
          <div class="detail-item"><label>UF</label><span>{{ fca.uf }}</span></div>
          <div class="detail-item"><label>Nº Remessa(s)</label>
            <span v-if="fca.remessas && fca.remessas.length">{{ fca.remessas.join(', ') }}</span>
            <span v-else>{{ fca.numero_remessa || '—' }}</span>
          </div>
        </div>
        <div v-if="fca.detalhe" class="detail-item full-width" style="margin-top:.75rem">
          <label>Detalhe / Observação</label>
          <p class="detalhe-text">{{ fca.detalhe }}</p>
        </div>

        <!-- Anexos com preview -->
        <div v-if="fca.anexo_urls && fca.anexo_urls.length" style="margin-top:.75rem">
          <label class="detail-label">Anexos</label>
          <div class="anexos-grid">
            <a
              v-for="key in fca.anexo_urls"
              :key="key"
              class="anexo-item"
              href="#"
              @click.prevent="abrirAnexo(key)"
            >
              <img v-if="isImage(key)" :src="anexoUrls[key]" class="anexo-thumb" :title="key.split('/').pop()" />
              <div v-else class="anexo-doc">
                <span>📄</span>
                <span class="anexo-doc-name">{{ key.split('/').pop() }}</span>
              </div>
            </a>
          </div>
        </div>
        <!-- fallback para FCAs legados com anexo_url simples -->
        <div v-else-if="fca.anexo_url" style="margin-top:.75rem">
          <label class="detail-label">Anexo</label>
          <button class="btn btn-outline btn-sm" @click="abrirAnexo(fca.anexo_url)" :disabled="loadingAnexo">
            {{ loadingAnexo ? 'Gerando link...' : '📎 Visualizar Anexo' }}
          </button>
        </div>
      </div>

      <!-- Seção 2: Linha do tempo -->
      <div class="card" style="margin-top:1rem">
        <h2 class="section-title">Histórico de Etapas</h2>
        <div class="timeline">
          <div
            v-for="etapa in fca.etapas"
            :key="etapa.id"
            :class="['timeline-item', etapa.status]"
          >
            <div class="tl-marker"></div>
            <div class="tl-content">
              <div class="tl-header">
                <strong>{{ etapa.setor }} · {{ etapa.empresa }}</strong>
                <span :class="['badge', statusEtapaBadge(etapa.status)]">{{ labelEtapaStatus(etapa.status) }}</span>
                <SlaBadge v-if="etapa.status !== 'concluido' && etapa.sla_deadline" :deadline="etapa.sla_deadline" />
                <span class="tl-index">#{{ etapa.order_index }}</span>
              </div>
              <div v-if="etapa.status === 'concluido'" class="tl-body">
                <p><strong>Problema Solucionado:</strong> {{ etapa.problema_solucionado ? 'Sim' : 'Não' }}</p>
                <p><strong>Devolutiva:</strong> {{ etapa.devolutiva }}</p>
                <p class="tl-meta">
                  Respondido por {{ etapa.respondido_por?.name || '—' }}
                  em {{ formatDate(etapa.concluded_at) }}
                </p>
              </div>
              <div v-else class="tl-pending">
                <span v-if="etapa.status === 'pendente'">Aguardando tratamento...</span>
                <span v-else>Em andamento...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Seção 3: Formulário de resposta (só quando é a vez do setor) -->
      <div v-if="minhaVez" class="card" style="margin-top:1rem">
        <h2 class="section-title">Responder Etapa</h2>
        <form @submit.prevent="responder">
          <div class="form-group">
            <label>Problema Solucionado? *</label>
            <div class="radio-group">
              <label><input type="radio" v-model="resposta.problema_solucionado" :value="true" required /> Sim</label>
              <label><input type="radio" v-model="resposta.problema_solucionado" :value="false" /> Não</label>
            </div>
          </div>

          <div class="form-group">
            <label>Detalhe / Devolutiva da Tratativa *</label>
            <textarea v-model="resposta.devolutiva" required rows="4" placeholder="Descreva como foi tratado o problema..."></textarea>
          </div>

          <div class="form-group">
            <label>Encaminhar para outro(s) setor(es)?</label>
            <div class="radio-group">
              <label><input type="radio" v-model="encaminhar" :value="false" /> Não</label>
              <label><input type="radio" v-model="encaminhar" :value="true" /> Sim</label>
            </div>
          </div>

          <div v-if="encaminhar" class="encaminhamentos">
            <div v-for="(enc, i) in resposta.encaminhar" :key="i" class="enc-row">
              <select v-model="enc.setor" required @change="enc.empresa = ''">
                <option value="">Setor...</option>
                <option v-for="s in SETORES_ENC" :key="s" :value="s">{{ s }}</option>
              </select>
              <select v-model="enc.empresa" required :disabled="!enc.setor">
                <option value="">Empresa...</option>
                <option v-for="e in empresasParaSetor(enc.setor)" :key="e" :value="e">{{ e }}</option>
              </select>
              <button type="button" class="btn btn-danger btn-sm" @click="removeEnc(i)">✕</button>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" @click="addEnc">+ Adicionar setor</button>
          </div>

          <p v-if="errorResp" class="error-msg">{{ errorResp }}</p>

          <div style="margin-top:1rem">
            <button class="btn btn-primary" type="submit" :disabled="submitting">
              {{ submitting ? 'Enviando...' : 'Enviar Resposta' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Confirmar ciência / encerrar -->
      <div v-if="podeEncerrar" class="card encerrar-box" style="margin-top:1rem">
        <h2 class="section-title">Devolutiva Recebida</h2>
        <p>Todas as etapas foram concluídas. Confirme o recebimento para encerrar o FCA.</p>
        <button class="btn btn-primary" style="margin-top:.75rem" @click="encerrar" :disabled="subEncerrar">
          {{ subEncerrar ? 'Encerrando...' : '✓ Confirmar Ciência e Encerrar' }}
        </button>
        <p v-if="errorEncerrar" class="error-msg">{{ errorEncerrar }}</p>
      </div>

      <!-- Seção 4: Fila pendente -->
      <div v-if="filaFutura.length" class="card" style="margin-top:1rem">        <h2 class="section-title">Próximos na Fila</h2>
        <div class="fila-lista">
          <div v-for="e in filaFutura" :key="e.id" class="fila-item">
            <span class="fila-index">#{{ e.order_index }}</span>
            <span>{{ e.setor }} · {{ e.empresa }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import SlaBadge from '../components/SlaBadge.vue'

const route = useRoute()
const user  = inject('user')

const fca      = ref(null)
const loading  = ref(true)
const loadingAnexo = ref(false)
const submitting = ref(false)
const errorResp  = ref('')
const encaminhar = ref(false)
const anexoUrls  = ref({})  // key → presigned URL (cache para imagens)

const resposta = ref({
  problema_solucionado: null,
  devolutiva: '',
  encaminhar: [],
})

const subEncerrar  = ref(false)
const errorEncerrar = ref('')

const podeEncerrar = computed(() => {
  if (!fca.value || !user.value) return false
  if (fca.value.status !== 'aguardando_devolutiva') return false
  if (user.value.role === 'admin') return true
  return fca.value.setor_solicitante === user.value.sector &&
         fca.value.empresa_solicitante === user.value.company
})

const SETOR_EMPRESAS = {
  ACL:              ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  PCP:              ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Qualidade:        ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  MEP:              ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Expedicao:        ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Producao:         ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS'],
  Comercial:        ['ACC'],
  Customer_Service: ['ACC'],
}
const SETORES_ENC = Object.keys(SETOR_EMPRESAS)

const etapaAtiva = computed(() => {
  if (!fca.value) return null
  return fca.value.etapas
    .filter(e => e.status === 'pendente' || e.status === 'em_andamento')
    .sort((a, b) => a.order_index - b.order_index)[0] || null
})

const minhaVez = computed(() => {
  if (!etapaAtiva.value || !user.value) return false
  return etapaAtiva.value.setor === user.value.sector &&
         etapaAtiva.value.empresa === user.value.company
})

const filaFutura = computed(() => {
  if (!fca.value) return []
  const atualIdx = etapaAtiva.value?.order_index || 0
  return fca.value.etapas
    .filter(e => e.status === 'pendente' && e.order_index > atualIdx)
    .sort((a, b) => a.order_index - b.order_index)
})

function empresasParaSetor(setor) {
  return SETOR_EMPRESAS[setor] || []
}

function addEnc() {
  resposta.value.encaminhar.push({ setor: '', empresa: '' })
}
function removeEnc(i) {
  resposta.value.encaminhar.splice(i, 1)
}

async function abrirAnexo(key) {
  loadingAnexo.value = true
  try {
    const res = await api.upload.url(key)
    window.open(res.url, '_blank')
  } catch (e) {
    alert('Erro ao gerar link: ' + e.message)
  } finally {
    loadingAnexo.value = false
  }
}

function isImage(key) {
  const lower = key.toLowerCase()
  return lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.png') || lower.endsWith('.webp')
}

async function preloadAnexoUrls() {
  const keys = fca.value?.anexo_urls || []
  for (const key of keys) {
    if (isImage(key) && !anexoUrls.value[key]) {
      try {
        const res = await api.upload.url(key)
        anexoUrls.value[key] = res.url
      } catch { /* silencia */ }
    }
  }
}

async function encerrar() {
  errorEncerrar.value = ''
  subEncerrar.value = true
  try {
    await api.fcas.encerrar(fca.value.id)
    await loadFca()
  } catch (e) {
    errorEncerrar.value = e.message
  } finally {
    subEncerrar.value = false
  }
}

async function responder() {
  errorResp.value = ''
  if (resposta.value.problema_solucionado === null) {
    errorResp.value = 'Informe se o problema foi solucionado.'
    return
  }
  if (encaminhar.value && resposta.value.encaminhar.some(e => !e.setor || !e.empresa)) {
    errorResp.value = 'Preencha todos os campos de encaminhamento.'
    return
  }
  submitting.value = true
  try {
    await api.fcas.responder(fca.value.id, {
      ...resposta.value,
      encaminhar: encaminhar.value ? resposta.value.encaminhar : [],
    })
    // Recarrega o FCA
    await loadFca()
    // Limpa o formulário
    resposta.value = { problema_solucionado: null, devolutiva: '', encaminhar: [] }
    encaminhar.value = false
  } catch (e) {
    errorResp.value = e.message
  } finally {
    submitting.value = false
  }
}

async function loadFca() {
  try {
    fca.value = await api.fcas.get(route.params.id)
  } catch {
    fca.value = null
  }
}

onMounted(async () => {
  await loadFca()
  loading.value = false
  await preloadAnexoUrls()
})

function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', aguardando_devolutiva: 'Ag. devolutiva', encerrado: 'Encerrado' }[s] || s
}
function labelEtapaStatus(s) {
  return { pendente: 'Pendente', em_andamento: 'Em andamento', concluido: 'Concluído' }[s] || s
}
function statusEtapaBadge(s) {
  return { pendente: 'badge-aberto', em_andamento: 'badge-em_andamento', concluido: 'badge-encerrado' }[s] || 'badge-aberto'
}
function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR')
}
</script>

<style scoped>
.loading-text { color: #888; text-align: center; padding: 2rem; }
.section-title { font-size: .95rem; font-weight: 700; margin-bottom: 1rem; color: #374151; text-transform: uppercase; letter-spacing: .5px; }
.detail-label { font-size: .8rem; font-weight: 600; color: #6b7280; display: block; margin-bottom: .25rem; }

.detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem 1.25rem; }
.detail-item label { display: block; font-size: .75rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; margin-bottom: .15rem; }
.detail-item span { font-size: .9rem; color: #1a1a2e; }
.full-width { grid-column: 1 / -1; }
.detalhe-text { font-size: .9rem; color: #374151; line-height: 1.5; background: #f9fafb; padding: .6rem .75rem; border-radius: 6px; margin-top: .25rem; }

/* Timeline */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item { display: flex; gap: 1rem; padding: .75rem 0; position: relative; }
.timeline-item:not(:last-child)::before {
  content: ''; position: absolute; left: 7px; top: 28px; bottom: -8px; width: 2px;
  background: #e5e7eb;
}
.tl-marker {
  width: 16px; height: 16px; border-radius: 50%; border: 2px solid #d1d5db;
  background: #fff; flex-shrink: 0; margin-top: 2px;
}
.concluido .tl-marker { background: #059669; border-color: #059669; }
.em_andamento .tl-marker { background: #f59e0b; border-color: #f59e0b; }
.pendente .tl-marker { background: #fff; border-color: #93c5fd; }

.tl-content { flex: 1; }
.tl-header { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; margin-bottom: .35rem; }
.tl-index { font-size: .72rem; color: #9ca3af; margin-left: auto; }
.tl-body { font-size: .875rem; color: #374151; line-height: 1.55; }
.tl-body p { margin-bottom: .2rem; }
.tl-meta { color: #9ca3af; font-size: .78rem; margin-top: .3rem; }
.tl-pending { font-size: .85rem; color: #9ca3af; font-style: italic; }

/* Formulário de resposta */
.radio-group { display: flex; gap: 1.5rem; }
.radio-group label { display: flex; align-items: center; gap: .35rem; font-size: .9rem; cursor: pointer; }

.encaminhamentos { margin-top: .5rem; display: flex; flex-direction: column; gap: .5rem; }
.enc-row { display: flex; gap: .5rem; align-items: center; }
.enc-row select { flex: 1; padding: .4rem .65rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: .875rem; }

/* Fila futura */
.fila-lista { display: flex; flex-direction: column; gap: .5rem; }
.fila-item { display: flex; align-items: center; gap: .75rem; padding: .5rem .75rem; background: #f9fafb; border-radius: 7px; font-size: .875rem; }
.fila-index { background: #e5e7eb; border-radius: 4px; padding: .1rem .45rem; font-size: .75rem; font-weight: 600; color: #6b7280; }

.encerrar-box { border: 1px solid #a7f3d0; background: #f0fdf4; }
.encerrar-box p { font-size: .9rem; color: #065f46; }

/* ── Anexos grid ── */
.anexos-grid { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: .35rem; }
.anexo-item { text-decoration: none; display: block; }
.anexo-thumb {
  width: 90px; height: 90px; object-fit: cover; border-radius: 7px;
  border: 1px solid #e2e8f0; transition: opacity .15s;
}
.anexo-thumb:hover { opacity: .8; }
.anexo-doc {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: .3rem; width: 90px; height: 90px;
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 7px;
  font-size: .75rem; color: #475569; cursor: pointer; transition: background .15s;
}
.anexo-doc:hover { background: #e2e8f0; }
.anexo-doc-name { font-size: .65rem; word-break: break-all; text-align: center; padding: 0 .2rem; }

@media (max-width: 600px) {
  .detail-grid { grid-template-columns: 1fr 1fr; }
}
</style>
