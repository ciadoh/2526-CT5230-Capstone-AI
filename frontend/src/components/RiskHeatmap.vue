<template>
  <div class="card">
    <div class="card-header">
      <div>
        <div class="card-title">File Risk Heatmap</div>
        <div class="card-sub">Per-file scores: rule-based vs ML models · ranked by random forest probability</div>
      </div>
      <div style="display: flex; gap: 8px; align-items: center;">
        <button @click="trainModels" :disabled="training || loading" class="btn-secondary" style="font-size: 11px; padding: 4px 10px;">
          {{ training ? 'Training…' : 'Train ML Models' }}
        </button>
        <button @click="load" :disabled="loading || training" class="btn-primary" style="font-size: 11px; padding: 4px 10px;">
          {{ loading ? 'Loading…' : 'Load' }}
        </button>
      </div>
    </div>

    <!-- Training result banner -->
    <div v-if="trainResult" style="margin: 0 0 14px; padding: 10px 14px; border-radius: 8px; background: var(--surface-2); font-size: 12px;">
      <div style="display: flex; gap: 24px; flex-wrap: wrap;">
        <div><span style="color: var(--text-faint);">Files analysed</span> <strong>{{ trainResult.n_samples }}</strong></div>
        <div><span style="color: var(--text-faint);">High-risk</span> <strong style="color: var(--red);">{{ trainResult.n_high_risk }}</strong></div>
        <div v-if="trainResult.models?.logistic_regression">
          <span style="color: var(--text-faint);">LR</span>
          F1 <strong>{{ trainResult.models.logistic_regression.f1 ?? 'n/a' }}</strong>
          · AUC <strong>{{ trainResult.models.logistic_regression.roc_auc ?? 'n/a' }}</strong>
        </div>
        <div v-if="trainResult.models?.random_forest">
          <span style="color: var(--text-faint);">RF</span>
          F1 <strong>{{ trainResult.models.random_forest.f1 ?? 'n/a' }}</strong>
          · AUC <strong>{{ trainResult.models.random_forest.roc_auc ?? 'n/a' }}</strong>
        </div>
      </div>
      <div v-if="trainResult.models?.random_forest?.feature_importances" style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">
        <span v-for="(v, k) in trainResult.models.random_forest.feature_importances" :key="k"
              style="font-size: 11px; padding: 2px 7px; border-radius: 4px; background: var(--surface-3);">
          {{ k }} <strong>{{ (v * 100).toFixed(1) }}%</strong>
        </span>
      </div>
    </div>

    <!-- Charts row (shown after training) -->
    <div v-if="trainResult && (rocChartData || distChartData)"
         style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 0 0 16px;">

      <!-- ROC Curve -->
      <div v-if="rocChartData" style="padding: 12px; border-radius: 8px; background: var(--surface-2);">
        <div style="font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">
          ROC Curve
        </div>
        <div style="position: relative; height: 200px;">
          <Line :data="rocChartData" :options="rocChartOptions" />
        </div>
      </div>

      <!-- Score Distribution -->
      <div v-if="distChartData" style="padding: 12px; border-radius: 8px; background: var(--surface-2);">
        <div style="font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">
          Score Distribution
        </div>
        <div style="position: relative; height: 200px;">
          <Bar :data="distChartData" :options="distChartOptions" />
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" style="font-size: 12px; color: var(--red); padding: 10px 0;">{{ error }}</div>

    <!-- Skeleton -->
    <div v-if="loading && !predictions.length" style="display: flex; flex-direction: column; gap: 6px;">
      <div v-for="i in PAGE_SIZE" :key="i" class="skeleton" style="height: 32px; border-radius: 6px;" />
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && !predictions.length && !error"
         style="padding: 32px; text-align: center; font-size: 13px; color: var(--text-faint);">
      Click <strong>Load</strong> to fetch file-level risk data.<br/>
      <span style="font-size: 11px;">Requires SonarQube scan to have run at least once.</span>
    </div>

    <!-- Table -->
    <div v-else-if="predictions.length" style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
        <thead>
          <tr style="border-bottom: 1px solid var(--border);">
            <th class="th">#</th>
            <th class="th" style="text-align: left;">File</th>
            <th class="th">Rule-based</th>
            <th class="th">LR prob</th>
            <th class="th">RF prob</th>
            <th class="th">Churn</th>
            <th class="th">Bugs</th>
            <th class="th">Vulns</th>
            <th class="th">Smells</th>
            <th class="th">Severity</th>
            <th class="th">Risk bar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in paginated" :key="row.key"
              style="border-bottom: 1px solid var(--border-faint);"
              :style="{ background: row.label === 1 ? 'rgba(220,61,67,0.04)' : 'transparent' }">
            <td class="td" style="color: var(--text-faint);">{{ (page - 1) * PAGE_SIZE + i + 1 }}</td>
            <td class="td" style="max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              <span :title="row.key" style="font-family: var(--mono); font-size: 11px;">
                {{ shortName(row.key) }}
              </span>
            </td>
            <td class="td" style="text-align: center;">
              <span :style="{ color: scoreColor(row.rule_based_score), fontWeight: 600 }">
                {{ row.rule_based_score }}
              </span>
            </td>
            <td class="td" style="text-align: center;">
              <span v-if="row.lr_risk_proba !== undefined" :style="{ color: probaColor(row.lr_risk_proba) }">
                {{ (row.lr_risk_proba * 100).toFixed(0) }}%
              </span>
              <span v-else style="color: var(--text-faint);">—</span>
            </td>
            <td class="td" style="text-align: center;">
              <span v-if="row.rf_risk_proba !== undefined" :style="{ color: probaColor(row.rf_risk_proba), fontWeight: 600 }">
                {{ (row.rf_risk_proba * 100).toFixed(0) }}%
              </span>
              <span v-else style="color: var(--text-faint);">—</span>
            </td>
            <td class="td" style="text-align: center;">{{ row.churn ?? '—' }}</td>
            <td class="td" style="text-align: center;">{{ row.bugs ?? '—' }}</td>
            <td class="td" style="text-align: center;">
              <span :style="{ color: row.vulnerabilities > 0 ? '#DC3D43' : 'inherit', fontWeight: row.vulnerabilities > 0 ? 600 : 400 }">
                {{ row.vulnerabilities ?? '—' }}
              </span>
            </td>
            <td class="td" style="text-align: center;">{{ row.code_smells ?? '—' }}</td>
            <td class="td" style="text-align: center;">
              <span :style="{ color: severityColor(row.severity_score), fontWeight: row.severity_score > 0 ? 600 : 400 }">
                {{ row.severity_score != null ? (row.severity_score * 100).toFixed(0) + '%' : '—' }}
              </span>
            </td>
            <td class="td" style="width: 90px;">
              <div style="height: 6px; border-radius: 3px; background: var(--border); overflow: hidden;">
                <div :style="{
                  width: `${Math.min(100, (row.rf_risk_proba ?? row.rule_based_score / 100) * 100)}%`,
                  height: '100%',
                  borderRadius: '3px',
                  background: probaColor(row.rf_risk_proba ?? row.rule_based_score / 100),
                }" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 4px 2px; font-size: 12px;">
        <span style="color: var(--text-faint);">
          {{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, predictions.length) }} of {{ predictions.length }} files
        </span>
        <div style="display: flex; gap: 4px; align-items: center;">
          <button class="page-btn" :disabled="page === 1" @click="page = 1">«</button>
          <button class="page-btn" :disabled="page === 1" @click="page--">‹</button>
          <span v-for="p in visiblePages" :key="p">
            <button
              v-if="p !== '…'"
              class="page-btn"
              :class="{ active: p === page }"
              @click="page = p">{{ p }}</button>
            <span v-else style="padding: 0 4px; color: var(--text-faint);">…</span>
          </span>
          <button class="page-btn" :disabled="page === totalPages" @click="page++">›</button>
          <button class="page-btn" :disabled="page === totalPages" @click="page = totalPages">»</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ml } from '../api/index.js'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement, BarElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler)

const PAGE_SIZE = 15

const predictions = ref([])
const trainResult = ref(null)
const loading = ref(false)
const training = ref(false)
const error = ref(null)
const page = ref(1)

const totalPages = computed(() => Math.ceil(predictions.value.length / PAGE_SIZE))

const paginated = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return predictions.value.slice(start, start + PAGE_SIZE)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const cur = page.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = []
  if (cur > 3) pages.push(1, '…')
  for (let p = Math.max(1, cur - 2); p <= Math.min(total, cur + 2); p++) pages.push(p)
  if (cur < total - 2) pages.push('…', total)
  return pages
})

const rocChartData = computed(() => {
  if (!trainResult.value) return null
  const datasets = []
  const models = [
    { key: 'logistic_regression', label: 'LR', color: '#6366F1' },
    { key: 'random_forest', label: 'RF', color: '#10B981' },
  ]
  for (const m of models) {
    const rc = trainResult.value.models?.[m.key]?.roc_curve
    if (!rc) continue
    const points = rc.fpr.map((fpr, i) => ({ x: fpr, y: rc.tpr[i] })).filter(p => p.x != null && p.y != null)
    datasets.push({
      label: m.label,
      data: points,
      borderColor: m.color,
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.1,
    })
  }
  // Diagonal reference line
  datasets.push({
    label: 'Random',
    data: [{ x: 0, y: 0 }, { x: 1, y: 1 }],
    borderColor: 'rgba(150,150,150,0.4)',
    borderDash: [4, 4],
    borderWidth: 1,
    pointRadius: 0,
    backgroundColor: 'transparent',
  })
  return datasets.length > 1 ? { datasets } : null
})

const rocChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  parsing: false,
  scales: {
    x: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'FPR', font: { size: 10 } }, ticks: { font: { size: 10 } } },
    y: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'TPR', font: { size: 10 } }, ticks: { font: { size: 10 } } },
  },
  plugins: { legend: { labels: { font: { size: 10 }, boxWidth: 12 } }, tooltip: { mode: 'nearest', intersect: false } },
}

const distChartData = computed(() => {
  const files = trainResult.value?.files
  if (!files?.length) return null
  const buckets = Array(10).fill(0)
  for (const f of files) {
    const idx = Math.min(9, Math.floor(f.rule_based_score / 10))
    buckets[idx]++
  }
  const labels = ['0–10', '10–20', '20–30', '30–40', '40–50', '50–60', '60–70', '70–80', '80–90', '90–100']
  const colors = labels.map((_, i) => {
    const mid = (i + 0.5) * 10
    if (mid >= 60) return '#DC3D43'
    if (mid >= 40) return '#C98200'
    if (mid >= 20) return '#D97706'
    return '#10B981'
  })
  return {
    labels,
    datasets: [{ label: 'Files', data: buckets, backgroundColor: colors, borderRadius: 4, borderSkipped: false }],
  }
})

const distChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: { ticks: { font: { size: 9 } } },
    y: { ticks: { stepSize: 1, font: { size: 10 } }, title: { display: true, text: 'Files', font: { size: 10 } } },
  },
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y} files` } } },
}

async function load() {
  loading.value = true
  error.value = null
  page.value = 1
  try {
    const res = await ml.predict()
    predictions.value = res.data.predictions ?? []
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message || 'Failed to load predictions.'
  } finally {
    loading.value = false
  }
}

async function trainModels() {
  training.value = true
  error.value = null
  page.value = 1
  try {
    const res = await ml.train()
    trainResult.value = res.data
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message || 'Training failed.'
  } finally {
    training.value = false
  }
}

function shortName(key) {
  const path = key.includes(':') ? key.split(':').pop() : key
  const parts = path.split('/')
  return parts.length > 3 ? '…/' + parts.slice(-2).join('/') : path
}

function scoreColor(score) {
  if (score >= 60) return '#DC3D43'
  if (score >= 40) return '#C98200'
  if (score >= 20) return '#D97706'
  return '#0E9F6E'
}

function probaColor(p) {
  if (p >= 0.7) return '#DC3D43'
  if (p >= 0.4) return '#C98200'
  return '#0E9F6E'
}

function severityColor(s) {
  if (s >= 0.6) return '#DC3D43'
  if (s >= 0.3) return '#C98200'
  if (s > 0)    return '#D97706'
  return 'var(--text-faint)'
}
</script>

<style scoped>
.th {
  padding: 7px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: center;
  white-space: nowrap;
}
.td {
  padding: 7px 10px;
  vertical-align: middle;
}
.page-btn {
  min-width: 28px;
  height: 28px;
  padding: 0 6px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface-1);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}
.page-btn:hover:not(:disabled) {
  background: var(--surface-2);
}
.page-btn:disabled {
  opacity: 0.35;
  cursor: default;
}
.page-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
  font-weight: 600;
}
</style>
