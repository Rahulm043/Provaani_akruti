import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

export default function BackButton({ to = '/', label = 'Back' }) {
  const navigate = useNavigate();

  return (
    <button className="btn-ghost" onClick={() => navigate(to)} style={{ marginBottom: '1rem', padding: '0.5rem 0.75rem' }}>
      <ChevronLeft size={18} /> {label}
    </button>
  );
}
