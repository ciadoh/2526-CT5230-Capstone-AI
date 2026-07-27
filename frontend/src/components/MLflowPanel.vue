<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">MLflow experiment runs</span>
      <a href="http://localhost:5001" target="_blank" class="btn-ghost" style="display: flex; align-items: center; gap: 4px;">
        Open MLflow
        <svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
      </a>
    </div>
    <div class="card-body">

      <div v-if="loading" style="display: flex; flex-direction: column; gap: 6px;">
        <div v-for="i in pageSize" :key="i" class="skeleton" style="height: 32px;" />
      </div>

      <table v-else-if="runs.length" class="data-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th style="text-align: right;">Risk score</th>
            <th style="text-align: right;">Bugs</th>
            <th style="text-align: right;">Debt (min)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in runs" :key="run.info?.run_id">
            <td class="mono" style="font-size: 11px; color: var(--brand);">{{ run.info?.run_id?.slice(0, 8) }}</td>
            <td style="text-align: right; font-variant-numeric: tabular-nums;">{{ metric(run, 'risk_score') }}</td>
            <td style="text-align: right; font-variant-numeric: tabular-nums;">{{ metric(run, 'bugs') }}</td>
            <td style="text-align: right; font-variant-numeric: tabular-nums;">{{ metric(run, 'technical_debt_minutes') }}</td>
          </tr>
        </tbody>
      </table>

      <p v-else style="font-size: 11px; color: var(--text-faint);">No runs yet — load the dashboard to log a run.</p>

      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-soft);">
        <div style="display: flex; align-items: center; gap: 4px;">
          <button @click="goPrev" :disabled="currentPage === 1 || loading" class="btn-secondary" style="padding: 3px 10px;">←</button>
          <span style="font-size: 10px; color: var(--text-dim); font-variant-numeric: tabular-nums; padding: 0 8px;">Page {{ currentPage }}</span>
          <button @click="goNext" :disabled="!hasNext || loading" class="btn-secondary" style="padding: 3px 10px;">→</button>
        </div>
        <select v-model="pageSize" @change="resetAndLoad" class="form-select">
          <option :value="5">5 / page</option>
          <option :value="10">10 / page</option>
          <option :value="20">20 / page</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { mlflow } from '../api/index.js'

const runs         = ref([])
const loading      = ref(true)
const pageSize     = ref(10)
const currentPage  = ref(1)
const hasNext      = ref(false)
const tokenForPage = ref([null])

async function load(page) {
  loading.value = true
  try {
    const token = tokenForPage.value[page - 1] ?? null
    const res   = await mlflow.runs(pageSize.value, token)
    runs.value  = res.data?.runs ?? []
    const nextToken = res.data?.next_page_token ?? null
    hasNext.value = !!nextToken
    if (nextToken && tokenForPage.value.length <= page) tokenForPage.value.push(nextToken)
  } catch { runs.value = [] }
  finally { loading.value = false }
}

function goNext() { currentPage.value++; load(currentPage.value) }
function goPrev() { if (currentPage.value > 1) { currentPage.value--; load(currentPage.value) } }
function resetAndLoad() { tokenForPage.value = [null]; currentPage.value = 1; load(1) }

function metric(run, key) {
  const m = run.data?.metrics?.find(x => x.key === key)
  return m ? parseFloat(m.value).toFixed(1) : '—'
}

onMounted(() => load(1))
</script>
