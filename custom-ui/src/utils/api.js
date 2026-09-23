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

export function parseSafeDate(isoString) {
  if (!isoString) return null;
  if (isoString instanceof Date) return isNaN(isoString.getTime()) ? null : isoString;
  let str = String(isoString).trim();
  if (str.includes(' ') && !str.includes('T')) {
    str = str.replace(' ', 'T');
  }
  if (str.endsWith('+00')) {
    str = str + ':00';
  }
  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

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

export async function fetchClinicSettings() {
  const res = await authFetch('/api/v1/campaign/clinic-settings');
  if (!res.ok) {
    throw new Error('Failed to fetch clinic settings');
  }
  return res.json();
}

export async function saveClinicSettings(payload) {
  const res = await authFetch('/api/v1/campaign/clinic-settings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save clinic settings');
  }
  return res.json();
}

export async function fetchAppointments(params = {}) {
  const query = new URLSearchParams();
  if (params.appointment_date) query.append('appointment_date', params.appointment_date);
  if (params.branch_id && params.branch_id !== 'all') query.append('branch_id', params.branch_id);
  if (params.status && params.status !== 'all') query.append('status', params.status);
  if (params.search) query.append('search', params.search);

  const qs = query.toString();
  const url = `/api/v1/campaign/appointments${qs ? `?${qs}` : ''}`;
  const res = await authFetch(url);
  if (!res.ok) {
    throw new Error('Failed to fetch appointments');
  }
  return res.json();
}

export async function bookAppointment(payload) {
  const res = await authFetch('/api/v1/campaign/appointments/book', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.success === false) {
    throw new Error(data.error || data.detail || 'Failed to book appointment');
  }
  return data;
}

export async function updateAppointment(id, payload) {
  const res = await authFetch(`/api/v1/campaign/appointments/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.success === false) {
    throw new Error(data.error || data.detail || 'Failed to update appointment');
  }
  return data;
}

export async function updateAppointmentStatus(id, { status, notes }) {
  const res = await authFetch(`/api/v1/campaign/appointments/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update appointment status');
  }
  return res.json();
}

export async function deleteAppointment(id) {
  const res = await authFetch(`/api/v1/campaign/appointments/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete appointment');
  }
  return res.json();
}


