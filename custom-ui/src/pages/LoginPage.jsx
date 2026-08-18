import React, { useState } from 'react';
import { useAuth } from '../components/AuthProvider.jsx';
import { LogIn, Loader2 } from 'lucide-react';

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
      setError(err.message || 'Invalid email or password.');
    }
    setLoading(false);
  };

  return (
    <div className="login-screen-wrapper">
      <div className="card login-auth-card">
        <div className="login-header-block">
          <div className="login-brand-badge">
            <img src="/logo.png" alt="Provaani Logo" className="login-brand-logo" />
          </div>
          <h1 className="login-brand-heading">Provaani</h1>
          <p className="login-brand-subheading">Voice AI Receptionist Console</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="login-error-banner" role="alert">
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="login-email" className="form-label">Email address</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@provaani.xyz"
              className="form-input-control"
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group" style={{ marginTop: '1.25rem' }}>
            <label htmlFor="login-password" className="form-label">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="form-input-control"
              required
              autoComplete="current-password"
            />
          </div>

          <button
            className="btn-primary login-submit-btn"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <Loader2 size={16} className="spinner-loader" aria-hidden="true" />
            ) : (
              <>
                <LogIn size={16} aria-hidden="true" />
                <span>Sign In to Console</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

