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

          <div class="form-group">
            <label>Empresa *</label>
            <select v-model="form.company" required @change="form.sector = ''">
              <option value="">Selecione...</option>
              <option v-for="e in EMPRESAS" :key="e" :value="e">{{ e }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>Setor *</label>
            <select v-model="form.sector" required :disabled="!form.company">
              <option value="">Selecione...</option>
              <option v-for="s in setoresDisponiveis" :key="s" :value="s">{{ s }}</option>
            </select>
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

const EMPRESAS = ['ACI_MATRIZ', 'ACI_FILIAL', 'SINOBRAS', 'ACC']
const SETORES_POR_EMPRESA = {
  ACI_MATRIZ: ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  ACI_FILIAL: ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  SINOBRAS:   ['ACL', 'PCP', 'Qualidade', 'MEP', 'Expedicao', 'Producao'],
  ACC:        ['Comercial', 'Customer_Service'],
}

const loading   = ref(false)
const submitting = ref(false)
const error     = ref('')
const success   = ref('')
const form = ref({ name: '', email: '', password: '', auth_provider: 'local', company: '', sector: '', role: 'user', matricula: '', turno: '' })

const setoresDisponiveis = computed(() => SETORES_POR_EMPRESA[form.value.company] || [])

onMounted(async () => {
  if (!isEdit.value) return
  loading.value = true
  try {
    const u = await api.usuarios.get(route.params.id)
    form.value = { ...u, password: '' }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

async function submit() {
  error.value = ''
  success.value = ''
  submitting.value = true
  try {
    const payload = { ...form.value }
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
.loading-text { color: #888; padding: 1.5rem; text-align: center; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem 1.25rem; }
.success-msg { color: #059669; font-size: .875rem; margin-top: .5rem; }

@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
