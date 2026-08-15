import React, { useState } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Bot, LogOut, ChevronLeft, ChevronRight, BarChart3 } from 'lucide-react';
import { AuthProvider, useAuth } from './components/AuthProvider.jsx';
import LoginPage from './pages/LoginPage.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Usage from './pages/Usage.jsx';
import './index.css';

const NAV_ITEMS = [
  { path: '/', icon: Bot, label: 'Call Logs' },
  { path: '/usage', icon: BarChart3, label: 'Usage' },
];

function MobileTopHeader({ onLogout }) {
  return (
    <header className="mobile-top-navbar">
      <div className="mobile-brand-wrap" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
        <img src="/logo.jpg" alt="Provaani Logo" style={{ width: '32px', height: '32px', borderRadius: '6px', objectFit: 'contain' }} />
        <div className="mobile-brand-text">
          <h1 className="mobile-brand-title">Provaani</h1>
          <span className="mobile-brand-sub">Voice AI Receptionist</span>
        </div>
      </div>
      <div className="mobile-header-actions">
        <button
          className="mobile-logout-btn"
          onClick={onLogout}
          title="Sign Out"
          aria-label="Sign Out"
          type="button"
        >
          <LogOut size={18} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}

function Sidebar({ onLogout, isCollapsed, setIsCollapsed }) {
  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <button className="collapse-btn" onClick={() => setIsCollapsed(!isCollapsed)} aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"} type="button">
        {isCollapsed ? <ChevronRight size={16} aria-hidden="true" /> : <ChevronLeft size={16} aria-hidden="true" />}
      </button>
      <div className="sidebar-brand">
        <img src="/logo.jpg" alt="Provaani Logo" className="brand-icon" style={{ width: '40px', height: '40px', borderRadius: '8px', objectFit: 'contain' }} />
        <div className="brand-text-container">
          <h2 className="brand-title">Provaani</h2>
          <span className="brand-sub">Voice AI Receptionist</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        <div className="nav-main-links">
          {NAV_ITEMS.map(({ path, icon: Icon, label }) => (
            <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon size={18} aria-hidden="true" /><span>{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
      <div className="sidebar-footer">
        <div className="user-profile interactive logout-trigger" onClick={onLogout} title="Sign Out" role="button" tabIndex={0}>
          <div className="logout-content"><LogOut size={18} aria-hidden="true" /><span>Logout</span></div>
        </div>
      </div>
    </aside>
  );
}

function AppContent() {
  const { isAuthenticated, loading, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (loading) {
    return (
      <div className="flex-center" style={{ height: '100vh', flexDirection: 'column', gap: '1rem' }}>
        <div className="spinner-lg" />
        <span style={{ color: 'var(--text-dim)' }}>Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className={`app-layout ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      <MobileTopHeader onLogout={logout} />
      <Sidebar onLogout={logout} isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      <main className={`main-content ${isCollapsed ? 'expanded' : ''}`}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/usage" element={<Usage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
