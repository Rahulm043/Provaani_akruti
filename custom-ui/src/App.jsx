import React, { useState } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Bot, LogOut, ChevronLeft, ChevronRight, BarChart3, Building2, CalendarClock } from 'lucide-react';
import { AuthProvider, useAuth } from './components/AuthProvider.jsx';
import LoginPage from './pages/LoginPage.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Usage from './pages/Usage.jsx';
import ClinicDetails from './pages/ClinicDetails.jsx';
import Appointments from './pages/Appointments.jsx';
import './index.css';

const NAV_ITEMS = [
  { path: '/', icon: Bot, label: 'Call Logs' },
  { path: '/usage', icon: BarChart3, label: 'Usage' },
  { path: '/clinic-details', icon: Building2, label: 'Clinic Details' },
  { path: '/appointments', icon: CalendarClock, label: 'Appointments' },
];

function MobileTopHeader({ onLogout }) {
  return (
    <header className="mobile-top-navbar">
      <div className="mobile-brand-wrap">
        <img
          src="/logo.png"
          alt="Provaani Logo"
          className="mobile-brand-img"
        />
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
          <LogOut size={16} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}

function Sidebar({ onLogout, isCollapsed, setIsCollapsed }) {
  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`} aria-label="Main Navigation">
      <button
        className="collapse-btn"
        onClick={() => setIsCollapsed(!isCollapsed)}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        type="button"
      >
        {isCollapsed ? <ChevronRight size={15} aria-hidden="true" /> : <ChevronLeft size={15} aria-hidden="true" />}
      </button>

      <div className="sidebar-brand">
        <img
          src="/logo.png"
          alt="Provaani Logo"
          className="brand-icon"
        />
        <div className="brand-text-container">
          <h2 className="brand-title">Provaani</h2>
          <span className="brand-sub">Voice AI Receptionist</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-main-links">
          {NAV_ITEMS.map(({ path, icon: Icon, label }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} aria-hidden="true" className="nav-icon" />
              <span>{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="sidebar-footer">
        <button
          className="user-profile interactive logout-trigger"
          onClick={onLogout}
          title="Sign Out"
          type="button"
        >
          <div className="logout-content">
            <LogOut size={16} aria-hidden="true" />
            <span>Logout</span>
          </div>
        </button>
      </div>
    </aside>
  );
}

function AppContent() {
  const { isAuthenticated, loading, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (loading) {
    return (
      <div className="app-loader-container">
        <div className="spinner-lg" />
        <span className="app-loader-text">Loading Provaani...</span>
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
          <Route path="/clinic-details" element={<ClinicDetails />} />
          <Route path="/appointments" element={<Appointments />} />
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

