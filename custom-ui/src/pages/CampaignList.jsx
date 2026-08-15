import React from 'react';
import useSWR from 'swr';
import { useNavigate } from 'react-router-dom';
import { Megaphone, PlusCircle, Play, Pause, RefreshCw, ArrowUpRight } from 'lucide-react';
import { swrFetcher, swrDefaults, formatDate } from '../utils/api.js';
import { TableSkeleton } from '../components/Skeleton.jsx';
import BackButton from '../components/BackButton.jsx';

function campaignStateLabel(state) {
  return {
    draft: 'Draft',
    scheduled: 'Scheduled',
    running: 'Running',
    paused: 'Paused',
    completed: 'Completed',
  }[state] || state;
}

export default function CampaignList() {
  const navigate = useNavigate();
  const { data, isLoading, mutate } = useSWR('/api/v1/campaign/', swrFetcher, {
    ...swrDefaults,
    refreshInterval: 15000,
  });

  const campaigns = data?.campaigns || [];

  return (
    <div className="fade-in">
      <BackButton />
      <div className="page-header flex-between">
        <div>
          <h1>Campaigns</h1>
          <p>Bulk outbound calling campaigns</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/campaigns/new')}>
          <PlusCircle size={16} /> New Campaign
        </button>
      </div>

      {isLoading ? <TableSkeleton columns={6} rows={4} /> : campaigns.length === 0 ? (
        <div className="empty-state card">
          <Megaphone size={48} />
          <h1>No Campaigns</h1>
          <p>Create your first calling campaign to start bulk outreach.</p>
          <button className="btn-primary" style={{ marginTop: '1rem' }} onClick={() => navigate('/campaigns/new')}>
            <PlusCircle size={16} /> New Campaign
          </button>
        </div>
      ) : (
        <div className="table-container" style={{ marginTop: '1.5rem' }}>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Concurrency</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map(c => {
                const pct = c.total_rows ? Math.round((c.processed_rows / c.total_rows) * 100) : 0;
                return (
                  <tr key={c.id} className="main-row clickable" onClick={() => navigate(`/campaigns/${c.id}`)}
                    style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 600 }}>{c.name}</td>
                    <td>
                      <span className={`badge ${c.state === 'running' ? 'connected' : c.state === 'paused' ? 'running' : c.state === 'completed' ? 'completed' : 'idle'}`}>
                        {campaignStateLabel(c.state)}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--primary)', borderRadius: 3, transition: 'width 0.3s' }} />
                        </div>
                        <span className="text-sm text-dim">{c.processed_rows}/{c.total_rows}</span>
                      </div>
                    </td>
                    <td><span>{c.max_concurrency || 1}</span></td>
                    <td className="text-dim text-sm">{formatDate(c.created_at)}</td>
                    <td>
                      <button className="btn-ghost" onClick={e => { e.stopPropagation(); navigate(`/campaigns/${c.id}`); }}>
                        <ArrowUpRight size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
