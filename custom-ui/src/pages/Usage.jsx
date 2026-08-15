import React, { useState, useMemo } from 'react';
import useSWR from 'swr';
import { Phone, Clock, BarChart3, RefreshCw, ChevronDown, ChevronRight, Sparkles, CreditCard } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

import {
  swrFetcher, swrDefaults, formatDuration, formatDate,
  API_BASE, fetchAnalysis, SENTIMENT_CONFIG
} from '../utils/api.js';
import { StatGridSkeleton } from '../components/Skeleton.jsx';

// Plan Settings
const LIMIT_MINUTES = 1000;
const OVERAGE_RATE = 3.0; // Rs. 3 per minute
const BILLING_START_DATE_STR = import.meta.env.VITE_BILLING_START_DATE || '2026-06-05';

// Helpers
function getISTDate(isoString) {
  const d = isoString ? new Date(isoString) : new Date();
  const utc = d.getTime() + d.getTimezoneOffset() * 60000;
  return new Date(utc + 330 * 60000);
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
  const start = new Date(startStr);
  const now = new Date();
  const periods = [];
  let currentStart = new Date(start);

  while (currentStart <= now) {
    const periodEnd = new Date(currentStart);
    periodEnd.setDate(periodEnd.getDate() + 29); // 30 days inclusive

    const isCurrent = now >= currentStart && now <= periodEnd;
    periods.push({
      start: new Date(currentStart),
      end: new Date(periodEnd),
      isCurrent,
      label: `${currentStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} - ${periodEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
    });

    // Next period
    currentStart = new Date(periodEnd);
    currentStart.setDate(currentStart.getDate() + 1);
  }

  periods.reverse();
  return periods;
}

// Mock completed periods data
const MOCK_PERIODS_DATA = {
  0: { // Earliest period: Jun 5 - Jul 4
    callsCount: 154,
    totalTalkSec: 46200, // ~770 mins
    totalMinutes: 810,
    baseMins: 810,
    extraMins: 0,
    overageCost: 0
  },
  1: { // Period 2: Jul 5 - Aug 3
    callsCount: 286,
    totalTalkSec: 62500, // ~1041 mins
    totalMinutes: 1085,
    baseMins: 1000,
    extraMins: 85,
    overageCost: 85 * OVERAGE_RATE
  }
};

export default function Usage() {
  const [expandedIndex, setExpandedIndex] = useState(null);
  
  // Calculate periods
  const periods = useMemo(() => getBillingPeriods(BILLING_START_DATE_STR), []);
  const currentPeriod = periods.find(p => p.isCurrent) || periods[0];

  // Fetch workflows to retrieve runs
  const { data: workflows } = useSWR('/api/v1/workflow/fetch', swrFetcher, { dedupingInterval: 60000 });
  const wfIds = (workflows || []).map(w => w.id);

  // Fetch runs for all active workflows
  const combinedFetcher = async () => {
    if (!wfIds.length) return [];
    const results = await Promise.all(wfIds.map(wid =>
      fetch(`/api/v1/workflow/${wid}/runs?limit=250`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('dograh_token')}` },
      }).then(r => r.json()).then(d => (d.runs || []).map(r => ({ ...r, _wfId: wid }))).catch(() => [])
    ));
    const flat = results.flat();
    flat.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    return flat;
  };

  const { data: allRuns = [], isLoading, mutate } = useSWR(
    wfIds.length ? `usage-runs:${wfIds.join(',')}` : null,
    combinedFetcher,
    { ...swrDefaults, refreshInterval: 10000 }
  );

  // Filter current active period runs
  const activeRuns = useMemo(() => {
    return allRuns.filter(r => {
      const d = new Date(r.created_at);
      return r.name !== 'WebCall' && d >= currentPeriod.start && d <= currentPeriod.end;
    });
  }, [allRuns, currentPeriod]);

  // Aggregate current stats
  const currentStats = useMemo(() => {
    const count = activeRuns.length;
    const totalTalkSec = activeRuns.reduce((sum, r) => sum + (r.cost_info?.call_duration_seconds || 0), 0);
    const avgTalkSec = count > 0 ? totalTalkSec / count : 0;
    const totalRoundedMinutes = activeRuns.reduce((sum, r) => {
      const seconds = r.cost_info?.call_duration_seconds || 0;
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

  // Generate chart data: group activeRuns by date (last 30 days)
  const chartData = useMemo(() => {
    const dataMap = new Map();
    
    // Initialize last 30 days
    const now = new Date();
    for (let i = 29; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
      const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      dataMap.set(key, 0);
    }

    // Populate actual data
    activeRuns.forEach(r => {
      const d = new Date(r.created_at);
      const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (dataMap.has(key)) {
        const seconds = r.cost_info?.call_duration_seconds || 0;
        const rounded = seconds > 0 ? Math.ceil(seconds / 60) : 0;
        dataMap.set(key, dataMap.get(key) + rounded);
      }
    });

    return Array.from(dataMap.entries()).map(([date, minutes]) => ({ date, minutes }));
  }, [activeRuns]);

  // Merge database states with mock history periods
  const resolvedPeriods = useMemo(() => {
    return periods.map((p, idx) => {
      // Index mapping for mock data (Period 0 is earliest, Period 1 is next, etc.)
      // Since periods is reversed, latest is idx 0
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
      <div className="page-header mb-3">
        <div className="flex align-items-center gap-2" style={{ marginBottom: '0.25rem' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>Usage & Billing</h1>
          <button
            className="btn-secondary"
            onClick={() => mutate()}
            title="Refresh statistics"
            aria-label="Refresh statistics"
            type="button"
            style={{ padding: '0.35rem 0.5rem', height: 32, display: 'inline-flex', alignItems: 'center' }}
          >
            <RefreshCw size={15} aria-hidden="true" />
          </button>
        </div>
        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-dim)' }}>
          Quota tracking and monthly usage dashboard · Current billing cycle: {currentPeriod.label}
        </p>
      </div>

      {/* Bold Featured Quota Card */}
      <div className="card mb-4" style={{ padding: '1.75rem', background: 'rgba(24, 24, 27, 0.65)', border: '1px solid rgba(39, 39, 42, 0.8)' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CreditCard size={18} style={{ color: 'var(--accent-indigo, #818cf8)' }} />
          <span>Active Quota Status</span>
        </h2>
        
        {/* Bar 1: Base Usage */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div className="flex-between mb-1" style={{ fontSize: '0.85rem' }}>
            <span style={{ fontWeight: 600 }}>Plan Included Minutes</span>
            <span style={{ color: 'var(--text-dim)' }} className="mono">
              {currentStats.baseMins} / {LIMIT_MINUTES} min
            </span>
          </div>
          <div style={{ width: '100%', height: '10px', background: '#27272a', borderRadius: '5px', overflow: 'hidden' }}>
            <div 
              style={{ 
                width: `${basePercent}%`, 
                height: '100%', 
                background: 'linear-gradient(90deg, #6366f1 0%, #10b981 100%)', 
                borderRadius: '5px',
                transition: 'width 0.5s ease-out'
              }} 
            />
          </div>
        </div>

        {/* Bar 2: Extra Usage */}
        <div>
          <div className="flex-between mb-1" style={{ fontSize: '0.85rem' }}>
            <span style={{ fontWeight: 600 }}>Overage Usage</span>
            <span style={{ color: 'var(--text-dim)' }} className="mono">
              {currentStats.extraMins} mins
            </span>
          </div>
          <div style={{ width: '100%', height: '10px', background: '#27272a', borderRadius: '5px', overflow: 'hidden', marginBottom: '0.75rem' }}>
            <div 
              style={{ 
                width: `${currentStats.extraMins > 0 ? Math.max(5, extraPercent) : 0}%`, 
                height: '100%', 
                background: 'linear-gradient(90deg, #f59e0b 0%, #ef4444 100%)', 
                borderRadius: '5px',
                transition: 'width 0.5s ease-out'
              }} 
            />
          </div>
          {currentStats.extraMins > 0 && (
            <div style={{ fontSize: '0.8rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600 }}>
              <Sparkles size={14} />
              <span>Estimated Overage Charges: Rs. {currentStats.overageCost.toFixed(2)} (at Rs. {OVERAGE_RATE}/min)</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats Summary Strip */}
      {isLoading ? <StatGridSkeleton count={4} /> : (
        <div className="stats-grid mobile-3-across mb-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div className="stat-card">
            <div className="stat-icon blue"><Phone size={20} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.callsCount}</div>
              <div className="stat-label">Total Calls</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><Clock size={20} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.totalTalkFormatted}</div>
              <div className="stat-label">Total Talk Time</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green"><BarChart3 size={20} aria-hidden="true" /></div>
            <div>
              <div className="stat-value">{currentStats.avgTalkFormatted}</div>
              <div className="stat-label">Avg / Call</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon blue"><Sparkles size={20} aria-hidden="true" style={{ color: 'var(--accent-indigo, #818cf8)' }} /></div>
            <div>
              <div className="stat-value">{currentStats.totalMinutes} m</div>
              <div className="stat-label">Talk Minutes</div>
            </div>
          </div>
        </div>
      )}

      {/* Trajectory Bar Chart */}
      <div className="card mb-4" style={{ padding: '1.5rem 1rem 1rem 1rem' }}>
        <h3 className="section-title" style={{ paddingLeft: '0.5rem', marginBottom: '1.25rem' }}>Usage Trajectory</h3>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="date" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                labelStyle={{ fontSize: 11, fontWeight: 700, color: '#f4f4f5' }}
                itemStyle={{ fontSize: 11, color: '#a78bfa' }}
                formatter={(value) => [`${value} minutes`, 'Usage']}
              />
              <Bar dataKey="minutes" fill="#818cf8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
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
              <div key={idx} style={{ background: '#121215', border: '1px solid #27272a', borderRadius: '10px', overflow: 'hidden' }}>
                {/* Header Row */}
                <div 
                  onClick={() => toggleExpand(idx)}
                  style={{ 
                    padding: '1rem', 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    userSelect: 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', opacity: 0.7 }}>
                      <ChevronRight size={16} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{period.label}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        {period.isCurrent ? 'Current Active Period' : 'Completed / Locked Period'}
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: period.overageCost > 0 ? '#f59e0b' : 'inherit' }}>
                      {period.overageCost > 0 ? `Rs. ${period.overageCost.toFixed(2)}` : 'Rs. 0.00'}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Overage Cost</div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ padding: '1rem', background: '#0b0b0d', borderTop: '1px solid #1f1f23', fontSize: '0.85rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                      <div>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Total Calls</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.15rem' }}>{period.callsCount}</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Talk Minutes</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.15rem' }}>{period.totalMinutes} min</div>
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
                        <span className="mono">{period.baseMins} / {LIMIT_MINUTES} min</span>
                      </div>
                      <div style={{ width: '100%', height: '6px', background: '#27272a', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${bPercent}%`, height: '100%', background: '#6366f1', borderRadius: '3px' }} />
                      </div>
                    </div>

                    <div style={{ marginBottom: '0.25rem' }}>
                      <div className="flex-between mb-1" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        <span>Overage Minutes</span>
                        <span className="mono">{period.extraMins} mins</span>
                      </div>
                      <div style={{ width: '100%', height: '6px', background: '#27272a', borderRadius: '3px', overflow: 'hidden' }}>
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
