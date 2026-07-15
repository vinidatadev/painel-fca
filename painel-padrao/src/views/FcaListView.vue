<template>
  <div>
    <div class="page-header">
      <h1>FCAs</h1>
      <RouterLink v-if="canOpen" to="/fca/novo" class="btn btn-primary">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Novo FCA
      </RouterLink>
    </div>

    <!-- Filtros -->
    <div class="card filters-panel">
      <div class="filters-row">
        <div class="filter-icon">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 3h12v1.5L9 9v5l-2-1.5V9L2 4.5V3z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
          Filtros
        </div>
        <div class="search-wrap">
          <svg class="search-icon" width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.4"/><path d="M10 10l2.5 2.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
          <input v-model="filters.q" type="text" placeholder="Buscar por código, causa..." class="input-search" />
        </div>
        <select v-model="filters.status_filter" @change="load" class="filter-select">
          <option value="">Todos os status</option>
          <option value="aberto">Aberto</option>
          <option value="em_andamento">Em andamento</option>
          <option value="aguardando_devolutiva">Ag. devolutiva</option>
          <option value="encerrado">Encerrado</option>
          <option v-if="user?.role === 'admin'" value="cancelado">Cancelado</option>
        </select>
        <select v-model="filters.area_causadora" @change="load" class="filter-select">
          <option value="">Área causadora</option>
          <option v-for="s in SETORES_AREA" :key="s" :value="s">{{ s }}</option>
        </select>
        <div class="date-range">
          <input v-model.lazy="filters.data_inicio" type="date" @change="load" class="filter-date" />
          <span class="date-sep">—</span>
          <input v-model.lazy="filters.data_fim" type="date" @change="load" class="filter-date" />
        </div>
        <div class="filters-actions">
          <button class="btn btn-secondary btn-sm" @click="clearFilters">Limpar</button>
          <button class="btn btn-secondary btn-sm" :disabled="exporting" @click="exportar('xlsx')">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1v7M3 5l3 3 3-3M1 10h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Excel
          </button>
          <button class="btn btn-secondary btn-sm" :disabled="exporting" @click="exportar('csv')">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1v7M3 5l3 3 3-3M1 10h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            CSV
          </button>
        </div>
      </div>

      <!-- Chips de filtros ativos -->
      <div v-if="hasActiveFilters" class="filter-chips">
        <span v-if="filters.q" class="filter-chip">
          Busca: "{{ filters.q }}"
          <button @click="filters.q = ''; load()">×</button>
        </span>
        <span v-if="filters.status_filter" class="filter-chip">
          Status: {{ labelStatus(filters.status_filter) }}
          <button @click="filters.status_filter = ''; load()">×</button>
        </span>
        <span v-if="filters.area_causadora" class="filter-chip">
          Área: {{ filters.area_causadora }}
          <button @click="filters.area_causadora = ''; load()">×</button>
        </span>
        <span v-if="filters.data_inicio" class="filter-chip">
          De: {{ filters.data_inicio }}
          <button @click="filters.data_inicio = ''; load()">×</button>
        </span>
        <span v-if="filters.data_fim" class="filter-chip">
          Até: {{ filters.data_fim }}
          <button @click="filters.data_fim = ''; load()">×</button>
        </span>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="card" style="margin-top:var(--space-4);padding:0;overflow:hidden">
      <div class="skeleton-table-header"></div>
      <div v-for="i in 5" :key="i" class="skeleton-table-row">
        <div class="skeleton skeleton-text" style="width:90px"></div>
        <div class="skeleton skeleton-text" style="width:180px"></div>
        <div class="skeleton skeleton-text" style="width:140px"></div>
        <div class="skeleton skeleton-text" style="width:140px"></div>
        <div class="skeleton skeleton-text" style="width:90px"></div>
        <div class="skeleton skeleton-text" style="width:70px"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!items.length" class="card empty-card">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none"><rect x="10" y="8" width="36" height="42" rx="4" stroke="var(--color-neutral-300)" stroke-width="2"/><path d="M18 20h20M18 28h14M18 36h10" stroke="var(--color-neutral-300)" stroke-width="2" stroke-linecap="round"/><circle cx="38" cy="38" r="8" stroke="var(--color-neutral-300)" stroke-width="2"/><path d="M44 44l4 4" stroke="var(--color-neutral-300)" stroke-width="2" stroke-linecap="round"/></svg>
      <p class="empty-title">Nenhum FCA encontrado.</p>
      <p class="empty-sub">Tente ajustar os filtros ou crie um novo FCA.</p>
      <RouterLink v-if="canOpen" to="/fca/novo" class="btn btn-primary btn-sm" style="margin-top:var(--space-3)">+ Novo FCA</RouterLink>
    </div>

    <!-- Tabela -->
    <div v-else class="card table-card">
      <div class="table-wrap">
        <table class="fca-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Causa</th>
              <th>Solicitante</th>
              <th>Área causadora</th>
              <th>Etapa atual</th>
              <th>Status</th>
              <th>Abertura</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(fca, idx) in items" :key="fca.id" :style="`animation-delay:${idx * 30}ms`" class="table-row">
              <td><span class="code-text">{{ fca.cod_fca }}</span></td>
              <td class="causa-cell">{{ fca.causa }}</td>
              <td class="muted-cell">{{ fca.setor_solicitante }} · {{ fca.empresa_solicitante }}</td>
              <td class="muted-cell">{{ fca.area_causadora }} · {{ fca.empresa_causadora }}</td>
              <td>
                <span v-if="fca.etapa_atual" class="etapa-text">{{ fca.etapa_atual.setor }} · {{ fca.etapa_atual.empresa }}</span>
                <span v-else class="dash-text">—</span>
              </td>
              <td><span :class="['badge', 'badge-' + fca.status]">{{ labelStatus(fca.status) }}</span></td>
              <td class="date-cell">{{ formatDate(fca.created_at) }}</td>
              <td>
                <RouterLink :to="`/fca/${fca.id}`" class="btn btn-outline btn-sm btn-ver">Ver</RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Paginação -->
    <div v-if="total > pageSize" class="pagination">
      <button class="btn btn-secondary btn-sm" :disabled="page === 1" @click="goPage(page - 1)">‹ Anterior</button>
      <div class="page-numbers">
        <button
          v-for="p in pageNumbers"
          :key="p"
          :class="['btn btn-sm', p === page ? 'btn-primary' : 'btn-secondary']"
          @click="goPage(p)"
        >{{ p }}</button>
      </div>
      <button class="btn btn-secondary btn-sm" :disabled="page >= totalPages" @click="goPage(page + 1)">Próxima ›</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, inject, onMounted, onUnmounted, onActivated } from 'vue'
import { api } from '../api'

const user = inject('user')
const registerWsListener = inject('registerWsListener')
const SETORES_AREA = ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao', 'Comercial', 'Customer_Service']

const items    = ref([])
const total    = ref(0)
const page     = ref(1)
const pageSize = 20
const loading  = ref(true)
const exporting = ref(false)
const filters  = ref({ q: '', status_filter: '', area_causadora: '', data_inicio: '', data_fim: '' })

const totalPages = computed(() => Math.ceil(total.value / pageSize))
const canOpen = computed(() => user.value && !['Producao'].includes(user.value.sector))
const hasActiveFilters = computed(() => Object.values(filters.value).some(v => v !== ''))

const pageNumbers = computed(() => {
  const total = totalPages.value
  const cur = page.value
  const delta = 2
  const pages = []
  for (let i = Math.max(1, cur - delta); i <= Math.min(total, cur + delta); i++) pages.push(i)
  return pages
})

let debounceTimer = null
watch(() => filters.value.q, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; load() }, 400)
})

async function load() {
  loading.value = true
  try {
    const res = await api.fcas.list({ ...filters.value, page: page.value, page_size: pageSize })
    items.value = res.items
    total.value = res.total
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function clearFilters() {
  filters.value = { q: '', status_filter: '', area_causadora: '', data_inicio: '', data_fim: '' }
  page.value = 1; load()
}
function goPage(p) { page.value = p; load() }
function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', aguardando_devolutiva: 'Ag. devolutiva', encerrado: 'Encerrado', cancelado: 'Cancelado' }[s] || s
}
function formatDate(iso) { return new Date(iso).toLocaleDateString('pt-BR') }
async function exportar(format) {
  exporting.value = true
  try { await api.fcas.export({ ...filters.value }, format) }
  catch (e) { alert('Erro ao exportar: ' + e.message) }
  finally { exporting.value = false }
}

onMounted(() => { load(); registerWsListener?.(load) })
onActivated(load)
onUnmounted(() => { registerWsListener?.(null) })
</script>

<style scoped>
/* Filters */
.filters-panel { margin-bottom: var(--space-4); }
.filters-row { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.filter-icon {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-600); white-space: nowrap;
}
.search-wrap { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: var(--space-3); color: var(--color-neutral-400); pointer-events: none; }
.input-search {
  padding: var(--space-2) var(--space-3) var(--space-2) 34px;
  border: 1.5px solid var(--color-neutral-200); border-radius: var(--radius-md);
  font-size: var(--font-size-sm); outline: none; min-width: 220px;
  font-family: var(--font-family-base); background: var(--color-neutral-50);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.input-search:focus { border-color: var(--color-primary-500); box-shadow: 0 0 0 3px var(--color-primary-100); background: #fff; }
.filter-select {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm);
  background: var(--color-neutral-50); color: var(--color-neutral-700); outline: none;
  font-family: var(--font-family-base); cursor: pointer;
  transition: border-color var(--transition-fast);
}
.filter-select:focus { border-color: var(--color-primary-500); box-shadow: 0 0 0 3px var(--color-primary-100); }
.date-range { display: flex; align-items: center; gap: var(--space-2); }
.filter-date {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); background: var(--color-neutral-50);
  color: var(--color-neutral-700); outline: none; font-family: var(--font-family-base);
}
.filter-date:focus { border-color: var(--color-primary-500); }
.date-sep { color: var(--color-neutral-400); font-size: var(--font-size-sm); }
.filters-actions { display: flex; gap: var(--space-2); margin-left: auto; }

/* Chips */
.filter-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--color-neutral-100); }
.filter-chip {
  display: inline-flex; align-items: center; gap: var(--space-1);
  background: var(--color-primary-100); color: var(--color-primary-700);
  border-radius: var(--radius-full); padding: 3px var(--space-3);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-medium);
}
.filter-chip button {
  background: none; border: none; cursor: pointer; color: var(--color-primary-500);
  font-size: var(--font-size-sm); padding: 0; line-height: 1; margin-left: 2px;
  display: flex; align-items: center;
}
.filter-chip button:hover { color: var(--color-danger); }

/* Skeleton table */
.skeleton-table-header {
  height: 42px; background: var(--color-neutral-50);
  border-bottom: 2px solid var(--color-neutral-200);
}
.skeleton-table-row {
  display: flex; gap: var(--space-4); align-items: center;
  padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--color-neutral-100);
}

/* Empty */
.empty-card {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-3); padding: var(--space-12); text-align: center;
}
.empty-title { font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); color: var(--color-neutral-600); }
.empty-sub   { font-size: var(--font-size-sm); color: var(--color-neutral-400); }

/* Table */
.table-card { padding: 0; overflow: hidden; margin-top: var(--space-4); }
.table-wrap { overflow-x: auto; }
.fca-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.fca-table th {
  text-align: left; padding: var(--space-3) var(--space-4);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: .05em;
  border-bottom: 2px solid var(--color-neutral-200);
  background: var(--color-neutral-50); white-space: nowrap;
}
.fca-table td { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.fca-table tr:last-child td { border-bottom: none; }
.table-row { animation: fadeInUp 250ms ease both; }
.fca-table tr:hover td { background: var(--color-primary-50); }
.code-text { font-weight: var(--font-weight-semibold); color: var(--color-primary-700); }
.causa-cell { color: var(--color-neutral-800); max-width: 200px; }
.muted-cell { color: var(--color-neutral-500); font-size: var(--font-size-xs); }
.etapa-text { font-size: var(--font-size-xs); color: var(--color-neutral-600); }
.dash-text  { color: var(--color-neutral-300); }
.date-cell  { color: var(--color-neutral-500); white-space: nowrap; font-size: var(--font-size-xs); }
.btn-ver:hover { background: var(--color-primary-500) !important; color: #fff !important; border-color: var(--color-primary-500) !important; }

/* Pagination */
.pagination { display: flex; align-items: center; gap: var(--space-3); justify-content: center; margin-top: var(--space-5); }
.page-numbers { display: flex; gap: var(--space-1); }
</style>
