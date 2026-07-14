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
.page-container { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: .75rem; margin-bottom: 1.5rem; }
.page-header h1 { font-size: 1.4rem; font-weight: 600; }
.filters { display: flex; gap: .6rem; flex-wrap: wrap; }
.filters select, .filters input {
  padding: .4rem .75rem; border: 1px solid var(--border, #cbd5e1);
  border-radius: 6px; font-size: .9rem; background: var(--input-bg, #f8fafc);
}

.tickets-table-wrap { overflow-x: auto; }
.tickets-table { width: 100%; border-collapse: collapse; font-size: .9rem; }
.tickets-table th { text-align: left; padding: .6rem .75rem; border-bottom: 2px solid var(--border, #e2e8f0); color: var(--text-muted, #64748b); font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
.tickets-table td { padding: .6rem .75rem; border-bottom: 1px solid var(--border, #f1f5f9); }
.row-click { cursor: pointer; }
.row-click:hover td { background: var(--bg-subtle, #f8fafc); }
.center { text-align: center; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: var(--card-bg, #fff); border-radius: 10px;
  padding: 1.8rem; width: 100%; max-width: 680px; max-height: 90vh; overflow-y: auto;
}
.detalhe-header { display: flex; justify-content: space-between; align-items: center; gap: .75rem; margin-bottom: .5rem; flex-wrap: wrap; }
.detalhe-header h2 { font-size: 1.15rem; font-weight: 600; }
.detalhe-meta { font-size: .85rem; color: var(--text-muted, #64748b); margin-bottom: .6rem; }
.detalhe-desc { white-space: pre-wrap; margin-bottom: .75rem; }

.anexos-grid { display: flex; flex-wrap: wrap; gap: .6rem; margin-bottom: 1rem; }
.anexo-item { text-decoration: none; display: block; }
.anexo-thumb {
  width: 90px; height: 90px; object-fit: cover; border-radius: 7px;
  border: 1px solid var(--border, #e2e8f0); transition: opacity .15s;
}
.anexo-thumb:hover { opacity: .85; }
.anexo-doc {
  display: flex; align-items: center; gap: .35rem; padding: .5rem .75rem;
  background: var(--bg-subtle, #f1f5f9); border-radius: 7px; font-size: .85rem;
  color: var(--text, #334155);
}
.anexo-doc span { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.link-anexo { color: var(--primary, #3b82f6); font-size: .9rem; display: block; margin-bottom: 1rem; }

.status-select {
  padding: .35rem .6rem; border: 1px solid var(--border, #cbd5e1);
  border-radius: 6px; font-size: .85rem; background: var(--input-bg, #f8fafc);
}

.mensagens { display: flex; flex-direction: column; gap: .6rem; margin: 1rem 0; }
.mensagem { background: var(--bg-subtle, #f1f5f9); border-radius: 8px; padding: .7rem 1rem; }
.mensagem.admin { background: #eff6ff; border-left: 3px solid #3b82f6; }
.msg-author { font-weight: 600; font-size: .85rem; margin-bottom: .2rem; }
.msg-author small { color: #3b82f6; }
.msg-text { white-space: pre-wrap; font-size: .92rem; }
.msg-date { color: var(--text-muted, #94a3b8); font-size: .75rem; margin-top: .3rem; }
.empty-msg { color: var(--text-muted, #64748b); font-style: italic; font-size: .9rem; }

.reply-box { display: flex; flex-direction: column; gap: .5rem; margin-top: .75rem; }
.reply-box textarea {
  width: 100%; padding: .5rem .75rem; border: 1px solid var(--border, #cbd5e1);
  border-radius: 6px; font-size: .9rem; resize: vertical;
}
.btn-sm { font-size: .85rem; padding: .35rem .85rem; align-self: flex-end; }
.mt { margin-top: 1rem; }
.loading, .empty { text-align: center; color: var(--text-muted, #64748b); padding: 2rem; }

.badge-warning { background: #fef9c3; color: #854d0e; }
.badge-info    { background: #dbeafe; color: #1d4ed8; }
.badge-success { background: #dcfce7; color: #15803d; }
.badge-neutral { background: #f1f5f9; color: #475569; }
</style>
