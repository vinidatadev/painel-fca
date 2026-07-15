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
          <th>Papel</th><th>Matrícula</th><th>Turno</th><th>Status</th><th>BI</th><th></th>
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
          <td>
            <button
              :class="['toggle-btn', u.acesso_relatorio ? 'toggle-on' : '']"
              :title="u.acesso_relatorio ? 'Revogar acesso BI' : 'Conceder acesso BI'"
              @click="toggleBiAccess(u)"
            >{{ u.acesso_relatorio ? '✓' : '—' }}</button>
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

async function toggleBiAccess(u) {
  try {
    const updated = await api.usuarios.patch(u.id, { acesso_relatorio: !u.acesso_relatorio })
    u.acesso_relatorio = updated.acesso_relatorio
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.filters-bar { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; margin-bottom: var(--space-4); padding: var(--space-3) var(--space-4); }
.filters-bar select {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); font-family: var(--font-family-base);
  background: var(--color-neutral-50); outline: none; cursor: pointer;
}
.filters-bar select:focus { border-color: var(--color-primary-500); }

.fca-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); padding: 0; }
.fca-table thead th {
  text-align: left; padding: var(--space-2) var(--space-4); font-weight: var(--font-weight-semibold);
  border-bottom: 2px solid var(--color-neutral-200); color: var(--color-neutral-500);
  font-size: var(--font-size-xs); text-transform: uppercase; background: var(--color-neutral-50);
}
.fca-table tbody td { padding: var(--space-2) var(--space-4); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.fca-table tbody tr.inactive td { opacity: .5; }
.fca-table tbody tr:hover td { background: var(--color-primary-50); }
.actions { display: flex; gap: var(--space-2); }

.toggle-btn {
  padding: var(--space-1) var(--space-2); border-radius: var(--radius-md);
  border: 1.5px solid var(--color-neutral-300); background: var(--color-neutral-50);
  cursor: pointer; font-size: var(--font-size-sm); color: var(--color-neutral-500);
  transition: all var(--transition-fast);
}
.toggle-btn.toggle-on {
  background: var(--color-success-bg); border-color: var(--color-success);
  color: var(--color-success-text); font-weight: var(--font-weight-semibold);
}
</style>
