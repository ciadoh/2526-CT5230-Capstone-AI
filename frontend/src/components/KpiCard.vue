<template>
  <div class="kpi-card">
    <div class="kpi-accent" :style="{ background: accent }" />
    <span class="kpi-label">{{ label }}</span>
    <div class="kpi-value" :style="{ color: accent }">
      {{ value ?? '—' }}<span v-if="value != null && suffix" style="font-size: 13px; font-weight: 500; margin-left: 3px; color: var(--text-faint);">{{ suffix }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label:  String,
  value:  [String, Number],
  suffix: { type: String, default: '' },
  color:  { type: String, default: 'brand' },
})

const PALETTE = {
  brand:  'var(--brand)',
  red:    'var(--red)',
  orange: 'var(--orange)',
  amber:  'var(--amber)',
  green:  'var(--green)',
  purple: 'var(--purple)',
}
const accent = computed(() => PALETTE[props.color] ?? 'var(--brand)')
</script>
