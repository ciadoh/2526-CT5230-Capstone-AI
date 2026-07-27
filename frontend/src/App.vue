<template>
  <div class="app-shell">

    <!-- ── Sidebar rail ──────────────────────────────────────────────── -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <rect x="2" y="2" width="20" height="20" rx="5" fill="var(--brand)"/>
          <path d="M7 15.5l3-7 2 4.5 1.5-3L17 15.5" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div style="line-height: 1.1;">
          <div style="font-size: 14px; font-weight: 700; color: #fff; letter-spacing: -0.01em;">TechDebt AI</div>
          <div class="mono" style="font-size: 9px; color: var(--rail-text-dim); letter-spacing: 0.08em;">QUALITY CONTROL</div>
        </div>
      </div>

      <nav style="flex: 1; overflow-y: auto; padding-bottom: 16px;">
        <div class="nav-group-label">Dashboard</div>
        <a v-for="item in sections" :key="item.id"
           class="nav-item" :class="{ active: activeSection === item.id }"
           @click="scrollTo(item.id)">
          <span v-html="item.icon" />
          {{ item.label }}
        </a>

        <div class="nav-group-label">Integrations</div>
        <a v-for="link in integrations" :key="link.label" class="nav-item" :href="link.url" target="_blank">
          <span :class="link.live ? 'status-ok' : 'status-warn'" style="margin: 0 4px;" />
          {{ link.label }}
        </a>
      </nav>

      <div style="padding: 14px 20px; border-top: 1px solid var(--rail-border);">
        <div class="mono" style="font-size: 9px; color: var(--rail-text-dim); letter-spacing: 0.06em; line-height: 1.6;">
          CAPSTONE · v1.0<br/>BEDROCK · OLLAMA
        </div>
      </div>
    </aside>

    <!-- ── Main column ───────────────────────────────────────────────── -->
    <div style="flex: 1; min-width: 0; display: flex; flex-direction: column;">

      <!-- Topbar -->
      <header class="topbar">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="card-title">Project</span>
          <select :value="activeRepo" @change="switchRepo($event.target.value)" class="form-select">
            <option v-for="r in availableRepos" :key="r" :value="r">{{ r }}</option>
          </select>
          <a v-if="summary?.repo?.full_name" :href="`https://github.com/${summary.repo.full_name}`" target="_blank"
             style="color: var(--text-faint); line-height: 0; display: inline-flex;">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24">
              <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"/>
            </svg>
          </a>
        </div>

        <div style="flex: 1;" />

        <span v-if="scanMessage" style="font-size: 12px;" :style="{ color: scanMessage.startsWith('Scan complete') ? 'var(--green)' : 'var(--red)' }">
          {{ scanMessage }}
        </span>

        <div v-if="summary?.risk" style="display: flex; align-items: center; gap: 8px;">
          <span class="card-title">Risk</span>
          <span class="risk-category-tag"
                :style="{ color: riskColor, background: riskBg, border: `1px solid ${riskColor}33` }">
            {{ summary.risk.score }} · {{ summary.risk.category }}
          </span>
        </div>

        <button @click="runScan" :disabled="scanning || loading" class="btn-secondary">
          <span v-if="scanning" style="display: flex; align-items: center; gap: 6px;">
            <span class="status-warn" style="animation: dot-pulse 1.4s ease-in-out infinite;" />Scanning…
          </span>
          <span v-else>Run Scan</span>
        </button>
        <button @click="loadAll" :disabled="loading" class="btn-primary">
          {{ loading ? 'Loading…' : 'Refresh' }}
        </button>
      </header>

      <!-- Content -->
      <main style="flex: 1; padding: 24px; display: flex; flex-direction: column; gap: 28px; max-width: 1600px; width: 100%;">

        <!-- Page header -->
        <div>
          <h1 class="page-title">Technical Debt Overview</h1>
          <p style="font-size: 13px; color: var(--text-faint); margin-top: 2px;">
            {{ summary?.repo?.full_name ?? activeRepo }} — aggregated quality signals across GitHub & SonarQube.
          </p>
        </div>

        <!-- Error -->
        <div v-if="error" style="border: 1px solid var(--red-border); background: var(--red-bg); border-radius: 10px; padding: 12px 16px; font-size: 13px; color: var(--red); display: flex; align-items: center; gap: 10px;">
          <span class="status-err" />{{ error }}
        </div>

        <!-- ── Overview / KPI strip ──────────────────────────────────── -->
        <section :id="'overview'" :ref="el => sectionEls.overview = el">
          <div class="section-heading">Overview</div>
          <div style="margin-top: 14px; display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px;">
            <template v-if="summary">
              <KpiCard label="Risk Score"      :value="summary.risk?.score"              suffix="/100" color="brand" />
              <KpiCard label="Bugs"            :value="summary.metrics?.bugs"            color="red" />
              <KpiCard label="Vulnerabilities" :value="summary.metrics?.vulnerabilities" color="orange" />
              <KpiCard label="Code Smells"     :value="summary.metrics?.code_smells"     color="amber" />
              <KpiCard label="Tech Debt"       :value="debtHours"                        suffix="h" color="purple" />
              <KpiCard label="Stars"           :value="summary.repo?.stars"              color="green" />
            </template>
            <template v-else-if="loading">
              <div v-for="i in 6" :key="i" class="kpi-card">
                <div class="skeleton" style="height: 10px; width: 55%;" />
                <div class="skeleton" style="height: 26px; width: 70%; margin-top: 12px;" />
              </div>
            </template>
          </div>
        </section>

        <!-- ── Insights grid ─────────────────────────────────────────── -->
        <section :id="'insights'" :ref="el => sectionEls.insights = el">
          <div class="section-heading">Insights</div>
          <div style="margin-top: 14px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px;">
            <div style="display: flex; flex-direction: column; gap: 14px;">
              <RiskBreakdown :risk="summary?.risk" :loading="loading" />
            </div>
            <div style="display: flex; flex-direction: column; gap: 14px;">
              <DebtTrendChart ref="debtChart" :key="activeRepo" :project-key="projectKey" />
              <LanguageChart :languages="summary?.repo?.languages" :loading="loading" />
            </div>
            <div>
              <IssuesList :key="activeRepo" :selected-issue="selectedIssue" @select="selectedIssue = $event" />
            </div>
          </div>
        </section>

        <!-- ── File risk heatmap ─────────────────────────────────────── -->
        <section :id="'heatmap'" :ref="el => sectionEls.heatmap = el">
          <div class="section-heading">File Risk Heatmap</div>
          <div style="margin-top: 14px;">
            <RiskHeatmap :key="activeRepo" />
          </div>
        </section>

        <!-- ── AI analysis ───────────────────────────────────────────── -->
        <section :id="'analysis'" :ref="el => sectionEls.analysis = el">
          <div class="section-heading">AI Analysis</div>
          <div style="margin-top: 14px;">
            <BedrockPanel :selected-issue="selectedIssue" :pr-enabled="prEnabled" />
          </div>
        </section>

        <!-- ── Experiments ───────────────────────────────────────────── -->
        <section :id="'experiments'" :ref="el => sectionEls.experiments = el" style="margin-bottom: 24px;">
          <div class="section-heading">Experiment Tracking</div>
          <div style="margin-top: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
            <MLflowPanel />
            <LangfusePanel />
          </div>
        </section>

      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { dashboard, config, scan } from './api/index.js'
import KpiCard from './components/KpiCard.vue'
import RiskBreakdown from './components/RiskBreakdown.vue'
import DebtTrendChart from './components/DebtTrendChart.vue'
import LanguageChart from './components/LanguageChart.vue'
import IssuesList from './components/IssuesList.vue'
import BedrockPanel from './components/BedrockPanel.vue'
import MLflowPanel from './components/MLflowPanel.vue'
import LangfusePanel from './components/LangfusePanel.vue'
import RiskHeatmap from './components/RiskHeatmap.vue'

const summary    = ref(null)
const loading    = ref(false)
const error      = ref(null)
const projectKey = ref('expressjs-express')
const selectedIssue  = ref(null)
const activeRepo     = ref('expressjs/express')
const availableRepos = ref(['expressjs/express', 'ciadoh/NodeGoat', 'ciadoh/WebGoat'])
const prEnabled  = ref(false)
const scanning   = ref(false)
const scanMessage = ref(null)
const debtChart  = ref(null)

const ICONS = {
  overview:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`,
  insights:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l5-5 4 4 8-8" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 8h4v4" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  heatmap:     `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="4" height="4" rx="1"/><rect x="10" y="3" width="4" height="4" rx="1"/><rect x="17" y="3" width="4" height="4" rx="1"/><rect x="3" y="10" width="4" height="4" rx="1"/><rect x="10" y="10" width="4" height="4" rx="1"/><rect x="17" y="10" width="4" height="4" rx="1"/><rect x="3" y="17" width="4" height="4" rx="1"/><rect x="10" y="17" width="4" height="4" rx="1"/><rect x="17" y="17" width="4" height="4" rx="1"/></svg>`,
  analysis:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2" stroke-linecap="round"/></svg>`,
  experiments: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3v6l-5 9a2 2 0 002 3h12a2 2 0 002-3l-5-9V3" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 3h8" stroke-linecap="round"/></svg>`,
}
const sections = [
  { id: 'overview',    label: 'Overview',      icon: ICONS.overview },
  { id: 'insights',    label: 'Insights',      icon: ICONS.insights },
  { id: 'heatmap',     label: 'File Risk',     icon: ICONS.heatmap },
  { id: 'analysis',    label: 'AI Analysis',   icon: ICONS.analysis },
  { id: 'experiments', label: 'Experiments',   icon: ICONS.experiments },
]
const integrations = computed(() => [
  { label: 'GitHub',    url: summary.value?.repo?.full_name ? `https://github.com/${summary.value.repo.full_name}` : 'https://github.com', live: !!summary.value },
  { label: 'SonarQube', url: 'http://localhost:9000', live: true },
  { label: 'MLflow',    url: 'http://localhost:5001', live: true },
  { label: 'Langfuse',  url: 'http://localhost:3001', live: true },
])

// ── Scroll-spy ──────────────────────────────────────────────────────────
const activeSection = ref('overview')
const sectionEls = reactive({})
let observer = null

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) activeSection.value = e.target.id })
  }, { rootMargin: '-20% 0px -70% 0px' })
  Object.values(sectionEls).forEach(el => el && observer.observe(el))
})
onBeforeUnmount(() => observer?.disconnect())

// ── Data ──────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  error.value = null
  selectedIssue.value = null
  try {
    const res = await dashboard.summary()
    summary.value = res.data
    if (res.data?.repo?.full_name) projectKey.value = res.data.repo.full_name.replace('/', '-')
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message || 'Failed to load dashboard data.'
  } finally {
    loading.value = false
  }
}

async function runScan() {
  scanning.value = true
  scanMessage.value = null
  try {
    await scan.trigger()
    const poll = setInterval(async () => {
      const res = await scan.status()
      if (!res.data.running) {
        clearInterval(poll)
        scanning.value = false
        const last = res.data.last
        scanMessage.value = last?.success ? 'Scan complete' : `Scan failed: ${last?.error ?? 'unknown error'}`
        if (last?.success) { await loadAll(); debtChart.value?.reload() }
        setTimeout(() => { scanMessage.value = null }, 5000)
      }
    }, 3000)
  } catch (e) {
    scanning.value = false
    scanMessage.value = e?.response?.data?.detail || e.message
  }
}

async function switchRepo(repo) {
  selectedIssue.value = null
  const res = await config.switchRepo(repo)
  activeRepo.value = repo
  prEnabled.value = res.data?.pr_enabled ?? false
  await loadAll()
}

onMounted(async () => {
  try {
    const res = await config.getRepo()
    activeRepo.value = res.data.active_repo
    availableRepos.value = res.data.available_repos
    prEnabled.value = res.data.pr_enabled ?? false
  } catch { /* defaults */ }
  await loadAll()
})

// ── Risk helpers ─────────────────────────────────────────────────────────
const riskColor = computed(() => {
  const s = summary.value?.risk?.score ?? 0
  if (s >= 70) return '#DC3D43'
  if (s >= 40) return '#C98200'
  return '#0E9F6E'
})
const riskBg = computed(() => {
  const s = summary.value?.risk?.score ?? 0
  if (s >= 70) return 'rgba(220,61,67,0.09)'
  if (s >= 40) return 'rgba(201,130,0,0.10)'
  return 'rgba(14,159,110,0.10)'
})

const debtHours = computed(() => {
  const mins = parseFloat(summary.value?.metrics?.sqale_index || 0)
  return mins ? Math.round(mins / 60) : '—'
})
</script>
