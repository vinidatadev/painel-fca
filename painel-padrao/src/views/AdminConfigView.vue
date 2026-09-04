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
      <!-- Aba dedicada: Empresas por Área -->
      <template v-if="tipoAtivo === 'area_empresa'">
        <div class="list-header">
          <h2 class="section-title" style="margin-bottom:0">Empresas por Área</h2>
        </div>
        <form @submit.prevent="criarVinculo" class="vinculo-form">
          <select v-model="vinculoArea" required>
            <option value="">Área...</option>
            <option v-for="a in opcoes.areas" :key="a" :value="a">{{ a }}</option>
          </select>
          <select v-model="vinculoEmpresa" required>
            <option value="">Empresa...</option>
            <option v-for="e in opcoes.empresas" :key="e" :value="e">{{ e }}</option>
          </select>
          <button class="btn btn-primary btn-sm" type="submit" :disabled="salvando || !vinculoArea || !vinculoEmpresa">
            {{ salvando ? 'Salvando...' : '+ Vincular' }}
          </button>
          <p v-if="errorVinculo" class="error-msg" style="margin:0">{{ errorVinculo }}</p>
        </form>

        <div v-if="loading" class="loading-text">Carregando...</div>
        <table v-else class="opcoes-table">
          <thead>
            <tr><th>Área</th><th>Empresa</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="v in itens" :key="v.id" :class="{ inactive: !v.ativo }">
              <td>{{ v.area }}</td>
              <td>{{ v.empresa }}</td>
              <td>
                <span :class="['badge', v.ativo ? 'badge-encerrado' : 'badge-aguardando_devolutiva']">
                  {{ v.ativo ? 'Ativo' : 'Inativo' }}
                </span>
              </td>
              <td class="actions">
                <button class="btn btn-sm btn-danger" @click="toggleVinculo(v)">
                  {{ v.ativo ? 'Desativar' : 'Ativar' }}
                </button>
              </td>
            </tr>
            <tr v-if="!itens.length">
              <td colspan="4" class="empty-state">Nenhum vínculo cadastrado.</td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- Aba dedicada: Dicas dos Campos -->
      <template v-else-if="tipoAtivo === 'campo_dica'">
        <div class="list-header">
          <h2 class="section-title" style="margin-bottom:0">Dicas dos Campos</h2>
        </div>
        <form @submit.prevent="criarDica" class="vinculo-form">
          <select v-model="dicaCampo" required>
            <option value="">Campo...</option>
            <option v-for="c in CAMPOS_DICA" :key="c.key" :value="c.key">{{ c.label }}</option>
          </select>
          <input v-model="dicaTitulo" type="text" placeholder="Título (opcional)" class="inline-input" style="flex:1;min-width:160px" />
          <input v-model="dicaTexto" type="text" placeholder="Texto de orientação (aparece no tooltip)" class="inline-input" style="flex:2;min-width:280px" />
          <button class="btn btn-primary btn-sm" type="submit" :disabled="salvando || !dicaCampo || !dicaTexto.trim()">
            {{ salvando ? 'Salvando...' : '+ Adicionar' }}
          </button>
          <p v-if="errorDica" class="error-msg" style="margin:0">{{ errorDica }}</p>
        </form>

        <div v-if="loading" class="loading-text">Carregando...</div>
        <table v-else class="opcoes-table">
          <thead>
            <tr><th>Campo</th><th>Título</th><th>Texto</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="d in itens" :key="d.id" :class="{ inactive: !d.ativo }">
              <td>{{ labelCampo(d.campo) }}</td>
              <td>
                <span v-if="editandoId !== d.id">{{ d.titulo || '—' }}</span>
                <input v-else v-model="editTitulo" class="inline-input" @keyup.enter="salvarDica(d)" @keyup.escape="editandoId = null" />
              </td>
              <td>
                <span v-if="editandoId !== d.id">{{ d.texto }}</span>
                <input v-else v-model="editTexto" class="inline-input" @keyup.enter="salvarDica(d)" @keyup.escape="editandoId = null" />
              </td>
              <td>
                <span :class="['badge', d.ativo ? 'badge-encerrado' : 'badge-aguardando_devolutiva']">
                  {{ d.ativo ? 'Ativo' : 'Inativo' }}
                </span>
              </td>
              <td class="actions">
                <template v-if="editandoId !== d.id">
                  <button class="btn btn-sm btn-outline" @click="iniciarEdicaoDica(d)">Editar</button>
                  <button class="btn btn-sm btn-danger" @click="toggleDica(d)">
                    {{ d.ativo ? 'Desativar' : 'Ativar' }}
                  </button>
                </template>
                <template v-else>
                  <button class="btn btn-sm btn-primary" @click="salvarDica(d)">Salvar</button>
                  <button class="btn btn-sm btn-secondary" @click="editandoId = null">Cancelar</button>
                </template>
              </td>
            </tr>
            <tr v-if="!itens.length">
              <td colspan="5" class="empty-state">Nenhuma dica cadastrada.</td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- Abas genéricas -->
      <template v-else>
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
      </template>
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
  { tipo: 'empresa', label: 'Empresas' },
  { tipo: 'area',    label: 'Áreas' },
  { tipo: 'area_empresa', label: 'Empresas por Área' },
  { tipo: 'campo_dica', label: 'Dicas dos Campos' },
  { tipo: 'causa', label: 'Causas do FCA' },
  { tipo: 'subsetor_causador', label: 'Sub-Setores Causadores' },
  { tipo: 'acao',  label: 'Ações' },
  { tipo: 'uf',    label: 'UFs da Remessa' },
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

const opcoes = ref({ areas: [], empresas: [] })
const vinculoArea = ref('')
const vinculoEmpresa = ref('')
const errorVinculo = ref('')

const CAMPOS_DICA = [
  { key: 'causa', label: 'Causa do FCA' },
  { key: 'subsetor_causador', label: 'Sub-Setor Causador' },
  { key: 'area_causadora', label: 'Área Causadora' },
  { key: 'empresa_causadora', label: 'Empresa do Causador' },
  { key: 'acao', label: 'Ação' },
  { key: 'uf', label: 'UF da Remessa' },
  { key: 'remessas', label: 'Número(s) da Remessa' },
  { key: 'dts', label: 'DT' },
  { key: 'cod_materiais', label: 'Cod Material' },
  { key: 'ordens_venda', label: 'Ordem de Venda' },
  { key: 'detalhe', label: 'Detalhe / Observação' },
  { key: 'anexos', label: 'Evidências / Anexos' },
  { key: 'problema_solucionado', label: 'Problema Solucionado? (tratativa)' },
  { key: 'devolutiva', label: 'Devolutiva da Tratativa' },
  { key: 'encaminhar', label: 'Encaminhar para outro setor?' },
  { key: 'apontar_causa', label: 'Apontar Causa' },
]
const dicaCampo = ref('')
const dicaTitulo = ref('')
const dicaTexto = ref('')
const errorDica = ref('')
const editTitulo = ref('')
const editTexto = ref('')

function labelCampo(key) {
  return CAMPOS_DICA.find(c => c.key === key)?.label || key
}

async function criarDica() {
  errorDica.value = ''
  salvando.value = true
  try {
    await api.opcoes.createDica({ campo: dicaCampo.value, titulo: dicaTitulo.value || null, texto: dicaTexto.value })
    dicaCampo.value = ''
    dicaTitulo.value = ''
    dicaTexto.value = ''
    await load()
  } catch (e) {
    errorDica.value = e.message
  } finally {
    salvando.value = false
  }
}

function iniciarEdicaoDica(d) {
  editandoId.value = d.id
  editTitulo.value = d.titulo || ''
  editTexto.value = d.texto
}

async function salvarDica(d) {
  try {
    await api.opcoes.updateDica(d.id, { titulo: editTitulo.value || null, texto: editTexto.value })
    editandoId.value = null
    await load()
  } catch (e) {
    alert(e.message)
  }
}

async function toggleDica(d) {
  const acao = d.ativo ? 'desativar' : 'ativar'
  if (!confirm(`${acao.charAt(0).toUpperCase() + acao.slice(1)} a dica "${labelCampo(d.campo)}"?`)) return
  try {
    if (d.ativo) {
      await api.opcoes.removeDica(d.id)
    } else {
      await api.opcoes.updateDica(d.id, { ativo: true })
    }
    await load()
  } catch (e) {
    alert(e.message)
  }
}

const tabAtual = computed(() => tabs.find(t => t.tipo === tipoAtivo.value))

async function carregarOpcoes() {
  try { opcoes.value = await api.opcoes.get() } catch (e) { /* opções opcionais */ }
}

async function load() {
  loading.value = true
  try {
    if (tipoAtivo.value === 'area_empresa') {
      itens.value = await api.opcoes.areasEmpresas()
    } else if (tipoAtivo.value === 'campo_dica') {
      itens.value = await api.opcoes.dicasAdmin()
    } else {
      itens.value = await api.opcoes.adminList(tipoAtivo.value)
    }
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

async function criarVinculo() {
  errorVinculo.value = ''
  salvando.value = true
  try {
    await api.opcoes.createAreaEmpresa({ area: vinculoArea.value, empresa: vinculoEmpresa.value })
    vinculoArea.value = ''
    vinculoEmpresa.value = ''
    await load()
  } catch (e) {
    errorVinculo.value = e.message
  } finally {
    salvando.value = false
  }
}

async function toggleVinculo(v) {
  const acao = v.ativo ? 'desativar' : 'ativar'
  if (!confirm(`${acao.charAt(0).toUpperCase() + acao.slice(1)} vínculo "${v.area}" + "${v.empresa}"?`)) return
  try {
    if (v.ativo) {
      await api.opcoes.removeAreaEmpresa(v.id)
    } else {
      await api.opcoes.updateAreaEmpresa(v.id, { ativo: true })
    }
    await load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(async () => {
  await carregarOpcoes()
  await load()
})
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

.vinculo-form {
  display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap;
  margin-bottom: var(--space-4);
}
.vinculo-form select {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm);
  font-family: var(--font-family-base); background: var(--color-neutral-50); outline: none;
  min-width: 180px; cursor: pointer;
}
.vinculo-form select:focus { border-color: var(--color-primary-500); }

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
