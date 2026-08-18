import React, { useState, useMemo } from 'react';
import useSWR from 'swr';
import { Phone, Clock, BarChart3, RefreshCw, ChevronDown, ChevronRight, Sparkles, CreditCard } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

import {
  swrFetcher, swrDefaults, formatDuration, formatDate,
  API_BASE, fetchAnalysis, SENTIMENT_CONFIG, parseSafeDate, authFetch
} from '../utils/api.js';
import { StatGridSkeleton } from '../components/Skeleton.jsx';

// Plan Settings
const LIMIT_MINUTES = 1000;
const OVERAGE_RATE = 3.0; // Rs. 3 per minute
const BILLING_START_DATE_STR = import.meta.env.VITE_BILLING_START_DATE || import.meta.env.VITE_START_DATE || '2026-08-18';

// Helpers
function getISTDate(isoString) {
  const d = isoString ? parseSafeDate(isoString) : new Date();
  if (!d) return new Date();
  const utc = d.getTime() + d.getTimezoneOffset() * 60000;
  return new Date(utc + 330 * 60000);
}

function getRunDuration(run) {
  if (!run) return 0;
  return run.cost_info?.call_duration_seconds || run.usage_info?.call_duration_seconds || run.duration || 0;
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

// Generate periods of 30 days starting from startStr
function getBillingPeriods(startStr) {
  const start = parseSafeDate(`${startStr}T00:00:00+05:30`) || new Date(startStr);
  const now = new Date();
  const periods = [];
  let currentStart = new Date(start);

  while (currentStart <= now) {
    const periodEnd = new Date(currentStart);
    periodEnd.setDate(periodEnd.getDate() + 29);
    periodEnd.setHours(23, 59, 59, 999);

    const isCurrent = now >= currentStart && now <= periodEnd;
    periods.push({
      start: new Date(currentStart),
      end: new Date(periodEnd),
      isCurrent,
      label: `${currentStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} - ${periodEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
    });

    currentStart = new Date(periodEnd);
    currentStart.setMilliseconds(currentStart.getMilliseconds() + 1);
  }

  periods.reverse();
  return periods;
}

// Mock completed periods data (reset for client start date)
const MOCK_PERIODS_DATA = {};

export default function Usage() {
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [selectedPeriodIdx, setSelectedPeriodIdx] = useState(0);
  const [rangeMode, setRangeMode] = useState('1Month'); // '7Days' | '1Month' | 'Lifetime'
  
  // Calculate periods
  const periods = useMemo(() => getBillingPeriods(BILLING_START_DATE_STR), []);
  const currentSelectedPeriod = periods[selectedPeriodIdx] || periods[0];

  // Fetch workflows to retrieve runs
  const { data: workflows } = useSWR('/api/v1/workflow/fetch', swrFetcher, { dedupingInterval: 60000 });
  const wfIds = (workflows || []).map(w => w.id);

  // Fetch runs for all active workflows using authFetch
  const combinedFetcher = async () => {
    if (!wfIds.length) return [];
    const results = await Promise.all(wfIds.map(wid =>
      authFetch(`/api/v1/workflow/${wid}/runs?limit=100`)
        .then(r => (r.ok ? r.json() : { runs: [] }))
        .then(d => (d.runs || []).map(r => ({ ...r, _wfId: wid })))
        .catch(() => [])
    ));
    const flat = results.flat();
    flat.sort((a, b) => (parseSafeDate(b.created_at)?.getTime() || 0) - (parseSafeDate(a.created_at)?.getTime() || 0));
    return flat;
  };

  const { data: allRuns = [], isLoading, mutate } = useSWR(
    wfIds.length ? `usage-runs:${wfIds.join(',')}` : null,
    combinedFetcher,
    { ...swrDefaults, refreshInterval: 10000 }
  );

  // Filter runs for the selected billing period
  const activeRuns = useMemo(() => {
    const startDateCutoff = parseSafeDate(`${BILLING_START_DATE_STR}T00:00:00+05:30`);
    return allRuns.filter(r => {
      if (r.name === 'WebCall') return false;
      const d = parseSafeDate(r.created_at);
      if (!d) return false;
      if (startDateCutoff && d < startDateCutoff) return false;
      return d >= currentSelectedPeriod.start && d <= currentSelectedPeriod.end;
    });
  }, [allRuns, currentSelectedPeriod]);

  // Aggregate selected stats
  const currentStats = useMemo(() => {
    const count = activeRuns.length;
    const totalTalkSec = activeRuns.reduce((sum, r) => sum + getRunDuration(r), 0);
    const avgTalkSec = count > 0 ? totalTalkSec / count : 0;
    const totalRoundedMinutes = activeRuns.reduce((sum, r) => {
      const seconds = getRunDuration(r);
      const rounded = seconds > 0 ? Math.ceil(seconds / 60) : 0;
      return sum + rounded;
    }, 0);

    const baseMins = Math.min(totalRoundedMinutes, LIMIT_MINUTES);
    const extraMins = Math.max(0, totalRoundedMinutes - LIMIT_MINUTES);
    const overageCost = extraMins * OVERAGE_RATE;

    return {
      callsCount: count,
      totalTalkSec,
      totalTalkFormatted: formatTalkTime(totalTalkSec),
      avgTalkFormatted: count > 0 ? formatTalkTime(avgTalkSec) : '—',
      totalMinutes: totalRoundedMinutes,
      baseMins,
      extraMins,
      overageCost
    };
  }, [activeRuns]);

  // Generate chart data based on rangeMode: '7Days' | '1Month' | 'Lifetime'
  const chartData = useMemo(() => {
    const dataMap = new Map();
    const now = new Date();

    if (rangeMode === '7Days') {
      // Past 7 days
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
        const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        dataMap.set(key, 0);
      }
    } else if (rangeMode === 'Lifetime') {
      // Every day from BILLING_START_DATE_STR up to today
      const start = parseSafeDate(`${BILLING_START_DATE_STR}T00:00:00+05:30`) || new Date();
      const diffTime = Math.max(0, now.getTime() - start.getTime());
      const totalDays = Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
      
      for (let i = 0; i < totalDays; i++) {
        const d = new Date(start);
        d.setDate(d.getDate() + i);
        const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        dataMap.set(key, 0);
      }
    } else {
      // '1Month' default: 30 days of the selected billing period
      const start = new Date(currentSelectedPeriod.start);
      for (let i = 0; i < 30; i++) {
        const d = new Date(start);
        d.setDate(d.getDate() + i);
        const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        dataMap.set(key, 0);
      }
    }

    // Populate actual run data
    const targetRuns = rangeMode === 'Lifetime' 
      ? allRuns.filter(r => r.name !== 'WebCall' && parseSafeDate(r.created_at) >= (parseSafeDate(`${BILLING_START_DATE_STR}T00:00:00+05:30`) || new Date(0)))
      : activeRuns;

    targetRuns.forEach(r => {
      const d = parseSafeDate(r.created_at);
      if (!d) return;
      const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (dataMap.has(key)) {
        const seconds = getRunDuration(r);
        const rounded = seconds > 0 ? Math.ceil(seconds / 60) : 0;
        dataMap.set(key, dataMap.get(key) + rounded);
      }
    });

    return Array.from(dataMap.entries()).map(([date, minutes]) => ({ date, minutes }));
  }, [rangeMode, activeRuns, allRuns, currentSelectedPeriod]);

  // Merge database states with mock history periods
  const resolvedPeriods = useMemo(() => {
    return periods.map((p, idx) => {
      const mockIdx = periods.length - 1 - idx;
      const mockData = MOCK_PERIODS_DATA[mockIdx];

      if (p.isCurrent) {
        return { ...p, ...currentStats };
      }
      return {
        ...p,
        ...(mockData || {
          callsCount: 0,
          totalTalkSec: 0,
          totalTalkFormatted: '0s',
          avgTalkFormatted: '—',
          totalMinutes: 0,
          baseMins: 0,
          extraMins: 0,
          overageCost: 0
        })
      };
    });
  }, [periods, currentStats]);

  const toggleExpand = (idx) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  const basePercent = (currentStats.baseMins / LIMIT_MINUTES) * 100;
  const extraPercent = currentStats.extraMins > 0 ? Math.min(100, (currentStats.extraMins / LIMIT_MINUTES) * 100) : 0;

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="page-header mb-4" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div className="flex align-items-center gap-2" style={{ marginBottom: '0.35rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>Usage & Billing</h1>
            <button
              className="btn-icon-refresh"
              onClick={() => mutate()}
              title="Refresh statistics"
              aria-label="Refresh statistics"
              type="button"
            >
              <RefreshCw size={14} aria-hidden="true" />
            </button>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-dim)' }}>
            Quota tracking and monthly usage dashboard · Cycle: <span style={{ color: 'var(--accent-indigo, #818cf8)', fontWeight: 600 }}>{currentSelectedPeriod.label}</span>
          </p>
        </div>

        {/* Billing Cycle Selector Dropdown */}
        <div className="cycle-selector-group">
          <label htmlFor="billing-cycle-select" className="cycle-select-label">Select Cycle:</label>
          <select
            id="billing-cycle-select"
            value={selectedPeriodIdx}
            onChange={(e) => setSelectedPeriodIdx(Number(e.target.value))}
            className="cycle-select-control"
            aria-label="Select Billing Cycle"
          >
            {periods.map((p, idx) => (
              <option key={idx} value={idx}>
                {p.label} {p.isCurrent ? '(Active)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Featured Quota Card */}
      <div className="card mb-4 quota-featured-card">
        <h2 className="quota-card-title">
          <CreditCard size={18} style={{ color: 'var(--accent-indigo, #818cf8)' }} aria-hidden="true" />
          <span>Active Quota Status</span>
        </h2>
        
        {/* Bar 1: Base Usage */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div className="flex-between mb-1" style={{ fontSize: '0.85rem' }}>
            <span style={{ fontWeight: 600, color: 'var(--text)' }}>Plan Included Minutes</span>
            <span style={{ color: 'var(--text-secondary)' }} className="mono tabular-nums">
              {currentStats.baseMins} / {LIMIT_MINUTES} min
            </span>
          </div>
          <div className="quota-track-bg">
            <div 
              className="quota-bar-fill base"
              style={{ 
                width: `${basePercent}%`
              }} 
            />
          </div>
        </div>

        {/* Bar 2: Extra Usage */}
        <div>
          <div className="flex-between mb-1" style={{ fontSize: '0.85rem' }}>
            <span style={{ fontWeight: 600, color: 'var(--text)' }}>Overage Usage</span>
            <span style={{ color: 'var(--text-secondary)' }} className="mono tabular-nums">
              {currentStats.extraMins} mins
            </span>
          </div>
          <div className="quota-track-bg" style={{ marginBottom: '0.75rem' }}>
            <div 
              className="quota-bar-fill overage"
              style={{ 
                width: `${currentStats.extraMins > 0 ? Math.max(5, extraPercent) : 0}%`
              }} 
            />
          </div>
          {currentStats.extraMins > 0 && (
            <div className="overage-alert-pill">
              <Sparkles size={14} aria-hidden="true" />
              <span>Estimated Overage Charges: Rs. {currentStats.overageCost.toFixed(2)} (at Rs. {OVERAGE_RATE}/min)</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats Summary Strip */}
      {isLoading ? <StatGridSkeleton count={4} /> : (
        <div className="stats-grid mobile-3-across mb-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div className="stat-card">
            <div className="stat-icon blue"><Phone size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.callsCount}</div>
              <div className="stat-label">Total Calls</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><Clock size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.totalTalkFormatted}</div>
              <div className="stat-label">Total Talk Time</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><BarChart3 size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.avgTalkFormatted}</div>
              <div className="stat-label">Avg / Call</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon indigo"><Sparkles size={18} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.totalMinutes} m</div>
              <div className="stat-label">Talk Minutes</div>
            </div>
          </div>
        </div>
      )}

      {/* Trajectory Bar Chart */}
      <div className="card mb-4 chart-card-container">
        <div className="chart-header-row">
          <h3 className="section-title" style={{ margin: 0 }}>Usage Trajectory</h3>

          {/* Segmented Range Control: 7 Days | 1 Month | Lifetime */}
          <div className="range-picker mobile-scroll" role="tablist" aria-label="Chart date range filter">
            <button
              role="tab"
              aria-selected={rangeMode === '7Days'}
              type="button"
              onClick={() => setRangeMode('7Days')}
              className={`range-btn ${rangeMode === '7Days' ? 'active' : ''}`}
            >
              7 Days
            </button>
            <button
              role="tab"
              aria-selected={rangeMode === '1Month'}
              type="button"
              onClick={() => setRangeMode('1Month')}
              className={`range-btn ${rangeMode === '1Month' ? 'active' : ''}`}
            >
              1 Month
            </button>
            <button
              role="tab"
              aria-selected={rangeMode === 'Lifetime'}
              type="button"
              onClick={() => setRangeMode('Lifetime')}
              className={`range-btn ${rangeMode === 'Lifetime' ? 'active' : ''}`}
            >
              Lifetime
            </button>
          </div>
        </div>

        {/* Scrollable Horizontal Container */}
        <div className="chart-scroll-wrap">
          <div style={{ width: '100%', minWidth: rangeMode === 'Lifetime' ? `${Math.max(100, chartData.length * 36)}px` : '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="usageBarGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#818cf8" stopOpacity={1} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0.75} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                  contentStyle={{
                    background: '#11141d',
                    border: '1px solid #232733',
                    borderRadius: '8px',
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
                    padding: '8px 12px'
                  }}
                  labelStyle={{ fontSize: 11, fontWeight: 700, color: '#f8fafc', marginBottom: 2 }}
                  itemStyle={{ fontSize: 11, color: '#818cf8', fontWeight: 600 }}
                  formatter={(value) => [`${value} minutes`, 'Usage']}
                />
                <Bar dataKey="minutes" radius={[6, 6, 0, 0]} maxBarSize={48}>
                  {chartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.minutes > 0 ? 'url(#usageBarGradient)' : 'rgba(35, 39, 51, 0.4)'}
                      stroke={entry.minutes > 0 ? '#a5b4fc' : 'transparent'}
                      strokeWidth={entry.minutes > 0 ? 1 : 0}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Accordion of Past Cycles */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <h3 className="section-title" style={{ marginBottom: '1.25rem' }}>Billing Cycles History</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {resolvedPeriods.map((period, idx) => {
            const isExpanded = expandedIndex === idx;
            const bPercent = (period.baseMins / LIMIT_MINUTES) * 100;
            const exPercent = period.extraMins > 0 ? Math.min(100, (period.extraMins / LIMIT_MINUTES) * 100) : 0;

            return (
              <div 
                key={idx} 
                className={`cycle-history-card ${selectedPeriodIdx === idx ? 'selected' : ''}`}
              >
                {/* Header Row */}
                <div 
                  onClick={() => {
                    setSelectedPeriodIdx(idx);
                    toggleExpand(idx);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedPeriodIdx(idx);
                      toggleExpand(idx);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-expanded={isExpanded}
                  className="cycle-history-header"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', opacity: 0.7 }}>
                      <ChevronRight size={16} aria-hidden="true" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text)' }}>{period.label}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        {period.isCurrent ? 'Current Active Period' : 'Completed / Locked Period'}
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: period.overageCost > 0 ? '#f59e0b' : 'inherit' }}>
                      {period.overageCost > 0 ? `Rs. ${period.overageCost.toFixed(2)}` : 'Rs. 0.00'}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Overage Cost</div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="cycle-history-detail">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                      <div>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Total Calls</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.15rem', color: 'var(--text)' }}>{period.callsCount}</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Talk Minutes</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.15rem', color: 'var(--text)' }}>{period.totalMinutes} min</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Overage Minutes</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.15rem', color: period.extraMins > 0 ? '#f59e0b' : 'inherit' }}>
                          {period.extraMins} min
                        </div>
                      </div>
                    </div>

                    {/* Quota Progress Bars */}
                    <div style={{ marginBottom: '1rem' }}>
                      <div className="flex-between mb-1" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        <span>Plan Included Minutes</span>
                        <span className="mono tabular-nums">{period.baseMins} / {LIMIT_MINUTES} min</span>
                      </div>
                      <div className="quota-track-bg" style={{ height: '6px' }}>
                        <div style={{ width: `${bPercent}%`, height: '100%', background: '#6366f1', borderRadius: '3px' }} />
                      </div>
                    </div>

                    <div style={{ marginBottom: '0.25rem' }}>
                      <div className="flex-between mb-1" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        <span>Overage Minutes</span>
                        <span className="mono tabular-nums">{period.extraMins} mins</span>
                      </div>
                      <div className="quota-track-bg" style={{ height: '6px' }}>
                        <div style={{ width: `${exPercent}%`, height: '100%', background: '#f59e0b', borderRadius: '3px' }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
