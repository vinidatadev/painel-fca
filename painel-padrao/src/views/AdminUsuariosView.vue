<template>
  <div>
    <div class="page-header">
      <h1>Usuários</h1>
      <RouterLink to="/admin/usuarios/novo" class="btn btn-primary">+ Novo Usuário</RouterLink>
    </div>

    <!-- Filtros -->
    <div class="card filters-bar">
      <select v-model="filters.company" @change="load">
        <option value="">Todas as empresas</option>
        <option v-for="e in EMPRESAS" :key="e" :value="e">{{ e }}</option>
      </select>
      <select v-model="filters.sector" @change="load">
        <option value="">Todos os setores</option>
        <option v-for="s in SETORES" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filters.active" @change="load">
        <option value="">Todos</option>
        <option value="true">Ativos</option>
        <option value="false">Inativos</option>
      </select>
      <button class="btn btn-secondary btn-sm" @click="clearFilters">Limpar</button>
    </div>

    <div v-if="loading" class="loading-text">Carregando...</div>
    <div v-else-if="!items.length" class="card empty-state">Nenhum usuário encontrado.</div>

    <table v-else class="fca-table card">
      <thead>
        <tr>
          <th>Nome</th><th>E-mail</th><th>Empresa</th><th>Setor</th>
          <th>Papel</th><th>Matrícula</th><th>Turno</th><th>Status</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in items" :key="u.id" :class="{ inactive: !u.is_active }">
          <td>{{ u.name }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.company }}</td>
          <td>{{ u.sector }}</td>
          <td><span :class="['badge', u.role === 'admin' ? 'badge-em_andamento' : 'badge-aberto']">{{ u.role }}</span></td>
          <td>{{ u.matricula || '—' }}</td>
          <td>{{ u.turno || '—' }}</td>
          <td>
            <span :class="['badge', u.is_active ? 'badge-encerrado' : 'badge-aguardando_devolutiva']">
              {{ u.is_active ? 'Ativo' : 'Inativo' }}
            </span>
          </td>
          <td class="actions">
            <RouterLink :to="`/admin/usuarios/${u.id}`" class="btn btn-sm btn-outline">Editar</RouterLink>
            <button v-if="u.is_active" class="btn btn-sm btn-danger" @click="desativar(u)">Desativar</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const EMPRESAS = ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS', 'ACC']
const SETORES  = ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao', 'Comercial', 'Customer_Service']

const items   = ref([])
const loading = ref(true)
const filters = ref({ company: '', sector: '', active: '' })

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.company) params.company = filters.value.company
    if (filters.value.sector)  params.sector  = filters.value.sector
    if (filters.value.active !== '') params.active = filters.value.active
    items.value = await api.usuarios.list(params)
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  filters.value = { company: '', sector: '', active: '' }
  load()
}

async function desativar(u) {
  if (!confirm(`Desativar ${u.name}?`)) return
  try {
    await api.usuarios.desativar(u.id)
    await load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.filters-bar { display: flex; gap: .6rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; padding: .75rem 1rem; }
.filters-bar select { padding: .4rem .65rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: .85rem; }
.loading-text { color: #888; text-align: center; padding: 2rem; }
.empty-state { color: #9ca3af; padding: 2rem; text-align: center; }

.fca-table { width: 100%; border-collapse: collapse; font-size: .875rem; padding: 0; }
.fca-table thead th { text-align: left; padding: .6rem 1rem; font-weight: 600; border-bottom: 2px solid #e5e7eb; color: #6b7280; font-size: .75rem; text-transform: uppercase; background: #f9fafb; }
.fca-table tbody td { padding: .55rem 1rem; border-bottom: 1px solid #f3f4f6; }
.fca-table tbody tr.inactive td { opacity: .5; }
.fca-table tbody tr:hover td { background: #f9fafb; }
.actions { display: flex; gap: .4rem; }
</style>
