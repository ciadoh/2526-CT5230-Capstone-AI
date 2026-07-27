<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">Language composition</span>
    </div>
    <div class="card-body">
      <div v-if="loading" class="skeleton" style="height: 128px;" />
      <Doughnut v-else-if="chartData" :data="chartData" :options="chartOptions" style="max-height: 144px;" />
      <p v-else style="font-size: 11px; color: var(--text-faint);">No language data.</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart, ArcElement, Tooltip, Legend } from 'chart.js'

Chart.register(ArcElement, Tooltip, Legend)

const props = defineProps({ languages: Object, loading: Boolean })

const COLORS = ['#3B63F2','#0E9F6E','#C98200','#DC3D43','#7C5CFC','#E0691F','#2C7BE5']

const chartData = computed(() => {
  if (!props.languages) return null
  const entries = Object.entries(props.languages).sort((a, b) => b[1] - a[1]).slice(0, 7)
  return {
    labels: entries.map(([k]) => k),
    datasets: [{ data: entries.map(([, v]) => v), backgroundColor: COLORS, borderWidth: 0, hoverOffset: 4 }],
  }
})

const chartOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'right',
      labels: { color: '#4A5568', boxWidth: 10, font: { size: 10, family: 'IBM Plex Mono' } },
    },
    tooltip: {
      backgroundColor: '#10141F',
      borderColor: '#232A3A',
      borderWidth: 1,
      bodyColor: '#fff',
      titleColor: '#9BA6B8',
      padding: 10,
      cornerRadius: 6,
    },
  },
}
</script>
