<template>
  <div>
    <div class="page-header">
      <h1>Dashboard</h1>
      <RouterLink to="/fca" class="btn btn-outline btn-sm">Ver todos os FCAs →</RouterLink>
    </div>

    <!-- KPI Cards skeleton -->
    <div v-if="loading" class="kpi-grid">
      <div v-for="i in 5" :key="i" class="kpi-card skeleton-card">
        <div class="skeleton skeleton-rect" style="height:2.5rem;width:60%;margin-bottom:.5rem"></div>
        <div class="skeleton skeleton-text" style="width:70%"></div>
      </div>
    </div>

    <!-- KPI Cards -->
    <div v-else class="kpi-grid">
      <div class="kpi-card kpi-blue" style="--delay:0ms">
        <div class="kpi-header">
          <span class="kpi-icon kpi-icon-blue">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M4 4h12M4 8h8M4 12h10M4 16h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          </span>
        </div>
        <div class="kpi-value">{{ data.acompanhamento.abertos }}</div>
        <div class="kpi-label">Abertos</div>
      </div>
      <div class="kpi-card kpi-warning" style="--delay:60ms">
        <div class="kpi-header">
          <span class="kpi-icon kpi-icon-warning">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="1.8"/><path d="M10 6v5M10 14v.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          </span>
        </div>
        <div class="kpi-value">{{ data.acompanhamento.em_andamento }}</div>
        <div class="kpi-label">Em andamento</div>
      </div>
      <div class="kpi-card kpi-purple" style="--delay:120ms">
        <div class="kpi-header">
          <span class="kpi-icon kpi-icon-purple">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 10h14M3 5h14M3 15h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          </span>
        </div>
        <div class="kpi-value">{{ data.acompanhamento.aguardando_devolutiva }}</div>
        <div class="kpi-label">Ag. devolutiva</div>
      </div>
      <div class="kpi-card kpi-green" style="--delay:180ms">
        <div class="kpi-header">
          <span class="kpi-icon kpi-icon-green">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 10l4 4 7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <div class="kpi-value">{{ data.acompanhamento.encerrados }}</div>
        <div class="kpi-label">Encerrados</div>
      </div>
      <div :class="['kpi-card', metricas.atrasados > 0 ? 'kpi-danger' : 'kpi-green']" style="--delay:240ms">
        <div class="kpi-header">
          <span :class="['kpi-icon', metricas.atrasados > 0 ? 'kpi-icon-danger' : 'kpi-icon-green']">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="1.8"/><path d="M10 5v5l3 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          </span>
        </div>
        <div class="kpi-value" :style="metricas.atrasados > 0 ? 'color:var(--color-danger)' : ''">{{ metricas.atrasados }}</div>
        <div class="kpi-label">Atrasados</div>
      </div>
    </div>

    <!-- Minha Fila -->
    <div class="card" style="margin-top:var(--space-6)">
      <div class="fila-header">
        <h2 class="section-title">
          Minha Fila
          <span class="count-badge">{{ filaBuscaFiltrada.length }}</span>
        </h2>
        <div class="search-wrap">
          <svg class="search-icon" width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.4"/><path d="M10 10l2.5 2.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
          <input v-model="filaBusca" type="text" placeholder="Filtrar por código, causa, área..." class="input-search" />
        </div>
      </div>

      <!-- Skeleton fila -->
      <div v-if="loading" class="skeleton-rows">
        <div v-for="i in 4" :key="i" class="skeleton-row">
          <div class="skeleton skeleton-text" style="width:80px"></div>
          <div class="skeleton skeleton-text" style="width:160px"></div>
          <div class="skeleton skeleton-text" style="width:120px"></div>
          <div class="skeleton skeleton-text" style="width:50px"></div>
          <div class="skeleton skeleton-text" style="width:70px"></div>
        </div>
      </div>

      <div v-else-if="!filaBuscaFiltrada.length" class="empty-full">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="8" y="12" width="32" height="28" rx="4" stroke="var(--color-neutral-300)" stroke-width="2"/><path d="M16 20h16M16 26h10" stroke="var(--color-neutral-300)" stroke-width="2" stroke-linecap="round"/><path d="M24 8v4" stroke="var(--color-neutral-300)" stroke-width="2" stroke-linecap="round"/></svg>
        <p>{{ filaBusca ? 'Nenhum item encontrado.' : 'Nenhum FCA aguardando sua ação.' }}</p>
      </div>

      <div v-else class="table-wrap">
        <table class="fca-table">
          <thead>
            <tr>
              <th>Código</th><th>Causa</th><th>Área Causadora</th><th>UF</th><th>Status</th><th>SLA</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(fca, idx) in filaBuscaFiltrada" :key="fca.id" :style="`animation-delay:${idx * 30}ms`" class="fade-in-up">
              <td><strong class="code-text">{{ fca.cod_fca }}</strong></td>
              <td>{{ fca.causa }}</td>
              <td>
                <span class="area-text">{{ fca.area_causadora }}</span>
                <span class="empresa-text"> · {{ fca.empresa_causadora }}</span>
              </td>
              <td><span class="uf-badge">{{ fca.uf }}</span></td>
              <td><span :class="['badge', 'badge-' + fca.status]">{{ labelStatus(fca.status) }}</span></td>
              <td>
                <SlaBadge v-if="fca.etapa_atual?.sla_deadline" :deadline="fca.etapa_atual.sla_deadline" />
              </td>
              <td>
                <RouterLink :to="`/fca/${fca.id}`" class="btn btn-primary btn-sm">Tratar</RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Gráficos -->
    <div class="card" style="margin-top:var(--space-6)">
      <div class="graficos-header">
        <h2 class="section-title">Métricas Históricas</h2>
        <div class="toggle-pills">
          <button :class="['btn btn-sm', agrupamento === 'semana' ? 'btn-primary' : 'btn-secondary']" @click="setAgrupamento('semana')">Semana</button>
          <button :class="['btn btn-sm', agrupamento === 'mes' ? 'btn-primary' : 'btn-secondary']" @click="setAgrupamento('mes')">Mês</button>
        </div>
      </div>
      <div v-if="loadingMetricas" class="graficos-grid">
        <div class="skeleton skeleton-rect" style="height:200px"></div>
        <div>
          <div v-for="i in 5" :key="i" class="skeleton skeleton-text" style="margin-bottom:12px"></div>
        </div>
      </div>
      <div v-else class="graficos-grid">
        <div class="grafico-wrap">
          <p class="grafico-titulo">FCAs por {{ agrupamento === 'semana' ? 'Semana' : 'Mês' }}</p>
          <Bar v-if="barData.labels.length" :data="barData" :options="barOptions" />
          <div v-else class="empty-full" style="padding:2rem 0">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none"><rect x="6" y="16" width="8" height="18" rx="2" fill="var(--color-neutral-200)"/><rect x="16" y="10" width="8" height="24" rx="2" fill="var(--color-neutral-200)"/><rect x="26" y="20" width="8" height="14" rx="2" fill="var(--color-neutral-200)"/></svg>
            <p>Sem dados no período.</p>
          </div>
        </div>
        <div class="ranking-wrap">
          <p class="grafico-titulo">Top 5 Áreas Causadoras</p>
          <div v-if="!metricas.ranking_areas.length" class="empty-full" style="padding:1rem 0"><p>Sem dados.</p></div>
          <div v-else class="ranking-bars">
            <div v-for="(item, idx) in metricas.ranking_areas" :key="idx" class="ranking-row">
              <div class="ranking-info">
                <span class="ranking-pos">{{ idx + 1 }}</span>
                <span class="ranking-area">{{ item.area_causadora }} · {{ item.empresa_causadora }}</span>
                <span class="ranking-total">{{ item.total }}</span>
              </div>
              <div class="progress-track">
                <div class="progress-fill" :style="`width:${(item.total / metricas.ranking_areas[0].total) * 100}%`"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { api } from '../api'
import SlaBadge from '../components/SlaBadge.vue'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const registerWsListener = inject('registerWsListener')
const loading = ref(true)
const loadingMetricas = ref(true)
const filaBusca = ref('')
const agrupamento = ref('semana')

const data = ref({
  minha_fila: { total: 0, itens: [] },
  acompanhamento: { abertos: 0, em_andamento: 0, aguardando_devolutiva: 0, encerrados: 0 }
})
const metricas = ref({ serie_temporal: [], ranking_areas: [], atrasados: 0 })

const filaBuscaFiltrada = computed(() => {
  if (!filaBusca.value) return data.value.minha_fila.itens
  const q = filaBusca.value.toLowerCase()
  return data.value.minha_fila.itens.filter(f =>
    f.cod_fca.toLowerCase().includes(q) ||
    f.causa.toLowerCase().includes(q) ||
    f.area_causadora.toLowerCase().includes(q)
  )
})

const barData = computed(() => ({
  labels: metricas.value.serie_temporal.map(r => r.periodo),
  datasets: [{ label: 'FCAs', data: metricas.value.serie_temporal.map(r => r.total), backgroundColor: '#3b82f6', borderRadius: 6, borderSkipped: false }]
}))

const barOptions = {
  responsive: true,
  plugins: { legend: { display: false }, tooltip: { bodyFont: { family: 'Inter, system-ui' } } },
  scales: { y: { beginAtZero: true, ticks: { stepSize: 1, font: { family: 'Inter, system-ui', size: 11 } }, grid: { color: '#f3f4f6' } }, x: { ticks: { font: { family: 'Inter, system-ui', size: 11 } }, grid: { display: false } } }
}

async function load() {
  try { data.value = await api.dashboard.get() }
  catch (e) { console.error(e) }
  finally { loading.value = false }
  loadMetricas()
}

async function loadMetricas() {
  loadingMetricas.value = true
  try { metricas.value = await api.dashboard.metricas(agrupamento.value) }
  catch (e) { console.error(e) }
  finally { loadingMetricas.value = false }
}

function setAgrupamento(val) { agrupamento.value = val; loadMetricas() }

onMounted(() => { load(); registerWsListener?.(load) })
onUnmounted(() => { registerWsListener?.(null) })

function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', aguardando_devolutiva: 'Ag. devolutiva', encerrado: 'Encerrado' }[s] || s
}
</script>

<style scoped>
/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
}
.kpi-card {
  background: #fff; border-radius: var(--radius-lg); padding: var(--space-5);
  box-shadow: var(--shadow-sm); border: 1px solid var(--color-neutral-100);
  border-top: 4px solid var(--color-neutral-200);
  animation: fadeInUp 300ms ease both;
  animation-delay: var(--delay, 0ms);
  transition: box-shadow var(--transition-base), transform var(--transition-base);
}
.kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.kpi-blue   { border-top-color: var(--color-info); }
.kpi-warning{ border-top-color: var(--color-warning); }
.kpi-purple { border-top-color: var(--color-purple); }
.kpi-green  { border-top-color: var(--color-success); }
.kpi-danger { border-top-color: var(--color-danger); }

.skeleton-card { border-top-color: var(--color-neutral-200); }

.kpi-header { margin-bottom: var(--space-3); }
.kpi-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: var(--radius-md);
}
.kpi-icon-blue    { background: var(--color-info-bg);    color: var(--color-info-text); }
.kpi-icon-warning { background: var(--color-warning-bg); color: var(--color-warning-text); }
.kpi-icon-purple  { background: var(--color-purple-bg);  color: var(--color-purple-text); }
.kpi-icon-green   { background: var(--color-success-bg); color: var(--color-success-text); }
.kpi-icon-danger  { background: var(--color-danger-bg);  color: var(--color-danger-text); }

.kpi-value { font-size: var(--font-size-3xl); font-weight: var(--font-weight-bold); color: var(--color-neutral-900); line-height: 1.1; }
.kpi-label { font-size: var(--font-size-xs); color: var(--color-neutral-500); margin-top: var(--space-1); font-weight: var(--font-weight-medium); }

/* Minha Fila */
.fila-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--space-3); margin-bottom: var(--space-4); }
.count-badge {
  background: var(--color-primary-100); color: var(--color-primary-700);
  border-radius: var(--radius-full); padding: 2px var(--space-2);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-bold);
}
.search-wrap { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: var(--space-3); color: var(--color-neutral-400); pointer-events: none; }
.input-search {
  padding: var(--space-2) var(--space-3) var(--space-2) 34px;
  border: 1.5px solid var(--color-neutral-200); border-radius: var(--radius-md);
  font-size: var(--font-size-sm); outline: none; min-width: 250px;
  font-family: var(--font-family-base); background: var(--color-neutral-50);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.input-search:focus { border-color: var(--color-primary-500); box-shadow: 0 0 0 3px var(--color-primary-100); background: #fff; }
.input-search::placeholder { color: var(--color-neutral-400); }

/* Skeletons */
.skeleton-rows { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-3) 0; }
.skeleton-row { display: flex; gap: var(--space-4); align-items: center; padding: var(--space-2) 0; }

/* Empty */
.empty-full { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-8) 0; color: var(--color-neutral-400); }
.empty-full p { font-size: var(--font-size-sm); }

/* Table */
.table-wrap { overflow-x: auto; }
.fca-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.fca-table th {
  text-align: left; padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-500); text-transform: uppercase; letter-spacing: .05em;
  border-bottom: 2px solid var(--color-neutral-200);
  background: var(--color-neutral-50); position: sticky; top: 0;
}
.fca-table td { padding: var(--space-3) var(--space-3); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.fca-table tr:last-child td { border-bottom: none; }
.fca-table tr:hover td { background: var(--color-primary-50); }
.code-text { font-weight: var(--font-weight-semibold); color: var(--color-primary-700); font-size: var(--font-size-sm); }
.empresa-text { color: var(--color-neutral-400); }
.area-text { color: var(--color-neutral-700); }
.uf-badge {
  display: inline-block; padding: 2px var(--space-2); background: var(--color-neutral-100);
  border-radius: var(--radius-sm); font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-600);
}

/* Gráficos */
.graficos-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-5); }
.toggle-pills { display: flex; gap: var(--space-1); background: var(--color-neutral-100); border-radius: var(--radius-full); padding: 3px; }
.toggle-pills .btn-sm { border-radius: var(--radius-full) !important; font-size: var(--font-size-xs); }
.graficos-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6); }
.grafico-wrap, .ranking-wrap { min-height: 200px; }
.grafico-titulo { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-neutral-700); margin-bottom: var(--space-4); }

/* Ranking bars */
.ranking-bars { display: flex; flex-direction: column; gap: var(--space-4); }
.ranking-row { display: flex; flex-direction: column; gap: var(--space-1); }
.ranking-info { display: flex; align-items: center; gap: var(--space-2); }
.ranking-pos {
  width: 20px; height: 20px; background: var(--color-primary-100); color: var(--color-primary-700);
  border-radius: var(--radius-full); display: flex; align-items: center; justify-content: center;
  font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); flex-shrink: 0;
}
.ranking-area { flex: 1; font-size: var(--font-size-sm); color: var(--color-neutral-700); }
.ranking-total { font-weight: var(--font-weight-bold); color: var(--color-primary-700); font-size: var(--font-size-sm); }
.progress-track { height: 8px; background: var(--color-neutral-100); border-radius: var(--radius-full); overflow: hidden; }
.progress-fill { height: 100%; background: var(--color-primary-500); border-radius: var(--radius-full); transition: width 0.6s ease; }

@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px)  { .graficos-grid { grid-template-columns: 1fr; } }
@media (max-width: 600px)  { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
