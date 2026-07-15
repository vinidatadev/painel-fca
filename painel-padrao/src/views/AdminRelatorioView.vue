<template>
  <div>
    <div class="page-header">
      <h1>Relatório de Desempenho</h1>
    </div>

    <div class="card filters-bar">
      <input v-model="filtros.data_inicio" type="date" placeholder="Data início" />
      <input v-model="filtros.data_fim" type="date" placeholder="Data fim" />
      <button class="btn btn-primary btn-sm" :disabled="loading" @click="load">
        {{ loading ? 'Carregando...' : '↺ Recarregar' }}
      </button>
      <button class="btn btn-secondary btn-sm" @click="limpar">Limpar filtros</button>
    </div>

    <div v-if="loading" class="loading-text">Carregando relatório...</div>
    <div v-else-if="!rows.length" class="card empty-state">Nenhum dado encontrado para o período.</div>

    <table v-else class="rel-table card">
      <thead>
        <tr>
          <th>Setor Responsável</th>
          <th>Empresa Responsável</th>
          <th>Tempo Médio de Resposta (h)</th>
          <th>% Etapas no Prazo (SLA)</th>
          <th>Total de Etapas Tratadas</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.setor + row.empresa">
          <td>{{ row.setor }}</td>
          <td>{{ row.empresa }}</td>
          <td>{{ row.tempo_medio_horas.toFixed(1) }}</td>
          <td>
            <span :class="['sla-badge', row.pct_dentro_sla >= 80 ? 'sla-ok' : 'sla-warn']">
              {{ row.pct_dentro_sla.toFixed(1) }}%
            </span>
          </td>
          <td>{{ row.total_etapas }}</td>
        </tr>
      </tbody>
    </table>

    <p v-if="erro" class="error-msg">{{ erro }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const rows    = ref([])
const loading = ref(false)
const erro    = ref('')
const filtros = ref({ data_inicio: '', data_fim: '' })

async function load() {
  loading.value = true
  erro.value = ''
  try {
    rows.value = await api.admin.relatorio(filtros.value)
  } catch (e) {
    erro.value = e.message
  } finally {
    loading.value = false
  }
}

function limpar() {
  filtros.value = { data_inicio: '', data_fim: '' }
  load()
}

onMounted(load)
</script>

<style scoped>
.filters-bar { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; margin-bottom: var(--space-4); padding: var(--space-3) var(--space-4); }
.filters-bar input {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm);
  font-family: var(--font-family-base); background: var(--color-neutral-50); outline: none;
}
.filters-bar input:focus { border-color: var(--color-primary-500); }

.rel-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); padding: 0; }
.rel-table thead th {
  text-align: left; padding: var(--space-2) var(--space-4); font-weight: var(--font-weight-semibold);
  border-bottom: 2px solid var(--color-neutral-200); color: var(--color-neutral-500);
  font-size: var(--font-size-xs); text-transform: uppercase; background: var(--color-neutral-50);
}
.rel-table tbody td { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.rel-table tbody tr:last-child td { border-bottom: none; }
.rel-table tbody tr:hover td { background: var(--color-primary-50); }

.sla-badge { padding: 3px var(--space-2); border-radius: var(--radius-full); font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); }
.sla-ok   { background: var(--color-success-bg); color: var(--color-success-text); }
.sla-warn { background: var(--color-danger-bg);  color: var(--color-danger-text); }
</style>
