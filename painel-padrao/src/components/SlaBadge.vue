<template>
  <span :class="['sla-badge', atrasado ? 'sla-atrasado' : diffMs < 3600000 ? 'sla-warning' : 'sla-ok']">
    <svg width="11" height="11" viewBox="0 0 11 11" fill="none" style="flex-shrink:0"><circle cx="5.5" cy="5.5" r="4.5" stroke="currentColor" stroke-width="1.2"/><path d="M5.5 3v2.5l1.5 1.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
    {{ atrasado ? 'Atrasado ' : 'Vence em ' }}{{ texto }}
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({ deadline: { type: String, required: true } })

const agora = ref(Date.now())
let timer = null

onMounted(() => { timer = setInterval(() => { agora.value = Date.now() }, 30000) })
onUnmounted(() => clearInterval(timer))

const diffMs = computed(() => new Date(props.deadline).getTime() - agora.value)
const atrasado = computed(() => diffMs.value < 0)

const texto = computed(() => {
  const abs = Math.abs(diffMs.value)
  const min = Math.floor(abs / 60000)
  if (min < 60) return `${min}min`
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h < 24) return m > 0 ? `${h}h ${m}min` : `${h}h`
  const d = Math.floor(h / 24)
  const hr = h % 24
  return hr > 0 ? `${d}d ${hr}h` : `${d}d`
})
</script>

<style scoped>
.sla-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px var(--space-2); border-radius: var(--radius-full);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); white-space: nowrap;
}
.sla-ok      { background: var(--color-success-bg); color: var(--color-success-text); }
.sla-warning { background: var(--color-warning-bg); color: var(--color-warning-text); }
.sla-atrasado { background: var(--color-danger-bg); color: var(--color-danger-text); animation: pulse 2s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .65; }
}
</style>
