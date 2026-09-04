<template>
  <span v-if="dica" class="field-info" tabindex="0">
    <svg class="field-info-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.3"/>
      <path d="M7 6.2v3.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
      <circle cx="7" cy="4.2" r="0.9" fill="currentColor"/>
    </svg>
    <span class="field-info-tip" role="tooltip">
      <strong v-if="dica.titulo">{{ dica.titulo }}</strong>
      <span>{{ dica.texto }}</span>
    </span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  campo: { type: String, required: true },
  dicas: { type: Object, default: () => ({}) },
})

const dica = computed(() => props.dicas?.[props.campo] || null)
</script>

<style scoped>
.field-info {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 5px;
  vertical-align: middle;
  color: var(--color-primary-500);
  cursor: help;
  outline: none;
}
.field-info-icon { flex-shrink: 0; }

.field-info-tip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  max-width: 62vw;
  background: var(--color-neutral-800);
  color: #fff;
  font-size: var(--font-size-xs);
  line-height: 1.55;
  font-weight: normal;
  text-transform: none;
  letter-spacing: normal;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 40;
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: left;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-fast);
}
.field-info-tip strong {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  text-transform: none;
  letter-spacing: normal;
}
.field-info:hover .field-info-tip,
.field-info:focus .field-info-tip {
  opacity: 1;
}
</style>