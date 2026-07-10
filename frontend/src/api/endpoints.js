import { apiClient, cleanParams } from "./client.js";

// Thin, exhaustive mapping of the Phase 9 REST surface. Every function is a
// one-to-one call to a backend endpoint — no business logic, no derived
// analytics, no mock data. Grouped by domain for discoverability.

const get = (url, params) =>
  apiClient.get(url, { params: cleanParams(params) }).then((r) => r.data);
const post = (url, body) => apiClient.post(url, body).then((r) => r.data);

export const healthApi = {
  live: () => get("/health"),
  db: () => get("/health/db"),
  enums: () => get("/health/enums"),
  root: () => apiClient.get("/", { baseURL: "" }).then((r) => r.data),
};

export const portfolioApi = {
  summary: () => get("/portfolio/summary"),
  overview: (topN = 5) => get("/portfolio/overview", { top_n: topN }),
  kpis: (range) => get("/portfolio/kpis", range),
  snapshot: (range) => get("/portfolio/kpis/snapshot", range),
  trends: (range) => get("/portfolio/trends", range),
  growth: () => get("/portfolio/growth"),
  health: () => get("/portfolio/health"),
  compare: (body) => post("/portfolio/compare", body),
};

export const dashboardApi = {
  portfolioCards: () => get("/dashboard/cards/portfolio"),
  summaryCards: (range) => get("/dashboard/cards/summary", range),
  quickStats: () => get("/dashboard/quick-stats"),
  recentActivity: (limit = 10) => get("/dashboard/recent-activity", { limit }),
  systemOverview: () => get("/dashboard/system-overview"),
  executive: (topN = 5) => get("/dashboard/executive", { top_n: topN }),
};

export const merchantApi = {
  search: (params) => get("/merchants/search", params),
  rankings: (params) => get("/merchants/rankings", params),
  top: (params) => get("/merchants/top", params),
  bottom: (params) => get("/merchants/bottom", params),
  contribution: (params) => get("/merchants/contribution", params),
  distribution: (range) => get("/merchants/distribution", range),
  successRate: (params) => get("/merchants/success-rate", params),
  growth: (body) => post("/merchants/growth", body),
  compare: (body, range) =>
    apiClient
      .post("/merchants/compare", body, { params: cleanParams(range) })
      .then((r) => r.data),
  profile: (id) => get(`/merchants/${encodeURIComponent(id)}/profile`),
  summary: (id) => get(`/merchants/${encodeURIComponent(id)}/summary`),
  activity: (id, limit = 20) =>
    get(`/merchants/${encodeURIComponent(id)}/activity`, { limit }),
};

export const customerApi = {
  search: (params) => get("/customers/search", params),
  byVpa: (vpa) => get("/customers/by-vpa", { vpa }),
  active: (range) => get("/customers/active", range),
  activityDistribution: (range) => get("/customers/activity-distribution", range),
  frequency: (range) => get("/customers/frequency", range),
  top: (params) => get("/customers/top", params),
  contribution: (params) => get("/customers/contribution", params),
  trend: (range) => get("/customers/trend", range),
  profile: (id) => get(`/customers/${encodeURIComponent(id)}/profile`),
  summary: (id) => get(`/customers/${encodeURIComponent(id)}/summary`),
  history: (id, limit = 20) =>
    get(`/customers/${encodeURIComponent(id)}/history`, { limit }),
};

export const bankApi = {
  list: (activeOnly = false) => get("/banks", { active_only: activeOnly }),
  rankings: (params) => get("/banks/rankings", params),
  contribution: (params) => get("/banks/contribution", params),
  volumeComparison: (params) => get("/banks/volume-comparison", params),
  successComparison: (params) => get("/banks/success-comparison", params),
  issuers: (range) => get("/banks/issuers", range),
  acquirers: (range) => get("/banks/acquirers", range),
  profile: (name) => get(`/banks/${encodeURIComponent(name)}/profile`),
  statistics: (name, side = "issuer") =>
    get(`/banks/${encodeURIComponent(name)}/statistics`, { side }),
  trend: (name, params) => get(`/banks/${encodeURIComponent(name)}/trend`, params),
};

export const pspApi = {
  list: (activeOnly = false) => get("/psps", { active_only: activeOnly }),
  overview: (range) => get("/psps/overview", range),
  rankings: (params) => get("/psps/rankings", params),
  top: (params) => get("/psps/top", params),
  performance: (range) => get("/psps/performance", range),
  contribution: (params) => get("/psps/contribution", params),
  successAnalysis: (params) => get("/psps/success-analysis", params),
  profile: (name) => get(`/psps/${encodeURIComponent(name)}/profile`),
  statistics: (name) => get(`/psps/${encodeURIComponent(name)}/statistics`),
  trend: (name, params) => get(`/psps/${encodeURIComponent(name)}/trend`, params),
};

export const analyticsApi = {
  catalogue: () => get("/analytics"),
  time: (grain, params) => get(`/analytics/time/${grain}`, params),
  hourly: (params) => get("/analytics/time/hourly", params),
  summary: (range) => get("/analytics/time/summary", range),
};

export const copilotApi = {
  chat: (message, conversationId = null) =>
    post("/copilot/chat", { message, conversation_id: conversationId }),
  intents: () => get("/copilot/intents"),
  tools: () => get("/copilot/tools"),
  suggestions: () => get("/copilot/suggestions"),
  history: (conversationId) =>
    get(`/copilot/conversations/${encodeURIComponent(conversationId)}`),
  clear: (conversationId) =>
    apiClient
      .delete(`/copilot/conversations/${encodeURIComponent(conversationId)}`)
      .then((r) => r.data),
};

export const searchApi = {
  merchants: (params) => get("/search/merchants", params),
  customers: (params) => get("/search/customers", params),
  banks: (params) => get("/search/banks", params),
  psps: (params) => get("/search/psps", params),
};
