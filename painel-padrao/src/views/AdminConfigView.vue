<template>
  <div>
    <div class="page-header">
      <h1>Configurações</h1>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs" :key="tab.tipo"
        :class="['tab-btn', { active: tipoAtivo === tab.tipo }]"
        @click="trocarTab(tab.tipo)"
      >{{ tab.label }}</button>
    </div>

    <div class="card">
      <div class="list-header">
        <h2 class="section-title" style="margin-bottom:0">{{ tabAtual.label }}</h2>
        <button class="btn btn-primary btn-sm" @click="abrirNovo">+ Adicionar</button>
      </div>

      <div v-if="loading" class="loading-text">Carregando...</div>

      <table v-else class="opcoes-table">
        <thead>
          <tr><th>Valor</th><th>Ordem</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="o in itens" :key="o.id" :class="{ inactive: !o.ativo }">
            <td>
              <span v-if="editandoId !== o.id">{{ o.valor }}</span>
              <input v-else v-model="editValor" class="inline-input" @keyup.enter="salvarEdicao(o)" @keyup.escape="editandoId = null" />
            </td>
            <td>
              <span v-if="editandoId !== o.id">{{ o.ordem }}</span>
              <input v-else v-model.number="editOrdem" type="number" class="inline-input small" />
            </td>
            <td>
              <span :class="['badge', o.ativo ? 'badge-encerrado' : 'badge-aguardando_devolutiva']">
                {{ o.ativo ? 'Ativo' : 'Inativo' }}
              </span>
            </td>
            <td class="actions">
              <template v-if="editandoId !== o.id">
                <button class="btn btn-sm btn-outline" @click="iniciarEdicao(o)">Editar</button>
                <button class="btn btn-sm btn-danger" @click="toggleAtivo(o)">
                  {{ o.ativo ? 'Desativar' : 'Ativar' }}
                </button>
              </template>
              <template v-else>
                <button class="btn btn-sm btn-primary" @click="salvarEdicao(o)">Salvar</button>
                <button class="btn btn-sm btn-secondary" @click="editandoId = null">Cancelar</button>
              </template>
            </td>
          </tr>
          <tr v-if="!itens.length">
            <td colspan="4" class="empty-state">Nenhum item cadastrado.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal novo item -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-box">
        <h3>Novo item — {{ tabAtual.label }}</h3>
        <form @submit.prevent="criarItem">
          <div class="form-group">
            <label>Valor *</label>
            <input v-model="novoValor" type="text" required autofocus />
          </div>
          <div class="form-group">
            <label>Ordem</label>
            <input v-model.number="novaOrdem" type="number" min="0" />
          </div>
          <p v-if="errorModal" class="error-msg">{{ errorModal }}</p>
          <div style="display:flex;gap:.6rem;margin-top:1rem">
            <button class="btn btn-primary" type="submit" :disabled="salvando">
              {{ salvando ? 'Salvando...' : 'Criar' }}
            </button>
            <button class="btn btn-secondary" type="button" @click="showModal = false">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const tabs = [
  { tipo: 'causa', label: 'Causas do FCA' },
  { tipo: 'acao',  label: 'Ações' },
  { tipo: 'uf',    label: 'UFs' },
]

const tipoAtivo  = ref('causa')
const itens      = ref([])
const loading    = ref(true)
const showModal  = ref(false)
const novoValor  = ref('')
const novaOrdem  = ref(999)
const errorModal = ref('')
const salvando   = ref(false)
const editandoId = ref(null)
const editValor  = ref('')
const editOrdem  = ref(0)

const tabAtual = computed(() => tabs.find(t => t.tipo === tipoAtivo.value))

async function load() {
  loading.value = true
  try {
    itens.value = await api.opcoes.adminList(tipoAtivo.value)
  } finally {
    loading.value = false
  }
}

async function trocarTab(tipo) {
  tipoAtivo.value = tipo
  editandoId.value = null
  await load()
}

function abrirNovo() {
  novoValor.value = ''
  novaOrdem.value = itens.value.length
  errorModal.value = ''
  showModal.value = true
}

async function criarItem() {
  errorModal.value = ''
  salvando.value = true
  try {
    await api.opcoes.create({ tipo: tipoAtivo.value, valor: novoValor.value, ordem: novaOrdem.value })
    showModal.value = false
    await load()
  } catch (e) {
    errorModal.value = e.message
  } finally {
    salvando.value = false
  }
}

function iniciarEdicao(o) {
  editandoId.value = o.id
  editValor.value = o.valor
  editOrdem.value = o.ordem
}

async function salvarEdicao(o) {
  try {
    await api.opcoes.update(o.id, { valor: editValor.value, ordem: editOrdem.value })
    editandoId.value = null
    await load()
  } catch (e) {
    alert(e.message)
  }
}

async function toggleAtivo(o) {
  const acao = o.ativo ? 'desativar' : 'ativar'
  if (!confirm(`${acao.charAt(0).toUpperCase() + acao.slice(1)} "${o.valor}"?`)) return
  try {
    if (o.ativo) {
      await api.opcoes.remove(o.id)
    } else {
      await api.opcoes.update(o.id, { ativo: true })
    }
    await load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.tabs { display: flex; gap: var(--space-1); margin-bottom: var(--space-5); background: var(--color-neutral-100); padding: 3px; border-radius: var(--radius-full); width: fit-content; }
.tab-btn {
  padding: var(--space-2) var(--space-4); border: none; border-radius: var(--radius-full);
  background: transparent; cursor: pointer; font-size: var(--font-size-sm);
  color: var(--color-neutral-500); font-family: var(--font-family-base);
  transition: background var(--transition-fast), color var(--transition-fast);
}
.tab-btn:hover { color: var(--color-primary-700); }
.tab-btn.active { background: #fff; color: var(--color-primary-700); font-weight: var(--font-weight-semibold); box-shadow: var(--shadow-sm); }

.list-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }

.opcoes-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.opcoes-table th {
  text-align: left; padding: var(--space-2) var(--space-3); font-weight: var(--font-weight-semibold);
  border-bottom: 2px solid var(--color-neutral-200); color: var(--color-neutral-500);
  font-size: var(--font-size-xs); text-transform: uppercase; background: var(--color-neutral-50);
}
.opcoes-table td { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.opcoes-table tr.inactive td { opacity: .5; }
.opcoes-table tr:hover td { background: var(--color-primary-50); }
.actions { display: flex; gap: var(--space-2); }

.inline-input {
  padding: var(--space-1) var(--space-2); border: 1.5px solid var(--color-primary-400);
  border-radius: var(--radius-sm); font-size: var(--font-size-sm);
  font-family: var(--font-family-base); outline: none; width: 100%;
}
.inline-input.small { width: 70px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 500; padding: var(--space-4); }
.modal-box {
  background: #fff; border-radius: var(--radius-xl); padding: var(--space-6);
  min-width: 360px; box-shadow: var(--shadow-lg); border: 1px solid var(--color-neutral-100);
}
.modal-box h3 { font-size: var(--font-size-base); font-weight: var(--font-weight-bold); margin-bottom: var(--space-5); color: var(--color-neutral-900); }
</style>
