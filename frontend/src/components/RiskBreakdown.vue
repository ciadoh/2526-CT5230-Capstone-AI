<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">Risk profile</span>
      <span v-if="risk" class="mono" style="font-size: 11px; font-weight: 600;" :style="{ color: scoreColor }">
        {{ risk.score }}/100
      </span>
    </div>
    <div class="card-body">

      <div v-if="loading" style="display: flex; flex-direction: column; gap: 12px;">
        <div class="skeleton" style="height: 120px; width: 120px; border-radius: 50%; margin: 0 auto;" />
        <div v-for="i in 5" :key="i" class="skeleton" style="height: 26px;" />
      </div>

      <template v-else-if="risk">
        <!-- Ring gauge (signature) -->
        <div style="display: flex; align-items: center; gap: 18px; padding-bottom: 16px; margin-bottom: 16px; border-bottom: 1px solid var(--border-soft);">
          <div style="position: relative; width: 104px; height: 104px; flex-shrink: 0;">
            <svg width="104" height="104" viewBox="0 0 104 104" style="position: absolute; inset: 0; overflow: visible;">
              <circle cx="52" cy="52" r="42" fill="none" stroke="var(--border)" stroke-width="8" />
              <g stroke="var(--border)" stroke-width="1">
                <line v-for="i in 20" :key="i"
                      :x1="52 + 46 * Math.cos((i/20 * 360 - 90) * Math.PI/180)"
                      :y1="52 + 46 * Math.sin((i/20 * 360 - 90) * Math.PI/180)"
                      :x2="52 + 50 * Math.cos((i/20 * 360 - 90) * Math.PI/180)"
                      :y2="52 + 50 * Math.sin((i/20 * 360 - 90) * Math.PI/180)" />
              </g>
              <circle cx="52" cy="52" r="42" fill="none"
                      :stroke="scoreColor" stroke-width="8" stroke-linecap="round"
                      :stroke-dasharray="circumference" :stroke-dashoffset="dashOffset"
                      style="transform: rotate(-90deg); transform-origin: 52px 52px; transition: stroke-dashoffset 1.4s cubic-bezier(0.34,1.56,0.64,1), stroke 0.4s;" />
            </svg>
            <div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;">
              <span class="risk-score-number" :style="{ color: scoreColor }">{{ risk.score }}</span>
              <span class="risk-score-label">RISK</span>
            </div>
          </div>
          <div style="min-width: 0;">
            <span class="risk-category-tag" :style="{ color: scoreColor, background: scoreBg, border: `1px solid ${scoreColor}33` }">
              {{ risk.category }}
            </span>
            <p style="font-size: 12px; color: var(--text-faint); margin-top: 8px; line-height: 1.5;">
              Weighted index across {{ Object.keys(risk.breakdown || {}).length }} quality dimensions.
            </p>
          </div>
        </div>

        <!-- Breakdown bars -->
        <div style="display: flex; flex-direction: column; gap: 11px;">
          <div v-for="(val, key) in risk.breakdown" :key="key">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
              <span style="font-size: 12px; color: var(--text-dim); text-transform: capitalize;">{{ key.replace('_', ' ') }}</span>
              <span class="mono" style="font-size: 11px; color: var(--text-faint); font-variant-numeric: tabular-nums;">{{ val.toFixed(1) }}</span>
            </div>
            <div style="height: 6px; background: var(--surface-2); border-radius: 3px; overflow: hidden;">
              <div style="height: 100%; border-radius: 3px; transition: width 0.7s ease-out;"
                   :style="{ width: `${Math.min(val / maxVal * 100, 100)}%`, background: barColor(key) }" />
            </div>
          </div>
        </div>
      </template>

      <p v-else style="font-size: 12px; color: var(--text-faint);">No risk data — run a SonarQube scan first.</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ risk: Object, loading: Boolean })

const RING_R = 42
const circumference = 2 * Math.PI * RING_R
const dashOffset = computed(() => circumference * (1 - (props.risk?.score ?? 0) / 100))

const maxVal = computed(() => {
  if (!props.risk?.breakdown) return 1
  return Math.max(...Object.values(props.risk.breakdown), 1)
})

const BAR_COLORS = {
  bugs:            '#DC3D43',
  vulnerabilities: '#E0691F',
  code_smells:     '#C98200',
  complexity:      '#7C5CFC',
  duplication:     '#2C7BE5',
  maintainability: '#0E9F6E',
}
function barColor(key) { return BAR_COLORS[key] ?? 'var(--text-faint)' }

const scoreColor = computed(() => {
  const s = props.risk?.score ?? 0
  if (s >= 70) return '#DC3D43'
  if (s >= 40) return '#C98200'
  return '#0E9F6E'
})
const scoreBg = computed(() => {
  const s = props.risk?.score ?? 0
  if (s >= 70) return 'rgba(220,61,67,0.09)'
  if (s >= 40) return 'rgba(201,130,0,0.10)'
  return 'rgba(14,159,110,0.10)'
})
</script>
