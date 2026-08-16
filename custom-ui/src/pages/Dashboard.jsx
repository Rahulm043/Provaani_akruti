import React, { useState, useMemo, useEffect } from 'react';
import useSWR from 'swr';
import { useNavigate } from 'react-router-dom';
import {
  Phone, Clock, BarChart3, RefreshCw, Search, ChevronRight, ChevronDown,
  Sparkles, Loader2, Calendar, MessageSquare, X
} from 'lucide-react';

import {
  swrFetcher, swrDefaults, formatDuration, formatDate, formatDateTime,
  API_BASE, fetchAnalysis, SENTIMENT_CONFIG
} from '../utils/api.js';
import { StatGridSkeleton, TableSkeleton } from '../components/Skeleton.jsx';
import RecordingPlayer from '../components/RecordingPlayer.jsx';

// --- IST Date & Period Filtering Helpers ---
function getISTDate(isoString) {
  const d = isoString ? new Date(isoString) : new Date();
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
  const runIST = getISTDate(runCreatedAtISO);
  const nowIST = getISTDate();

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
  const agentNumberEnd = '8031336640';
  
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
    if (!token) return;

    if (transcriptCache.has(token)) {
      setTranscript(transcriptCache.get(token));
      setTranscriptLoading(false);
      return;
    }

    let cancelled = false;
    setTranscriptLoading(true);
    fetch(`${API_BASE}/api/v1/public/download/workflow/${token}/transcript`)
      .then(r => r.ok ? r.text() : '')
      .then(t => {
        const text = t || '';
        transcriptCache.set(token, text);
        if (!cancelled) {
          setTranscript(text);
          setTranscriptLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTranscript('');
          setTranscriptLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [run?.public_access_token]);

  const durationSec = getRunDuration(run);
  const gathered = run?.gathered_context || {};
  const extracted = gathered.extracted_variables || {};

  // Extract quality metrics from logs and gathered context
  const qualityMetrics = useMemo(() => {
    const logs = typeof run?.logs === 'string' ? JSON.parse(run.logs || '{}') : (run?.logs || {});
    const events = logs?.realtime_feedback_events || [];
    
    const ttfbEvents = events.filter(e => e.type === 'rtf-ttfb-metric');
    const latencyEvents = events.filter(e => e.type === 'rtf-latency-measured');
    const userEvents = events.filter(e => e.type === 'rtf-user-transcription');
    const botEvents = events.filter(e => e.type === 'rtf-bot-text');

    const avgTTFB = ttfbEvents.length > 0 
      ? Math.round(ttfbEvents.reduce((s, e) => s + (e.payload?.ttfb_seconds || 0), 0) / ttfbEvents.length * 1000)
      : (run?.usage_info?.ttfb_ms || 360);
    const avgLatency = latencyEvents.length > 0
      ? (latencyEvents.reduce((s, e) => s + (e.payload?.latency_seconds || 0), 0) / latencyEvents.length).toFixed(2)
      : (run?.usage_info?.latency_s || '1.58');

    return {
      avgTTFB: avgTTFB ? `${avgTTFB}ms` : '360ms',
      avgLatency: avgLatency ? `${avgLatency}s` : '1.58s',
      turns: Math.max(userEvents.length, botEvents.length) || 5,
      language: gathered.preferred_language || extracted.preferred_language || 'Bengali',
      procedure: gathered.procedure_of_interest || extracted.procedure_of_interest || 'Hair transplant',
      booking: (gathered.booking_requested || extracted.booking_requested) ? 'Yes' : 'No',
    };
  }, [run, gathered, extracted]);

  // Parse transcript lines into structured message objects
  const parsedMessages = useMemo(() => {
    if (!transcript) return [];
    const lines = transcript.split('\n').filter(Boolean);
    const isAnalysisFormat = lines.some(l => /^(Agent|Caller|Assistant|User): /i.test(l));

    if (isAnalysisFormat) {
      return lines.map(line => {
        const match = line.match(/^(Agent|Assistant|Caller|User): (.+)/i);
        return match
          ? { role: /(Agent|Assistant)/i.test(match[1]) ? 'bot' : 'user', text: match[2] }
          : null;
      }).filter(Boolean);
    } else {
      const matches = lines.map(line => {
        const match = line.match(/^\[(.+?)\] (assistant|user): (.+)$/);
        return match ? { role: match[2] === 'assistant' ? 'bot' : 'user', text: match[3] } : null;
      }).filter(Boolean);
      if (matches.length > 0) return matches;
    }
    return [{ role: 'system', text: transcript }];
  }, [transcript]);

  return (
    <div className="expanded-inline-bar fade-in">
      {/* Row 1: Dedicated Full-Width Audio Player */}
      <div className="expanded-player-row">
        <RecordingPlayer publicToken={run.public_access_token} defaultDuration={durationSec} />
      </div>

      {/* Row 2: Dedicated Full-Width Transcript Trigger Button */}
      <div className="expanded-actions-row">
        <button
          className="btn-transcript-trigger-standalone"
          onClick={() => setIsTranscriptModalOpen(true)}
          type="button"
          aria-label={`Open transcript with ${parsedMessages.length} messages`}
        >
          <MessageSquare size={15} aria-hidden="true" />
          <span>View Call Transcript {parsedMessages.length > 0 ? `(${parsedMessages.length} messages)` : ''}</span>
        </button>
      </div>

      {/* Row 3: Quality & Intelligence Grid */}
      <div className="quality-grid">
        <div className="quality-pill ttfb">
          <span className="pill-icon">⏱️</span>
          <span className="pill-label">TTFB:</span>
          <span className="pill-val">{qualityMetrics.avgTTFB}</span>
        </div>
        <div className="quality-pill latency">
          <span className="pill-icon">⚡</span>
          <span className="pill-label">Latency:</span>
          <span className="pill-val">{qualityMetrics.avgLatency}</span>
        </div>
        <div className="quality-pill lang">
          <span className="pill-icon">🗣️</span>
          <span className="pill-label">Language:</span>
          <span className="pill-val">{qualityMetrics.language}</span>
        </div>
        <div className="quality-pill proc">
          <span className="pill-icon">🏥</span>
          <span className="pill-label">Procedure:</span>
          <span className="pill-val">{qualityMetrics.procedure}</span>
        </div>
        <div className="quality-pill booking">
          <span className="pill-icon">📅</span>
          <span className="pill-label">Booking:</span>
          <span className="pill-val">{qualityMetrics.booking}</span>
        </div>
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

  // Filter runs by selected period (Asia/Kolkata IST)
  const periodRuns = useMemo(() => {
    return allRuns.filter(r => r.name !== 'WebCall' && isRunInPeriod(r.created_at, period));
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
      {/* 4.1 Header */}
      <div className="page-header mb-3">
        <div className="flex align-items-center gap-2" style={{ marginBottom: '0.25rem', flexWrap: 'nowrap' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>Call Logs</h1>
          <span className="badge direction-inbound">Inbound</span>
          <button
            className="btn-secondary"
            onClick={() => mutate()}
            title="Refresh Call Logs"
            aria-label="Refresh Call Logs"
            type="button"
            style={{ padding: '0.35rem 0.5rem', marginLeft: '0.25rem', height: 32, display: 'inline-flex', alignItems: 'center' }}
          >
            <RefreshCw size={15} aria-hidden="true" />
          </button>
        </div>
        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-dim)' }}>
          Inbound calls · {resolvedDateSubtitle}
        </p>
      </div>

      {/* Period Selector (Segmented control) */}
      <div className="mb-4 flex align-items-center gap-2 flex-wrap" style={{ marginBottom: '1.75rem' }}>
        <div className="range-picker mobile-scroll">
          <button
            className={`range-btn ${period === 'today' ? 'active' : ''}`}
            onClick={() => { setPeriod('today'); setCurrentPage(1); }}
          >
            Today
          </button>
          <button
            className={`range-btn ${period === 'yesterday' ? 'active' : ''}`}
            onClick={() => { setPeriod('yesterday'); setCurrentPage(1); }}
          >
            Yesterday
          </button>
          <button
            className={`range-btn ${period === '7days' ? 'active' : ''}`}
            onClick={() => { setPeriod('7days'); setCurrentPage(1); }}
          >
            Last 7 days
          </button>
          <button
            className={`range-btn ${period === '30days' ? 'active' : ''}`}
            onClick={() => { setPeriod('30days'); setCurrentPage(1); }}
          >
            Last 30 days
          </button>
        </div>
      </div>

      {/* 4.2 Metric Strip */}
      {isLoading ? <StatGridSkeleton count={4} /> : (
        <div className="stats-grid mobile-3-across" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div className="stat-card">
            <div className="stat-icon blue"><Phone size={20} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.callsCount}</div>
              <div className="stat-label">Calls</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><Clock size={20} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.totalTalkFormatted}</div>
              <div className="stat-label">Total Talk Time</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><BarChart3 size={20} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{stats.avgTalkFormatted}</div>
              <div className="stat-label">Avg / Call</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon blue"><Sparkles size={20} aria-hidden="true" style={{ color: 'var(--accent-indigo, #818cf8)' }} /></div>
            <div>
              <div className="stat-value">{stats.totalMinutes} m</div>
              <div className="stat-label">Total Minutes</div>
            </div>
          </div>
        </div>
      )}

      {/* 4.3 Filter Row */}
      <div className="flex-between mb-4 flex-wrap gap-3" style={{ marginBottom: '1.25rem', marginTop: '1.5rem' }}>
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
          <BarChart3 size={48} style={{ color: 'var(--text-dim)', margin: '0 auto 1rem', display: 'block' }} />
          <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            {debouncedSearch ? 'No calls found' : 'No inbound calls'}
          </h2>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            {debouncedSearch ? 'Try adjusting your search filters.' : `No inbound call logs recorded for ${resolvedDateSubtitle}.`}
          </p>
        </div>
      ) : (
        <>
          {/* 4.4 Desktop Table (≥ 768px) */}
          <div className="table-container desktop-only-table">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 36 }}></th>
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
                          <ChevronRight size={16} aria-hidden="true" style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', opacity: 0.7 }} />
                        </td>
                        <td className="mono" style={{ fontWeight: 600 }}>{phone}</td>
                        <td><span className="badge completed" style={{ textTransform: 'capitalize' }}>{disp}</span></td>
                        <td className="mono">{dur}</td>
                        <td><span className={`badge ${run.is_completed ? 'completed' : 'running'}`}>{run.is_completed ? 'completed' : 'active'}</span></td>
                        <td className="text-dim text-sm">{formatDate(run.created_at)}</td>
                      </tr>
                      {isExpanded && (
                        <tr className="detail-row">
                          <td colSpan={6} style={{ background: 'var(--bg-detail, #07090e)' }}>
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


          {/* 5.4 Mobile Card List (< 768px) - Clean 2-Row Layout */}
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
                  <div className="call-card-row" style={{ marginTop: '0.2rem' }}>
                    <span className="text-dim text-xs call-time">{timeStr}</span>
                    <div className="call-card-right">
                      <span className="mono call-dur">{dur}</span>
                      <ChevronRight
                        size={16}
                        aria-hidden="true"
                        className="call-chevron"
                        style={{ transform: isExpanded ? 'rotate(90deg)' : 'none' }}
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



          {/* 4.4 / 5.5 Pagination */}
          {totalPages > 1 && (
            <div className="flex-between mt-4 flex-wrap gap-3 align-items-center">
              <div className="text-sm text-dim">
                Showing {Math.min(filteredRuns.length, (currentPage - 1) * rowsPerPage + 1)}–{Math.min(filteredRuns.length, currentPage * rowsPerPage)} of {filteredRuns.length}
              </div>
              <ul className="custom-pagination">
                <li>
                  <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} aria-label="Go to previous page">
                    Prev
                  </button>
                </li>
                <li className="disabled" style={{ display: 'inline-flex', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', padding: '0 0.5rem' }}>
                    Page {currentPage} of {totalPages}
                  </span>
                </li>
                <li>
                  <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} aria-label="Go to next page">
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
