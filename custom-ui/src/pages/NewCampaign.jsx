import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Type, Loader2, CheckCircle, XCircle, Megaphone } from 'lucide-react';
import { authFetch, API_BASE, swrFetcher } from '../utils/api.js';
import useSWR from 'swr';
import BackButton from '../components/BackButton.jsx';

const DEFAULT_WF = 3;
const TEL_CONFIG_ID = 1;

export default function NewCampaign() {
  const navigate = useNavigate();
  const [workflowId, setWorkflowId] = useState(DEFAULT_WF);
  const { data: workflows } = useSWR('/api/v1/workflow/fetch', swrFetcher, { dedupingInterval: 60000 });
  const [mode, setMode] = useState('paste'); // 'paste' | 'csv'
  const [name, setName] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [csvFile, setCsvFile] = useState(null);
  const [concurrency, setConcurrency] = useState(2);
  const [retryMax, setRetryMax] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [parsedNumbers, setParsedNumbers] = useState([]);
  const fileInputRef = useRef(null);

  const parseNumbers = (text) => {
    const cleaned = text
      .replace(/[,\s]+/g, '\n')
      .split('\n')
      .map(n => n.trim())
      .filter(n => n.length >= 10)
      .map(n => n.startsWith('+') ? n : `+91${n}`);
    return [...new Set(cleaned)];
  };

  const handlePasteChange = (text) => {
    setPasteText(text);
    setParsedNumbers(parseNumbers(text));
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    setCsvFile(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setParsedNumbers(parseNumbers(ev.target.result));
      };
      reader.readAsText(file);
    }
  };

  const hexEncode = (s) => {
    const chars = s.split('').map(c => c.charCodeAt(0).toString(16).padStart(2, '0'));
    return `hex:${chars.join('-')}`;
  };

  const createCampaign = async (sourceId) => {
    const payload = {
      name: name || `Campaign ${new Date().toLocaleString()}`,
      workflow_id: workflowId,
      source_type: 'csv',
      source_id: sourceId,
      telephony_configuration_id: TEL_CONFIG_ID,
      max_concurrency: concurrency,
      retry_config: {
        enabled: true,
        max_retries: retryMax,
        retry_delay_seconds: 120,
        retry_on_busy: true,
        retry_on_no_answer: true,
      },
    };

    const res = await authFetch('/api/v1/campaign/create', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create campaign');
    }
    return res.json();
  };

  const uploadCsvAndCreate = async (csvContent, fileName) => {
    const file = new File([csvContent], fileName, { type: 'text/csv' });

    // Get presigned URL
    const presignRes = await authFetch('/api/v1/s3/presigned-upload-url', {
      method: 'POST',
      body: JSON.stringify({
        file_name: fileName,
        file_size: file.size,
        content_type: 'text/csv',
      }),
    });
    if (!presignRes.ok) {
      const err = await presignRes.json();
      throw new Error(err.detail || 'Failed to get upload URL');
    }
    const presignData = await presignRes.json();

    // Upload to presigned URL
    const uploadHeaders = { 'Content-Type': 'text/csv' };
    if (presignData.headers) {
      Object.assign(uploadHeaders, presignData.headers);
    }
    const uploadRes = await fetch(presignData.upload_url, {
      method: 'PUT',
      headers: uploadHeaders,
      body: file,
    });
    if (!uploadRes.ok && uploadRes.status !== 200) {
      throw new Error(`Upload failed: ${uploadRes.status}`);
    }

    // Create campaign
    const fileKey = presignData.file_key;
    const campaign = await createCampaign(fileKey);

    // Start it
    await authFetch(`/api/v1/campaign/${campaign.id}/start`, { method: 'POST' });

    return campaign;
  };

  const handleSubmit = async () => {
    if (parsedNumbers.length === 0) return;
    setSubmitting(true);
    setResult(null);
    try {
      const csvContent = 'phone_number\n' + parsedNumbers.join('\n');
      const fileName = `campaign-${Date.now()}.csv`;
      const campaign = await uploadCsvAndCreate(csvContent, fileName);
      setResult({ success: true, message: `Campaign created with ${parsedNumbers.length} recipients. Redirecting...`, id: campaign.id });
      setTimeout(() => navigate(`/campaigns/${campaign.id}`), 2000);
    } catch (e) {
      setResult({ success: false, message: e.message });
    }
    setSubmitting(false);
  };

  const canSubmit = parsedNumbers.length > 0 && !submitting;

  return (
    <div className="fade-in">
      <BackButton to="/campaigns" label="Campaigns" />
      <div className="page-header">
        <h1>New Campaign</h1>
        <p>Create a bulk calling campaign</p>
      </div>

      <div style={{ maxWidth: 680 }}>
        {/* Mode toggle */}
        <div className="inspector-tabs" style={{ maxWidth: 300, marginBottom: '1.5rem' }}>
          <button className={`inspector-tab ${mode === 'paste' ? 'active' : ''}`} onClick={() => setMode('paste')}>
            <Type size={14} style={{ marginRight: 4 }} /> Paste Numbers
          </button>
          <button className={`inspector-tab ${mode === 'csv' ? 'active' : ''}`} onClick={() => setMode('csv')}>
            <FileText size={14} style={{ marginRight: 4 }} /> CSV Upload
          </button>
        </div>

        {/* Workflow selector */}
        <div className="form-group" style={{ marginBottom: '1.25rem' }}>
          <label>Agent / Workflow</label>
          <select value={workflowId} onChange={e => setWorkflowId(parseInt(e.target.value))}
            style={{ width: '100%', padding: '0.7rem 0.75rem', background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', color: 'var(--text)', fontSize: '0.9rem' }}>
            {(workflows || []).filter(w => w.status === 'active').map(w => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>

        {/* Campaign name */}
        <div className="form-group" style={{ marginBottom: '1.25rem' }}>
          <label>Campaign Name (optional)</label>
          <input type="text" placeholder="e.g. Durgapur Class 10 Parents"
            value={name} onChange={e => setName(e.target.value)} />
        </div>

        {/* Input area */}
        {mode === 'paste' ? (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Phone Numbers</label>
              <p className="text-dim text-sm" style={{ marginBottom: '0.75rem' }}>
                Paste numbers separated by commas, spaces, or new lines
              </p>
              <textarea placeholder="+919876543210&#10;+919123456780&#10;9876543210, 9123456780"
                value={pasteText} onChange={e => handlePasteChange(e.target.value)}
                style={{ minHeight: 180, fontFamily: 'monospace', fontSize: '0.875rem' }} />
            </div>
          </div>
        ) : (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed var(--border)', borderRadius: 'var(--radius)',
                padding: '2rem', textAlign: 'center', cursor: 'pointer',
                transition: 'border-color 0.2s',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--primary)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              <Upload size={32} style={{ opacity: 0.4, marginBottom: '0.75rem' }} />
              <p className="text-sm" style={{ fontWeight: 600 }}>
                {csvFile ? csvFile.name : 'Click to upload a CSV file'}
              </p>
              <p className="text-dim text-sm" style={{ marginTop: '0.25rem' }}>
                CSV must have a <code>phone_number</code> column
              </p>
              <input ref={fileInputRef} type="file" accept=".csv" onChange={handleFileChange}
                style={{ display: 'none' }} />
            </div>
          </div>
        )}

        {/* Parsed numbers preview */}
        {parsedNumbers.length > 0 && (
          <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
            <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
              <span className="text-sm" style={{ fontWeight: 600 }}>{parsedNumbers.length} recipients detected</span>
              <span className="text-dim text-sm">Duplicates removed</span>
            </div>
            <div style={{ maxHeight: 150, overflowY: 'auto', fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--text-dim)', lineHeight: 1.8 }}>
              {parsedNumbers.slice(0, 50).join(', ')}{parsedNumbers.length > 50 && ' ...'}
            </div>
          </div>
        )}

        {/* Configuration */}
        <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem' }}>
          <h4 className="section-title" style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>Call Configuration</h4>

          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
              <label style={{ marginBottom: 0 }}>Concurrent Calls</label>
              <span className="badge" style={{ fontWeight: 700, fontSize: '0.9rem' }}>{concurrency}</span>
            </div>
            <input type="range" min={1} max={5} step={1} value={concurrency}
              onChange={e => setConcurrency(parseInt(e.target.value))}
              style={{ width: '100%' }} />
            <div className="flex-between text-dim text-sm" style={{ marginTop: '0.25rem' }}>
              <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
            </div>
            <p className="text-dim text-sm" style={{ marginTop: '0.5rem' }}>How many calls to place simultaneously. Higher = faster but more resource usage.</p>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
              <label style={{ marginBottom: 0 }}>Max Retries</label>
              <span className="badge" style={{ fontWeight: 700, fontSize: '0.9rem' }}>{retryMax}</span>
            </div>
            <input type="range" min={0} max={5} step={1} value={retryMax}
              onChange={e => setRetryMax(parseInt(e.target.value))}
              style={{ width: '100%' }} />
            <div className="flex-between text-dim text-sm" style={{ marginTop: '0.25rem' }}>
              <span>0</span><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
            </div>
            <p className="text-dim text-sm" style={{ marginTop: '0.5rem' }}>Retry on busy, no-answer, or voicemail. 0 = no retries.</p>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div style={{
            background: result.success ? 'var(--success-bg)' : 'var(--error-bg)',
            border: `1px solid ${result.success ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
            padding: '0.75rem 1rem', marginBottom: '1rem', borderRadius: 'var(--radius-sm)',
            fontSize: '0.875rem', color: result.success ? 'var(--success)' : 'var(--error)',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            {result.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
            {result.message}
          </div>
        )}

        {/* Submit */}
        <button className="btn-primary" onClick={handleSubmit} disabled={!canSubmit}
          style={{ width: '100%', padding: '0.875rem' }}>
          {submitting ? <><Loader2 size={16} className="animate-spin" /> Creating campaign...</>
            : <><Megaphone size={16} /> Create & Start Campaign ({parsedNumbers.length} calls)</>}
        </button>
      </div>
    </div>
  );
}
