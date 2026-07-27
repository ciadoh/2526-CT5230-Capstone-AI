import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const dashboard = {
  summary: () => api.get('/dashboard/summary'),
}

export const sonar = {
  metrics: () => api.get('/sonar/metrics'),
  issues: (n = 50) => api.get(`/sonar/issues?page_size=${n}`),
  hotspots: () => api.get('/sonar/hotspots'),
  history: (metric = 'sqale_index') => api.get(`/sonar/history?metric=${metric}`),
}

export const github = {
  repo: () => api.get('/github/repo'),
  commits: (n = 20) => api.get(`/github/commits?per_page=${n}`),
  languages: () => api.get('/github/languages'),
  contributors: () => api.get('/github/contributors'),
  createFixPr: (issue, analysis, model_alias) => api.post('/github/create-fix-pr', {
    issue_key: issue.key,
    issue_message: issue.message,
    component: issue.component,
    analysis,
    model_alias,
  }),
}

export const scan = {
  trigger: () => api.post('/scan/trigger'),
  status: () => api.get('/scan/status'),
}

export const config = {
  getRepo: () => api.get('/config/repo'),
  switchRepo: (repo) => api.post('/config/repo', { repo }),
}

export const bedrock = {
  models: () => api.get('/bedrock/models'),
  analyse: (model_alias) => api.post('/bedrock/analyse', { model_alias }),
  analyseIssue: (model_alias, issue) => api.post('/bedrock/analyse-issue', {
    model_alias,
    issue_key: issue.key,
    message: issue.message,
    component: issue.component,
    severity: issue.severity ?? '',
    issue_type: issue.type ?? '',
    rule: issue.rule ?? '',
  }),
  compare: (model_alias) => api.post('/bedrock/compare', { model_alias }),
}

export const mlflow = {
  experiments: () => api.get('/mlflow/experiments'),
  runs: (maxResults = 10, pageToken = null) => {
    const params = { max_results: maxResults }
    if (pageToken) params.page_token = pageToken
    return api.get('/mlflow/runs', { params })
  },
}

export const langfuse = {
  traces: (limit = 10, page = 1) => api.get('/langfuse/traces', { params: { limit, page } }),
}

export const ollama = {
  status: () => api.get('/ollama/status'),
}

export const ml = {
  train: () => api.post('/ml/train'),
  predict: () => api.get('/ml/predict'),
}

export const churn = {
  get: () => api.get('/dashboard/churn'),
}
