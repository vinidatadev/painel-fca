<template>
  <div>
    <!-- Page header com código + status -->
    <div v-if="!loading && fca" class="fca-page-header">
      <div class="fca-header-left">
        <div class="fca-code-row">
          <h1>{{ fca.cod_fca }}</h1>
          <span :class="['badge', 'badge-' + fca.status]">{{ labelStatus(fca.status) }}</span>
        </div>
        <span class="fca-meta">Aberto em {{ formatDate(fca.created_at) }} · por {{ fca.created_by?.name }}</span>
      </div>
      <RouterLink to="/fca" class="btn btn-secondary btn-sm">← Voltar</RouterLink>
    </div>
    <div v-else-if="!loading" class="page-header">
      <h1>Detalhe FCA</h1>
      <RouterLink to="/fca" class="btn btn-secondary btn-sm">← Voltar</RouterLink>
    </div>

    <div v-if="loading" class="card" style="padding:var(--space-8)">
      <div v-for="i in 3" :key="i" class="skeleton skeleton-text" style="margin-bottom:12px"></div>
    </div>
    <div v-else-if="!fca" class="card" style="color:var(--color-danger-text);text-align:center;padding:var(--space-8)">FCA não encontrado ou sem permissão.</div>

    <template v-else>
      <!-- Dados da Abertura -->
      <div class="card">
        <p class="section-title" style="margin-bottom:var(--space-4)">Dados da Abertura</p>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-label">Setor Solicitante</span><span class="detail-value">{{ fca.setor_solicitante }} · {{ fca.empresa_solicitante }}</span></div>
          <div class="detail-item"><span class="detail-label">Área Causadora</span><span class="detail-value">{{ fca.area_causadora }} · {{ fca.empresa_causadora }}</span></div>
          <div class="detail-item"><span class="detail-label">Causa</span><span class="detail-value">{{ fca.causa }}</span></div>
          <div class="detail-item"><span class="detail-label">Ação</span><span class="detail-value">{{ fca.acao }}</span></div>
          <div class="detail-item"><span class="detail-label">UF</span><span class="detail-value"><span class="uf-badge">{{ fca.uf }}</span></span></div>
          <div class="detail-item">
            <span class="detail-label">Remessa(s)</span>
            <span class="detail-value">{{ fca.remessas?.length ? fca.remessas.join(', ') : fca.numero_remessa || '—' }}</span>
          </div>
        </div>
        <div v-if="fca.detalhe" class="detalhe-obs">
          <span class="detail-label" style="display:block;margin-bottom:var(--space-2)">Detalhe / Observação</span>
          <p class="detalhe-text">{{ fca.detalhe }}</p>
        </div>
        <!-- Anexos -->
        <div v-if="fca.anexo_urls?.length" style="margin-top:var(--space-4)">
          <span class="detail-label" style="display:block;margin-bottom:var(--space-2)">Anexos</span>
          <div class="anexos-grid">
            <a v-for="key in fca.anexo_urls" :key="key" href="#" @click.prevent="abrirAnexo(key)" class="anexo-item">
              <img v-if="isImage(key)" :src="anexoUrls[key]" class="anexo-thumb" />
              <div v-else class="anexo-doc"><svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M12 2H6a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V8L12 2z" stroke="currentColor" stroke-width="1.5"/><path d="M12 2v6h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg><span>{{ key.split('/').pop() }}</span></div>
            </a>
          </div>
        </div>
        <div v-else-if="fca.anexo_url" style="margin-top:var(--space-3)">
          <button class="btn btn-outline btn-sm" @click="abrirAnexo(fca.anexo_url)" :disabled="loadingAnexo">📎 Visualizar Anexo</button>
        </div>
      </div>

      <!-- Timeline -->
      <div class="card" style="margin-top:var(--space-4)">
        <p class="section-title" style="margin-bottom:var(--space-5)">Histórico de Etapas</p>
        <div class="timeline">
          <div v-for="(etapa, idx) in fca.etapas" :key="etapa.id" :class="['tl-item', etapa.status]">
            <div class="tl-left">
              <div :class="['tl-marker', 'tl-marker-' + etapa.status]"></div>
              <div v-if="idx < fca.etapas.length - 1" :class="['tl-line', 'tl-line-' + etapa.status]"></div>
            </div>
            <div class="tl-card">
              <div class="tl-card-header">
                <span class="tl-setor">{{ etapa.setor }} · {{ etapa.empresa }}</span>
                <span :class="['badge', statusEtapaBadge(etapa.status)]">{{ labelEtapaStatus(etapa.status) }}</span>
                <SlaBadge v-if="etapa.status !== 'concluido' && etapa.sla_deadline" :deadline="etapa.sla_deadline" />
                <span class="tl-idx">#{{ etapa.order_index }}</span>
              </div>
              <div v-if="etapa.status === 'concluido'" class="tl-card-body">
                <div class="tl-result" :class="etapa.problema_solucionado ? 'result-ok' : 'result-no'">
                  <svg v-if="etapa.problema_solucionado" width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7l4 4 6-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                  <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                  Problema {{ etapa.problema_solucionado ? 'solucionado' : 'não solucionado' }}
                </div>
                <p class="tl-devolutiva">{{ etapa.devolutiva }}</p>
                <p class="tl-meta-resp">Respondido por {{ etapa.respondido_por?.name || '—' }} em {{ formatDate(etapa.concluded_at) }}</p>
              </div>
              <div v-else class="tl-pending-text">
                <span v-if="etapa.status === 'pendente'">Aguardando tratamento...</span>
                <span v-else>Em andamento...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Formulário de resposta -->
      <div v-if="minhaVez" class="card resposta-card" style="margin-top:var(--space-4)">
        <div class="resposta-header">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M15 3L3 9l5 2 2 5 5-13z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          <span>Responder Etapa — <strong>é sua vez</strong></span>
        </div>
        <form @submit.prevent="responder" style="padding:var(--space-4)">
          <div class="form-group">
            <label>Problema Solucionado? <span class="req">*</span></label>
            <div class="radio-group">
              <label class="radio-opt"><input type="radio" v-model="resposta.problema_solucionado" :value="true" required /> Sim</label>
              <label class="radio-opt"><input type="radio" v-model="resposta.problema_solucionado" :value="false" /> Não</label>
            </div>
          </div>
          <div class="form-group">
            <label>Devolutiva da Tratativa <span class="req">*</span></label>
            <textarea v-model="resposta.devolutiva" required rows="4" placeholder="Descreva como foi tratado o problema..."></textarea>
          </div>
          <div class="form-group">
            <label>Encaminhar para outro setor?</label>
            <div class="radio-group">
              <label class="radio-opt"><input type="radio" v-model="encaminhar" :value="false" /> Não</label>
              <label class="radio-opt"><input type="radio" v-model="encaminhar" :value="true" /> Sim</label>
            </div>
          </div>
          <div v-if="encaminhar" class="enc-list">
            <div v-for="(enc, i) in resposta.encaminhar" :key="i" class="enc-row">
              <select v-model="enc.setor" required @change="enc.empresa = ''">
                <option value="">Setor...</option>
                <option v-for="s in SETORES_ENC" :key="s" :value="s">{{ s }}</option>
              </select>
              <select v-model="enc.empresa" required :disabled="!enc.setor">
                <option value="">Empresa...</option>
                <option v-for="e in empresasParaSetor(enc.setor)" :key="e" :value="e">{{ e }}</option>
              </select>
              <button type="button" class="btn btn-secondary btn-sm" @click="removeEnc(i)">✕</button>
            </div>
            <button type="button" class="btn btn-ghost btn-sm" @click="addEnc">+ Adicionar setor</button>
          </div>
          <p v-if="errorResp" class="error-msg">{{ errorResp }}</p>
          <button class="btn btn-primary" type="submit" :disabled="submitting" style="margin-top:var(--space-4)">
            {{ submitting ? 'Enviando...' : 'Enviar Resposta' }}
          </button>
        </form>
      </div>

      <!-- Encerrar -->
      <div v-if="podeEncerrar" class="card encerrar-card" style="margin-top:var(--space-4)">
        <div class="encerrar-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M5 12l5 5 9-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <p class="encerrar-title">Devolutiva Recebida</p>
          <p class="encerrar-sub">Todas as etapas foram concluídas. Confirme o recebimento para encerrar o FCA.</p>
        </div>
        <button class="btn btn-success" @click="encerrar" :disabled="subEncerrar">
          {{ subEncerrar ? 'Encerrando...' : '✓ Confirmar e Encerrar' }}
        </button>
        <p v-if="errorEncerrar" class="error-msg">{{ errorEncerrar }}</p>
      </div>

      <!-- Admin: Cancelar -->
      <div v-if="user?.role === 'admin' && fca.status !== 'cancelado'" class="card admin-danger-card" style="margin-top:var(--space-4)">
        <div class="admin-card-header">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 2L1 16h16L9 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M9 8v4M9 13.5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <h3>Cancelar FCA</h3>
        </div>
        <p class="admin-card-desc">O FCA ficará invisível para usuários não-admin.</p>
        <button class="btn btn-danger btn-sm" @click="showCancelar = !showCancelar">✕ Cancelar FCA</button>
        <div v-if="showCancelar" class="admin-form">
          <textarea v-model="cancelarMotivo" placeholder="Motivo do cancelamento (obrigatório)..." rows="2"></textarea>
          <button class="btn btn-danger btn-sm" :disabled="subCancelar || !cancelarMotivo.trim()" @click="cancelar">
            {{ subCancelar ? 'Cancelando...' : 'Confirmar Cancelamento' }}
          </button>
          <p v-if="errorCancelar" class="error-msg">{{ errorCancelar }}</p>
        </div>
      </div>

      <!-- Admin: Ações -->
      <div v-if="user?.role === 'admin' && (fca.status === 'encerrado' || etapaAtiva)" class="card" style="margin-top:var(--space-4)">
        <h3 class="section-title" style="margin-bottom:var(--space-4)">Ações Administrativas</h3>
        <!-- Reabrir -->
        <div v-if="fca.status === 'encerrado'">
          <button class="btn btn-warning btn-sm" @click="showReabrir = !showReabrir">↩ Reabrir FCA</button>
          <div v-if="showReabrir" class="admin-form">
            <div class="enc-row" style="margin-top:var(--space-3)">
              <select v-model="reabrirBody.setor" @change="reabrirBody.empresa = ''"><option value="">Setor destino...</option><option v-for="s in SETORES_ENC" :key="s" :value="s">{{ s }}</option></select>
              <select v-model="reabrirBody.empresa" :disabled="!reabrirBody.setor"><option value="">Empresa...</option><option v-for="e in empresasParaSetor(reabrirBody.setor)" :key="e" :value="e">{{ e }}</option></select>
              <button class="btn btn-primary btn-sm" :disabled="subReabrir || !reabrirBody.setor || !reabrirBody.empresa" @click="reabrir">{{ subReabrir ? 'Aguarde...' : 'Confirmar' }}</button>
            </div>
            <p v-if="errorReabrir" class="error-msg">{{ errorReabrir }}</p>
          </div>
        </div>
        <!-- Reatribuir -->
        <div v-if="etapaAtiva" :style="fca.status === 'encerrado' ? 'margin-top:var(--space-3)' : ''">
          <button class="btn btn-warning btn-sm" @click="showReatribuir = !showReatribuir">⇄ Reatribuir Etapa</button>
          <div v-if="showReatribuir" class="admin-form">
            <div class="enc-row" style="margin-top:var(--space-3)">
              <select v-model="reatribuirBody.setor" @change="reatribuirBody.empresa = ''"><option value="">Setor...</option><option v-for="s in SETORES_ENC" :key="s" :value="s">{{ s }}</option></select>
              <select v-model="reatribuirBody.empresa" :disabled="!reatribuirBody.setor"><option value="">Empresa...</option><option v-for="e in empresasParaSetor(reatribuirBody.setor)" :key="e" :value="e">{{ e }}</option></select>
            </div>
            <div class="form-group" style="margin-top:var(--space-2)">
              <textarea v-model="reatribuirBody.justificativa" placeholder="Justificativa obrigatória..." rows="2"></textarea>
            </div>
            <button class="btn btn-primary btn-sm" :disabled="subReatribuir || !reatribuirBody.setor || !reatribuirBody.empresa || !reatribuirBody.justificativa.trim()" @click="reatribuir">{{ subReatribuir ? 'Aguarde...' : 'Confirmar Reatribuição' }}</button>
            <p v-if="errorReatribuir" class="error-msg">{{ errorReatribuir }}</p>
          </div>
        </div>
      </div>

      <!-- Comentários internos -->
      <div class="card" style="margin-top:var(--space-4)">
        <p class="section-title" style="margin-bottom:var(--space-4)">Comentários Internos</p>
        <div class="comentarios-thread">
          <p v-if="!comentarios.length" class="empty-state">Nenhum comentário ainda.</p>
          <div v-for="c in comentarios" :key="c.id" class="comentario-item">
            <div class="com-avatar">{{ c.autor.name.charAt(0).toUpperCase() }}</div>
            <div class="com-body">
              <div class="com-header">
                <span class="com-author">{{ c.autor.name }}</span>
                <span class="com-date">{{ formatDate(c.created_at) }}</span>
              </div>
              <p class="com-text">{{ c.texto }}</p>
            </div>
          </div>
        </div>
        <form @submit.prevent="adicionarComentario" class="com-form">
          <textarea v-model="novoComentario" rows="2" placeholder="Adicionar comentário interno..." required></textarea>
          <button class="btn btn-secondary btn-sm" type="submit" :disabled="subComentario || !novoComentario.trim()">{{ subComentario ? 'Enviando...' : 'Comentar' }}</button>
        </form>
        <p v-if="errorComentario" class="error-msg">{{ errorComentario }}</p>
      </div>

      <!-- Auditoria admin -->
      <div v-if="user?.role === 'admin'" class="card" style="margin-top:var(--space-4)">
        <button class="audit-toggle" @click="toggleAudit">
          <span style="display:flex;align-items:center;gap:var(--space-2)">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.3"/><path d="M7 4v3l2 2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
            Histórico de Auditoria
          </span>
          <span>{{ showAudit ? '▲' : '▼' }}</span>
        </button>
        <div v-if="showAudit" class="audit-list">
          <div v-if="loadingAudit" class="skeleton skeleton-text" style="margin:8px 0"></div>
          <p v-else-if="!auditLogs.length" class="empty-state">Sem registros.</p>
          <div v-else v-for="log in auditLogs" :key="log.id" class="audit-item">
            <span class="audit-acao">{{ log.acao }}</span>
            <span class="audit-user">{{ log.usuario?.name || 'Sistema' }}</span>
            <span class="audit-detalhe">{{ log.detalhe || '' }}</span>
            <span class="audit-date">{{ formatDate(log.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Fila futura -->
      <div v-if="filaFutura.length" class="card" style="margin-top:var(--space-4)">
        <p class="section-title" style="margin-bottom:var(--space-3)">Próximos na Fila</p>
        <div class="fila-lista">
          <div v-for="e in filaFutura" :key="e.id" class="fila-item">
            <span class="fila-idx">#{{ e.order_index }}</span>
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
const registerWsListener = inject('registerWsListener')

const fca           = ref(null)
const loading       = ref(true)
const loadingAnexo  = ref(false)
const submitting    = ref(false)
const errorResp     = ref('')
const encaminhar    = ref(false)
const anexoUrls     = ref({})

const resposta = ref({ problema_solucionado: null, devolutiva: '', encaminhar: [] })
const subEncerrar    = ref(false); const errorEncerrar  = ref('')
const comentarios    = ref([]); const novoComentario = ref(''); const subComentario = ref(false); const errorComentario = ref('')
const showReabrir    = ref(false); const reabrirBody = ref({ setor: '', empresa: '' }); const subReabrir = ref(false); const errorReabrir = ref('')
const showReatribuir = ref(false); const reatribuirBody = ref({ setor: '', empresa: '', justificativa: '' }); const subReatribuir = ref(false); const errorReatribuir = ref('')
const showAudit      = ref(false); const auditLogs = ref([]); const loadingAudit = ref(false)
const showCancelar   = ref(false); const cancelarMotivo = ref(''); const subCancelar = ref(false); const errorCancelar = ref('')

const SETOR_EMPRESAS = {
  ACL:['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'], PCP:['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'],
  Qualidade:['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'], MEP:['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'],
  Expedicao:['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'], Producao:['ACI_MATRIZ','ACI_FILIAL','SINOBRAS'],
  Comercial:['ACC'], Customer_Service:['ACC'],
}
const SETORES_ENC = Object.keys(SETOR_EMPRESAS)
const empresasParaSetor = (s) => SETOR_EMPRESAS[s] || []

const etapaAtiva = computed(() => {
  if (!fca.value) return null
  return fca.value.etapas.filter(e => e.status === 'pendente' || e.status === 'em_andamento').sort((a,b) => a.order_index - b.order_index)[0] || null
})
const minhaVez = computed(() => {
  if (!etapaAtiva.value || !user.value) return false
  return etapaAtiva.value.setor === user.value.sector && etapaAtiva.value.empresa === user.value.company
})
const podeEncerrar = computed(() => {
  if (!fca.value || !user.value) return false
  if (fca.value.status !== 'aguardando_devolutiva') return false
  if (user.value.role === 'admin') return true
  return fca.value.setor_solicitante === user.value.sector && fca.value.empresa_solicitante === user.value.company
})
const filaFutura = computed(() => {
  if (!fca.value) return []
  const atualIdx = etapaAtiva.value?.order_index || 0
  return fca.value.etapas.filter(e => e.status === 'pendente' && e.order_index > atualIdx).sort((a,b) => a.order_index - b.order_index)
})

function addEnc() { resposta.value.encaminhar.push({ setor: '', empresa: '' }) }
function removeEnc(i) { resposta.value.encaminhar.splice(i, 1) }

async function abrirAnexo(key) {
  loadingAnexo.value = true
  try { const res = await api.upload.url(key); window.open(res.url, '_blank') }
  catch (e) { alert('Erro: ' + e.message) } finally { loadingAnexo.value = false }
}
function isImage(key) { const l = key.toLowerCase(); return l.endsWith('.jpg')||l.endsWith('.jpeg')||l.endsWith('.png')||l.endsWith('.webp') }
async function preloadAnexoUrls() {
  for (const key of (fca.value?.anexo_urls || [])) {
    if (isImage(key) && !anexoUrls.value[key]) {
      try { const res = await api.upload.url(key); anexoUrls.value[key] = res.url } catch { /* silencia */ }
    }
  }
}
async function loadFca() {
  try { fca.value = await api.fcas.get(route.params.id) } catch { fca.value = null }
}
async function loadComentarios() {
  if (!fca.value) return
  try { comentarios.value = await api.fcas.comentarios.list(fca.value.id) } catch { /* silencia */ }
}
async function adicionarComentario() {
  errorComentario.value = ''; subComentario.value = true
  try { await api.fcas.comentarios.create(fca.value.id, novoComentario.value.trim()); novoComentario.value = ''; await loadComentarios() }
  catch (e) { errorComentario.value = e.message } finally { subComentario.value = false }
}
async function responder() {
  errorResp.value = ''
  if (resposta.value.problema_solucionado === null) { errorResp.value = 'Informe se o problema foi solucionado.'; return }
  if (encaminhar.value && resposta.value.encaminhar.some(e => !e.setor || !e.empresa)) { errorResp.value = 'Preencha os campos de encaminhamento.'; return }
  submitting.value = true
  try {
    await api.fcas.responder(fca.value.id, { ...resposta.value, encaminhar: encaminhar.value ? resposta.value.encaminhar : [] })
    await loadFca()
    resposta.value = { problema_solucionado: null, devolutiva: '', encaminhar: [] }; encaminhar.value = false
  } catch (e) { errorResp.value = e.message } finally { submitting.value = false }
}
async function encerrar() {
  errorEncerrar.value = ''; subEncerrar.value = true
  try { await api.fcas.encerrar(fca.value.id); await loadFca() }
  catch (e) { errorEncerrar.value = e.message } finally { subEncerrar.value = false }
}
async function reabrir() {
  errorReabrir.value = ''; subReabrir.value = true
  try { await api.fcas.reabrir(fca.value.id, reabrirBody.value.setor, reabrirBody.value.empresa); showReabrir.value = false; reabrirBody.value = { setor: '', empresa: '' }; await loadFca() }
  catch (e) { errorReabrir.value = e.message } finally { subReabrir.value = false }
}
async function reatribuir() {
  errorReatribuir.value = ''; subReatribuir.value = true
  try { await api.fcas.reatribuir(fca.value.id, reatribuirBody.value.setor, reatribuirBody.value.empresa, reatribuirBody.value.justificativa); showReatribuir.value = false; reatribuirBody.value = { setor: '', empresa: '', justificativa: '' }; await loadFca() }
  catch (e) { errorReatribuir.value = e.message } finally { subReatribuir.value = false }
}
async function cancelar() {
  errorCancelar.value = ''; subCancelar.value = true
  try { await api.fcas.cancelar(fca.value.id, cancelarMotivo.value.trim()); showCancelar.value = false; cancelarMotivo.value = ''; await loadFca() }
  catch (e) { errorCancelar.value = e.message } finally { subCancelar.value = false }
}
async function toggleAudit() {
  showAudit.value = !showAudit.value
  if (showAudit.value && !auditLogs.value.length) {
    loadingAudit.value = true
    try { auditLogs.value = await api.fcas.audit(fca.value.id) } catch { } finally { loadingAudit.value = false }
  }
}
async function _onWsUpdate() { await loadFca(); await loadComentarios() }

onMounted(async () => {
  await loadFca(); loading.value = false
  await preloadAnexoUrls(); await loadComentarios()
  registerWsListener?.(_onWsUpdate)
})

function labelStatus(s) { return { aberto:'Aberto', em_andamento:'Em andamento', aguardando_devolutiva:'Ag. devolutiva', encerrado:'Encerrado' }[s] || s }
function labelEtapaStatus(s) { return { pendente:'Pendente', em_andamento:'Em andamento', concluido:'Concluído' }[s] || s }
function statusEtapaBadge(s) { return { pendente:'badge-aberto', em_andamento:'badge-em_andamento', concluido:'badge-encerrado' }[s] || 'badge-aberto' }
function formatDate(iso) { if (!iso) return '—'; return new Date(iso).toLocaleString('pt-BR') }
</script>

<style scoped>
/* Page header especial */
.fca-page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--space-6); gap: var(--space-4); }
.fca-code-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-1); }
.fca-code-row h1 { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); }
.fca-meta { font-size: var(--font-size-sm); color: var(--color-neutral-500); }

/* Detail grid */
.detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-4) var(--space-6); margin-bottom: var(--space-2); }
.detail-item { display: flex; flex-direction: column; gap: 3px; }
.detail-label { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-neutral-400); text-transform: uppercase; letter-spacing: .05em; }
.detail-value { font-size: var(--font-size-sm); color: var(--color-neutral-900); }
.uf-badge { display: inline-block; padding: 2px var(--space-2); background: var(--color-neutral-100); border-radius: var(--radius-sm); font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); }
.detalhe-obs { margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--color-neutral-100); }
.detalhe-text { font-size: var(--font-size-sm); color: var(--color-neutral-700); line-height: 1.6; background: var(--color-neutral-50); padding: var(--space-3); border-radius: var(--radius-md); }

/* Anexos */
.anexos-grid { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-2); }
.anexo-item { text-decoration: none; }
.anexo-thumb { width: 88px; height: 88px; object-fit: cover; border-radius: var(--radius-md); border: 1px solid var(--color-neutral-200); transition: opacity var(--transition-fast); cursor: pointer; }
.anexo-thumb:hover { opacity: .8; }
.anexo-doc { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-1); width: 88px; height: 88px; background: var(--color-neutral-100); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); font-size: var(--font-size-xs); color: var(--color-neutral-500); cursor: pointer; text-align: center; padding: var(--space-1); }
.anexo-doc span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80px; }

/* Timeline */
.timeline { display: flex; flex-direction: column; }
.tl-item { display: flex; gap: var(--space-4); padding-bottom: var(--space-2); }
.tl-left { display: flex; flex-direction: column; align-items: center; width: 16px; flex-shrink: 0; padding-top: 3px; }
.tl-marker { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }
.tl-marker-concluido    { background: var(--color-success); box-shadow: 0 0 0 3px var(--color-success-bg); }
.tl-marker-em_andamento { background: var(--color-warning); box-shadow: 0 0 0 3px var(--color-warning-bg); }
.tl-marker-pendente     { background: var(--color-neutral-300); box-shadow: 0 0 0 3px var(--color-neutral-100); }
.tl-line { flex: 1; width: 2px; margin-top: 4px; border-radius: 1px; min-height: 24px; }
.tl-line-concluido    { background: var(--color-success); }
.tl-line-em_andamento { background: var(--color-warning); }
.tl-line-pendente     { background: var(--color-neutral-200); }
.tl-card { flex: 1; background: #fff; border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); margin-bottom: var(--space-3); box-shadow: var(--shadow-sm); }
.tl-item.concluido .tl-card { border-color: var(--color-success-bg); }
.tl-item.em_andamento .tl-card { border-color: var(--color-warning-bg); border-left: 3px solid var(--color-warning); }
.tl-card-header { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.tl-setor { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-neutral-800); }
.tl-idx { font-size: var(--font-size-xs); color: var(--color-neutral-400); margin-left: auto; }
.tl-card-body { margin-top: var(--space-3); }
.tl-result { display: inline-flex; align-items: center; gap: var(--space-1); font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); padding: 3px var(--space-2); border-radius: var(--radius-full); margin-bottom: var(--space-2); }
.result-ok  { background: var(--color-success-bg); color: var(--color-success-text); }
.result-no  { background: var(--color-danger-bg);  color: var(--color-danger-text); }
.tl-devolutiva { font-size: var(--font-size-sm); color: var(--color-neutral-700); line-height: 1.5; margin-bottom: var(--space-2); }
.tl-meta-resp { font-size: var(--font-size-xs); color: var(--color-neutral-400); }
.tl-pending-text { font-size: var(--font-size-sm); color: var(--color-neutral-400); font-style: italic; margin-top: var(--space-2); }

/* Resposta card */
.resposta-card { border: 1px solid var(--color-primary-300); border-left: 4px solid var(--color-primary-500); padding: 0; overflow: hidden; }
.resposta-header {
  display: flex; align-items: center; gap: var(--space-3);
  background: var(--color-primary-50); padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-primary-100);
  font-size: var(--font-size-sm); color: var(--color-primary-700);
}
.radio-group { display: flex; gap: var(--space-5); margin-top: var(--space-1); }
.radio-opt { display: flex; align-items: center; gap: var(--space-2); font-size: var(--font-size-sm); cursor: pointer; }
.enc-list { display: flex; flex-direction: column; gap: var(--space-2); margin-bottom: var(--space-3); }
.enc-row { display: flex; gap: var(--space-2); align-items: center; }
.enc-row select { flex: 1; padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-300); border-radius: var(--radius-md); font-size: var(--font-size-sm); font-family: var(--font-family-base); outline: none; }
.enc-row select:focus { border-color: var(--color-primary-500); }

/* Encerrar */
.encerrar-card {
  display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap;
  border: 1px solid var(--color-success-bg); background: #f0fdf4;
}
.encerrar-icon { width: 40px; height: 40px; background: var(--color-success-bg); color: var(--color-success); border-radius: var(--radius-full); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.encerrar-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-success-text); }
.encerrar-sub { font-size: var(--font-size-sm); color: var(--color-success-text); opacity: .8; }

/* Admin danger card */
.admin-danger-card { border: 1px solid var(--color-danger-bg); background: #fff5f5; }
.admin-card-header { display: flex; align-items: center; gap: var(--space-2); color: var(--color-danger-text); margin-bottom: var(--space-2); }
.admin-card-header h3 { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); margin: 0; color: var(--color-danger-text); }
.admin-card-desc { font-size: var(--font-size-xs); color: var(--color-neutral-500); margin-bottom: var(--space-3); }
.admin-form { margin-top: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2); }
.admin-form textarea { width: 100%; padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-300); border-radius: var(--radius-md); font-size: var(--font-size-sm); font-family: var(--font-family-base); outline: none; resize: vertical; }
.admin-form textarea:focus { border-color: var(--color-primary-500); }

/* Comentários */
.comentarios-thread { display: flex; flex-direction: column; gap: var(--space-3); margin-bottom: var(--space-4); }
.comentario-item { display: flex; gap: var(--space-3); }
.com-avatar { width: 32px; height: 32px; background: var(--color-primary-100); color: var(--color-primary-700); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); flex-shrink: 0; }
.com-body { flex: 1; background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: var(--space-3); }
.com-header { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-1); }
.com-author { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-neutral-800); }
.com-date { font-size: var(--font-size-xs); color: var(--color-neutral-400); margin-left: auto; }
.com-text { font-size: var(--font-size-sm); color: var(--color-neutral-700); line-height: 1.5; margin: 0; }
.com-form { display: flex; flex-direction: column; gap: var(--space-2); }
.com-form textarea { width: 100%; padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200); border-radius: var(--radius-md); font-size: var(--font-size-sm); font-family: var(--font-family-base); resize: vertical; outline: none; transition: border-color var(--transition-fast); }
.com-form textarea:focus { border-color: var(--color-primary-500); }
.com-form button { align-self: flex-end; }

/* Auditoria */
.audit-toggle { background: none; border: none; font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-neutral-700); cursor: pointer; display: flex; align-items: center; justify-content: space-between; width: 100%; padding: var(--space-1) 0; }
.audit-list { margin-top: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2); }
.audit-item { display: grid; grid-template-columns: 150px 140px 1fr auto; gap: var(--space-3); font-size: var(--font-size-xs); padding: var(--space-2) var(--space-3); background: var(--color-neutral-50); border-radius: var(--radius-sm); }
.audit-acao { font-weight: var(--font-weight-semibold); color: var(--color-primary-700); }
.audit-user { color: var(--color-neutral-500); }
.audit-detalhe { color: var(--color-neutral-600); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.audit-date { color: var(--color-neutral-400); white-space: nowrap; }

/* Fila futura */
.fila-lista { display: flex; flex-direction: column; gap: var(--space-2); }
.fila-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); background: var(--color-neutral-50); border-radius: var(--radius-md); font-size: var(--font-size-sm); }
.fila-idx { background: var(--color-neutral-200); border-radius: var(--radius-sm); padding: 2px var(--space-2); font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-neutral-600); }

.req { color: var(--color-danger); }

@media (max-width: 768px) {
  .detail-grid { grid-template-columns: 1fr 1fr; }
  .audit-item { grid-template-columns: 1fr 1fr; }
  .enc-row { flex-wrap: wrap; }
}
@media (max-width: 480px) {
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
