<template>
  <div>
    <div class="page-header">
      <h1>FCAs</h1>
      <RouterLink v-if="canOpen" to="/fca/novo" class="btn btn-primary">+ Novo FCA</RouterLink>
    </div>

    <!-- Filtros -->
    <div class="card filters-bar">
      <select v-model="filters.status_filter" @change="load">
        <option value="">Todos os status</option>
        <option value="aberto">Aberto</option>
        <option value="em_andamento">Em andamento</option>
        <option value="aguardando_devolutiva">Ag. devolutiva</option>
        <option value="encerrado">Encerrado</option>
      </select>
      <select v-model="filters.area_causadora" @change="load">
        <option value="">Área causadora</option>
        <option v-for="s in SETORES_AREA" :key="s" :value="s">{{ s }}</option>
      </select>
      <input v-model.lazy="filters.data_inicio" type="date" placeholder="De" @change="load" />
      <input v-model.lazy="filters.data_fim" type="date" placeholder="Até" @change="load" />
      <button class="btn btn-secondary btn-sm" @click="clearFilters">Limpar</button>
    </div>

    <div v-if="loading" class="loading-text">Carregando...</div>
    <div v-else-if="!items.length" class="card empty-state">Nenhum FCA encontrado.</div>

    <table v-else class="fca-table card">
      <thead>
        <tr>
          <th>Código</th>
          <th>Causa</th>
          <th>Solicitante</th>
          <th>Área causadora</th>
          <th>Etapa atual</th>
          <th>Status</th>
          <th>Data abertura</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="fca in items" :key="fca.id">
          <td><strong>{{ fca.cod_fca }}</strong></td>
          <td>{{ fca.causa }}</td>
          <td>{{ fca.setor_solicitante }} · {{ fca.empresa_solicitante }}</td>
          <td>{{ fca.area_causadora }} · {{ fca.empresa_causadora }}</td>
          <td>
            <span v-if="fca.etapa_atual">{{ fca.etapa_atual.setor }} · {{ fca.etapa_atual.empresa }}</span>
            <span v-else class="text-muted">—</span>
          </td>
          <td><span :class="['badge', 'badge-' + fca.status]">{{ labelStatus(fca.status) }}</span></td>
          <td>{{ formatDate(fca.created_at) }}</td>
          <td><RouterLink :to="`/fca/${fca.id}`" class="btn btn-sm btn-outline">Ver</RouterLink></td>
        </tr>
      </tbody>
    </table>

    <!-- Paginação -->
    <div v-if="total > pageSize" class="pagination">
      <button class="btn btn-secondary btn-sm" :disabled="page === 1" @click="goPage(page - 1)">‹ Anterior</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-secondary btn-sm" :disabled="page >= totalPages" @click="goPage(page + 1)">Próxima ›</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, onActivated } from 'vue'
import { api } from '../api'

const user = inject('user')
const registerWsListener = inject('registerWsListener')
const SETORES_AREA = ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao', 'Comercial', 'Customer_Service']

const items    = ref([])
const total    = ref(0)
const page     = ref(1)
const pageSize = 20
const loading  = ref(true)
const filters  = ref({ status_filter: '', area_causadora: '', data_inicio: '', data_fim: '' })

const totalPages = computed(() => Math.ceil(total.value / pageSize))
const canOpen = computed(() => user.value && !['Producao'].includes(user.value.sector))

async function load() {
  loading.value = true
  try {
    const res = await api.fcas.list({ ...filters.value, page: page.value, page_size: pageSize })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  filters.value = { status_filter: '', area_causadora: '', data_inicio: '', data_fim: '' }
  page.value = 1
  load()
}

function goPage(p) {
  page.value = p
  load()
}

function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', aguardando_devolutiva: 'Ag. devolutiva', encerrado: 'Encerrado' }[s] || s
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('pt-BR')
}

onMounted(() => {
  load()
  // Registra callback no WS global do App.vue
  registerWsListener?.(load)
})

// Recarrega ao voltar para a view (ex: após criar um FCA na mesma aba)
onActivated(load)

onUnmounted(() => {
  // Remove o listener ao sair da view
  registerWsListener?.(null)
})
</script>

<style scoped>
.filters-bar { display: flex; gap: .6rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; padding: .75rem 1rem; }
.filters-bar select, .filters-bar input { padding: .4rem .65rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: .85rem; }

.fca-table { width: 100%; border-collapse: collapse; font-size: .875rem; padding: 0; }
.fca-table thead th { text-align: left; padding: .65rem 1rem; font-weight: 600; border-bottom: 2px solid #e5e7eb; color: #6b7280; font-size: .78rem; text-transform: uppercase; background: #f9fafb; }
.fca-table tbody td { padding: .6rem 1rem; border-bottom: 1px solid #f3f4f6; }
.fca-table tbody tr:last-child td { border-bottom: none; }
.fca-table tbody tr:hover td { background: #f9fafb; }

.loading-text { color: #888; text-align: center; padding: 2rem; }
.empty-state { color: #9ca3af; padding: 2rem; text-align: center; }
.text-muted { color: #9ca3af; }

.pagination { display: flex; align-items: center; gap: 1rem; justify-content: center; margin-top: 1rem; font-size: .875rem; }
</style>
