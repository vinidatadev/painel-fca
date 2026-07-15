<template>
  <div class="bi-view">

    <!-- Banner de erro -->
    <div v-if="erroBI" class="erro-banner">
      <span>{{ erroBI }}</span>
      <button class="btn btn-sm btn-secondary" @click="loadBI">Tentar novamente</button>
    </div>

    <!-- Aviso de escopo não-admin removido: acesso_relatorio tem visão global -->

    <!-- Filtros Globais -->
    <div class="card filters-panel">
      <div class="filters-row">
        <div class="filter-group">
          <label>Data início</label>
          <input type="date" v-model="filtros.data_inicio" />
          <span v-if="erroData" class="inline-error">{{ erroData }}</span>
        </div>
        <div class="filter-group">
          <label>Data fim</label>
          <input type="date" v-model="filtros.data_fim" />
        </div>
        <div class="filter-group">
          <label>Empresa do Causador</label>
          <select v-model="filtros.empresa">
            <option value="">Todas</option>
            <option value="ACI_MATRIZ">ACI_MATRIZ</option>
            <option value="ACI_FILIAL">ACI_FILIAL</option>
            <option value="SINOBRAS">SINOBRAS</option>
            <option value="ACC">ACC</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Setor Causador</label>
          <select v-model="filtros.setor">
            <option value="">Todos</option>
            <option v-for="s in SETORES" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>UF</label>
          <select v-model="filtros.uf">
            <option value="">Todas</option>
            <option v-for="u in UFS" :key="u" :value="u">{{ u }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Causa</label>
          <select v-model="filtros.causa">
            <option value="">Todas</option>
            <option v-for="c in causasOpcoes" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Status</label>
          <select v-model="filtros.status">
            <option value="">Todos</option>
            <option value="aberto">Aberto</option>
            <option value="em_andamento">Em andamento</option>
            <option value="aguardando_devolutiva">Aguardando devolutiva</option>
            <option value="encerrado">Encerrado</option>
          </select>
        </div>
      </div>

      <div class="filters-actions">
        <div class="atalhos">
          <button :class="['btn btn-sm', atalhoAtivo === 7 ? 'btn-primary' : 'btn-secondary']" @click="setAtalho(7)">7 dias</button>
          <button :class="['btn btn-sm', atalhoAtivo === 30 ? 'btn-primary' : 'btn-secondary']" @click="setAtalho(30)">30 dias</button>
          <button :class="['btn btn-sm', atalhoAtivo === 0 ? 'btn-primary' : 'btn-secondary']" @click="setAtalhoMes">Este mês</button>
        </div>
        <button class="btn btn-sm btn-ghost" @click="limparFiltros">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.51"/></svg>
          Limpar filtros
        </button>
      </div>
    </div>

    <!-- KPIs -->
    <h2 class="section-title">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
      Indicadores
    </h2>
    <div class="kpi-grid">
      <template v-if="loadingBI">
        <div v-for="i in 5" :key="i" class="skeleton kpi-skeleton"></div>
      </template>
      <template v-else>
        <div class="kpi-card kpi-blue">
          <div class="kpi-top">
            <span class="kpi-icon-wrap kpi-icon-blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
            </span>
            <span class="kpi-trend">Total</span>
          </div>
          <span class="kpi-value">{{ kpis.total }}</span>
          <span class="kpi-label">FCAs Registrados</span>
        </div>
        <div class="kpi-card kpi-green">
          <div class="kpi-top">
            <span class="kpi-icon-wrap kpi-icon-green">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span class="kpi-trend kpi-trend-up">Resolvidos</span>
          </div>
          <span class="kpi-value">{{ kpis.encerrados }}</span>
          <span class="kpi-label">Encerrados</span>
        </div>
        <div class="kpi-card kpi-sky">
          <div class="kpi-top">
            <span class="kpi-icon-wrap kpi-icon-sky">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.51"/></svg>
            </span>
            <span class="kpi-trend">Ativos</span>
          </div>
          <span class="kpi-value">{{ kpis.em_aberto }}</span>
          <span class="kpi-label">Em Aberto</span>
        </div>
        <div class="kpi-card kpi-red">
          <div class="kpi-top">
            <span class="kpi-icon-wrap kpi-icon-red">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </span>
            <span class="kpi-trend kpi-trend-down">Crítico</span>
          </div>
          <span class="kpi-value">{{ kpis.atrasados }}</span>
          <span class="kpi-label">Atrasados</span>
        </div>
        <div class="kpi-card kpi-amber">
          <div class="kpi-top">
            <span class="kpi-icon-wrap kpi-icon-amber">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            </span>
            <span class="kpi-trend">Eficiência</span>
          </div>
          <span class="kpi-value">{{ kpis.taxa_resolucao }}%</span>
          <span class="kpi-label">Taxa de Resolução</span>
        </div>
      </template>
    </div>

    <hr class="section-divider" />
    <h2 class="section-title">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><polyline points="18 9 14 5 10 9 6 5"/></svg>
      Análise Detalhada
    </h2>

    <!-- Grid de gráficos 2 colunas -->
    <div class="charts-grid">

      <!-- Grafico_Status + Grafico_Empresa (lado a lado num card full) -->
      <div class="card chart-card chart-full chart-status-empresa">
        <div class="status-empresa-left">
          <h3 class="chart-title">FCAs por Status</h3>
          <div v-if="!porStatus.length" class="empty-state">Nenhum FCA no período selecionado.</div>
          <Bar v-else :data="statusChartData" :options="barOptions" />
        </div>
        <div class="status-empresa-divider"></div>
        <div class="status-empresa-right">
          <h3 class="chart-title">FCAs por Empresa Causadora</h3>
          <div v-if="!empresaChartData.datasets[0]?.data.length" class="empty-state">Sem dados no período.</div>
          <div v-else class="doughnut-wrap">
            <Doughnut :data="empresaChartData" :options="doughnutOptions" />
          </div>
        </div>
      </div>

      <!-- Grafico_Evolucao (ocupa 2 colunas) -->
      <div class="card chart-card chart-full">
        <div class="chart-header">
          <h3 class="chart-title">Evolução Temporal</h3>
          <div class="toggle-temporal">
            <button :class="['btn btn-sm', agrupamento === 'semana' ? 'btn-primary' : 'btn-secondary']"
                    @click="agrupamento = 'semana'">Semana</button>
            <button :class="['btn btn-sm', agrupamento === 'mes' ? 'btn-primary' : 'btn-secondary']"
                    @click="agrupamento = 'mes'">Mês</button>
          </div>
        </div>
        <div v-if="!evolucaoTemporal.length" class="empty-state">Sem dados no período selecionado.</div>
        <div v-else style="position: relative; height: 260px;">
          <Chart type="bar" :data="evolucaoChartData" :options="evolucaoOptions" />
        </div>
      </div>

      <!-- Grafico_Causas -->
      <div class="card chart-card">
        <h3 class="chart-title">Top 10 Causas</h3>
        <div v-if="rankingCausas.length < 3" class="empty-state">Dados insuficientes para o período.</div>
        <Bar v-else :data="causasChartData" :options="hBarOptions" />
      </div>

      <!-- Grafico_Areas -->
      <div class="card chart-card">
        <h3 class="chart-title">Top 10 Áreas Causadoras</h3>
        <div v-if="rankingAreas.length < 3" class="empty-state">Dados insuficientes para o período.</div>
        <Bar v-else :data="areasChartData" :options="hBarOptions" />
      </div>

      <!-- Grafico_UF -->
      <div class="card chart-card">
        <h3 class="chart-title">FCAs por UF</h3>
        <div v-if="!porUf.length" class="empty-state">Sem FCAs por UF no período.</div>
        <template v-else>
          <table class="uf-table">
            <tbody>
              <tr v-for="(row, i) in (ufExpandida ? porUf : porUf.slice(0, 10))" :key="row.uf">
                <td class="uf-sigla">{{ row.uf }}</td>
                <td class="uf-bar-cell">
                  <div class="uf-bar-track">
                    <div class="uf-bar-fill"
                         :style="{ width: (porUf[0].total > 0 ? row.total / porUf[0].total * 100 : 0) + '%',
                                   background: ufColor(row.total, porUf[0].total) }">
                    </div>
                  </div>
                </td>
                <td class="uf-count">{{ row.total }}</td>
              </tr>
            </tbody>
          </table>
          <button v-if="porUf.length > 10 && !ufExpandida"
                  class="btn btn-sm btn-secondary" style="margin-top: var(--space-2)"
                  @click="ufExpandida = true">Ver todas</button>
        </template>
      </div>

      <!-- Grafico_Solucao -->
      <div class="card chart-card">
        <h3 class="chart-title">Taxa de Solução por Área Causadora</h3>
        <div v-if="!solucaoPorArea.length" class="empty-state">Nenhuma etapa concluída com avaliação no período.</div>
        <Bar v-else :data="solucaoChartData" :options="{ responsive: true, plugins: { legend: { display: true, position: 'top' } }, scales: { y: { beginAtZero: true } } }" />
      </div>

      <!-- Grafico_SLA -->
      <div class="card chart-card">
        <h3 class="chart-title">SLA OK vs NOK por Setor Responsável</h3>
        <div v-if="!slaPorSetor.length" class="empty-state">Sem dados de SLA no período.</div>
        <Bar v-else :data="slaChartData" :options="slaStackedOptions" />
      </div>

      <!-- Grafico_Tempo -->
      <div class="card chart-card">
        <h3 class="chart-title">Tempo Médio de Resolução por Setor Responsável (h)</h3>
        <div v-if="!tempoMedioSetor.length" class="empty-state">Sem dados de tempo no período.</div>
        <Bar v-else :data="tempoChartData" :options="hBarOptions" />
      </div>

    </div>

    <!-- Tabelas cruzadas -->
    <hr class="section-divider" />
    <h2 class="section-title">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="9" x2="9" y2="21"/><line x1="15" y1="9" x2="15" y2="21"/></svg>
      Tabelas Cruzadas
    </h2>

    <!-- Tabela_EmpresaCausa pivot -->
    <div class="card" style="overflow-x: auto; margin-bottom: var(--space-4)">
      <h3 class="chart-title">Empresa Causadora × Causa</h3>
      <div v-if="!tabelaEmpresaCausa.length" class="empty-state">Nenhum dado para os filtros selecionados.</div>
      <table v-else class="pivot-table">
        <thead>
          <tr>
            <th>Empresa Causadora</th>
            <th v-for="causa in empresaCausaPivot.causas" :key="causa">{{ causa }}</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in empresaCausaPivot.empresas" :key="emp">
            <td>{{ emp }}</td>
            <td v-for="causa in empresaCausaPivot.causas" :key="causa"
                :style="pivotCellStyle(empresaCausaPivot.map[emp]?.[causa])">
              {{ empresaCausaPivot.map[emp]?.[causa] || 0 }}
            </td>
            <td class="pivot-total">
              {{ empresaCausaPivot.causas.reduce((s, c) => s + (empresaCausaPivot.map[emp]?.[c] || 0), 0) }}
            </td>
          </tr>
          <tr class="pivot-total-row">
            <td>Total</td>
            <td v-for="causa in empresaCausaPivot.causas" :key="causa">
              {{ empresaCausaPivot.empresas.reduce((s, e) => s + (empresaCausaPivot.map[e]?.[causa] || 0), 0) }}
            </td>
            <td>{{ tabelaEmpresaCausa.reduce((s, r) => s + r.total, 0) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Tabela_SetorEmpresaCausa ordenável + paginada -->
    <div class="card" style="overflow-x: auto; margin-bottom: var(--space-4)">
      <h3 class="chart-title">Setor Solicitante × Empresa Solicitante × Causa</h3>
      <div v-if="!tabelaSetorEmpresaCausa.length" class="empty-state">Nenhum dado para os filtros selecionados.</div>
      <template v-else>
        <table class="data-table">
          <thead>
            <tr>
              <th class="sortable" @click="sortBy('setor')">
                Setor Solicitante <span>{{ sortColuna === 'setor' ? (sortAsc ? '↑' : '↓') : '' }}</span>
              </th>
              <th class="sortable" @click="sortBy('empresa')">
                Empresa Solicitante <span>{{ sortColuna === 'empresa' ? (sortAsc ? '↑' : '↓') : '' }}</span>
              </th>
              <th class="sortable" @click="sortBy('causa')">
                Causa <span>{{ sortColuna === 'causa' ? (sortAsc ? '↑' : '↓') : '' }}</span>
              </th>
              <th class="sortable" @click="sortBy('total')">
                Qtd FCAs <span>{{ sortColuna === 'total' ? (sortAsc ? '↑' : '↓') : '' }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in tabelaSorted" :key="row.setor + row.empresa + row.causa">
              <td>{{ row.setor }}</td>
              <td>{{ row.empresa }}</td>
              <td>{{ row.causa }}</td>
              <td>{{ row.total }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <button class="btn btn-sm btn-secondary" :disabled="paginaAtual <= 1" @click="paginaAtual--">Anterior</button>
          <span class="pagination-info">
            {{ (paginaAtual - 1) * paginaTamanho + 1 }}–{{ Math.min(paginaAtual * paginaTamanho, tabelaSetorEmpresaCausa.length) }}
            de {{ tabelaSetorEmpresaCausa.length }} registros
          </span>
          <button class="btn btn-sm btn-secondary" :disabled="paginaAtual >= totalPaginas" @click="paginaAtual++">Próxima</button>
        </div>
      </template>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Bar, Doughnut, Chart } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, LineController, BarController
} from 'chart.js'
import { api } from '../api'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend, LineController, BarController)

const router = useRouter()
const user   = inject('user')

// ── Computed ──────────────────────────────────────────────────────────────────
const isAdmin = computed(() => user.value?.role === 'admin')

// ── Dados da API ──────────────────────────────────────────────────────────────
const kpis               = ref({ total: 0, encerrados: 0, em_aberto: 0, atrasados: 0, taxa_resolucao: 0 })
const porStatus          = ref([])
const evolucaoTemporal   = ref([])
const rankingCausas      = ref([])
const rankingAreas       = ref([])
const porUf              = ref([])
const porEmpresa         = ref([])
const solucaoPorArea     = ref([])
const tempoMedioSetor    = ref([])
const slaPorSetor        = ref([])
const tabelaEmpresaCausa      = ref([])
const tabelaSetorEmpresaCausa = ref([])

// ── Estado UI ─────────────────────────────────────────────────────────────────
const loadingBI   = ref(false)
const erroBI      = ref('')
const agrupamento = ref('semana')
const ufExpandida = ref(false)
const atalhoAtivo = ref(null) // null = nenhum; 7 = 7 dias; 30 = 30 dias; 0 = este mês

// ── Filtros globais ───────────────────────────────────────────────────────────
const filtros = ref({
  data_inicio: '',
  data_fim:    '',
  empresa:     '',
  setor:       '',
  uf:          '',
  causa:       '',
  status:      '',
})

const erroData = computed(() => {
  if (filtros.value.data_inicio && filtros.value.data_fim &&
      filtros.value.data_inicio > filtros.value.data_fim) {
    return 'Data início não pode ser maior que data fim'
  }
  return ''
})

// ── Listas estáticas ──────────────────────────────────────────────────────────
const SETORES = [
  'ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao', 'Comercial', 'Customer_Service',
]
const UFS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
  'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
]
const causasOpcoes = ref([])

// ── Constantes de cores (hex — Chart.js não resolve CSS vars no canvas) ───────
const STATUS_COLORS = {
  aberto:                '#3b82f6',
  em_andamento:          '#d97706',
  aguardando_devolutiva: '#7c3aed',
  encerrado:             '#059669',
  cancelado:             '#6b7280',
}
const EMPRESA_COLORS = {
  ACI_MATRIZ: '#3b82f6',
  ACI_FILIAL: '#6366f1',
  SINOBRAS:   '#d97706',
  ACC:        '#7c3aed',
}

// ── Chart options base ────────────────────────────────────────────────────────
const barOptions = {
  responsive: true, maintainAspectRatio: true,
  plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
  scales: { y: { beginAtZero: true } },
}
const evolucaoOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: true, position: 'top' } },
  scales: { y: { beginAtZero: true } },
}
const hBarOptions = {
  responsive: true, maintainAspectRatio: true, indexAxis: 'y',
  plugins: { legend: { display: false } },
  scales: { x: { beginAtZero: true } },
}

// ── Computeds de gráficos ─────────────────────────────────────────────────────
const statusChartData = computed(() => ({
  labels: porStatus.value.map(r => r.status),
  datasets: [{
    data: porStatus.value.map(r => r.total),
    backgroundColor: porStatus.value.map(r => STATUS_COLORS[r.status] || 'var(--color-neutral-400)'),
  }],
}))

const evolucaoChartData = computed(() => ({
  labels: evolucaoTemporal.value.map(r => r.periodo.slice(0, 10)),
  datasets: [
    {
      type: 'bar',
      label: 'Abertos',
      data: evolucaoTemporal.value.map(r => r.abertos),
      backgroundColor: '#3b82f6',
    },
    {
      type: 'line',
      label: 'Encerrados',
      data: evolucaoTemporal.value.map(r => r.encerrados),
      borderColor: '#059669',
      backgroundColor: 'transparent',
      tension: 0.3,
      pointBackgroundColor: '#059669',
    },
  ],
}))

const causasChartData = computed(() => ({
  labels: rankingCausas.value.map(r => r.causa),
  datasets: [{
    data: rankingCausas.value.map(r => r.total),
    backgroundColor: '#3b82f6',
  }],
}))

const areasChartData = computed(() => ({
  labels: rankingAreas.value.map(r => `${r.area_causadora} / ${r.empresa_causadora}`),
  datasets: [{
    data: rankingAreas.value.map(r => r.total),
    backgroundColor: '#d97706',
  }],
}))

const empresaChartData = computed(() => {
  const filtered = porEmpresa.value.filter(r => r.total > 0)
  return {
    labels: filtered.map(r => r.empresa_causadora),
    datasets: [{
      data: filtered.map(r => r.total),
      backgroundColor: filtered.map(r => EMPRESA_COLORS[r.empresa_causadora] || 'var(--color-neutral-400)'),
    }],
  }
})

const solucaoChartData = computed(() => ({
  labels: solucaoPorArea.value.map(r => r.area_causadora),
  datasets: [
    {
      label: 'Solucionado',
      data: solucaoPorArea.value.map(r => r.solucionado),
      backgroundColor: '#059669',
    },
    {
      label: 'Não Solucionado',
      data: solucaoPorArea.value.map(r => r.nao_solucionado),
      backgroundColor: '#dc2626',
    },
  ],
}))

const tempoChartData = computed(() => ({
  labels: tempoMedioSetor.value.map(r => r.setor),
  datasets: [{
    data: tempoMedioSetor.value.map(r => r.tempo_medio_horas),
    backgroundColor: tempoMedioSetor.value.map(r => {
      const h = r.tempo_medio_horas
      if (h <= 8)  return '#059669'
      if (h <= 12) return '#d97706'
      return '#dc2626'
    }),
  }],
}))

const slaChartData = computed(() => ({
  labels: slaPorSetor.value.map(r => r.setor),
  datasets: [
    {
      label: 'SLA OK',
      data: slaPorSetor.value.map(r => r.ok),
      backgroundColor: '#059669',
    },
    {
      label: 'SLA NOK',
      data: slaPorSetor.value.map(r => r.nok),
      backgroundColor: '#dc2626',
    },
  ],
}))
const slaStackedOptions = {
  responsive: true, maintainAspectRatio: true, indexAxis: 'y',
  plugins: { legend: { display: true, position: 'top' } },
  scales: { x: { stacked: true, beginAtZero: true }, y: { stacked: true } },
}

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { display: true, position: 'bottom', labels: { boxWidth: 12, padding: 16, font: { size: 12 } } },
    tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed} FCAs` } },
  },
  cutout: '60%',
}

// ── Tabela cruzada pivot ──────────────────────────────────────────────────────
const empresaCausaPivot = computed(() => {
  const causas   = [...new Set(tabelaEmpresaCausa.value.map(r => r.causa))].sort()
  const empresas = [...new Set(tabelaEmpresaCausa.value.map(r => r.empresa_causadora))].sort()
  const map = {}
  for (const row of tabelaEmpresaCausa.value) {
    if (!map[row.empresa_causadora]) map[row.empresa_causadora] = {}
    map[row.empresa_causadora][row.causa] = (map[row.empresa_causadora][row.causa] || 0) + row.total
  }
  return { empresas, causas, map }
})

// ── Tabela ordenável + paginada ───────────────────────────────────────────────
const tabelaSorted = computed(() => {
  const sorted = [...tabelaSetorEmpresaCausa.value].sort((a, b) => {
    const va = a[sortColuna.value], vb = b[sortColuna.value]
    return sortAsc.value ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1)
  })
  const start = (paginaAtual.value - 1) * paginaTamanho
  return sorted.slice(start, start + paginaTamanho)
})
const totalPaginas = computed(() => Math.ceil(tabelaSetorEmpresaCausa.value.length / paginaTamanho))

function sortBy(col) {
  if (sortColuna.value === col) {
    sortAsc.value = !sortAsc.value
  } else {
    sortColuna.value = col
    sortAsc.value = false
  }
  paginaAtual.value = 1
}

// ── Intensidade de cor UF ─────────────────────────────────────────────────────
function ufColor(total, max) {
  const pct = max > 0 ? total / max : 0
  if (pct >= 0.7) return 'var(--color-danger)'
  if (pct >= 0.3) return 'var(--color-warning)'
  return 'var(--color-success)'
}

// ── Intensidade de cor tabela pivot ──────────────────────────────────────────
function pivotCellStyle(val) {
  if (!val) return ''
  if (val >= 6) return 'background: var(--color-primary-500); color: #fff;'
  if (val >= 3) return 'background: var(--color-primary-100);'
  if (val >= 1) return 'background: var(--color-primary-50);'
  return ''
}

// ── Paginação Tabela_SetorEmpresaCausa ────────────────────────────────────────
const paginaAtual   = ref(1)
const paginaTamanho = 15
const sortColuna    = ref('total')
const sortAsc       = ref(false)

// ── Atalhos de período ────────────────────────────────────────────────────────
function setAtalho(dias) {
  const hoje = new Date()
  const inicio = new Date()
  inicio.setDate(hoje.getDate() - dias)
  filtros.value.data_inicio = inicio.toISOString().slice(0, 10)
  filtros.value.data_fim    = hoje.toISOString().slice(0, 10)
  atalhoAtivo.value = dias
}

function setAtalhoMes() {
  const hoje = new Date()
  const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
  filtros.value.data_inicio = inicio.toISOString().slice(0, 10)
  filtros.value.data_fim    = hoje.toISOString().slice(0, 10)
  atalhoAtivo.value = 0
}

// ── Limpar filtros ────────────────────────────────────────────────────────────
function limparFiltros() {
  filtros.value = {
    data_inicio: '',
    data_fim:    '',
    empresa:     '',
    setor:       '',
    uf:          '',
    causa:       '',
    status:      '',
  }
  atalhoAtivo.value = null
}

// ── Debounce watch ────────────────────────────────────────────────────────────
let _debounceTimer = null
watch(filtros, () => {
  if (erroData.value) return
  clearTimeout(_debounceTimer)
  _debounceTimer = setTimeout(loadBI, 400)
}, { deep: true })

watch(agrupamento, loadBI)

// ── loadBI ────────────────────────────────────────────────────────────────────
async function loadBI() {
  loadingBI.value = true
  erroBI.value = ''
  try {
    const params = { ...filtros.value, agrupamento: agrupamento.value }
    const data = await api.bi.fca(params)
    kpis.value               = data.kpis
    porStatus.value          = data.por_status
    evolucaoTemporal.value   = data.evolucao_temporal
    rankingCausas.value      = data.ranking_causas
    rankingAreas.value       = data.ranking_areas
    porUf.value              = data.por_uf
    porEmpresa.value         = data.por_empresa
    solucaoPorArea.value     = data.solucao_por_area
    tempoMedioSetor.value    = data.tempo_medio_setor
    slaPorSetor.value        = data.sla_por_setor
    tabelaEmpresaCausa.value      = data.tabela_empresa_causa
    tabelaSetorEmpresaCausa.value = data.tabela_setor_empresa_causa
  } catch (e) {
    erroBI.value = e.message
  } finally {
    loadingBI.value = false
  }
}

// ── Carregar opções de causa ──────────────────────────────────────────────────
async function carregarOpcoes() {
  try {
    const data = await api.opcoes.get()
    causasOpcoes.value = data.causas || []
  } catch { /* silencioso */ }
}

// ── onMounted: guarda de acesso ───────────────────────────────────────────────
onMounted(async () => {
  if (!isAdmin.value && !user.value?.acesso_relatorio) {
    router.replace('/')
    return
  }
  await carregarOpcoes()
  await loadBI()
})
</script>

<style scoped>
.bi-view { padding: var(--space-5) var(--space-6); }

/* ── Banner de erro ── */
.erro-banner {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--color-danger-bg); color: var(--color-danger-text);
  padding: var(--space-3) var(--space-4); border-radius: var(--radius-md);
  border-left: 4px solid var(--color-danger);
  margin-bottom: var(--space-4);
}

/* ── Painel de Filtros ── */
.filters-panel {
  padding: var(--space-5);
  margin-bottom: var(--space-5);
  border-radius: var(--radius-xl);
  background: #fff;
  box-shadow: var(--shadow-sm);
}
.filters-row {
  display: flex; flex-wrap: wrap; gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.filter-group { display: flex; flex-direction: column; gap: 5px; min-width: 130px; }
.filter-group label {
  font-size: var(--font-size-xs); color: var(--color-neutral-500);
  font-weight: var(--font-weight-semibold); text-transform: uppercase; letter-spacing: 0.04em;
}
.filter-group input,
.filter-group select {
  padding: 7px var(--space-3);
  border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family-base);
  background: var(--color-neutral-50);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  color: var(--color-neutral-800);
}
.filter-group input:focus,
.filter-group select:focus {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px var(--color-primary-100);
  background: #fff;
}
.filter-group select:disabled { opacity: 0.5; cursor: not-allowed; }
.inline-error { font-size: var(--font-size-xs); color: var(--color-danger); }

.filters-actions {
  display: flex; align-items: center; justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-neutral-100);
}
.atalhos { display: flex; gap: var(--space-2); }

.btn-ghost {
  background: transparent; border: 1px solid var(--color-neutral-200);
  color: var(--color-neutral-500); border-radius: var(--radius-md);
  padding: 5px var(--space-3); font-size: var(--font-size-sm);
  cursor: pointer; display: inline-flex; align-items: center; gap: var(--space-1);
  transition: all var(--transition-fast);
}
.btn-ghost:hover { border-color: var(--color-neutral-400); color: var(--color-neutral-700); background: var(--color-neutral-50); }

/* ── Section titles ── */
.section-title {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: var(--font-size-lg); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-800);
  margin: var(--space-5) 0 var(--space-4);
}
.section-title svg { color: var(--color-primary-500); flex-shrink: 0; }
.section-divider {
  border: none; border-top: 1px solid var(--color-neutral-200);
  margin: var(--space-7) 0 0;
}

/* ── KPI Grid ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-2);
}
@media (max-width: 1199px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 767px)  { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }

.kpi-card {
  background: #fff;
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
  display: flex; flex-direction: column; gap: var(--space-1);
  transition: box-shadow var(--transition-base), transform var(--transition-base);
  position: relative; overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.kpi-blue::before  { background: var(--color-primary-500); }
.kpi-green::before { background: var(--color-success); }
.kpi-sky::before   { background: var(--color-info); }
.kpi-red::before   { background: var(--color-danger); }
.kpi-amber::before { background: var(--color-warning); }

.kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

.kpi-top {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-2);
}
.kpi-icon-wrap {
  width: 36px; height: 36px; border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.kpi-icon-blue  { background: var(--color-primary-100); color: var(--color-primary-700); }
.kpi-icon-green { background: var(--color-success-bg);  color: var(--color-success); }
.kpi-icon-sky   { background: var(--color-info-bg);     color: var(--color-info); }
.kpi-icon-red   { background: var(--color-danger-bg);   color: var(--color-danger); }
.kpi-icon-amber { background: var(--color-warning-bg);  color: var(--color-warning); }

.kpi-trend {
  font-size: var(--font-size-xs); font-weight: var(--font-weight-medium);
  color: var(--color-neutral-400); background: var(--color-neutral-100);
  padding: 2px var(--space-2); border-radius: var(--radius-full);
}
.kpi-trend-up   { background: var(--color-success-bg);  color: var(--color-success-text); }
.kpi-trend-down { background: var(--color-danger-bg);   color: var(--color-danger-text); }

.kpi-value {
  font-size: 2rem; font-weight: var(--font-weight-bold);
  color: var(--color-neutral-900); line-height: 1;
  margin: var(--space-1) 0;
}
.kpi-label { font-size: var(--font-size-sm); color: var(--color-neutral-500); }

/* Skeleton */
.skeleton { background: linear-gradient(90deg, var(--color-neutral-100) 25%, var(--color-neutral-50) 50%, var(--color-neutral-100) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: var(--radius-xl); }
.kpi-skeleton { height: 120px; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── Charts Grid ── */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
@media (max-width: 1023px) { .charts-grid { grid-template-columns: 1fr; } }

.chart-card {
  padding: var(--space-5);
  border-radius: var(--radius-xl);
  background: #fff;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}
.chart-full { grid-column: 1 / -1; min-height: 300px; }

/* ── Status + Empresa side-by-side ── */
.chart-status-empresa {
  display: flex !important;
  gap: var(--space-5);
  align-items: flex-start;
  min-height: unset;
}
.status-empresa-left  { flex: 3; min-width: 0; }
.status-empresa-right { flex: 2; min-width: 0; display: flex; flex-direction: column; }
.status-empresa-divider {
  width: 1px; background: var(--color-neutral-100);
  align-self: stretch; flex-shrink: 0;
}
.doughnut-wrap {
  flex: 1; display: flex; align-items: center; justify-content: center;
  max-height: 260px;
}
@media (max-width: 767px) {
  .chart-status-empresa { flex-direction: column; }
  .status-empresa-divider { width: 100%; height: 1px; align-self: auto; }
}
.chart-title {
  font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-700); margin-bottom: var(--space-4);
  padding-bottom: var(--space-3); border-bottom: 1px solid var(--color-neutral-100);
}
.chart-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3); border-bottom: 1px solid var(--color-neutral-100);
}
.chart-header .chart-title { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
.toggle-temporal { display: flex; gap: var(--space-1); }

.empty-state {
  text-align: center; padding: var(--space-8) var(--space-4);
  color: var(--color-neutral-400); font-size: var(--font-size-sm);
}

/* ── UF Table ── */
.uf-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.uf-sigla  { width: 44px; font-weight: var(--font-weight-semibold); padding: var(--space-1) var(--space-2); color: var(--color-neutral-700); }
.uf-count  { width: 40px; text-align: right; color: var(--color-neutral-600); padding: var(--space-1) var(--space-2); font-weight: var(--font-weight-medium); }
.uf-bar-cell { padding: var(--space-1) var(--space-2); }
.uf-bar-track { background: var(--color-neutral-100); border-radius: var(--radius-full); height: 8px; overflow: hidden; }
.uf-bar-fill  { height: 8px; border-radius: var(--radius-full); transition: width var(--transition-slow); }

/* ── Pivot Table ── */
.pivot-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-xs); }
.pivot-table th, .pivot-table td {
  padding: var(--space-2) var(--space-3); border: 1px solid var(--color-neutral-200);
  text-align: center; white-space: nowrap;
}
.pivot-table th {
  background: var(--color-neutral-50); font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-600); text-transform: uppercase; letter-spacing: 0.04em; font-size: 11px;
}
.pivot-table td:first-child { text-align: left; font-weight: var(--font-weight-medium); }
.pivot-total { font-weight: var(--font-weight-semibold); background: var(--color-neutral-50); }
.pivot-total-row td { font-weight: var(--font-weight-bold); background: var(--color-neutral-100); }

/* ── Data Table ── */
.data-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.data-table thead th {
  text-align: left; padding: var(--space-3) var(--space-4); font-weight: var(--font-weight-semibold);
  border-bottom: 2px solid var(--color-neutral-200); color: var(--color-neutral-500);
  font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: 0.06em;
  background: var(--color-neutral-50);
}
.data-table tbody td {
  padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-neutral-100);
  color: var(--color-neutral-700);
}
.data-table tbody tr:nth-child(even) td { background: var(--color-neutral-50); }
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover td { background: var(--color-primary-50) !important; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: var(--color-primary-500); }

/* ── Pagination ── */
.pagination {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) var(--space-4); border-top: 1px solid var(--color-neutral-100);
  background: var(--color-neutral-50); border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
.pagination-info { font-size: var(--font-size-sm); color: var(--color-neutral-500); }
</style>
