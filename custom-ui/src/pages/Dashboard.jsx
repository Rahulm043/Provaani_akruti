import React, { useState, useMemo, useEffect } from 'react';
import useSWR from 'swr';
import { useNavigate } from 'react-router-dom';
import {
  Phone, Clock, BarChart3, RefreshCw, Search, ChevronRight, ChevronDown,
  Sparkles, Loader2, Calendar, MessageSquare, X
} from 'lucide-react';

import {
  swrFetcher, swrDefaults, formatDuration, formatDate, formatDateTime,
  API_BASE, fetchAnalysis, SENTIMENT_CONFIG, parseSafeDate
} from '../utils/api.js';
import { StatGridSkeleton, TableSkeleton } from '../components/Skeleton.jsx';
import RecordingPlayer from '../components/RecordingPlayer.jsx';

// --- IST Date & Period Filtering Helpers ---
const START_DATE_STR = import.meta.env.VITE_START_DATE || import.meta.env.VITE_BILLING_START_DATE || '2026-08-18';

function getISTDate(isoString) {
  const d = isoString ? parseSafeDate(isoString) : new Date();
  if (!d) return new Date();
  // IST is UTC + 5:30 (330 minutes)
  const utc = d.getTime() + d.getTimezoneOffset() * 60000;
  return new Date(utc + 330 * 60000);
}

function formatResolvedDate(periodOption) {
  if (periodOption === 'today') return 'Today';
  if (periodOption === 'yesterday') return 'Yesterday';
  if (periodOption === '7days') return 'Last 7 days';
  if (periodOption === '30days') return 'Last 30 days';
  return 'Last 30 days';
}

function isRunInPeriod(runCreatedAtISO, periodOption) {
  if (!runCreatedAtISO) return false;

  const runDate = parseSafeDate(runCreatedAtISO);
  if (!runDate) return false;

  // Filter out all calls before the configured START_DATE (00:00:00 IST)
  const startDateCutoff = parseSafeDate(`${START_DATE_STR}T00:00:00+05:30`);
  if (startDateCutoff && runDate < startDateCutoff) return false;

  const runIST = getISTDate(runCreatedAtISO);
  const nowIST = getISTDate();
  if (!runIST || !nowIST) return false;

  const rY = runIST.getFullYear();
  const rM = runIST.getMonth();
  const rD = runIST.getDate();

  const nY = nowIST.getFullYear();
  const nM = nowIST.getMonth();
  const nD = nowIST.getDate();

  if (periodOption === 'today') {
    return rY === nY && rM === nM && rD === nD;
  }
  if (periodOption === 'yesterday') {
    const yest = new Date(nowIST);
    yest.setDate(yest.getDate() - 1);
    return rY === yest.getFullYear() && rM === yest.getMonth() && rD === yest.getDate();
  }
  if (periodOption === '7days') {
    const start7 = new Date(nowIST.getFullYear(), nowIST.getMonth(), nowIST.getDate() - 6, 0, 0, 0);
    const end7 = new Date(nowIST.getFullYear(), nowIST.getMonth(), nowIST.getDate(), 23, 59, 59, 999);
    return runIST >= start7 && runIST <= end7;
  }
  if (periodOption === '30days') {
    const start30 = new Date(nowIST.getFullYear(), nowIST.getMonth(), nowIST.getDate() - 29, 0, 0, 0);
    const end30 = new Date(nowIST.getFullYear(), nowIST.getMonth(), nowIST.getDate(), 23, 59, 59, 999);
    return runIST >= start30 && runIST <= end30;
  }
  return true;
}

function formatTalkTime(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const totalM = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (totalM >= 60) {
    const h = Math.floor(totalM / 60);
    const m = totalM % 60;
    return `${h}h ${m}m`;
  }
  return totalM > 0 ? `${totalM}m ${s}s` : `${s}s`;
}

function getCustomerPhone(run) {
  const ic = run?.initial_context || {};
  const agentNumberEnd = '8031825997';
  
  const candidates = [
    ic.caller_number,
    ic.phone_number,
    ic.called_number
  ].filter(Boolean);

  const realCustomerNumber = candidates.find(num => typeof num === 'string' && !num.endsWith(agentNumberEnd));
  return realCustomerNumber || candidates[0] || '—';
}

function formatDateTimeShort(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}


// In-memory transcript cache to prevent duplicate fetches on re-expanding rows
const transcriptCache = new Map();

// --- Decoupled Transcript Modal Component ---
function TranscriptModal({ isOpen, onClose, run, parsedMessages, isLoading }) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="transcript-modal-title"
    >
      <div className="transcript-modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-header-title">
            <MessageSquare size={18} aria-hidden="true" style={{ color: 'var(--accent-indigo, #818cf8)', flexShrink: 0 }} />
            <div>
              <div id="transcript-modal-title" style={{ fontWeight: 700, fontSize: '0.95rem' }}>Call Transcript</div>
              <div className="mono text-dim text-xs">{getCustomerPhone(run)} · {formatDateTimeShort(run.created_at)}</div>
            </div>
          </div>
          <button
            className="modal-close-btn"
            onClick={onClose}
            type="button"
            aria-label="Close transcript modal"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="modal-body transcript-inline-container" style={{ maxHeight: '60vh', overflowY: 'auto', padding: '1rem' }}>
          {isLoading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
              Loading transcript...
            </div>
          ) : parsedMessages.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
              No transcript available for this call.
            </div>
          ) : (
            parsedMessages.map((msg, idx) => (
              <div key={idx} className={`transcript-msg ${msg.role}`}>
                <div className="role-label">
                  {msg.role === 'bot' ? 'Assistant' : msg.role === 'user' ? 'Caller' : 'System'}
                </div>
                <div style={{ fontSize: '0.85rem', lineHeight: 1.45 }}>{msg.text}</div>
              </div>
            ))
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn-secondary"
            onClick={onClose}
            type="button"
            aria-label="Close modal"
            style={{ padding: '0.4rem 1.25rem', fontSize: '0.82rem' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Helper to reliably extract call duration across schemas
function getRunDuration(run) {
  if (!run) return 0;
  return run.cost_info?.call_duration_seconds || run.usage_info?.call_duration_seconds || run.duration || 0;
}

// --- Inline Call Detail Component ---
function InlineCallDetail({ run }) {
  const [transcript, setTranscript] = useState(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = useState(false);

  useEffect(() => {
    const token = run?.public_access_token;
    const runId = run?.id;
    if (!token && !runId) return;

    const cacheKey = token || `run_${runId}`;
    if (transcriptCache.has(cacheKey)) {
      setTranscript(transcriptCache.get(cacheKey));
      setTranscriptLoading(false);
      return;
    }

    let cancelled = false;
    setTranscriptLoading(true);

    const tryFetch = async () => {
      let text = '';
      if (token) {
        try {
          const r = await fetch(`${API_BASE}/api/v1/public/download/workflow/${token}/transcript`);
          if (r.ok) text = await r.text();
        } catch { /* ignore */ }
      }
      if (!text && runId) {
        try {
          const r = await fetch(`${API_BASE}/voice-audio/transcripts/${runId}.txt`);
          if (r.ok) text = await r.text();
        } catch { /* ignore */ }
      }
      if (!cancelled) {
        if (text) {
          transcriptCache.set(cacheKey, text);
          setTranscript(text);
        } else {
          setTranscript('');
        }
        setTranscriptLoading(false);
      }
    };

    tryFetch();
    return () => { cancelled = true; };
  }, [run?.public_access_token, run?.id]);

  const durationSec = getRunDuration(run);
  const gathered = run?.gathered_context || {};
  const extracted = gathered.extracted_variables || {};

  // Extract quality metrics & metadata from logs and gathered context
  const qualityMetrics = useMemo(() => {
    return {
      language: gathered.preferred_language || extracted.preferred_language || 'Bengali',
      procedure: gathered.procedure_of_interest || extracted.procedure_of_interest || 'Hair transplant',
      booking: (gathered.booking_requested || extracted.booking_requested) ? 'Yes' : 'No',
    };
  }, [gathered, extracted]);

  // Parse transcript lines into structured message objects
  const parsedMessages = useMemo(() => {
    if (transcript) {
      const lines = transcript.split('\n').filter(Boolean);
      const isAnalysisFormat = lines.some(l => /^(Agent|Caller|Assistant|User): /i.test(l));

      if (isAnalysisFormat) {
        const msgs = lines.map(line => {
          const match = line.match(/^(Agent|Assistant|Caller|User): (.+)/i);
          return match
            ? { role: /(Agent|Assistant)/i.test(match[1]) ? 'bot' : 'user', text: match[2] }
            : null;
        }).filter(Boolean);
        if (msgs.length > 0) return msgs;
      } else {
        const matches = lines.map(line => {
          const match = line.match(/^\[(.+?)\] (assistant|user): (.+)$/);
          return match ? { role: match[2] === 'assistant' ? 'bot' : 'user', text: match[3] } : null;
        }).filter(Boolean);
        if (matches.length > 0) return matches;
      }
    }

    // Fallback: extract messages directly from run logs realtime feedback events
    const logs = typeof run?.logs === 'string' ? JSON.parse(run.logs || '{}') : (run?.logs || {});
    const events = logs?.realtime_feedback_events || [];
    if (events.length > 0) {
      const rtfMsgs = [];
      for (const ev of events) {
        if (ev.type === 'rtf-bot-text' && ev.payload?.text) {
          rtfMsgs.push({ role: 'bot', text: ev.payload.text });
        } else if (ev.type === 'rtf-user-transcription' && ev.payload?.text && ev.payload?.final !== false) {
          rtfMsgs.push({ role: 'user', text: ev.payload.text });
        }
      }
      if (rtfMsgs.length > 0) return rtfMsgs;
    }

    return transcript ? [{ role: 'system', text: transcript }] : [];
  }, [transcript, run]);

  return (
    <div className="expanded-inline-bar fade-in">
      {/* Row 1: 80% Audio Player / 20% Transcript Button */}
      <div className="expanded-player-transcript-row">
        <div className="player-col-80">
          <RecordingPlayer publicToken={run.public_access_token} runId={run.id} defaultDuration={durationSec} />
        </div>
        <div className="transcript-col-20">
          <button
            className="btn-transcript-trigger-compact"
            onClick={() => setIsTranscriptModalOpen(true)}
            type="button"
            aria-label={`Open transcript with ${parsedMessages.length} messages`}
            title="View full conversation transcript"
          >
            <MessageSquare size={16} aria-hidden="true" />
            <span>Transcript {parsedMessages.length > 0 ? `(${parsedMessages.length})` : ''}</span>
          </button>
        </div>
      </div>

      {/* Row 2: Ultra-Compact Metadata Row (Language, Procedure, Booking) */}
      <div className="compact-meta-row">
        <span className="compact-meta-chip lang">
          <span className="meta-label">Language:</span>
          <span className="meta-val">{qualityMetrics.language}</span>
        </span>
        <span className="compact-meta-chip proc">
          <span className="meta-label">Procedure:</span>
          <span className="meta-val">{qualityMetrics.procedure}</span>
        </span>
        <span className="compact-meta-chip booking">
          <span className="meta-label">Booking:</span>
          <span className="meta-val">{qualityMetrics.booking}</span>
        </span>
      </div>

      {/* Standalone Decoupled Transcript Modal */}
      <TranscriptModal
        isOpen={isTranscriptModalOpen}
        onClose={() => setIsTranscriptModalOpen(false)}
        run={run}
        parsedMessages={parsedMessages}
        isLoading={transcriptLoading}
      />
    </div>
  );
}

// --- Main Dashboard Component ---
export default function Dashboard() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState('30days'); // 'today' | 'yesterday' | '7days' | '30days'

  const [expandedRunId, setExpandedRunId] = useState(null);
  const [expandedRun, setExpandedRun] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 25;

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch workflows
  const { data: workflows } = useSWR('/api/v1/workflow/fetch', swrFetcher, { dedupingInterval: 60000 });
  const wfIds = (workflows || []).map(w => w.id);

  // Fetch runs for workflows
  const combinedFetcher = async () => {
    if (!wfIds.length) return [];
    const results = await Promise.all(wfIds.map(wid =>
      fetch(`/api/v1/workflow/${wid}/runs?limit=100`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('dograh_token')}` },
      }).then(r => r.json()).then(d => (d.runs || []).map(r => ({ ...r, _wfId: wid }))).catch(() => [])
    ));
    const flat = results.flat();
    flat.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    return flat;
  };


  const { data: allRuns = [], isLoading, mutate } = useSWR(
    wfIds.length ? `all-runs:${wfIds.join(',')}` : null,
    combinedFetcher,
    { ...swrDefaults, refreshInterval: 10000 }
  );

  const wfNames = useMemo(() => Object.fromEntries((workflows || []).map(w => [w.id, w.name])), [workflows]);

  // Filter runs by selected period (Asia/Kolkata IST) and filter out duplicate/empty initialized artifacts
  const periodRuns = useMemo(() => {
    return allRuns.filter(r => {
      if (r.name === 'WebCall') return false;
      // Filter out orphaned initialized ghost runs
      if (r.state === 'initialized' && !r.is_completed && getRunDuration(r) === 0) return false;
      return isRunInPeriod(r.created_at, period);
    });
  }, [allRuns, period]);

  // Metric strip calculation
  const stats = useMemo(() => {
    const count = periodRuns.length;
    const totalTalkSec = periodRuns.reduce((sum, r) => sum + getRunDuration(r), 0);
    const avgTalkSec = count > 0 ? totalTalkSec / count : 0;
    const totalRoundedMinutes = periodRuns.reduce((sum, r) => {
      const seconds = getRunDuration(r);
      const rounded = seconds > 0 ? Math.ceil(seconds / 60) : 0;
      return sum + rounded;
    }, 0);

    return {
      callsCount: count,
      totalTalkFormatted: formatTalkTime(totalTalkSec),
      avgTalkFormatted: count > 0 ? formatTalkTime(avgTalkSec) : '—',
      totalMinutes: totalRoundedMinutes,
    };
  }, [periodRuns]);

  // Filtered runs (search + status)
  const filteredRuns = useMemo(() => {
    let res = periodRuns;
    if (debouncedSearch) {
      const term = debouncedSearch.toLowerCase();
      res = res.filter(r =>
        getCustomerPhone(r).toLowerCase().includes(term) ||
        (r.name || '').toLowerCase().includes(term)
      );
    }
    if (statusFilter !== 'all') {
      res = res.filter(r => {
        const d = (r.gathered_context?.call_disposition || '').toLowerCase();
        if (statusFilter === 'completed') return r.is_completed || d.includes('completed');
        if (statusFilter === 'hangup') return d.includes('hangup') || d.includes('user_hangup');
        if (statusFilter === 'qualified') return d.includes('qualified');
        if (statusFilter === 'failed') return d.includes('failed');
        if (statusFilter === 'error') return d.includes('error');
        return true;
      });
    }
    return res;
  }, [periodRuns, debouncedSearch, statusFilter]);

  // Pagination
  const totalPages = Math.ceil(filteredRuns.length / rowsPerPage) || 1;
  const paginatedRuns = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return filteredRuns.slice(start, start + rowsPerPage);
  }, [filteredRuns, currentPage, rowsPerPage]);

  const handleExpand = async (runId, wfId, originalRun) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null);
      setExpandedRun(null);
      return;
    }
    setExpandedRunId(runId);
    setExpandedRun(originalRun);
    try {
      const res = await fetch(`${API_BASE}/api/v1/workflow/${wfId}/runs/${runId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('dograh_token')}` },
      });
      if (res.ok) {
        const fullData = await res.json();
        setExpandedRun({ ...originalRun, ...fullData, gathered_context: originalRun?.gathered_context || fullData.gathered_context });
      }
    } catch { /* ignore */ }
  };

  const resolvedDateSubtitle = useMemo(() => formatResolvedDate(period), [period]);

  return (
    <div className="fade-in">
      {/* Page Header */}
      <div className="page-header mb-4">
        <div className="flex align-items-center gap-2" style={{ marginBottom: '0.35rem', flexWrap: 'nowrap' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>Call Logs</h1>
          <span className="badge direction-inbound">Inbound</span>
          <button
            className="btn-icon-refresh"
            onClick={() => mutate()}
            title="Refresh Call Logs"
            aria-label="Refresh Call Logs"
            type="button"
          >
            <RefreshCw size={14} aria-hidden="true" />
          </button>
        </div>
        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-dim)' }}>
          Inbound calls · <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{resolvedDateSubtitle}</span>
        </p>
      </div>

      {/* Period Selector (Segmented control) */}
      <div className="period-selector-row mb-4">
        <div className="range-picker mobile-scroll" role="tablist" aria-label="Select call logs timeframe">
          <button
            role="tab"
            aria-selected={period === 'today'}
            className={`range-btn ${period === 'today' ? 'active' : ''}`}
            onClick={() => { setPeriod('today'); setCurrentPage(1); }}
            type="button"
          >
            Today
          </button>
          <button
            role="tab"
            aria-selected={period === 'yesterday'}
            className={`range-btn ${period === 'yesterday' ? 'active' : ''}`}
            onClick={() => { setPeriod('yesterday'); setCurrentPage(1); }}
            type="button"
          >
            Yesterday
          </button>
          <button
            role="tab"
            aria-selected={period === '7days'}
            className={`range-btn ${period === '7days' ? 'active' : ''}`}
            onClick={() => { setPeriod('7days'); setCurrentPage(1); }}
            type="button"
          >
            Last 7 days
          </button>
          <button
            role="tab"
            aria-selected={period === '30days'}
            className={`range-btn ${period === '30days' ? 'active' : ''}`}
            onClick={() => { setPeriod('30days'); setCurrentPage(1); }}
            type="button"
          >
            Last 30 days
          </button>
        </div>
      </div>

      {/* Metric Strip */}
      {isLoading ? <StatGridSkeleton count={4} /> : (
        <div className="stats-grid mobile-3-across" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div className="stat-card">
            <div className="stat-icon blue"><Phone size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.callsCount}</div>
              <div className="stat-label">Calls</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><Clock size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.totalTalkFormatted}</div>
              <div className="stat-label">Total Talk Time</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><BarChart3 size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.avgTalkFormatted}</div>
              <div className="stat-label">Avg / Call</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon indigo"><Sparkles size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.totalMinutes} m</div>
              <div className="stat-label">Total Minutes</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter & Search Row */}
      <div className="flex-between mb-4 flex-wrap gap-3" style={{ marginBottom: '1.25rem', marginTop: '1.75rem' }}>
        <div className="flex align-items-center gap-2">
          <h3 className="section-title" style={{ margin: 0 }}>Recent Calls</h3>
        </div>
        <div className="filter-controls-row" style={{ margin: 0 }}>
          <select
            className="filter-select"
            aria-label="Filter calls by status"
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setCurrentPage(1); }}
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="hangup">User Hangup</option>
            <option value="qualified">Qualified</option>
            <option value="failed">Failed</option>
            <option value="error">Error</option>
          </select>
          <div className="search-input-group" style={{ width: 280, flex: 'none' }}>
            <Search size={14} aria-hidden="true" className="search-input-icon" />
            <input
              type="text"
              aria-label="Search phone number"
              placeholder="Search phone number..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Loading Skeleton or Empty States */}
      {isLoading ? <TableSkeleton columns={6} rows={6} /> : paginatedRuns.length === 0 ? (
        <div className="empty-state card">
          <BarChart3 size={44} style={{ color: 'var(--text-dim)', margin: '0 auto 1rem', display: 'block', opacity: 0.5 }} />
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '0.4rem' }}>
            {debouncedSearch ? 'No calls found' : 'No inbound calls'}
          </h2>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            {debouncedSearch ? 'Try adjusting your search filters or phone query.' : `No inbound call logs recorded for ${resolvedDateSubtitle}.`}
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table (≥ 768px) */}
          <div className="table-container desktop-only-table">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 36 }} aria-label="Expand indicator"></th>
                  <th>Phone</th>
                  <th>End reason</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {paginatedRuns.map(run => {
                  const isExpanded = expandedRunId === run.id;
                  const phone = getCustomerPhone(run);
                  const disp = (run.gathered_context?.call_disposition || 'completed').replace(/_/g, ' ');
                  const dur = formatDuration(getRunDuration(run));

                  return (
                    <React.Fragment key={run.id}>
                      <tr
                        className={`main-row ${isExpanded ? 'expanded' : ''}`}
                        onClick={() => handleExpand(run.id, run._wfId, run)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleExpand(run.id, run._wfId, run);
                          }
                        }}
                        tabIndex={0}
                        role="button"
                        aria-expanded={isExpanded}
                        aria-label={`Call log for ${phone}, duration ${dur}, status ${run.is_completed ? 'completed' : 'active'}`}
                        style={{ cursor: 'pointer' }}
                      >
                        <td style={{ textAlign: 'center', paddingRight: 0 }}>
                          <ChevronRight
                            size={15}
                            aria-hidden="true"
                            style={{
                              transform: isExpanded ? 'rotate(90deg)' : 'none',
                              transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                              color: isExpanded ? 'var(--accent-indigo, #818cf8)' : 'var(--text-dim)'
                            }}
                          />
                        </td>
                        <td className="mono" style={{ fontWeight: 600, color: 'var(--text)' }}>{phone}</td>
                        <td><span className="badge completed" style={{ textTransform: 'capitalize' }}>{disp}</span></td>
                        <td className="mono tabular-nums">{dur}</td>
                        <td><span className={`badge ${run.is_completed ? 'completed' : 'running'}`}>{run.is_completed ? 'completed' : 'active'}</span></td>
                        <td className="text-dim text-sm">{formatDate(run.created_at)}</td>
                      </tr>
                      {isExpanded && (
                        <tr className="detail-row">
                          <td colSpan={6} style={{ background: 'var(--bg-detail, #07090e)', padding: '0.75rem 1rem' }}>
                            {expandedRun ? <InlineCallDetail run={expandedRun} /> : (
                              <div className="flex-center" style={{ padding: '2rem' }}><div className="spinner-loader" /></div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card List (< 768px) - Clean Ergonomic 2-Row Layout */}
          <div className="mobile-only-cards">
            {paginatedRuns.map(run => {
              const isExpanded = expandedRunId === run.id;
              const phone = getCustomerPhone(run);
              const disp = (run.gathered_context?.call_disposition || 'completed').replace(/_/g, ' ');
              const dur = formatDuration(getRunDuration(run));
              const timeStr = formatDateTimeShort(run.created_at);

              return (
                <div
                  key={run.id}
                  className={`call-touch-card ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => handleExpand(run.id, run._wfId, run)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleExpand(run.id, run._wfId, run);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-expanded={isExpanded}
                  aria-label={`Call details for ${phone}, duration ${dur}`}
                >
                  {/* Row 1: Phone number (left) | Reason for hang up (right) */}
                  <div className="call-card-row">
                    <span className="mono call-phone">{phone}</span>
                    <span className="badge completed call-badge">{disp}</span>
                  </div>

                  {/* Row 2: Time of call (left) | Duration + Chevron (right) */}
                  <div className="call-card-row" style={{ marginTop: '0.25rem' }}>
                    <span className="text-dim text-xs call-time">{timeStr}</span>
                    <div className="call-card-right">
                      <span className="mono call-dur">{dur}</span>
                      <ChevronRight
                        size={15}
                        aria-hidden="true"
                        className="call-chevron"
                        style={{
                          transform: isExpanded ? 'rotate(90deg)' : 'none',
                          color: isExpanded ? 'var(--accent-indigo, #818cf8)' : 'inherit'
                        }}
                      />
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="call-card-detail" onClick={e => e.stopPropagation()}>
                      {expandedRun ? <InlineCallDetail run={expandedRun} /> : (
                        <div className="flex-center" style={{ padding: '1.5rem' }}><div className="spinner-loader" /></div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex-between mt-4 flex-wrap gap-3 align-items-center">
              <div className="text-sm text-dim">
                Showing {Math.min(filteredRuns.length, (currentPage - 1) * rowsPerPage + 1)}–{Math.min(filteredRuns.length, currentPage * rowsPerPage)} of {filteredRuns.length}
              </div>
              <ul className="custom-pagination">
                <li>
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    aria-label="Go to previous page"
                    type="button"
                  >
                    Prev
                  </button>
                </li>
                <li className="disabled" style={{ display: 'inline-flex', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', padding: '0 0.5rem' }}>
                    Page {currentPage} of {totalPages}
                  </span>
                </li>
                <li>
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    aria-label="Go to next page"
                    type="button"
                  >
                    Next
                  </button>
                </li>
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
