<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">Langfuse traces</span>
      <div style="display: flex; align-items: center; gap: 10px;">
        <button @click="load" :disabled="loading" class="btn-ghost">{{ loading ? 'Loading…' : 'Refresh' }}</button>
        <a href="http://localhost:3001" target="_blank" class="btn-ghost" style="display: flex; align-items: center; gap: 4px;">
          Open Langfuse
          <svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
        </a>
      </div>
    </div>
    <div class="card-body">

      <div v-if="loading" style="display: flex; flex-direction: column; gap: 6px;">
        <div v-for="i in pageSize" :key="i" class="skeleton" style="height: 32px;" />
      </div>

      <table v-else-if="traces.length" class="data-table">
        <thead>
          <tr>
            <th>Trace ID</th>
            <th>Model</th>
            <th style="display: none;" class="sm:table-cell">Source</th>
            <th style="text-align: right;">Latency</th>
            <th style="text-align: right;">Age</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in traces" :key="t.id" style="cursor: pointer;" @click="openTrace(t)">
            <td class="mono" style="font-size: 11px; color: var(--brand);">{{ t.id.slice(0, 8) }}</td>
            <td style="color: var(--text-dim);">{{ t.input?.model ?? '—' }}</td>
            <td style="color: var(--text-faint); display: none;" class="sm:table-cell">{{ t.input?.source ?? '—' }}</td>
            <td style="text-align: right; font-variant-numeric: tabular-nums;">{{ t.latency ? `${t.latency.toFixed(1)}s` : '—' }}</td>
            <td style="text-align: right; color: var(--text-faint); font-size: 10px; font-variant-numeric: tabular-nums;">{{ relativeTime(t.timestamp) }}</td>
          </tr>
        </tbody>
      </table>

      <div v-else style="display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-faint);">
        <span class="status-ok" style="animation: dot-pulse 2s ease-in-out infinite;" />
        Langfuse connected — no traces yet. Run an analysis to generate the first trace.
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-soft);">
        <div style="display: flex; align-items: center; gap: 4px;">
          <button @click="goPrev" :disabled="page === 1 || loading" class="btn-secondary" style="padding: 3px 10px;">←</button>
          <span style="font-size: 10px; color: var(--text-dim); font-variant-numeric: tabular-nums; padding: 0 8px;">
            Page {{ page }}{{ totalPages > 0 ? ` / ${totalPages}` : '' }}
          </span>
          <button @click="goNext" :disabled="page >= totalPages || loading" class="btn-secondary" style="padding: 3px 10px;">→</button>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span v-if="totalItems > 0" style="font-size: 10px; color: var(--text-faint); font-variant-numeric: tabular-nums;">{{ totalItems }} total</span>
          <select v-model="pageSize" @change="resetAndLoad" class="form-select">
            <option :value="5">5 / page</option>
            <option :value="10">10 / page</option>
            <option :value="20">20 / page</option>
          </select>
        </div>
      </div>

      <p v-if="error" style="font-size: 11px; color: var(--red); margin-top: 8px; display: flex; align-items: center; gap: 6px;">
        <span class="status-err" />{{ error }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { langfuse } from '../api/index.js'

const traces     = ref([])
const loading    = ref(true)
const error      = ref(null)
const page       = ref(1)
const pageSize   = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)

async function load() {
  loading.value = true; error.value = null
  try {
    const res   = await langfuse.traces(pageSize.value, page.value)
    traces.value      = res.data?.data ?? []
    totalPages.value  = res.data?.meta?.totalPages ?? 1
    totalItems.value  = res.data?.meta?.totalItems ?? 0
  } catch (e) { error.value = e?.response?.data?.detail || e.message }
  finally { loading.value = false }
}

function goNext() { if (page.value < totalPages.value) { page.value++; load() } }
function goPrev() { if (page.value > 1) { page.value--; load() } }
function resetAndLoad() { page.value = 1; load() }

function relativeTime(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  return `${Math.floor(diff / 3600)}h`
}

function openTrace(t) { window.open(`http://localhost:3001${t.htmlPath}`, '_blank') }

onMounted(load)
</script>
