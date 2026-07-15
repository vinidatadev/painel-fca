<template>
  <div>
    <div class="page-header">
      <h1>Regras de SLA</h1>
      <button class="btn btn-primary" @click="abrirNovo">+ Nova Regra</button>
    </div>

    <div class="card info-box">
      <strong>Como funciona a hierarquia:</strong>
      <span>Setor + Empresa</span> <span class="arrow">›</span>
      <span>Empresa inteira</span> <span class="arrow">›</span>
      <span>Global (padrão)</span>
      <p>A regra mais específica sempre tem prioridade.</p>
    </div>

    <div v-if="loading" class="loading-text">Carregando...</div>

    <table v-else class="sla-table card">
      <thead>
        <tr><th>Escopo</th><th>Prazo</th><th>Equivalente</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in regras" :key="r.id" :class="{ inactive: !r.ativo }">
          <td><strong>{{ r.escopo }}</strong></td>
          <td>{{ r.valor }} {{ r.unidade }}{{ r.valor > 1 ? 's' : '' }}</td>
          <td class="text-muted">{{ formatMinutos(r.prazo_minutos) }}</td>
          <td>
            <span :class="['badge', r.ativo ? 'badge-encerrado' : 'badge-aguardando_devolutiva']">
              {{ r.ativo ? 'Ativa' : 'Inativa' }}
            </span>
          </td>
          <td class="actions">
            <button class="btn btn-sm btn-outline" @click="abrirEdicao(r)">Editar</button>
            <button class="btn btn-sm btn-danger" @click="remover(r)">Remover</button>
          </td>
        </tr>
        <tr v-if="!regras.length">
          <td colspan="5" class="empty-state">Nenhuma regra cadastrada. Sem regras, nenhum prazo é exibido.</td>
        </tr>
      </tbody>
    </table>

    <!-- Modal criar/editar -->
    <div v-if="showModal" class="modal-overlay" @click.self="fecharModal">
      <div class="modal-box">
        <h3>{{ editando ? 'Editar Regra' : 'Nova Regra de SLA' }}</h3>

        <form @submit.prevent="salvar">
          <div v-if="!editando">
            <div class="form-group">
              <label>Escopo</label>
              <select v-model="form.escopo">
                <option value="global">Global (padrão para tudo)</option>
                <option value="empresa">Por empresa</option>
                <option value="setor">Por setor + empresa</option>
              </select>
            </div>

            <div v-if="form.escopo !== 'global'" class="form-group">
              <label>Empresa *</label>
              <select v-model="form.empresa" required @change="form.setor = ''">
                <option value="">Selecione...</option>
                <option v-for="e in EMPRESAS" :key="e" :value="e">{{ e }}</option>
              </select>
            </div>

            <div v-if="form.escopo === 'setor'" class="form-group">
              <label>Setor *</label>
              <select v-model="form.setor" required :disabled="!form.empresa">
                <option value="">Selecione...</option>
                <option v-for="s in setoresDisponiveis" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </div>

          <div v-else class="escopo-label">
            <label>Escopo</label>
            <strong>{{ editando.escopo }}</strong>
          </div>

          <div class="prazo-row">
            <div class="form-group" style="flex:1">
              <label>Valor *</label>
              <input v-model.number="form.valor" type="number" min="1" required />
            </div>
            <div class="form-group" style="flex:1">
              <label>Unidade *</label>
              <select v-model="form.unidade" required>
                <option value="minuto">Minuto(s)</option>
                <option value="hora">Hora(s)</option>
                <option value="dia">Dia(s)</option>
              </select>
            </div>
          </div>

          <div v-if="form.valor && form.unidade" class="preview-prazo">
            ≈ {{ formatMinutos(calcMinutos(form.valor, form.unidade)) }}
          </div>

          <p v-if="errorModal" class="error-msg">{{ errorModal }}</p>

          <div style="display:flex;gap:.6rem;margin-top:1rem">
            <button class="btn btn-primary" type="submit" :disabled="salvando">
              {{ salvando ? 'Salvando...' : 'Salvar' }}
            </button>
            <button class="btn btn-secondary" type="button" @click="fecharModal">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const EMPRESAS = ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS', 'ACC']
const SETORES_POR_EMPRESA = {
  ACI_MATRIZ: ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  ACI_FILIAL: ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  SINOBRAS:   ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  ACC:        ['Comercial', 'Customer_Service'],
}
const UNIDADE_MIN = { minuto: 1, hora: 60, dia: 1440 }

const regras   = ref([])
const loading  = ref(true)
const showModal = ref(false)
const editando  = ref(null)
const salvando  = ref(false)
const errorModal = ref('')

const form = ref({ escopo: 'global', empresa: '', setor: '', valor: 1, unidade: 'hora' })

const setoresDisponiveis = computed(() => SETORES_POR_EMPRESA[form.value.empresa] || [])

function calcMinutos(valor, unidade) {
  return valor * (UNIDADE_MIN[unidade] || 60)
}

function formatMinutos(min) {
  if (min < 60) return `${min} min`
  if (min < 1440) return `${(min / 60).toFixed(1).replace('.0', '')} h`
  return `${(min / 1440).toFixed(1).replace('.0', '')} dia(s)`
}

async function load() {
  loading.value = true
  try { regras.value = await api.sla.list() }
  finally { loading.value = false }
}

function abrirNovo() {
  editando.value = null
  form.value = { escopo: 'global', empresa: '', setor: '', valor: 1, unidade: 'hora' }
  errorModal.value = ''
  showModal.value = true
}

function abrirEdicao(r) {
  editando.value = r
  form.value = { escopo: '', empresa: r.empresa || '', setor: r.setor || '', valor: r.valor, unidade: r.unidade }
  errorModal.value = ''
  showModal.value = true
}

function fecharModal() { showModal.value = false; editando.value = null }

async function salvar() {
  errorModal.value = ''
  salvando.value = true
  try {
    if (editando.value) {
      await api.sla.update(editando.value.id, { valor: form.value.valor, unidade: form.value.unidade })
    } else {
      const payload = { valor: form.value.valor, unidade: form.value.unidade }
      if (form.value.escopo !== 'global') payload.empresa = form.value.empresa || null
      if (form.value.escopo === 'setor')  payload.setor   = form.value.setor || null
      await api.sla.create(payload)
    }
    fecharModal()
    await load()
  } catch (e) {
    errorModal.value = e.message
  } finally {
    salvando.value = false
  }
}

async function remover(r) {
  if (!confirm(`Remover regra "${r.escopo}"?`)) return
  try { await api.sla.remove(r.id); await load() }
  catch (e) { alert(e.message) }
}

onMounted(load)
</script>

<style scoped>
.info-box {
  background: var(--color-info-bg); border: 1px solid var(--color-primary-300);
  margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-2);
  flex-wrap: wrap; font-size: var(--font-size-sm); color: var(--color-info-text);
}
.info-box p { width: 100%; margin-top: var(--space-1); color: var(--color-neutral-500); font-size: var(--font-size-xs); }
.arrow { color: var(--color-primary-300); font-size: 1rem; }

.sla-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); padding: 0; }
.sla-table thead th {
  text-align: left; padding: var(--space-2) var(--space-4); font-weight: var(--font-weight-semibold);
  border-bottom: 2px solid var(--color-neutral-200); color: var(--color-neutral-500);
  font-size: var(--font-size-xs); text-transform: uppercase; background: var(--color-neutral-50);
}
.sla-table tbody td { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.sla-table tbody tr.inactive td { opacity: .5; }
.sla-table tbody tr:hover td { background: var(--color-primary-50); }
.actions { display: flex; gap: var(--space-2); }
.text-muted { color: var(--color-neutral-400); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 500; padding: var(--space-4); }
.modal-box {
  background: #fff; border-radius: var(--radius-xl); padding: var(--space-6) var(--space-6);
  min-width: 400px; box-shadow: var(--shadow-lg); border: 1px solid var(--color-neutral-100);
}
.modal-box h3 { font-size: var(--font-size-base); font-weight: var(--font-weight-bold); margin-bottom: var(--space-5); color: var(--color-neutral-900); }

.prazo-row { display: flex; gap: var(--space-3); }
.preview-prazo {
  background: var(--color-success-bg); border: 1px solid #bbf7d0; border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3); font-size: var(--font-size-sm); color: var(--color-success-text);
  margin-top: calc(-1 * var(--space-1)); margin-bottom: var(--space-2);
}
.escopo-label { display: flex; flex-direction: column; gap: var(--space-1); margin-bottom: var(--space-3); font-size: var(--font-size-sm); }
.escopo-label label { font-size: var(--font-size-xs); color: var(--color-neutral-400); font-weight: var(--font-weight-semibold); text-transform: uppercase; }
</style>
