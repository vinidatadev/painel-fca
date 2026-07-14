<template>
  <div>
    <div class="page-header">
      <h1>Dashboard</h1>
    </div>

    <div v-if="loading" class="loading-text">Carregando...</div>

    <template v-else>
      <!-- Indicadores -->
      <div class="indicators">
        <div class="indicator">
          <span class="ind-value">{{ data.acompanhamento.abertos }}</span>
          <span class="ind-label">Abertos</span>
        </div>
        <div class="indicator ind-warning">
          <span class="ind-value">{{ data.acompanhamento.em_andamento }}</span>
          <span class="ind-label">Em andamento</span>
        </div>
        <div class="indicator ind-purple">
          <span class="ind-value">{{ data.acompanhamento.aguardando_devolutiva }}</span>
          <span class="ind-label">Aguard. devolutiva</span>
        </div>
        <div class="indicator ind-green">
          <span class="ind-value">{{ data.acompanhamento.encerrados }}</span>
          <span class="ind-label">Encerrados</span>
        </div>
      </div>

      <!-- Minha Fila -->
      <div class="card" style="margin-top:1.5rem">
        <h2 class="section-title">Minha Fila <span class="count-badge">{{ data.minha_fila.total }}</span></h2>
        <div v-if="!data.minha_fila.itens.length" class="empty-state">Nenhum FCA aguardando sua ação.</div>
        <table v-else class="fca-table">
          <thead>
            <tr>
              <th>Código</th><th>Causa</th><th>Área Causadora</th><th>UF</th><th>Status</th><th>SLA</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fca in data.minha_fila.itens" :key="fca.id">
              <td><strong>{{ fca.cod_fca }}</strong></td>
              <td>{{ fca.causa }}</td>
              <td>{{ fca.area_causadora }} · {{ fca.empresa_causadora }}</td>
              <td>{{ fca.uf }}</td>
              <td><span :class="['badge', 'badge-' + fca.status]">{{ labelStatus(fca.status) }}</span></td>
              <td>
                <SlaBadge v-if="fca.etapa_atual?.sla_deadline" :deadline="fca.etapa_atual.sla_deadline" />
              </td>
              <td><RouterLink :to="`/fca/${fca.id}`" class="btn btn-sm btn-primary">Tratar</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Link para lista completa -->
      <div style="margin-top:1rem;text-align:right">
        <RouterLink to="/fca" class="btn btn-outline btn-sm">Ver todos os FCAs →</RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, inject, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import SlaBadge from '../components/SlaBadge.vue'

const registerWsListener = inject('registerWsListener')

const loading = ref(true)
const data = ref({ minha_fila: { total: 0, itens: [] }, acompanhamento: { abertos: 0, em_andamento: 0, aguardando_devolutiva: 0, encerrados: 0 } })

async function load() {
  try {
    data.value = await api.dashboard.get()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  registerWsListener?.(load)
})

onUnmounted(() => {
  registerWsListener?.(null)
})

function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', aguardando_devolutiva: 'Ag. devolutiva', encerrado: 'Encerrado' }[s] || s
}
</script>

<style scoped>
.loading-text { color: #888; margin-top: 2rem; text-align: center; }
.indicators { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.indicator {
  background: #fff; border-radius: 10px; padding: 1.1rem 1rem;
  box-shadow: 0 1px 4px rgba(0,0,0,.07); text-align: center;
  border-left: 4px solid #1a56db;
}
.ind-warning { border-left-color: #f59e0b; }
.ind-purple { border-left-color: #7c3aed; }
.ind-green { border-left-color: #059669; }
.ind-value { display: block; font-size: 2rem; font-weight: 700; color: #1a1a2e; }
.ind-label { font-size: .78rem; color: #6b7280; margin-top: .1rem; display: block; }

.section-title { font-size: 1rem; font-weight: 700; margin-bottom: 1rem; display: flex; align-items: center; gap: .5rem; }
.count-badge { background: #dbeafe; color: #1d4ed8; border-radius: 20px; padding: .1rem .55rem; font-size: .78rem; }
.empty-state { color: #9ca3af; font-size: .9rem; padding: 1rem 0; }

.fca-table { width: 100%; border-collapse: collapse; font-size: .875rem; }
.fca-table th { text-align: left; padding: .5rem .75rem; font-weight: 600; border-bottom: 2px solid #e5e7eb; color: #6b7280; font-size: .78rem; text-transform: uppercase; }
.fca-table td { padding: .6rem .75rem; border-bottom: 1px solid #f3f4f6; }
.fca-table tr:last-child td { border-bottom: none; }
.fca-table tr:hover td { background: #f9fafb; }

@media (max-width: 700px) {
  .indicators { grid-template-columns: repeat(2, 1fr); }
}
</style>
