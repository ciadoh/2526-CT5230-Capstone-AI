<template>
  <div class="card">
    <div class="card-header">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="card-title">LLM Analysis</span>
        <select v-model="selectedModel" class="form-select">
          <option v-for="m in modelList" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <button @click="analyse" :disabled="analysing || comparing || reviewingIssue" class="btn-primary">
          {{ analysing ? 'Running…' : 'Analyse' }}
        </button>
        <button @click="compare" :disabled="analysing || comparing || reviewingIssue || selectedModel === 'ollama'"
                :title="selectedModel === 'ollama' ? 'Select a Bedrock model to compare against Ollama' : ''" class="btn-secondary">
          <span :class="ollamaAvailable ? 'status-ok' : 'status-err'" />
          {{ comparing ? 'Running…' : 'Compare vs Ollama' }}
        </button>
        <button v-if="selectedIssue" @click="reviewIssue"
                :disabled="analysing || comparing || reviewingIssue"
                class="btn-secondary">
          {{ reviewingIssue ? 'Running…' : 'Review issue' }}
        </button>
      </div>
    </div>

    <div class="card-body" style="display: flex; flex-direction: column; gap: 12px;">

      <!-- Selected issue context -->
      <div v-if="selectedIssue" style="display: flex; align-items: flex-start; gap: 12px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px;">
        <span style="font-size: 9px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.14em; flex-shrink: 0; margin-top: 1px;">Issue</span>
        <div style="min-width: 0;">
          <p style="font-size: 11px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ selectedIssue.message }}</p>
          <p style="font-size: 10px; color: var(--text-faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ shortComponent(selectedIssue.component) }} · {{ selectedIssue.severity }}</p>
        </div>
      </div>

      <!-- PR result -->
      <div v-if="prResult" style="display: flex; align-items: center; gap: 10px; border: 1px solid var(--green-border); background: var(--green-bg); border-radius: 8px; padding: 8px 12px;">
        <span class="status-ok" />
        <span style="font-size: 11px; color: var(--green); font-weight: 600;">Pull request created</span>
        <a :href="prResult.pr_url" target="_blank" style="font-size: 11px; color: var(--brand); text-decoration: underline; text-underline-offset: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ prResult.pr_url }}</a>
      </div>

      <!-- Issue review -->
      <div v-if="issueResult" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden;">
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--surface-2);">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: var(--brand);">Issue review</span>
            <span style="font-size: 10px; color: var(--text-faint);">·</span>
            <span style="font-size: 10px; color: var(--text-dim);">{{ issueResult.model_alias }}</span>
            <span v-if="issueResult.trace_id" style="font-size: 9px; color: var(--text-faint);">trace:{{ issueResult.trace_id.slice(0, 8) }}</span>
          </div>
          <button v-if="prEnabled && !prResult" @click="createPr" :disabled="creatingPr" class="btn-secondary" style="padding: 3px 10px;">
            {{ creatingPr ? 'Creating…' : 'Create PR' }}
          </button>
        </div>
        <div style="padding: 14px; font-size: 11px; color: var(--text-dim); white-space: pre-wrap; line-height: 1.7;">{{ issueResult.analysis }}</div>
      </div>

      <!-- Single model result -->
      <div v-if="result" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden;">
        <div style="display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--surface-2);">
          <span style="font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: var(--brand);">Analysis</span>
          <span style="font-size: 10px; color: var(--text-faint);">·</span>
          <span style="font-size: 10px; color: var(--text-dim);">{{ result.model_alias }}</span>
          <span v-if="result.trace_id" style="font-size: 9px; color: var(--text-faint);">trace:{{ result.trace_id.slice(0, 8) }}</span>
        </div>
        <div style="padding: 14px; font-size: 11px; color: var(--text-dim); white-space: pre-wrap; line-height: 1.7;">{{ result.analysis }}</div>
      </div>

      <!-- Compare results -->
      <div v-if="compareResults.length" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
        <div v-for="r in compareResults" :key="r.model" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden;">
          <div style="display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--surface-2);">
            <span :class="r.provider === 'ollama' ? 'status-ok' : 'status-warn'" />
            <span style="font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: var(--brand);">{{ r.provider }}</span>
            <span style="font-size: 10px; color: var(--text-faint);">·</span>
            <span style="font-size: 10px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ r.model }}</span>
            <span v-if="r.error" style="margin-left: auto; font-size: 10px; color: var(--red);">error</span>
          </div>
          <div style="padding: 14px; font-size: 11px; color: var(--text-dim); white-space: pre-wrap; line-height: 1.7;">{{ r.response }}</div>
        </div>
      </div>

      <!-- Empty state -->
      <p v-if="!result && !compareResults.length && !issueResult && !analysing && !comparing && !reviewingIssue"
         style="font-size: 11px; color: var(--text-faint);">
        Select a model and click Analyse for a debt assessment, or Compare vs Ollama for a side-by-side evaluation.
      </p>

      <div v-if="bedrockError" style="font-size: 11px; color: var(--red); display: flex; align-items: center; gap: 8px;">
        <span class="status-err" />{{ bedrockError }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { bedrock, github, ollama } from '../api/index.js'

const props = defineProps({
  selectedIssue: { type: Object, default: null },
  prEnabled:     { type: Boolean, default: false },
})

const selectedModel  = ref('nova-lite')
const modelList      = ref(['nova-micro', 'nova-lite', 'nova-pro', 'mistral'])
const result         = ref(null)
const compareResults = ref([])
const issueResult    = ref(null)
const analysing      = ref(false)
const comparing      = ref(false)
const reviewingIssue = ref(false)
const creatingPr     = ref(false)
const prResult       = ref(null)
const bedrockError   = ref(null)
const ollamaAvailable = ref(false)

onMounted(async () => {
  try { const res = await bedrock.models(); modelList.value = res.data?.models ?? modelList.value } catch { /* ok */ }
  try {
    const res = await ollama.status()
    ollamaAvailable.value = res.data?.available ?? false
    if (ollamaAvailable.value && !modelList.value.includes('ollama')) modelList.value = [...modelList.value, 'ollama']
  } catch { /* ok */ }
})

watch(() => props.selectedIssue, () => { issueResult.value = null; prResult.value = null })

async function analyse() {
  analysing.value = true; bedrockError.value = null; compareResults.value = []
  try { const res = await bedrock.analyse(selectedModel.value); result.value = res.data }
  catch (e) { bedrockError.value = e?.response?.data?.detail || e.message }
  finally { analysing.value = false }
}

async function compare() {
  comparing.value = true; bedrockError.value = null; result.value = null
  try { const res = await bedrock.compare(selectedModel.value); compareResults.value = res.data?.results ?? [] }
  catch (e) { bedrockError.value = e?.response?.data?.detail || e.message }
  finally { comparing.value = false }
}

async function reviewIssue() {
  if (!props.selectedIssue) return
  reviewingIssue.value = true; bedrockError.value = null; result.value = null; compareResults.value = []
  try { const res = await bedrock.analyseIssue(selectedModel.value, props.selectedIssue); issueResult.value = res.data }
  catch (e) { bedrockError.value = e?.response?.data?.detail || e.message }
  finally { reviewingIssue.value = false }
}

async function createPr() {
  if (!props.selectedIssue || !issueResult.value) return
  creatingPr.value = true; bedrockError.value = null
  try { const res = await github.createFixPr(props.selectedIssue, issueResult.value.analysis, selectedModel.value); prResult.value = res.data }
  catch (e) { bedrockError.value = e?.response?.data?.detail || e.message }
  finally { creatingPr.value = false }
}

function shortComponent(c) {
  if (!c) return ''
  return c.split(':').pop()?.split('/').slice(-2).join('/')
}
</script>
