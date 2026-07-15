<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Painel de Help / Suporte</h1>
      <div class="filters">
        <select v-model="filterStatus" @change="applyFilter">
          <option value="">Todos os status</option>
          <option value="aberto">Aberto</option>
          <option value="em_andamento">Em andamento</option>
          <option value="resolvido">Resolvido</option>
          <option value="fechado">Fechado</option>
        </select>
        <input v-model="search" placeholder="Buscar por título..." @input="applyFilter" />
      </div>
    </div>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="filtered.length === 0" class="empty">Nenhum ticket encontrado.</div>

    <div v-else class="tickets-table-wrap">
      <table class="tickets-table">
        <thead>
          <tr>
            <th>Título</th>
            <th>Usuário</th>
            <th>Status</th>
            <th>Abertura</th>
            <th>Respostas</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in filtered" :key="t.id" @click="openTicket(t)" class="row-click">
            <td>{{ t.titulo }}</td>
            <td>{{ t.created_by.name }}</td>
            <td><span class="badge" :class="badgeClass(t.status)">{{ labelStatus(t.status) }}</span></td>
            <td>{{ fmtDate(t.created_at) }}</td>
            <td class="center">{{ t.mensagens.length }}</td>
            <td class="center"><button class="btn btn-outline btn-sm" @click.stop="openTicket(t)">Ver</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Detalhe / resposta admin -->
    <div v-if="selected" class="modal-overlay" @click.self="selected = null">
      <div class="modal-box">
        <div class="detalhe-header">
          <h2>{{ selected.titulo }}</h2>
          <select v-model="newStatus" class="status-select" @change="changeStatus">
            <option value="aberto">Aberto</option>
            <option value="em_andamento">Em andamento</option>
            <option value="resolvido">Resolvido</option>
            <option value="fechado">Fechado</option>
          </select>
        </div>
        <p class="detalhe-meta">
          Aberto por <strong>{{ selected.created_by.name }}</strong> ({{ selected.created_by.email }}) em {{ fmtDate(selected.created_at) }}
        </p>
        <p class="detalhe-desc">{{ selected.descricao }}</p>

        <div v-if="selected.anexos?.length" class="anexos-grid">
          <a v-for="a in selected.anexos" :key="a.key" :href="a.url" target="_blank" class="anexo-item">
            <img v-if="a.is_image" :src="a.url" class="anexo-thumb" />
            <div v-else class="anexo-doc">📄 <span>{{ a.key.split('/').pop() }}</span></div>
          </a>
        </div>

        <div class="mensagens">
          <div v-for="m in selected.mensagens" :key="m.id" class="mensagem" :class="{ admin: m.autor.role === 'admin' }">
            <div class="msg-author">
              {{ m.autor.name }}
              <small v-if="m.autor.role === 'admin'">(Suporte)</small>
            </div>
            <div class="msg-text">{{ m.texto }}</div>
            <div class="msg-date">{{ fmtDate(m.created_at) }}</div>
          </div>
          <div v-if="selected.mensagens.length === 0" class="empty-msg">Sem mensagens ainda.</div>
        </div>

        <div class="reply-box">
          <textarea v-model="replyText" rows="3" placeholder="Responder ao usuário..."></textarea>
          <button class="btn btn-primary btn-sm" :disabled="!replyText.trim() || sendingReply" @click="sendReply">
            {{ sendingReply ? 'Enviando...' : 'Responder' }}
          </button>
        </div>
        <button class="btn btn-outline btn-sm mt" @click="selected = null">Fechar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import { api } from '../api'

const user = inject('user')
const registerWsListener = inject('registerWsListener')

const tickets = ref([])
const loading = ref(false)
const selected = ref(null)
const replyText = ref('')
const sendingReply = ref(false)
const newStatus = ref('aberto')
const filterStatus = ref('')
const search = ref('')

const filtered = computed(() => {
  return tickets.value.filter(t => {
    const matchStatus = !filterStatus.value || t.status === filterStatus.value
    const matchSearch = !search.value || t.titulo.toLowerCase().includes(search.value.toLowerCase())
    return matchStatus && matchSearch
  })
})

async function load() {
  loading.value = true
  try { tickets.value = await api.help.list() }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}

onMounted(() => {
  load()
  registerWsListener?.((evt) => {
    if (evt === 'help_ticket_novo' || evt === 'help_ticket_atualizado') load()
  })
})

function applyFilter() { /* computed reativo, nada a fazer */ }

async function openTicket(t) {
  try {
    selected.value = await api.help.get(t.id)
    newStatus.value = selected.value.status
    replyText.value = ''
  } catch (e) { console.error(e) }
}

async function sendReply() {
  if (!replyText.value.trim()) return
  sendingReply.value = true
  try {
    await api.help.responder(selected.value.id, replyText.value)
    replyText.value = ''
    selected.value = await api.help.get(selected.value.id)
    newStatus.value = selected.value.status
    await load()
  } catch (e) { console.error(e) }
  finally { sendingReply.value = false }
}

async function changeStatus() {
  try {
    await api.help.status(selected.value.id, newStatus.value)
    selected.value = await api.help.get(selected.value.id)
    await load()
  } catch (e) { console.error(e) }
}

function labelStatus(s) {
  return { aberto: 'Aberto', em_andamento: 'Em andamento', resolvido: 'Resolvido', fechado: 'Fechado' }[s] || s
}
function badgeClass(s) {
  return { aberto: 'badge-warning', em_andamento: 'badge-info', resolvido: 'badge-success', fechado: 'badge-neutral' }[s] || ''
}
function fmtDate(iso) {
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.filters { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.filters select, .filters input {
  padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200);
  border-radius: var(--radius-md); font-size: var(--font-size-sm);
  background: var(--color-neutral-50); font-family: var(--font-family-base); outline: none;
}
.filters select:focus, .filters input:focus { border-color: var(--color-primary-500); }

.tickets-table-wrap { overflow-x: auto; }
.tickets-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.tickets-table th {
  text-align: left; padding: var(--space-2) var(--space-3);
  border-bottom: 2px solid var(--color-neutral-200); color: var(--color-neutral-500);
  font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: .05em;
  background: var(--color-neutral-50);
}
.tickets-table td { padding: var(--space-3) var(--space-3); border-bottom: 1px solid var(--color-neutral-100); vertical-align: middle; }
.row-click { cursor: pointer; }
.row-click:hover td { background: var(--color-primary-50); }
.center { text-align: center; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 500; padding: var(--space-4); }
.modal-box {
  background: #fff; border-radius: var(--radius-xl); padding: var(--space-6);
  width: 100%; max-width: 700px; max-height: 90vh; overflow-y: auto; box-shadow: var(--shadow-lg);
}
.detalhe-header { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); margin-bottom: var(--space-3); flex-wrap: wrap; }
.detalhe-header h2 { font-size: var(--font-size-lg); font-weight: var(--font-weight-semibold); }
.detalhe-meta { font-size: var(--font-size-sm); color: var(--color-neutral-500); margin-bottom: var(--space-3); }
.detalhe-desc { white-space: pre-wrap; font-size: var(--font-size-sm); color: var(--color-neutral-700); margin-bottom: var(--space-4); line-height: 1.6; }

.status-select {
  padding: var(--space-1) var(--space-3); border: 1.5px solid var(--color-neutral-300);
  border-radius: var(--radius-md); font-size: var(--font-size-sm); background: var(--color-neutral-50);
  font-family: var(--font-family-base); outline: none; cursor: pointer;
}
.status-select:focus { border-color: var(--color-primary-500); }

.anexos-grid { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-4); }
.anexo-item { text-decoration: none; }
.anexo-thumb { width: 88px; height: 88px; object-fit: cover; border-radius: var(--radius-md); border: 1px solid var(--color-neutral-200); transition: opacity var(--transition-fast); }
.anexo-thumb:hover { opacity: .8; }
.anexo-doc { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--color-neutral-100); border-radius: var(--radius-md); font-size: var(--font-size-xs); color: var(--color-neutral-600); }

.mensagens { display: flex; flex-direction: column; gap: var(--space-2); margin: var(--space-4) 0; }
.mensagem { background: var(--color-neutral-50); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); border: 1px solid var(--color-neutral-100); }
.mensagem.admin { background: var(--color-primary-50); border-left: 3px solid var(--color-primary-500); border-color: var(--color-primary-100); }
.msg-author { font-weight: var(--font-weight-semibold); font-size: var(--font-size-sm); margin-bottom: var(--space-1); color: var(--color-neutral-800); }
.msg-author small { color: var(--color-primary-600); font-weight: var(--font-weight-medium); margin-left: var(--space-1); }
.msg-text { white-space: pre-wrap; font-size: var(--font-size-sm); color: var(--color-neutral-700); line-height: 1.5; }
.msg-date { color: var(--color-neutral-400); font-size: var(--font-size-xs); margin-top: var(--space-1); }
.empty-msg { color: var(--color-neutral-400); font-style: italic; font-size: var(--font-size-sm); text-align: center; padding: var(--space-4) 0; }

.reply-box { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-3); background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: var(--radius-md); padding: var(--space-3); }
.reply-box textarea { width: 100%; padding: var(--space-2) var(--space-3); border: 1.5px solid var(--color-neutral-200); border-radius: var(--radius-md); font-size: var(--font-size-sm); resize: vertical; font-family: var(--font-family-base); outline: none; }
.reply-box textarea:focus { border-color: var(--color-primary-500); }
.reply-box .btn { align-self: flex-end; }

.badge-warning { background: var(--color-warning-bg); color: var(--color-warning-text); }
.badge-info    { background: var(--color-info-bg);    color: var(--color-info-text); }
.badge-success { background: var(--color-success-bg); color: var(--color-success-text); }
.badge-neutral { background: var(--color-neutral-100); color: var(--color-neutral-500); }
</style>
