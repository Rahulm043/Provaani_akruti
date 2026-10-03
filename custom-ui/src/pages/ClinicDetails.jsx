import React, { useState, useEffect } from 'react';
import {
  Building2,
  Stethoscope,
  MapPin,
  FileText,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Clock,
  Copy,
} from 'lucide-react';
import { fetchClinicSettings, saveClinicSettings } from '../utils/api.js';

const DAYS_OF_WEEK = [
  { key: 'monday', label: 'Monday' },
  { key: 'tuesday', label: 'Tuesday' },
  { key: 'wednesday', label: 'Wednesday' },
  { key: 'thursday', label: 'Thursday' },
  { key: 'friday', label: 'Friday' },
  { key: 'saturday', label: 'Saturday' },
  { key: 'sunday', label: 'Sunday' },
];

// 30-minute intervals from 06:00 to 23:00
const TIME_OPTIONS = (() => {
  const options = [];
  for (let h = 6; h <= 23; h++) {
    for (let m = 0; m < 60; m += 30) {
      const hh = String(h).padStart(2, '0');
      const mm = String(m).padStart(2, '0');
      const val = `${hh}:${mm}`;

      const hour12 = h % 12 === 0 ? 12 : h % 12;
      const ampm = h < 12 ? 'AM' : 'PM';
      const label = `${hour12}:${mm === '00' ? '00' : mm} ${ampm}`;

      options.push({ value: val, label });
    }
  }
  return options;
})();

const DEFAULT_BRANCH_SCHEDULE = {
  monday: [{ start: '10:00', end: '19:00' }],
  tuesday: [{ start: '10:00', end: '19:00' }],
  wednesday: [{ start: '10:00', end: '19:00' }],
  thursday: [{ start: '10:00', end: '19:00' }],
  friday: [{ start: '10:00', end: '19:00' }],
  saturday: [],
  sunday: [],
};

export default function ClinicDetails() {
  const [activeTab, setActiveTab] = useState('general'); // 'general' | 'timings'
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [selectedBranchId, setSelectedBranchId] = useState('');

  const [formData, setFormData] = useState({
    clinic_name: '',
    doctor_name: '',
    doctor_credentials: '',
    official_reception: '',
    email: '',
    procedures: '',
    special_notes: '',
    branches: [],
    appointment_config: { enabled: true, allow_booking: false, schedule: {} },
    formatted_branch_timings: {},
  });

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await fetchClinicSettings();
      if (data && data.settings) {
        const s = data.settings;
        const branches = s.branches || [];
        const apptConfig = s.appointment_config || { enabled: true, allow_booking: false, schedule: {} };
        const schedule = { ...(apptConfig.schedule || {}) };

        // Ensure every branch has a valid schedule initialized
        branches.forEach((b) => {
          if (!schedule[b.id] || Object.keys(schedule[b.id]).length === 0) {
            schedule[b.id] = JSON.parse(JSON.stringify(DEFAULT_BRANCH_SCHEDULE));
          }
        });

        setFormData({
          clinic_name: s.clinic_name || '',
          doctor_name: s.doctor_name || '',
          doctor_credentials: s.doctor_credentials || '',
          official_reception: s.official_reception || '',
          email: s.email || '',
          procedures: s.procedures || '',
          special_notes: s.special_notes || '',
          branches,
          appointment_config: {
            enabled: true,
            allow_booking: false,
            schedule,
          },
          formatted_branch_timings: s.formatted_branch_timings || {},
        });

        if (branches.length > 0) {
          setSelectedBranchId(branches[0].id);
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load clinic settings');
    } finally {
      setLoading(false);
    }
  }

  function handleChange(field, value) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setIsDirty(true);
    setSuccessMsg('');
  }

  function handleBranchChange(index, field, value) {
    setFormData((prev) => {
      const updated = [...prev.branches];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, branches: updated };
    });
    setIsDirty(true);
    setSuccessMsg('');
  }

  function addBranch() {
    const newId = `branch_${Date.now()}`;
    setFormData((prev) => {
      const newBranches = [
        ...prev.branches,
        {
          id: newId,
          name: `Branch ${prev.branches.length + 1}`,
          address: '',
          landmark: '',
          phone: '',
        },
      ];
      const newSchedule = {
        ...(prev.appointment_config?.schedule || {}),
        [newId]: JSON.parse(JSON.stringify(DEFAULT_BRANCH_SCHEDULE)),
      };
      return {
        ...prev,
        branches: newBranches,
        appointment_config: {
          ...prev.appointment_config,
          schedule: newSchedule,
        },
      };
    });
    setSelectedBranchId(newId);
    setIsDirty(true);
  }

  function removeBranch(index) {
    setFormData((prev) => {
      const branchToRemove = prev.branches[index];
      const updated = prev.branches.filter((_, i) => i !== index);
      const newSchedule = { ...(prev.appointment_config?.schedule || {}) };
      if (branchToRemove?.id) {
        delete newSchedule[branchToRemove.id];
      }
      return {
        ...prev,
        branches: updated,
        appointment_config: {
          ...prev.appointment_config,
          schedule: newSchedule,
        },
      };
    });
    setIsDirty(true);
  }

  // --- Schedule handlers ---
  function getBranchSchedule(branchId) {
    return formData.appointment_config?.schedule?.[branchId] || {};
  }

  function toggleDayOpen(branchId, dayKey) {
    setFormData((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      if (!copy.appointment_config) copy.appointment_config = { enabled: true, allow_booking: false, schedule: {} };
      if (!copy.appointment_config.schedule) copy.appointment_config.schedule = {};
      const sched = copy.appointment_config.schedule[branchId] || {};
      const currentChunks = sched[dayKey] || [];

      if (currentChunks.length > 0) {
        sched[dayKey] = [];
      } else {
        sched[dayKey] = [{ start: '10:00', end: '19:00' }];
      }

      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function handleChunkChange(branchId, dayKey, chunkIndex, field, value) {
    setFormData((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const dayChunks = sched[dayKey] || [];
      if (dayChunks[chunkIndex]) {
        dayChunks[chunkIndex][field] = value;
      }
      sched[dayKey] = dayChunks;
      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function addChunk(branchId, dayKey) {
    setFormData((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const dayChunks = sched[dayKey] || [];
      dayChunks.push({ start: '10:00', end: '19:00' });
      sched[dayKey] = dayChunks;
      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function removeChunk(branchId, dayKey, chunkIndex) {
    setFormData((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const dayChunks = sched[dayKey] || [];
      dayChunks.splice(chunkIndex, 1);
      sched[dayKey] = dayChunks;
      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function copyMondayToWeekdays(branchId) {
    setFormData((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const monChunks = sched['monday'] || [];
      ['tuesday', 'wednesday', 'thursday', 'friday'].forEach((d) => {
        sched[d] = JSON.parse(JSON.stringify(monChunks));
      });
      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
    setSuccessMsg('Monday hours copied to Tuesday through Friday!');
    setTimeout(() => setSuccessMsg(''), 3000);
  }

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    if (!formData.clinic_name.trim() || !formData.doctor_name.trim()) {
      setErrorMsg('Clinic Name and Doctor Name are required.');
      return;
    }

    setSaving(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await saveClinicSettings(formData);
      if (res && res.formatted_branch_timings) {
        setFormData((prev) => ({
          ...prev,
          formatted_branch_timings: res.formatted_branch_timings,
        }));
      }
      setSuccessMsg('Clinic details and operating hours saved! WhatsApp consultation timings updated.');
      setIsDirty(false);
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save clinic details.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="clinic-page-loading">
        <Loader2 size={32} className="animate-spin text-accent" />
        <span>Loading clinic profile...</span>
      </div>
    );
  }

  const branches = formData.branches || [];
  const currentBranchId = selectedBranchId || (branches[0] ? branches[0].id : '');
  const activeBranch = branches.find((b) => b.id === currentBranchId) || branches[0];
  const activeBranchSchedule = activeBranch ? getBranchSchedule(activeBranch.id) : {};

  return (
    <div className="clinic-settings-container">
      {/* Top Header Bar */}
      <div className="clinic-settings-header">
        <div>
          <div className="clinic-header-badge">
            <Sparkles size={14} /> Clinic Profile
          </div>
          <h1 className="clinic-page-title">Clinic Details</h1>
          <p className="clinic-page-subtitle">
            Manage practice details, doctor credentials, branch locations, and operating hours.
          </p>
        </div>

        <div className="clinic-header-actions">
          {isDirty && <span className="clinic-unsaved-badge">Unsaved changes</span>}
          <button
            type="button"
            className="btn-primary-action"
            onClick={handleSubmit}
            disabled={saving}
          >
            {saving ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Saving...
              </>
            ) : (
              <>
                <Save size={16} /> Save Changes
              </>
            )}
          </button>
        </div>
      </div>

      {/* Status Alerts */}
      {successMsg && (
        <div className="clinic-alert clinic-alert-success">
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="clinic-alert clinic-alert-error">
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Top Navigation Tabs */}
      <div className="cockpit-tabs-nav" style={{ marginBottom: '1.5rem' }}>
        <button
          type="button"
          className={`cockpit-tab-btn ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          <Building2 size={16} />
          <span>General Info</span>
        </button>

        <button
          type="button"
          className={`cockpit-tab-btn ${activeTab === 'timings' ? 'active' : ''}`}
          onClick={() => setActiveTab('timings')}
        >
          <Clock size={16} />
          <span>Clinic Timings</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: GENERAL INFO                                                       */}
      {/* ========================================================================= */}
      {activeTab === 'general' && (
        <form onSubmit={handleSubmit} className="clinic-form-grid">
          {/* Card 1: Practice & Doctor Profile */}
          <section className="clinic-card">
            <div className="clinic-card-header">
              <div className="clinic-card-icon-wrap">
                <Stethoscope size={20} className="text-accent" />
              </div>
              <div>
                <h2 className="clinic-card-title">Practice & Doctor Profile</h2>
                <p className="clinic-card-desc">Core clinic identity and chief physician information.</p>
              </div>
            </div>

            <div className="clinic-field-group">
              <div className="clinic-input-row">
                <div className="clinic-input-col">
                  <label className="clinic-label">
                    Clinic / Hospital Name <span className="req">*</span>
                  </label>
                  <input
                    type="text"
                    className="clinic-input"
                    placeholder="e.g. Aakruti Aesthetics & Plastic Surgery Clinic"
                    value={formData.clinic_name}
                    onChange={(e) => handleChange('clinic_name', e.target.value)}
                    required
                  />
                </div>

                <div className="clinic-input-col">
                  <label className="clinic-label">
                    Chief Doctor / Surgeon Name <span className="req">*</span>
                  </label>
                  <input
                    type="text"
                    className="clinic-input"
                    placeholder="e.g. Doctor Kaushal Priya Anand"
                    value={formData.doctor_name}
                    onChange={(e) => handleChange('doctor_name', e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="clinic-input-row">
                <div className="clinic-input-col full-width">
                  <label className="clinic-label">Doctor Qualifications & Titles</label>
                  <input
                    type="text"
                    className="clinic-input"
                    placeholder="e.g. M.B.B.S, M.S, M.Ch Plastic Surgery | 20+ Years Experience"
                    value={formData.doctor_credentials}
                    onChange={(e) => handleChange('doctor_credentials', e.target.value)}
                  />
                </div>
              </div>

              <div className="clinic-input-row">
                <div className="clinic-input-col">
                  <label className="clinic-label">Official Reception Contact Numbers</label>
                  <input
                    type="text"
                    className="clinic-input"
                    placeholder="e.g. +91 90020 08137 / +91 90020 08147"
                    value={formData.official_reception}
                    onChange={(e) => handleChange('official_reception', e.target.value)}
                  />
                  <span className="clinic-hint">Spoken by the agent and sent via WhatsApp.</span>
                </div>

                <div className="clinic-input-col">
                  <label className="clinic-label">Official Email</label>
                  <input
                    type="email"
                    className="clinic-input"
                    placeholder="e.g. akrutiaestheticsurgery@gmail.com"
                    value={formData.email}
                    onChange={(e) => handleChange('email', e.target.value)}
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Card 2: Clinic Locations / Branches */}
          <section className="clinic-card">
            <div className="clinic-card-header-flex">
              <div className="clinic-card-header-left">
                <div className="clinic-card-icon-wrap">
                  <MapPin size={20} className="text-accent" />
                </div>
                <div>
                  <h2 className="clinic-card-title">Clinic Locations / Branches</h2>
                  <p className="clinic-card-desc">Physical addresses and landmarks where consultations take place.</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-secondary-action"
                onClick={addBranch}
              >
                <Plus size={15} /> Add Branch
              </button>
            </div>

            <div className="clinic-branches-list">
              {formData.branches.length === 0 ? (
                <div className="clinic-empty-state">
                  <Building2 size={28} className="text-dim" />
                  <p>No branches configured. Click "Add Branch" to specify clinic locations.</p>
                </div>
              ) : (
                formData.branches.map((b, idx) => (
                  <div key={b.id || idx} className="clinic-branch-item">
                    <div className="clinic-branch-header">
                      <span className="clinic-branch-number">Branch #{idx + 1}</span>
                      <button
                        type="button"
                        className="btn-danger-icon"
                        onClick={() => removeBranch(idx)}
                        title="Remove branch"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>

                    <div className="clinic-branch-inputs">
                      <div className="clinic-input-row">
                        <div className="clinic-input-col">
                          <label className="clinic-label">Branch Name</label>
                          <input
                            type="text"
                            className="clinic-input"
                            placeholder="e.g. Durgapur Clinic"
                            value={b.name}
                            onChange={(e) => handleBranchChange(idx, 'name', e.target.value)}
                          />
                        </div>
                        <div className="clinic-input-col">
                          <label className="clinic-label">Direct Phone / Reception</label>
                          <input
                            type="text"
                            className="clinic-input"
                            placeholder="e.g. +91 90020 08137"
                            value={b.phone}
                            onChange={(e) => handleBranchChange(idx, 'phone', e.target.value)}
                          />
                        </div>
                      </div>

                      <div className="clinic-input-row">
                        <div className="clinic-input-col full-width">
                          <label className="clinic-label">Full Address</label>
                          <input
                            type="text"
                            className="clinic-input"
                            placeholder="e.g. 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216"
                            value={b.address}
                            onChange={(e) => handleBranchChange(idx, 'address', e.target.value)}
                          />
                        </div>
                      </div>

                      <div className="clinic-input-row">
                        <div className="clinic-input-col full-width">
                          <label className="clinic-label">Landmark</label>
                          <input
                            type="text"
                            className="clinic-input"
                            placeholder="e.g. Near City Centre or Opposite Park Nursing Home"
                            value={b.landmark}
                            onChange={(e) => handleBranchChange(idx, 'landmark', e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* Card 3: Procedures & Specializations */}
          <section className="clinic-card">
            <div className="clinic-card-header">
              <div className="clinic-card-icon-wrap">
                <FileText size={20} className="text-accent" />
              </div>
              <div>
                <h2 className="clinic-card-title">Procedures & Treatments Offered</h2>
                <p className="clinic-card-desc">
                  List services and treatments provided at your clinic.
                </p>
              </div>
            </div>

            <div className="clinic-field-group">
              <label className="clinic-label">List of Services / Procedures</label>
              <textarea
                className="clinic-textarea"
                rows={6}
                placeholder="e.g. Head & Face: Rhinoplasty, Blepharoplasty, Dimpleplasty...&#10;Body: Liposuction, Tummy Tuck...&#10;Hair: Hair Transplant, PRP..."
                value={formData.procedures}
                onChange={(e) => handleChange('procedures', e.target.value)}
              />
              <span className="clinic-hint">
                Add common treatments and specializations to help answer patient inquiries accurately.
              </span>
            </div>
          </section>

          {/* Card 4: Practice Notes & Announcements */}
          <section className="clinic-card">
            <div className="clinic-card-header">
              <div className="clinic-card-icon-wrap">
                <Building2 size={20} className="text-accent" />
              </div>
              <div>
                <h2 className="clinic-card-title">Practice Notes & Announcements</h2>
                <p className="clinic-card-desc">
                  Special rules or guidelines (e.g. registration requirements, holiday closures).
                </p>
              </div>
            </div>

            <div className="clinic-field-group">
              <label className="clinic-label">Additional Practice Information</label>
              <textarea
                className="clinic-textarea"
                rows={3}
                placeholder="e.g. Consultations are by appointment. Walk-ins subject to availability."
                value={formData.special_notes}
                onChange={(e) => handleChange('special_notes', e.target.value)}
              />
            </div>
          </section>
        </form>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CLINIC TIMINGS                                                     */}
      {/* ========================================================================= */}
      {activeTab === 'timings' && (
        <div className="settings-view-stack">
          {branches.length === 0 ? (
            <div className="clinic-empty-state card-empty">
              <Building2 size={32} className="text-dim" />
              <h3>No Clinic Locations Configured</h3>
              <p>Add at least one clinic branch under "General Info" to set operating hours.</p>
            </div>
          ) : (
            <div className="schedule-panel">
              {/* Branch Tab Bar */}
              <div className="branch-tab-bar">
                <div className="branch-tab-list">
                  {branches.map((b) => (
                    <button
                      key={b.id}
                      type="button"
                      className={`branch-tab-btn ${currentBranchId === b.id ? 'active' : ''}`}
                      onClick={() => setSelectedBranchId(b.id)}
                    >
                      <Building2 size={16} />
                      <span>{b.name || 'Branch'}</span>
                    </button>
                  ))}
                </div>

                <div className="branch-actions-stack">
                  <div className="branch-save-row">
                    {isDirty && <span className="clinic-unsaved-badge-sm">Unsaved</span>}
                    <button
                      type="button"
                      className="btn-primary-action btn-save-compact"
                      onClick={handleSubmit}
                      disabled={saving}
                    >
                      {saving ? (
                        <>
                          <Loader2 size={13} className="animate-spin" /> Saving...
                        </>
                      ) : (
                        <>
                          <Save size={13} /> Save Hours
                        </>
                      )}
                    </button>
                  </div>

                  {activeBranch && (
                    <button
                      type="button"
                      className="btn-shortcut"
                      onClick={() => copyMondayToWeekdays(activeBranch.id)}
                      title="Copy Monday hours to Tuesday through Friday"
                    >
                      <Copy size={13} /> Copy Monday to Weekdays
                    </button>
                  )}
                </div>
              </div>

              {/* WhatsApp Template Output Preview */}
              <div style={{
                background: 'rgba(34, 197, 94, 0.05)',
                border: '1px solid rgba(34, 197, 94, 0.25)',
                borderRadius: '8px',
                padding: '12px 16px',
                marginBottom: '16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '13px', color: '#16a34a' }}>
                    <Sparkles size={15} />
                    <span>WhatsApp Template Active Hours (clinic_and_appointment_details)</span>
                  </div>
                  <span style={{ fontSize: '11px', background: 'rgba(34, 197, 94, 0.15)', color: '#15803d', padding: '2px 8px', borderRadius: '10px', fontWeight: 500 }}>
                    Auto-Formatted on Save
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#475569', lineHeight: 1.6 }}>
                  <div><strong>Durgapur Clinic:</strong> {formData.formatted_branch_timings?.durgapur || "Monday to Friday: 9:00 AM to 7:00 PM"}</div>
                  <div><strong>Burdwan Clinic:</strong> {formData.formatted_branch_timings?.burdwan || "Thursday: 2:00 PM to 6:00 PM; Friday: 9:00 AM to 7:00 PM; Saturday: 11:00 AM to 3:00 PM"}</div>
                </div>
              </div>

              {/* Days List */}
              <div className="weekly-schedule-list">
                {DAYS_OF_WEEK.map(({ key: dayKey, label: dayLabel }) => {
                  const dayChunks = activeBranchSchedule[dayKey] || [];
                  const isOpen = dayChunks.length > 0;

                  return (
                    <div key={dayKey} className={`day-schedule-row ${isOpen ? 'is-open' : 'is-closed'}`}>
                      <div className="day-header-cell">
                        <span className="day-name">{dayLabel}</span>
                        <button
                          type="button"
                          className={`day-status-pill ${isOpen ? 'pill-open' : 'pill-closed'}`}
                          onClick={() => toggleDayOpen(activeBranch.id, dayKey)}
                        >
                          {isOpen ? 'Open' : 'Closed'}
                        </button>
                      </div>

                      <div className="day-chunks-cell">
                        {!isOpen ? (
                          <span className="day-closed-text">Closed</span>
                        ) : (
                          <div className="chunks-flow">
                            {dayChunks.map((chunk, cIdx) => (
                              <div key={cIdx} className="time-chunk-item">
                                <span className="chunk-label">Session {cIdx + 1}</span>
                                <div className="time-select-group">
                                  <select
                                    className="time-dropdown"
                                    value={chunk.start}
                                    onChange={(e) =>
                                      handleChunkChange(activeBranch.id, dayKey, cIdx, 'start', e.target.value)
                                    }
                                  >
                                    {TIME_OPTIONS.map((t) => (
                                      <option key={t.value} value={t.value}>
                                        {t.label}
                                      </option>
                                    ))}
                                  </select>

                                  <span className="time-separator">to</span>

                                  <select
                                    className="time-dropdown"
                                    value={chunk.end}
                                    onChange={(e) =>
                                      handleChunkChange(activeBranch.id, dayKey, cIdx, 'end', e.target.value)
                                    }
                                  >
                                    {TIME_OPTIONS.map((t) => (
                                      <option key={t.value} value={t.value}>
                                        {t.label}
                                      </option>
                                    ))}
                                  </select>
                                </div>

                                {dayChunks.length > 1 && (
                                  <button
                                    type="button"
                                    className="btn-remove-chunk"
                                    onClick={() => removeChunk(activeBranch.id, dayKey, cIdx)}
                                    title="Remove session"
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                )}
                              </div>
                            ))}

                            <button
                              type="button"
                              className="btn-add-chunk"
                              onClick={() => addChunk(activeBranch.id, dayKey)}
                            >
                              <Plus size={13} /> Add Session
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
