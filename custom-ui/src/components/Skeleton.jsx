import React from 'react';

export function Skeleton({ className = '', style = {} }) {
  return <div className={`skeleton ${className}`} style={style} />;
}

export function StatGridSkeleton({ count = 4 }) {
  return (
    <div className="stats-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="stat-card skeleton-card">
          <Skeleton className="stat-icon" style={{ width: 40, height: 40, borderRadius: 'var(--radius-sm)' }} />
          <div>
            <Skeleton className="skeleton-value" />
            <Skeleton className="skeleton-label" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ columns = 6, rows = 5 }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            {Array.from({ length: columns }, (_, i) => (
              <th key={i}><Skeleton className="skeleton-th" /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }, (_, r) => (
            <tr key={r}>
              {Array.from({ length: columns }, (_, c) => (
                <td key={c}><Skeleton className="skeleton-cell" /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
