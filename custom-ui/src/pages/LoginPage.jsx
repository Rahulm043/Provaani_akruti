import React, { useState } from 'react';
import { useAuth } from '../components/AuthProvider.jsx';
import { LogIn } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="flex-center" style={{ height: '100vh', background: 'var(--bg)' }}>
      <div className="card" style={{ width: '100%', maxWidth: 400, padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Voice AI</h1>
          <p className="text-dim text-sm" style={{ marginTop: '0.5rem' }}>Sign in to your calling dashboard</p>
        </div>
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="card" style={{ background: 'var(--error-bg)', border: '1px solid rgba(239,68,68,0.2)', padding: '0.75rem 1rem', marginBottom: '1rem', color: 'var(--error)', fontSize: '0.875rem' }}>
              {error}
            </div>
          )}
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@sukanyaclasses.com" required />
          </div>
          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Your password" required />
          </div>
          <button className="btn-primary" type="submit" disabled={loading} style={{ width: '100%', marginTop: '1.5rem' }}>
            {loading ? <div className="spinner-loader" style={{ width: 16, height: 16 }} /> : <><LogIn size={16} /> Sign In</>}
          </button>
        </form>
      </div>
    </div>
  );
}
