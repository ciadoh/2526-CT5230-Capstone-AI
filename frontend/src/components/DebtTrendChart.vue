<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">Technical debt trend</span>
      <span style="font-size: 9px; color: var(--text-faint);">sqale_index (minutes)</span>
    </div>
    <div class="card-body">
      <div v-if="loading" class="skeleton" style="height: 160px;" />
      <Line v-else-if="chartData" :data="chartData" :options="chartOptions" style="max-height: 192px;" />
      <p v-else style="font-size: 11px; color: var(--text-faint);">No history — run multiple scans to see the trend.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, defineExpose } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler } from 'chart.js'
import { sonar } from '../api/index.js'

Chart.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler)

defineProps({ projectKey: String })

const chartData = ref(null)
const loading   = ref(true)

async function load() {
  loading.value = true
  try {
    const res      = await sonar.history('sqale_index')
    const measures = res.data?.measures?.[0]?.history ?? []
    if (!measures.length) { chartData.value = null; return }
    chartData.value = {
      labels: measures.map(p => p.date?.slice(0, 10)),
      datasets: [{
        label: 'Debt (min)',
        data:  measures.map(p => parseInt(p.value ?? 0)),
        borderColor: '#3B63F2',
        backgroundColor: 'rgba(59,99,242,0.07)',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointBackgroundColor: '#3B63F2',
      }],
    }
  } catch { /* SonarQube may not be ready */ }
  finally { loading.value = false }
}

onMounted(load)
defineExpose({ reload: load })

const chartOptions = {
  responsive: true,
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: '#10141F', borderColor: '#232A3A', borderWidth: 1, bodyColor: '#fff', titleColor: '#9BA6B8', padding: 10, cornerRadius: 6 },
  },
  scales: {
    x: {
      ticks: { color: '#8A94A6', font: { size: 10, family: 'IBM Plex Mono' }, maxTicksLimit: 6 },
      grid:  { color: '#EDF0F4' },
      border: { color: '#E3E7ED' },
    },
    y: {
      ticks: { color: '#8A94A6', font: { size: 10, family: 'IBM Plex Mono' } },
      grid:  { color: '#EDF0F4' },
      border: { color: '#E3E7ED' },
    },
  },
}
</script>
