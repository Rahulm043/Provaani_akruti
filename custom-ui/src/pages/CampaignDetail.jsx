import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import { useParams } from 'react-router-dom';
import { Play, Pause, StopCircle, RefreshCw, ChevronRight, Sparkles, Loader2 } from 'lucide-react';
import { swrFetcher, authFetch, formatDuration, formatDate, formatDateTime, API_BASE, fetchAnalysis, SENTIMENT_CONFIG } from '../utils/api.js';
import BackButton from '../components/BackButton.jsx';
import RecordingPlayer from '../components/RecordingPlayer.jsx';

const DEFAULT_WF = 1;

export default function CampaignDetail() {
  const { id } = useParams();
  const { data, mutate, isLoading } = useSWR(`/api/v1/campaign/${id}`, swrFetcher, { refreshInterval: 5000 });

  const campaign = data?.campaign || data;
  const state = campaign?.state;

  const handleAction = async (action) => {
    try {
      await authFetch(`/api/v1/campaign/${id}/${action}`, { method: 'POST' });
      mutate();
    } catch (e) { console.error(e); }
  };

  if (isLoading && !campaign) {
    return <div className="fade-in"><BackButton /><div className="flex-center" style={{ padding: '4rem' }}><div className="spinner-lg" /></div></div>;
  }
  if (!campaign) {
    return <div className="fade-in"><BackButton /><div className="empty-state card"><h1>Campaign not found</h1></div></div>;
  }

  const pct = campaign.total_rows ? Math.round((campaign.processed_rows / campaign.total_rows) * 100) : 0;
  const remaining = (campaign.total_rows || 0) - (campaign.processed_rows || 0);

  return (
    <div className="fade-in">
      <BackButton to="/campaigns" label="Campaigns" />
      <div className="page-header flex-between">
        <div>
          <h1>{campaign.name}</h1>
          <p>Workflow: {campaign.workflow_name || '—'} · {campaign.total_rows || 0} recipients</p>
        </div>
        <button className="btn-secondary" onClick={() => mutate()}><RefreshCw size={16} /></button>
      </div>

      <div className="card flex-between" style={{ padding: '1rem 1.5rem', marginBottom: '1.5rem' }}>
        <div className="flex align-items-center gap-2">
          <span className={`badge ${state === 'running' ? 'connected' : state === 'paused' ? 'running' : state === 'completed' ? 'completed' : 'idle'}`} style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}>{state}</span>
          <span className="text-dim text-sm">Concurrency: {campaign.max_concurrency || 1}</span>
        </div>
        <div className="flex gap-1">
          {(!state || state === 'draft' || state === 'scheduled') && <button className="btn-primary" onClick={() => handleAction('start')}><Play size={14} /> Start</button>}
          {state === 'running' && <button className="btn-secondary" onClick={() => handleAction('pause')}><Pause size={14} /> Pause</button>}
          {state === 'paused' && (<><button className="btn-primary" onClick={() => handleAction('resume')}><Play size={14} /> Resume</button><button className="btn-secondary" onClick={() => handleAction('start')}><StopCircle size={14} /> Stop</button></>)}
          {state === 'completed' && campaign.failed_rows > 0 && <button className="btn-secondary" onClick={() => handleAction('redial')}><RefreshCw size={14} /> Redial Failed</button>}
        </div>
      </div>

      <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
          <span className="text-sm">Progress</span>
          <span className="text-sm mono">{campaign.processed_rows} / {campaign.total_rows} ({pct}%)</span>
        </div>
        <div style={{ height: 10, background: 'rgba(255,255,255,0.06)', borderRadius: 5, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--primary)', borderRadius: 5, transition: 'width 0.5s' }} />
        </div>
        <div className="flex-between" style={{ marginTop: '0.75rem' }}>
          <span className="text-dim text-sm">{remaining} remaining</span>
          <span className="text-dim text-sm">{campaign.failed_rows || 0} failed</span>
        </div>
      </div>

      <CampaignRuns campaignId={id} workflowId={campaign.workflow_id || DEFAULT_WF} />
    </div>
  );
}

function TranscriptModal({ isOpen, onClose, transcriptText }) {
  if (!isOpen) return null;
  const lines = transcriptText ? transcriptText.split('\n').filter(Boolean) : [];
  const isAnalysisFormat = lines.some(l => /^(Agent|Caller|Assistant|User): /i.test(l));
  let messages = [];
  if (isAnalysisFormat) {
    messages = lines.map(line => {
      const match = line.match(/^(Agent|Assistant|Caller|User): (.+)/i);
      return match ? { role: /(Agent|Assistant)/i.test(match[1]) ? 'bot' : 'user', text: match[2] } : null;
    }).filter(Boolean);
  } else {
    messages = lines.map(line => {
      const match = line.match(/^\[(.+?)\] (assistant|user): (.+)$/);
      return match ? { role: match[2] === 'assistant' ? 'bot' : 'user', text: match[3] } : null;
    }).filter(Boolean);
  }
  if (messages.length === 0 && transcriptText) messages = [{ role: 'system', text: transcriptText }];

  return (
    <div className="transcript-modal-overlay" onClick={onClose}>
      <div className="transcript-modal-panel" onClick={e => e.stopPropagation()}>
        <div className="transcript-modal-header">
          <h2><span>💬</span> Transcript</h2>
          <button className="minimal-btn-icon" onClick={onClose} style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>✕</button>
        </div>
        <div className="transcript-modal-body">
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 2rem', color: 'var(--text-dim)' }}><p className="text-sm">No transcript available.</p></div>
          ) : messages.map((msg, i) => (
            <div key={i} className={`transcript-msg ${msg.role}`}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-dim)', marginBottom: '0.2rem', textTransform: 'uppercase' }}>
                {msg.role === 'bot' ? 'Agent (AI)' : msg.role === 'user' ? 'Caller' : 'Transcript'}
              </div>
              <div style={{ fontSize: '0.85rem', lineHeight: 1.4 }}>{msg.text}</div>
            </div>
          ))}
        </div>
        <div className="transcript-modal-footer"><button className="btn-secondary" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
}

function CampaignRunRow({ run, workflowId }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [fullRun, setFullRun] = useState(run);
  const [transcript, setTranscript] = useState(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false);

  useEffect(() => {
    if (!isExpanded) return;
    let cancelled = false;
    setAnalysisLoading(true);
    // Fetch full run detail for public_access_token + recording URL
    authFetch(`/api/v1/workflow/${workflowId}/runs/${run.id}`)
      .then(r => r.json()).then(data => { if (!cancelled) setFullRun(data); })
      .catch(() => {});
    fetchAnalysis(run.id).then(data => { if (!cancelled) { setAnalysis(data); setAnalysisLoading(false); } }).catch(() => { if (!cancelled) setAnalysisLoading(false); });
    return () => { cancelled = true; };
  }, [run.id, isExpanded, workflowId]);

  const openTranscript = () => {
    const token = fullRun.public_access_token;
    if (transcript !== null) { setIsTranscriptOpen(true); return; }
    if (analysis?.transcript) { setTranscript(analysis.transcript); setIsTranscriptOpen(true); return; }
    if (!token) return;
    setTranscriptLoading(true);
    fetch(`${API_BASE}/api/v1/public/download/workflow/${token}/transcript`)
      .then(r => r.ok ? r.text() : '').then(t => { setTranscript(t || ''); setTranscriptLoading(false); setIsTranscriptOpen(true); })
      .catch(() => { setTranscript(''); setTranscriptLoading(false); });
  };

  const gc = fullRun.gathered_context || {};
  const costInfo = fullRun.cost_info || {};
  const phone = fullRun.initial_context?.phone_number || '—';
  const disp = (gc.call_disposition || 'unknown').replace(/_/g, ' ');
  const sentCfg = analysis?.sentiment ? SENTIMENT_CONFIG[analysis.sentiment] : null;

  return (
    <React.Fragment>
      <tr className={`main-row ${isExpanded ? 'expanded' : ''}`} onClick={() => setIsExpanded(!isExpanded)} style={{ cursor: 'pointer' }}>
        <td style={{ width: 30 }}><span className="expand-icon"><ChevronRight size={16} /></span></td>
        <td className="mono" style={{ fontSize: '0.8rem' }}>{fullRun.name?.replace('WR-', '') || `#${fullRun.id}`}</td>
        <td className="mono">{phone}</td>
        <td><span className={`badge ${fullRun.is_completed ? 'completed' : 'running'}`}>{disp}</span></td>
        <td>{formatDuration(costInfo.call_duration_seconds)}</td>
        <td><span className={`badge ${fullRun.is_completed ? 'completed' : 'running'}`}>{fullRun.is_completed ? 'done' : 'active'}</span></td>
        <td className="text-dim text-sm">{formatDate(fullRun.created_at)}</td>
      </tr>
      {isExpanded && (
        <tr className="detail-row">
          <td colSpan={7}>
            <div className="flex flex-column gap-3 fade-in" style={{ padding: '0.25rem 0.5rem' }}>
              <div style={{ width: '100%' }}>
                <div className="detail-section-title">Call Recording</div>
                <RecordingPlayer publicToken={fullRun.public_access_token} defaultDuration={costInfo.call_duration_seconds} />
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <button className="minimal-transcript-btn" onClick={openTranscript} disabled={transcriptLoading}>
                    💬 {transcriptLoading ? 'Loading...' : analysis?.transcript ? 'Analysis Transcript' : 'Transcript'}
                  </button>
                </div>
              </div>

              {analysisLoading && (
                <div style={{ background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: 'var(--radius)', padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Loader2 size={16} className="animate-spin" style={{ color: 'var(--primary)' }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>AI Analysis</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Processing...</div>
                  </div>
                </div>
              )}

              {analysis && analysis.status === 'completed' && (
                <div style={{ background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: 'var(--radius)', padding: '1rem 1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div className="flex align-items-center gap-2">
                      <Sparkles size={16} style={{ color: 'var(--primary)' }} />
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Analysis</span>
                    </div>
                    {sentCfg && <span style={{ background: sentCfg.bg, color: sentCfg.color, padding: '0.25rem 0.65rem', borderRadius: '100px', fontSize: '0.75rem', fontWeight: 700, textTransform: 'capitalize', border: `1px solid ${sentCfg.color}20` }}>{sentCfg.label}</span>}
                  </div>
                  {analysis.summary && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-dim)', marginBottom: '0.3rem', textTransform: 'uppercase' }}>Summary</div>
                      <p style={{ margin: 0, fontSize: '0.85rem', lineHeight: 1.5, color: 'var(--text)' }}>{analysis.summary}</p>
                    </div>
                  )}
                  {analysis.key_points && analysis.key_points.length > 0 && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-dim)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>Key Points</div>
                      <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.82rem', lineHeight: 1.6, color: 'var(--text-dim)' }}>
                        {analysis.key_points.map((point, i) => <li key={i}>{point}</li>)}
                      </ul>
                    </div>
                  )}
                  {analysis.language && <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Language: {analysis.language.replace(/_/g, ' / ')}</div>}
                </div>
              )}

              <div className="accordion-detail-columns">
                <div className="detail-column">
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-dim)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>Disposition</div>
                  <p style={{ margin: 0, fontSize: '0.85rem', lineHeight: 1.45, color: 'var(--text)' }}>{disp}</p>
                </div>
                <div className="detail-column">
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-dim)', paddingBottom: '0.35rem', textTransform: 'uppercase' }}>Call Details</div>
                  <div className="call-insight-row"><span style={{ color: 'var(--text-dim)' }}>Duration</span><span style={{ fontWeight: 500 }}>{formatDuration(costInfo.call_duration_seconds)}</span></div>
                  <div className="call-insight-row"><span style={{ color: 'var(--text-dim)' }}>Status</span><span className={`badge ${fullRun.is_completed ? 'completed' : 'running'}`}>{fullRun.is_completed ? 'Completed' : 'Active'}</span></div>
                </div>
                <div className="detail-column">
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-dim)', paddingBottom: '0.35rem', textTransform: 'uppercase' }}>Timing</div>
                  <div className="call-insight-row"><span style={{ color: 'var(--text-dim)' }}>Created</span><span style={{ fontWeight: 500, fontSize: '0.75rem' }}>{formatDateTime(fullRun.created_at)}</span></div>
                </div>
              </div>
            </div>
            <TranscriptModal isOpen={isTranscriptOpen} onClose={() => setIsTranscriptOpen(false)} transcriptText={transcript} />
          </td>
        </tr>
      )}
    </React.Fragment>
  );
}

function CampaignRuns({ campaignId, workflowId }) {
  const { data, isLoading } = useSWR(`/api/v1/campaign/${campaignId}/runs`, swrFetcher, { refreshInterval: 5000 });
  const runs = data?.runs || [];

  return (
    <div className="card" style={{ padding: '1.5rem' }}>
      <h3 className="section-title">Call Records</h3>
      {isLoading && runs.length === 0 ? (
        <div className="flex-center" style={{ padding: '2rem' }}><div className="spinner-loader" /></div>
      ) : runs.length === 0 ? (
        <p className="text-dim text-sm" style={{ padding: '1rem 0' }}>No calls processed yet.</p>
      ) : (
        <div className="table-container" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 30 }}></th>
                <th>Run</th>
                <th>Phone</th>
                <th>Disposition</th>
                <th>Duration</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => <CampaignRunRow key={run.id} run={run} workflowId={workflowId} />)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
