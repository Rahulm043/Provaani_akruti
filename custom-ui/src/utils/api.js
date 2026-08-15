const TOKEN_KEY = 'dograh_token';
const API_BASE = '';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function authFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    window.location.href = '/login';
  }
  return response;
}

export const swrFetcher = async (endpoint) => {
  const res = await authFetch(endpoint);
  if (!res.ok) {
    const error = new Error('API request failed');
    error.info = await res.json().catch(() => ({}));
    error.status = res.status;
    throw error;
  }
  return res.json();
};

export const swrDefaults = {
  fetcher: swrFetcher,
  dedupingInterval: 5000,
  revalidateOnFocus: true,
  shouldRetryOnError: false,
};

export { API_BASE };

export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString([], {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

export function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export async function fetchAnalysis(runId) {
  try {
    const res = await authFetch(`/analysis/${runId}`);
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'completed') return data;
    }
  } catch {}
  return null;
}

export async function fetchAnalyses(runIds) {
  try {
    const ids = runIds.join(',');
    const res = await authFetch(`/analysis?run_ids=${ids}`);
    if (res.ok) {
      const data = await res.json();
      return data.analyses || {};
    }
  } catch {}
  return {};
}

export const SENTIMENT_CONFIG = {
  interested: { label: 'Interested', color: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
  not_interested: { label: 'Not Interested', color: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
  irrelevant: { label: 'Irrelevant', color: '#94a3b8', bg: 'rgba(148,163,184,0.1)' },
  unsure: { label: 'Unsure', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
};
