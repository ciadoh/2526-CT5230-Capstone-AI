<template>
  <div class="card" style="display: flex; flex-direction: column; max-height: 540px;">
    <div class="card-header">
      <span class="card-title">Issues</span>
      <select v-model="severity" @change="load" class="form-select">
        <option value="">All severities</option>
        <option value="BLOCKER">Blocker</option>
        <option value="CRITICAL">Critical</option>
        <option value="MAJOR">Major</option>
      </select>
    </div>

    <!-- Scrollable table -->
    <div style="flex: 1; overflow-y: auto;">
      <div v-if="loading" style="padding: 14px; display: flex; flex-direction: column; gap: 6px;">
        <div v-for="i in 8" :key="i" class="skeleton" style="height: 36px;" />
      </div>

      <table v-else-if="issues.length" class="data-table" style="width: 100%;">
        <thead style="position: sticky; top: 0; background: var(--surface); z-index: 10; box-shadow: 0 1px 0 var(--border);">
          <tr>
            <th style="padding-left: 14px; width: 52px;">Sev</th>
            <th>Message</th>
            <th style="padding-right: 14px; width: 80px; display: none;" class="sm:table-cell">Type</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="issue in issues" :key="issue.key"
              @click="select(issue)"
              style="cursor: pointer;"
              :class="selectedIssue?.key === issue.key ? 'row-selected' : ''">
            <td style="padding-left: 14px;">
              <span :class="sevClass(issue.severity)">{{ sevLabel(issue.severity) }}</span>
            </td>
            <td>
              <p style="color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px;">{{ issue.message }}</p>
              <p style="color: var(--text-faint); font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ shortComponent(issue.component) }}</p>
            </td>
            <td style="padding-right: 14px; display: none;" class="sm:table-cell">
              <span style="font-size: 9px; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.08em;">{{ issue.type }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-else style="padding: 14px; font-size: 11px; color: var(--text-faint);">No issues found — run a scan first.</p>
    </div>

    <!-- Footer -->
    <div style="flex-shrink: 0; border-top: 1px solid var(--border-soft); padding: 8px 14px; display: flex; align-items: center; justify-content: space-between; min-height: 36px;">
      <span v-if="selectedIssue" style="font-size: 11px; color: var(--amber); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
        {{ selectedIssue.message.slice(0, 60) }}
      </span>
      <span v-else style="font-size: 10px; color: var(--text-faint);">Click an issue to review with AI</span>
      <button v-if="selectedIssue" @click="select(null)" class="btn-ghost" style="margin-left: 8px; flex-shrink: 0;">Clear</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { sonar } from '../api/index.js'

const props = defineProps({ selectedIssue: { type: Object, default: null } })
const emit  = defineEmits(['select'])

const issues   = ref([])
const loading  = ref(true)
const severity = ref('')

async function load() {
  loading.value = true
  try {
    const res = await sonar.issues(30)
    let all = res.data?.issues ?? []
    if (severity.value) all = all.filter(i => i.severity === severity.value)
    issues.value = all
  } catch { issues.value = [] }
  finally { loading.value = false }
}

onMounted(load)

function select(issue) {
  emit('select', issue?.key === props.selectedIssue?.key ? null : issue)
}

function shortComponent(c) {
  if (!c) return ''
  return c.split(':').pop()?.split('/').slice(-2).join('/')
}

function sevLabel(s) {
  const map = { BLOCKER: 'BLK', CRITICAL: 'CRT', MAJOR: 'MAJ', MINOR: 'MIN', INFO: 'INF' }
  return map[s] ?? s
}

function sevClass(s) {
  const map = {
    BLOCKER: 'sev-blocker', CRITICAL: 'sev-critical',
    MAJOR: 'sev-major',    MINOR: 'sev-minor', INFO: 'sev-info',
  }
  return map[s] ?? 'sev-info'
}
</script>
