<template>
  <div class="onb-wrapper">
    <div class="onb-container">
      <!-- Header -->
      <div class="onb-header">
        <div class="onb-logo">
          <svg width="32" height="32" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="var(--color-primary-500)"/>
            <path d="M7 14h14M7 9h9M7 19h11" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <span>Sistema FCA</span>
        </div>
        <div class="onb-progress-text">
          {{ assistidos }} de {{ videos.length }} vídeos assistidos
        </div>
      </div>

      <!-- Progress bar -->
      <div class="onb-progress-bar-wrap">
        <div class="onb-progress-bar" :style="{ width: progressPct + '%' }"></div>
      </div>

      <!-- Concluído -->
      <div v-if="allDone" class="onb-done">
        <div class="onb-done-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <circle cx="28" cy="28" r="27" stroke="var(--color-primary-500)" stroke-width="2"/>
            <path d="M16 28l8 8 16-16" stroke="var(--color-primary-500)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h2>Tudo certo!</h2>
        <p>Você concluiu o onboarding e está pronto para usar o sistema.</p>
        <button class="btn-primary" @click="emit('done')">Acessar o sistema</button>
      </div>

      <!-- Player + lista -->
      <div v-else class="onb-body">
        <!-- Vídeo ativo -->
        <div class="onb-player-wrap" v-if="currentVideo">
          <div class="onb-video-meta">
            <span class="onb-badge">{{ currentIndex + 1 }} / {{ videos.length }}</span>
            <h2 class="onb-video-title">{{ currentVideo.titulo }}</h2>
            <p v-if="currentVideo.descricao" class="onb-video-desc">{{ currentVideo.descricao }}</p>
          </div>

          <div class="onb-player" v-if="videoUrl">
            <video
              ref="videoEl"
              :src="videoUrl"
              controls
              controlslist="nodownload"
              @ended="onVideoEnded"
              @timeupdate="onTimeUpdate"
              class="onb-video-el"
            ></video>
            <div v-if="!canConclude" class="onb-watch-hint">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3.5l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              Assista pelo menos 90% do vídeo para continuar
            </div>
          </div>
          <div v-else-if="loadingUrl" class="onb-loading">Carregando vídeo...</div>

          <button
            class="btn-primary onb-btn-conclude"
            :disabled="!canConclude || concluding"
            @click="concludeVideo"
          >
            <span v-if="concluding" class="btn-spinner"></span>
            <span v-else>
              {{ currentIndex + 1 < videos.length ? 'Próximo vídeo →' : 'Concluir onboarding' }}
            </span>
          </button>
        </div>

        <!-- Lista de vídeos -->
        <div class="onb-list">
          <div
            v-for="(v, i) in videos"
            :key="v.id"
            class="onb-list-item"
            :class="{
              'is-current': i === currentIndex,
              'is-done': v.assistido,
              'is-locked': !v.liberado && !v.assistido,
            }"
            @click="v.liberado || v.assistido ? selectVideo(i) : null"
          >
            <div class="onb-item-num">
              <svg v-if="v.assistido" width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="8" fill="var(--color-primary-500)"/><path d="M4.5 8l2.5 2.5 4-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <svg v-else-if="!v.liberado" width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="7" width="8" height="7" rx="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 7V5a2.5 2.5 0 015 0v2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <div class="onb-item-info">
              <span class="onb-item-title">{{ v.titulo }}</span>
              <span class="onb-item-status">
                {{ v.assistido ? 'Assistido' : v.liberado ? 'Disponível' : 'Bloqueado' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api.js'

const emit = defineEmits(['done'])

const videos = ref([])
const currentIndex = ref(0)
const videoUrl = ref(null)
const loadingUrl = ref(false)
const canConclude = ref(false)
const concluding = ref(false)
const videoEl = ref(null)
const allDone = ref(false)

const currentVideo = computed(() => videos.value[currentIndex.value] ?? null)
const assistidos = computed(() => videos.value.filter(v => v.assistido).length)
const progressPct = computed(() =>
  videos.value.length ? (assistidos.value / videos.value.length) * 100 : 0
)

onMounted(async () => {
  await loadVideos()
})

async function loadVideos() {
  try {
    const data = await api.onboarding.videos()
    videos.value = data
    if (!data.length) {
      allDone.value = true
      return
    }
    if (data.every(v => v.assistido)) {
      allDone.value = true
      return
    }
    const idx = data.findIndex(v => !v.assistido)
    currentIndex.value = idx >= 0 ? idx : 0
    await loadVideoUrl()
  } catch {
    // silencia
  }
}

async function loadVideoUrl() {
  videoUrl.value = null
  canConclude.value = false
  const v = currentVideo.value
  if (!v || v.assistido) return
  loadingUrl.value = true
  try {
    const data = await api.onboarding.videoUrl(v.id)
    videoUrl.value = data.url
  } catch {
    // sem url
  } finally {
    loadingUrl.value = false
  }
}

function onVideoEnded() {
  canConclude.value = true
}

function onTimeUpdate() {
  if (!videoEl.value || canConclude.value) return
  const { currentTime, duration } = videoEl.value
  if (duration > 0 && currentTime / duration >= 0.9) {
    canConclude.value = true
  }
}

async function concludeVideo() {
  const v = currentVideo.value
  if (!v) return
  concluding.value = true
  try {
    const data = await api.onboarding.concluir(v.id)
    v.assistido = true
    if (data.onboarding_completed) {
      allDone.value = true
      return
    }
    const next = videos.value.findIndex((vid, i) => i > currentIndex.value && !vid.assistido)
    if (next >= 0) {
      videos.value[next].liberado = true
      currentIndex.value = next
      await loadVideoUrl()
    }
  } finally {
    concluding.value = false
  }
}

function selectVideo(i) {
  currentIndex.value = i
  canConclude.value = videos.value[i].assistido
  loadVideoUrl()
}

watch(currentIndex, () => {
  canConclude.value = false
})
</script>

<style scoped>
.onb-wrapper {
  min-height: 100vh;
  background: var(--color-bg-primary);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1.5rem;
}

.onb-container {
  width: 100%;
  max-width: 900px;
}

.onb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  margin-bottom: 0.5rem;
}

.onb-logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-weight: 700;
  font-size: 1rem;
  color: var(--color-text-primary);
}

.onb-progress-text {
  font-size: 0.82rem;
  color: var(--color-text-secondary);
}

.onb-progress-bar-wrap {
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  margin-bottom: 2rem;
  overflow: hidden;
}

.onb-progress-bar {
  height: 100%;
  background: var(--color-primary-500);
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* Done state */
.onb-done {
  text-align: center;
  padding: 4rem 2rem;
}

.onb-done-icon { margin-bottom: 1.25rem; }
.onb-done h2 { font-size: 1.5rem; color: var(--color-text-primary); margin: 0 0 0.5rem; }
.onb-done p { color: var(--color-text-secondary); margin: 0 0 1.5rem; }

/* Body */
.onb-body {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 1.5rem;
  align-items: start;
}

@media (max-width: 700px) {
  .onb-body { grid-template-columns: 1fr; }
}

.onb-player-wrap {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.onb-badge {
  display: inline-block;
  background: var(--color-primary-50, rgba(99,102,241,0.1));
  color: var(--color-primary-500);
  border-radius: 20px;
  padding: 0.15rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.onb-video-meta { display: flex; flex-direction: column; gap: 0.2rem; }

.onb-video-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.onb-video-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
}

.onb-player { display: flex; flex-direction: column; gap: 0.5rem; }

.onb-video-el {
  width: 100%;
  border-radius: 8px;
  background: #000;
  max-height: 360px;
}

.onb-watch-hint {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--color-text-tertiary);
}

.onb-loading {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 3rem;
  font-size: 0.9rem;
}

.onb-btn-conclude {
  width: 100%;
  justify-content: center;
}

/* Lista lateral */
.onb-list {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  overflow: hidden;
}

.onb-list-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background 0.15s;
}

.onb-list-item:last-child { border-bottom: none; }

.onb-list-item:hover:not(.is-locked) { background: var(--color-bg-tertiary, rgba(0,0,0,0.03)); }

.onb-list-item.is-current { background: var(--color-primary-50, rgba(99,102,241,0.07)); }

.onb-list-item.is-locked { cursor: not-allowed; opacity: 0.5; }

.onb-item-num {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.onb-list-item.is-done .onb-item-num {
  background: none;
  border: none;
}

.onb-item-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.onb-item-title {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.onb-item-status {
  font-size: 0.73rem;
  color: var(--color-text-tertiary);
}

.onb-list-item.is-done .onb-item-status { color: var(--color-primary-500); }

/* Shared button */
.btn-primary {
  padding: 0.65rem 1.25rem;
  background: var(--color-primary-500);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
