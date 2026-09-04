<template>
  <div>
    <div class="page-header">
      <h1>{{ isEdit ? 'Editar Usuário' : 'Novo Usuário' }}</h1>
      <RouterLink to="/admin/usuarios" class="btn btn-secondary btn-sm">← Voltar</RouterLink>
    </div>

    <div class="card">
      <div v-if="loading" class="loading-text">Carregando...</div>

      <form v-else @submit.prevent="submit">
        <div class="form-grid">
          <div class="form-group">
            <label>Nome completo *</label>
            <input v-model="form.name" type="text" required minlength="2" />
          </div>

          <div class="form-group">
            <label>E-mail *</label>
            <input v-model="form.email" type="email" required :disabled="isEdit" />
          </div>

          <div class="form-group" v-if="form.auth_provider === 'local'">
            <label>{{ isEdit ? 'Nova Senha (deixe em branco para manter)' : 'Senha *' }}</label>
            <input v-model="form.password" type="password" :required="!isEdit && form.auth_provider === 'local'" minlength="8" placeholder="Mínimo 8 caracteres" />
          </div>

          <div class="form-group" style="grid-column: 1 / -1">
            <label>Setores / Empresas * <span style="font-weight:normal;color:var(--color-neutral-400)">— um é o principal</span></label>
            <div class="vinculos-list">
              <div v-for="(v, i) in form.setores" :key="i" class="vinculo-row">
                <select v-model="v.empresa" required @change="v.setor = ''">
                  <option value="">Empresa...</option>
                  <option v-for="e in EMPRESAS" :key="e" :value="e">{{ e }}</option>
                </select>
                <select v-model="v.setor" required :disabled="!v.empresa">
                  <option value="">Setor...</option>
                  <option v-for="s in setoresPorEmpresa(v.empresa)" :key="s" :value="s">{{ s }}</option>
                </select>
                <label class="principal-opt" title="Define o setor principal (exibido no perfil)">
                  <input type="radio" :name="'vinculo-principal'" :checked="v.principal" @change="marcarPrincipal(i)" />
                  Principal
                </label>
                <button type="button" class="btn btn-secondary btn-sm" :disabled="form.setores.length === 1" @click="removerVinculo(i)">✕</button>
              </div>
              <button type="button" class="btn btn-ghost btn-sm" @click="adicionarVinculo">+ Adicionar setor/empresa</button>
            </div>
          </div>

          <div class="form-group">
            <label>Tipo de Login *</label>
            <select v-model="form.auth_provider" required @change="form.password = ''">
              <option value="local">Local (e-mail + senha)</option>
              <option value="microsoft">Microsoft (sem senha)</option>
            </select>
          </div>

          <div class="form-group">
            <label>Papel *</label>
            <select v-model="form.role" required>
              <option value="user">Usuário</option>
              <option value="admin">Administrador</option>
            </select>
          </div>

          <div class="form-group">
            <label>Matrícula</label>
            <input v-model="form.matricula" type="text" placeholder="Número de matrícula" />
          </div>

          <div class="form-group">
            <label>Turno</label>
            <select v-model="form.turno">
              <option value="">—</option>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>
        <p v-if="success" class="success-msg">{{ success }}</p>

        <div style="display:flex;gap:.75rem;margin-top:1.25rem">
          <button class="btn btn-primary" type="submit" :disabled="submitting">
            {{ submitting ? 'Salvando...' : (isEdit ? 'Salvar Alterações' : 'Criar Usuário') }}
          </button>
          <RouterLink to="/admin/usuarios" class="btn btn-secondary">Cancelar</RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route  = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)

const loading   = ref(false)
const submitting = ref(false)
const error     = ref('')
const success   = ref('')
const form = ref({
  name: '', email: '', password: '', auth_provider: 'local', role: 'user',
  matricula: '', turno: '',
  setores: [{ setor: '', empresa: '', principal: true }],
})

const opcoes = ref({ empresas: [], areas: [], empresas_por_area: {} })
const EMPRESAS = computed(() => opcoes.value.empresas || [])

function setoresPorEmpresa(empresa) {
  if (!empresa) return []
  const areas = []
  for (const [area, empresas] of Object.entries(opcoes.value.empresas_por_area || {})) {
    if (empresas.includes(empresa)) areas.push(area)
  }
  return areas
}

function adicionarVinculo() {
  form.value.setores.push({ setor: '', empresa: '', principal: false })
}

function removerVinculo(i) {
  if (form.value.setores.length === 1) return
  form.value.setores.splice(i, 1)
  garantirPrincipal()
}

function marcarPrincipal(i) {
  form.value.setores.forEach((v, idx) => { v.principal = idx === i })
}

function garantirPrincipal() {
  if (!form.value.setores.some(v => v.principal) && form.value.setores.length) {
    form.value.setores[0].principal = true
  }
}

onMounted(async () => {
  try {
    opcoes.value = await api.opcoes.get()
  } catch (e) {
    error.value = 'Erro ao carregar opções: ' + e.message
  }
  if (!isEdit.value) return
  loading.value = true
  try {
    const u = await api.usuarios.get(route.params.id)
    const vinculos = (u.setores && u.setores.length)
      ? u.setores.map(s => ({ setor: s.setor, empresa: s.empresa, principal: s.principal }))
      : [{ setor: u.sector, empresa: u.company, principal: true }]
    form.value = { ...u, password: '', setores: vinculos }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

async function submit() {
  error.value = ''
  success.value = ''
  const setoresValidos = form.value.setores.filter(v => v.setor && v.empresa)
  if (!setoresValidos.length) {
    error.value = 'Informe ao menos um setor/empresa.'
    return
  }
  if (!setoresValidos.some(v => v.principal)) setoresValidos[0].principal = true

  submitting.value = true
  try {
    const payload = { ...form.value, setores: setoresValidos }
    delete payload.company
    delete payload.sector
    if (!payload.password) delete payload.password
    if (!payload.matricula) delete payload.matricula
    if (!payload.turno) delete payload.turno

    if (isEdit.value) {
      await api.usuarios.update(route.params.id, payload)
      success.value = 'Usuário atualizado com sucesso.'
    } else {
      await api.usuarios.create(payload)
      router.push('/admin/usuarios')
    }
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3) var(--space-6); }
.success-msg { color: var(--color-success-text); font-size: var(--font-size-sm); margin-top: var(--space-2); background: var(--color-success-bg); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); }

.vinculos-list { display: flex; flex-direction: column; gap: var(--space-2); }
.vinculo-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }
.vinculo-row select {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--font-size-sm);
  font-family: var(--font-family-base); outline: none; flex: 1; min-width: 180px;
}
.vinculo-row select:focus { border-color: var(--color-primary-500); }
.principal-opt {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: var(--font-size-xs); color: var(--color-neutral-600);
  cursor: pointer; white-space: nowrap;
}

@media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
</style>
