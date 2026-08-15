import React, { useState, useEffect } from 'react';
import { PhoneCall, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { authFetch, swrFetcher } from '../utils/api.js';
import BackButton from '../components/BackButton.jsx';
import useSWR from 'swr';

const DEFAULT_WF = 3;

export default function SingleCall() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [workflowId, setWorkflowId] = useState(DEFAULT_WF);
  const [isDialing, setIsDialing] = useState(false);
  const [result, setResult] = useState(null);

  const { data: workflows } = useSWR('/api/v1/workflow/fetch', swrFetcher, { dedupingInterval: 60000 });
  const { data: phoneNumbers } = useSWR(
    '/api/v1/organizations/telephony-configs/1/phone-numbers',
    swrFetcher,
    { dedupingInterval: 60000 }
  );
  const fromPhoneNumber = (phoneNumbers?.phone_numbers || [])
    .filter(n => n.is_active)
    .find(n => n.is_default_caller_id) || (phoneNumbers?.phone_numbers || []).find(n => n.is_active);
  const selectedWorkflow = (workflows || []).find(w => w.id === workflowId);

  const handleCall = async () => {
    const cleaned = phoneNumber.replace(/[\s\-()]/g, '');
    if (!cleaned) return;
    if (!fromPhoneNumber) {
      setResult({ success: false, message: 'No active caller number found for this telephony configuration' });
      return;
    }
    setIsDialing(true);
    setResult(null);
    try {
      const res = await authFetch('/api/v1/telephony/initiate-call', {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: workflowId,
          phone_number: cleaned.startsWith('+') ? cleaned : `+91${cleaned}`,
          telephony_configuration_id: 1,
          from_phone_number_id: fromPhoneNumber.id,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResult({ success: true, message: `Call initiated to ${cleaned}. Check Call Logs for status.` });
      } else {
        setResult({ success: false, message: data.detail || 'Failed to initiate call' });
      }
    } catch (e) {
      setResult({ success: false, message: e.message });
    }
    setIsDialing(false);
  };

  return (
    <div className="fade-in">
      <BackButton />
      <div className="page-header">
        <h1>Single Call</h1>
        <p>Make an outbound call to a phone number</p>
      </div>

      <div style={{ maxWidth: 500, margin: '0 auto' }}>
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h3 className="section-title flex-center"><PhoneCall size={18} /> Call Details</h3>

          <div className="form-group">
            <label>Agent / Workflow</label>
            <select value={workflowId} onChange={e => setWorkflowId(parseInt(e.target.value))}
              style={{ width: '100%', padding: '0.7rem 0.75rem', background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', color: 'var(--text)', fontSize: '0.9rem' }}>
              {(workflows || []).filter(w => w.status === 'active').map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>Caller ID</label>
            <input type="text" value={fromPhoneNumber ? fromPhoneNumber.address : 'Loading…'} disabled style={{ opacity: 0.7 }} />
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>Agent</label>
            <input type="text" value={selectedWorkflow ? selectedWorkflow.name : '—'} disabled style={{ opacity: 0.7 }} />
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>Phone Number</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.7rem 0.75rem', color: 'var(--text-dim)', fontSize: '0.9rem', fontWeight: 500 }}>+91</span>
              <input type="tel" placeholder="Mobile number" value={phoneNumber}
                onChange={e => setPhoneNumber(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCall()} />
            </div>
          </div>

          {result && (
            <div style={{
              background: result.success ? 'var(--success-bg)' : 'var(--error-bg)',
              border: `1px solid ${result.success ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
              padding: '0.75rem 1rem', marginTop: '1rem', borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem', color: result.success ? 'var(--success)' : 'var(--error)',
              display: 'flex', alignItems: 'center', gap: '0.5rem',
            }}>
              {result.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
              {result.message}
            </div>
          )}

          <button className="btn-primary" onClick={handleCall} disabled={isDialing || !phoneNumber.trim()}
            style={{ width: '100%', marginTop: '1.25rem' }}>
            {isDialing ? <><Loader2 size={16} className="animate-spin" /> Dialing...</> : <><PhoneCall size={16} /> Call Now</>}
          </button>
        </div>
      </div>
    </div>
  );
}
