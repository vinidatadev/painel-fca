<template>
  <div class="notif-panel-backdrop" @click.self="$emit('close')">
    <div class="notif-panel" role="dialog" aria-label="Notificações">
      <!-- Header -->
      <div class="notif-panel-header">
        <span class="notif-panel-title">Notificações</span>
        <div class="notif-panel-actions">
          <button v-if="unread > 0" class="notif-mark-all" @click="markAllRead">
            Marcar todas como lidas
          </button>
          <button class="notif-close-btn" @click="$emit('close')" aria-label="Fechar">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Lista -->
      <div class="notif-list" ref="listEl">
        <div v-if="loading" class="notif-empty">Carregando…</div>
        <div v-else-if="!items.length" class="notif-empty">Nenhuma notificação</div>

        <div
          v-for="n in items"
          :key="n.id"
          class="notif-item"
          :class="{ 'notif-unread': !n.lida, [`notif-tipo-${n.tipo}`]: true }"
          @click="onClickItem(n)"
        >
          <div class="notif-item-icon">
            <span v-if="n.tipo === 'comunicado'">📢</span>
            <span v-else-if="n.tipo === 'fca'">📋</span>
            <span v-else>🎫</span>
          </div>
          <div class="notif-item-body">
            <!-- imagem do comunicado -->
            <img
              v-if="n.imagem_url"
              :src="n.imagem_url"
              class="notif-item-img"
              alt=""
            />
            <div class="notif-item-titulo">{{ n.titulo }}</div>
            <div v-if="n.mensagem" class="notif-item-msg">{{ n.mensagem }}</div>
            <div class="notif-item-time">{{ fmtTime(n.created_at) }}</div>
          </div>
          <div v-if="!n.lida" class="notif-dot" aria-label="Não lida"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const emit = defineEmits(['close', 'update:unread'])
const router = useRouter()
const items = ref([])
const loading = ref(true)

const unread = computed(() => items.value.filter(n => !n.lida).length)

onMounted(load)

async function load() {
  loading.value = true
  try {
    items.value = await api.notifications.list()
  } catch { /* silencioso */ }
  loading.value = false
  emit('update:unread', unread.value)
}

async function markAllRead() {
  await api.notifications.markAllRead().catch(() => {})
  items.value.forEach(n => { n.lida = true })
  emit('update:unread', 0)
}

async function onClickItem(n) {
  if (!n.lida) {
    await api.notifications.markRead(n.id).catch(() => {})
    n.lida = true
    emit('update:unread', unread.value)
  }
  if (n.link_rota) {
    emit('close')
    router.push(n.link_rota)
  }
}

function fmtTime(iso) {
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return 'agora'
  if (diff < 3600) return `${Math.floor(diff / 60)}min`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

defineExpose({ load })
</script>

<style scoped>
.notif-panel-backdrop {
  position: fixed; inset: 0; z-index: 500;
}

.notif-panel {
  position: fixed; top: var(--topbar-height, 56px); right: var(--space-4, 16px);
  width: 360px; max-height: 520px;
  background: #fff; border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg, 12px); box-shadow: var(--shadow-lg, 0 8px 32px rgba(0,0,0,.12));
  display: flex; flex-direction: column; overflow: hidden;
  animation: notif-in 0.15s ease;
}
@keyframes notif-in {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.notif-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid var(--color-neutral-100);
  flex-shrink: 0;
}
.notif-panel-title {
  font-size: var(--font-size-sm, 14px); font-weight: 600;
  color: var(--color-neutral-800);
}
.notif-panel-actions { display: flex; align-items: center; gap: 8px; }
.notif-mark-all {
  font-size: 11px; color: var(--color-primary-600, #2563eb);
  background: none; border: none; cursor: pointer; padding: 0;
}
.notif-mark-all:hover { text-decoration: underline; }
.notif-close-btn {
  background: none; border: none; cursor: pointer;
  color: var(--color-neutral-400); display: flex; align-items: center; padding: 2px;
  border-radius: 4px;
}
.notif-close-btn:hover { background: var(--color-neutral-100); color: var(--color-neutral-700); }

.notif-list {
  overflow-y: auto; flex: 1;
}
.notif-empty {
  padding: 32px 16px; text-align: center;
  font-size: var(--font-size-sm, 14px); color: var(--color-neutral-400);
}

.notif-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 16px; cursor: pointer; position: relative;
  border-bottom: 1px solid var(--color-neutral-50);
  transition: background 0.12s;
}
.notif-item:hover { background: var(--color-neutral-50); }
.notif-unread { background: var(--color-primary-50, #eff6ff); }
.notif-unread:hover { background: #dbeafe; }

.notif-item-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.notif-item-body { flex: 1; min-width: 0; }
.notif-item-img {
  width: 100%; max-height: 140px; object-fit: cover;
  border-radius: 6px; margin-bottom: 6px;
}
.notif-item-titulo {
  font-size: 13px; font-weight: 600; color: var(--color-neutral-800);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.notif-item-msg {
  font-size: 12px; color: var(--color-neutral-500); margin-top: 2px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.notif-item-time {
  font-size: 11px; color: var(--color-neutral-400); margin-top: 4px;
}

.notif-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--color-primary-500, #3b82f6);
  flex-shrink: 0; margin-top: 4px;
}
</style>
