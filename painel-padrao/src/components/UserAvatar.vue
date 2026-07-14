<template>
  <div class="avatar-wrap" :style="{ width: size + 'px', height: size + 'px' }">
    <img v-if="src" :src="src" class="avatar-img" :alt="name" @error="imgError = true" />
    <div v-else class="avatar-initials" :style="{ fontSize: (size * 0.38) + 'px', background: color }">
      {{ initials }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  avatarUrl: { type: String, default: null },
  size: { type: Number, default: 36 },
})

const imgError = ref(false)

// Reseta o erro sempre que a URL mudar (ex: após upload de nova foto)
watch(() => props.avatarUrl, () => { imgError.value = false })

const src = computed(() => (!imgError.value && props.avatarUrl) ? props.avatarUrl : null)

const initials = computed(() => {
  const parts = (props.name || '').trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return (parts[0]?.[0] || '?').toUpperCase()
})

// Cor determinística baseada no nome
const COLORS = ['#1a56db','#7c3aed','#059669','#d97706','#dc2626','#0891b2','#be185d']
const color = computed(() => {
  let hash = 0
  for (const c of props.name) hash = c.charCodeAt(0) + ((hash << 5) - hash)
  return COLORS[Math.abs(hash) % COLORS.length]
})
</script>

<style scoped>
.avatar-wrap { border-radius: 50%; overflow: hidden; flex-shrink: 0; display: inline-flex; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.avatar-initials {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; border-radius: 50%; user-select: none;
}
</style>
