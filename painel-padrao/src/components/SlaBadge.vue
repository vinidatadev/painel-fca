<template>
  <span :class="['sla-badge', atrasado ? 'sla-atrasado' : 'sla-ok']">
    {{ atrasado ? '⚠ Atrasado ' : '⏱ Vence em ' }}{{ texto }}
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
  display: inline-flex; align-items: center;
  padding: .15rem .55rem; border-radius: 20px;
  font-size: .72rem; font-weight: 600; white-space: nowrap;
}
.sla-ok { background: #dcfce7; color: #166534; }
.sla-atrasado { background: #fee2e2; color: #991b1b; animation: pulse 2s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .65; }
}
</style>
