import React, { useState, useEffect } from 'react';
import {
  CalendarClock,
  Clock,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  Copy,
  Building2,
  User,
  Bot,
  Search,
  Calendar,
  Check,
  X,
  Phone,
  RefreshCw,
  XCircle,
  Pencil,
} from 'lucide-react';
import {
  fetchClinicSettings,
  saveClinicSettings,
  fetchAppointments,
  bookAppointment,
  updateAppointment,
  updateAppointmentStatus,
  deleteAppointment,
} from '../utils/api.js';

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

function getTodayString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getOffsetDateString(daysOffset) {
  const d = new Date();
  d.setDate(d.getDate() + daysOffset);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function Appointments() {
  // Top-Level Tab: 'bookings' | 'settings'
  const [activeTab, setActiveTab] = useState('bookings');

  // Clinic Settings
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingMainToggle, setSavingMainToggle] = useState(false);
  const [fullSettings, setFullSettings] = useState(null);
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [isDirty, setIsDirty] = useState(false);

  // Bookings List State (defaults to all upcoming dates so no bookings are hidden)
  const [selectedDate, setSelectedDate] = useState(getTodayString());
  const [allDatesMode, setAllDatesMode] = useState(true);
  const [branchFilter, setBranchFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [appointments, setAppointments] = useState([]);
  const [shiftMetrics, setShiftMetrics] = useState({ total: 0, confirmed: 0, completed: 0, cancelled: 0, no_show: 0 });
  const [loadingBookings, setLoadingBookings] = useState(false);
  const [updatingStatusId, setUpdatingStatusId] = useState(null);

  // New Appointment Modal
  const [quickBookOpen, setQuickBookOpen] = useState(false);
  const [bookingSaving, setBookingSaving] = useState(false);
  const [bookingForm, setBookingForm] = useState({
    patient_name: '',
    phone_number: '',
    branch_id: '',
    appointment_date: getTodayString(),
    appointment_time: '11:00 AM',
    procedure_of_interest: '',
    notes: '',
  });
  const [bookingError, setBookingError] = useState('');

  // Edit Appointment Modal
  const [editingAppt, setEditingAppt] = useState(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');

  // Status Alerts
  const [globalSuccess, setGlobalSuccess] = useState('');
  const [globalError, setGlobalError] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  useEffect(() => {
    if (activeTab === 'bookings') {
      loadBookings();
    }
  }, [activeTab, selectedDate, allDatesMode, branchFilter, statusFilter, searchQuery]);

  async function loadSettings() {
    setLoadingSettings(true);
    try {
      const data = await fetchClinicSettings();
      if (data && data.settings) {
        const s = data.settings;
        if (!s.appointment_config) {
          s.appointment_config = { enabled: false, allow_booking: true, schedule: {} };
        }
        if (s.appointment_config.allow_booking === undefined) {
          s.appointment_config.allow_booking = true;
        }
        if (!s.appointment_config.schedule) {
          s.appointment_config.schedule = {};
        }

        if (Array.isArray(s.branches) && s.branches.length > 0) {
          s.branches.forEach((b) => {
            if (!s.appointment_config.schedule[b.id]) {
              s.appointment_config.schedule[b.id] = {
                monday: [{ start: '09:00', end: '19:00' }],
                tuesday: [{ start: '09:00', end: '19:00' }],
                wednesday: [{ start: '09:00', end: '19:00' }],
                thursday: [{ start: '09:00', end: '19:00' }],
                friday: [{ start: '09:00', end: '19:00' }],
                saturday: [],
                sunday: [],
              };
            }
          });
          setSelectedBranchId(s.branches[0].id);
          setBookingForm((prev) => ({ ...prev, branch_id: s.branches[0].id }));
        }

        setFullSettings(s);
      }
    } catch (err) {
      setGlobalError(err.message || 'Failed to load clinic settings');
    } finally {
      setLoadingSettings(false);
    }
  }

  async function loadBookings() {
    setLoadingBookings(true);
    setGlobalError('');
    try {
      const params = {};
      if (!allDatesMode && selectedDate) {
        params.appointment_date = selectedDate;
      }
      if (branchFilter && branchFilter !== 'all') {
        params.branch_id = branchFilter;
      }
      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter;
      }
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      const res = await fetchAppointments(params);
      if (res && res.success) {
        setAppointments(res.appointments || []);
        setShiftMetrics(res.shift_metrics || { total: 0, confirmed: 0, completed: 0, cancelled: 0, no_show: 0 });
      }
    } catch (err) {
      setGlobalError(err.message || 'Failed to load appointments');
    } finally {
      setLoadingBookings(false);
    }
  }

  async function handleStatusChange(appointmentId, newStatus) {
    setUpdatingStatusId(appointmentId);
    try {
      await updateAppointmentStatus(appointmentId, { status: newStatus });
      setAppointments((prev) =>
        prev.map((a) => (a.id === appointmentId ? { ...a, status: newStatus } : a))
      );
      loadBookings();
    } catch (err) {
      alert(`Error updating appointment: ${err.message}`);
    } finally {
      setUpdatingStatusId(null);
    }
  }

  async function handleDeleteAppointment(appointmentId, patientName) {
    if (!window.confirm(`Are you sure you want to delete the appointment for ${patientName}?`)) {
      return;
    }
    try {
      await deleteAppointment(appointmentId);
      setAppointments((prev) => prev.filter((a) => a.id !== appointmentId));
      loadBookings();
    } catch (err) {
      alert(`Error deleting appointment: ${err.message}`);
    }
  }

  // Open Edit Modal with selected appointment data
  function openEditModal(appt) {
    setEditingAppt({
      id: appt.id,
      patient_name: appt.patient_name || '',
      phone_number: appt.phone_number || '',
      branch_id: appt.branch_id || branches[0]?.id || '',
      appointment_date: appt.appointment_date || getTodayString(),
      appointment_time: appt.appointment_time || '11:00 AM',
      procedure_of_interest: appt.procedure_of_interest || '',
      status: appt.status || 'confirmed',
      notes: appt.notes || '',
    });
    setEditError('');
  }

  // Handle Edit Submit
  async function handleEditSubmit(e) {
    e.preventDefault();
    if (!editingAppt) return;
    setEditSaving(true);
    setEditError('');

    try {
      const payload = {
        patient_name: editingAppt.patient_name.trim(),
        phone_number: editingAppt.phone_number.trim(),
        branch_id: editingAppt.branch_id,
        appointment_date: editingAppt.appointment_date,
        appointment_time: editingAppt.appointment_time.trim(),
        procedure_of_interest: editingAppt.procedure_of_interest.trim(),
        status: editingAppt.status,
        notes: editingAppt.notes.trim(),
      };

      const res = await updateAppointment(editingAppt.id, payload);
      if (res && res.success) {
        setEditingAppt(null);
        setGlobalSuccess('Appointment updated successfully.');
        setTimeout(() => setGlobalSuccess(''), 3000);
        loadBookings();
      }
    } catch (err) {
      setEditError(err.message || 'Failed to update appointment');
    } finally {
      setEditSaving(false);
    }
  }

  // Handle New Booking Submit
  async function handleQuickBookSubmit(e) {
    e.preventDefault();
    setBookingSaving(true);
    setBookingError('');

    try {
      const payload = {
        patient_name: bookingForm.patient_name.trim(),
        phone_number: bookingForm.phone_number.trim(),
        branch_id: bookingForm.branch_id,
        appointment_date: bookingForm.appointment_date,
        appointment_time: bookingForm.appointment_time.trim(),
        procedure_of_interest: bookingForm.procedure_of_interest.trim(),
        booked_by: 'staff',
        notes: bookingForm.notes.trim(),
      };

      const res = await bookAppointment(payload);
      if (res && res.success) {
        setQuickBookOpen(false);
        setBookingForm({
          patient_name: '',
          phone_number: '',
          branch_id: branches[0]?.id || '',
          appointment_date: selectedDate || getTodayString(),
          appointment_time: '11:00 AM',
          procedure_of_interest: '',
          notes: '',
        });
        setGlobalSuccess('Appointment booked successfully.');
        setTimeout(() => setGlobalSuccess(''), 3000);
        loadBookings();
      }
    } catch (err) {
      setBookingError(err.message || 'Failed to book appointment');
    } finally {
      setBookingSaving(false);
    }
  }

  // -------------------------------------------------------------
  // Operating Hours & AI Voice Agent Toggle Operations
  // -------------------------------------------------------------
  const branches = fullSettings?.branches || [];
  const appointmentConfig = fullSettings?.appointment_config || { enabled: false, allow_booking: true, schedule: {} };
  // Main Toggle: Whether AI discusses appointment timings with callers
  const isTimingsEnabled = Boolean(appointmentConfig.enabled);
  // Secondary Toggle: Whether AI autonomously confirms/books appointments
  const isBookingEnabled = isTimingsEnabled && Boolean(appointmentConfig.allow_booking !== false);

  // Main Toggle: Auto-saves instantly when flipped in header
  async function toggleTimingsEnabled() {
    if (!fullSettings || savingMainToggle) return;
    const nextVal = !isTimingsEnabled;
    const updated = JSON.parse(JSON.stringify(fullSettings));
    if (!updated.appointment_config) {
      updated.appointment_config = { enabled: false, allow_booking: true, schedule: {} };
    }
    updated.appointment_config.enabled = nextVal;
    setFullSettings(updated);
    setSavingMainToggle(true);
    setGlobalError('');
    setGlobalSuccess('');
    try {
      const res = await saveClinicSettings(updated);
      if (res && res.success) {
        setIsDirty(false);
        setGlobalSuccess(
          nextVal
            ? 'Appointment timings enabled. Voice agent will share consultation hours with callers.'
            : 'Appointment timings disabled. Voice agent will provide general clinic info only.'
        );
        setTimeout(() => setGlobalSuccess(''), 4000);
      }
    } catch (err) {
      setFullSettings(fullSettings);
      setGlobalError(`Failed to update appointment toggle: ${err.message}`);
    } finally {
      setSavingMainToggle(false);
    }
  }

  // Secondary Toggle: Controlled inside Operating Hours tab (auto-saves instantly)
  async function toggleAllowBooking() {
    if (!isTimingsEnabled || !fullSettings || savingSettings) return;
    const current = fullSettings.appointment_config?.allow_booking !== false;
    const nextVal = !current;
    const updated = JSON.parse(JSON.stringify(fullSettings));
    if (!updated.appointment_config) {
      updated.appointment_config = { enabled: true, allow_booking: true, schedule: {} };
    }
    updated.appointment_config.allow_booking = nextVal;
    setFullSettings(updated);
    setSavingSettings(true);
    setGlobalError('');
    setGlobalSuccess('');
    try {
      const res = await saveClinicSettings(updated);
      if (res && res.success) {
        setIsDirty(false);
        setGlobalSuccess(
          nextVal
            ? 'Autonomous Phone Booking ACTIVATED. AI agent will collect caller details and book appointments.'
            : 'Phone Booking PAUSED (Reception Referral Mode). AI agent will share consultation hours but refer callers to reception.'
        );
        setTimeout(() => setGlobalSuccess(''), 4000);
      }
    } catch (err) {
      setFullSettings(fullSettings);
      setGlobalError(`Failed to update booking mode: ${err.message}`);
    } finally {
      setSavingSettings(false);
    }
  }

  function getBranchSchedule(branchId) {
    return appointmentConfig.schedule[branchId] || {};
  }

  function toggleDayOpen(branchId, dayKey) {
    setFullSettings((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const currentChunks = sched[dayKey] || [];

      if (currentChunks.length > 0) {
        sched[dayKey] = [];
      } else {
        sched[dayKey] = [{ start: '09:00', end: '19:00' }];
      }

      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function handleChunkChange(branchId, dayKey, chunkIndex, field, value) {
    setFullSettings((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const dayChunks = sched[dayKey] || [];
      if (dayChunks[chunkIndex]) {
        dayChunks[chunkIndex][field] = value;
      }
      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function addChunk(branchId, dayKey) {
    setFullSettings((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const dayChunks = sched[dayKey] || [];
      const lastChunk = dayChunks[dayChunks.length - 1];

      let newStart = '14:00';
      let newEnd = '18:00';

      if (lastChunk) {
        newStart = lastChunk.end;
        const [h] = lastChunk.end.split(':').map(Number);
        const nextH = Math.min(h + 3, 22);
        newEnd = `${String(nextH).padStart(2, '0')}:00`;
      }

      dayChunks.push({ start: newStart, end: newEnd });
      sched[dayKey] = dayChunks;
      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
  }

  function removeChunk(branchId, dayKey, chunkIndex) {
    setFullSettings((prev) => {
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
    setFullSettings((prev) => {
      const copy = JSON.parse(JSON.stringify(prev));
      const sched = copy.appointment_config.schedule[branchId] || {};
      const mondayChunks = sched['monday'] || [];

      ['tuesday', 'wednesday', 'thursday', 'friday'].forEach((day) => {
        sched[day] = JSON.parse(JSON.stringify(mondayChunks));
      });

      copy.appointment_config.schedule[branchId] = sched;
      return copy;
    });
    setIsDirty(true);
    setGlobalSuccess('Monday schedule copied to Tuesday through Friday.');
    setTimeout(() => setGlobalSuccess(''), 3000);
  }

  async function handleSaveSettings() {
    setSavingSettings(true);
    setGlobalError('');
    setGlobalSuccess('');
    try {
      const res = await saveClinicSettings(fullSettings);
      if (res && res.success) {
        setIsDirty(false);
        setGlobalSuccess('Operating hours and settings saved successfully.');
        setTimeout(() => setGlobalSuccess(''), 3000);
      }
    } catch (err) {
      setGlobalError(err.message || 'Failed to save settings');
    } finally {
      setSavingSettings(false);
    }
  }

  if (loadingSettings) {
    return (
      <div className="clinic-settings-container">
        <div className="clinic-page-loading">
          <Loader2 size={36} className="animate-spin text-accent" />
          <p>Loading appointments...</p>
        </div>
      </div>
    );
  }

  const activeBranch = branches.find((b) => b.id === selectedBranchId) || branches[0];
  const activeBranchSchedule = activeBranch ? getBranchSchedule(activeBranch.id) : {};

  return (
    <div className="clinic-settings-container">
      {/* Header Bar */}
      <div className="clinic-settings-header">
        <div className="clinic-header-info">
          <h1 className="clinic-page-title">Appointments</h1>
          <p className="clinic-page-subtitle">
            Manage patient bookings and clinic operating hours.
          </p>
        </div>

        <div className="clinic-header-actions">
          {activeTab === 'bookings' && (
            <button
              type="button"
              className="btn-primary-action"
              onClick={() => setQuickBookOpen(true)}
            >
              <Plus size={16} /> New Appointment
            </button>
          )}
        </div>
      </div>

      {/* Appointment AI Controls (Dual Toggles in General Section) */}
      <div className="appointment-top-controls">
        {/* Toggle 1: Share Clinic Timing Details */}
        <div className={`appointment-control-card ${!isTimingsEnabled ? 'control-disabled' : 'control-active'}`}>
          <div className="appointment-control-header">
            <div className="appointment-control-title-group">
              <div className={`appointment-control-icon-badge ${isTimingsEnabled ? 'active' : 'off'}`}>
                <Clock size={18} />
              </div>
              <div>
                <h3 className="appointment-control-title">Share Clinic Timing Details</h3>
              </div>
            </div>
            <label
              className="switch-container switch-sm"
              title={isTimingsEnabled ? "Timings sharing active (click to pause)" : "Timings sharing paused (click to activate)"}
            >
              <input
                type="checkbox"
                checked={isTimingsEnabled}
                onChange={toggleTimingsEnabled}
                disabled={savingMainToggle}
              />
              <span className="switch-slider"></span>
            </label>
          </div>
          <p className="appointment-control-desc">
            Allow the AI voice agent to share consultation hours and clinic schedules with callers.
          </p>
        </div>

        {/* Toggle 2: Book Appointments via Phone */}
        <div className={`appointment-control-card ${!isTimingsEnabled ? 'control-disabled' : isBookingEnabled ? 'control-active' : 'control-warning'}`}>
          <div className="appointment-control-header">
            <div className="appointment-control-title-group">
              <div className={`appointment-control-icon-badge ${!isTimingsEnabled ? 'off' : isBookingEnabled ? 'active' : 'warning'}`}>
                <Bot size={18} />
              </div>
              <div>
                <h3 className="appointment-control-title">Book Appointments via Phone</h3>
              </div>
            </div>
            <label
              className={`switch-container switch-sm ${!isTimingsEnabled ? 'switch-disabled' : ''}`}
              title={!isTimingsEnabled ? "Enable clinic timings first" : isBookingEnabled ? "Autonomous booking active (click to switch to reception referral)" : "Reception referral active (click to enable autonomous booking)"}
            >
              <input
                type="checkbox"
                checked={isBookingEnabled}
                onChange={toggleAllowBooking}
                disabled={!isTimingsEnabled || savingSettings}
              />
              <span className="switch-slider"></span>
            </label>
          </div>
          <p className="appointment-control-desc">
            {!isTimingsEnabled
              ? 'Requires clinic timings to be enabled first.'
              : isBookingEnabled
              ? 'AI voice agent autonomously collects patient details and books appointments into your calendar.'
              : 'AI voice agent shares timings but directs callers to reception to confirm appointments.'}
          </p>
        </div>
      </div>

      {/* Alerts */}
      {globalSuccess && (
        <div className="clinic-alert clinic-alert-success">
          <CheckCircle2 size={18} />
          <span>{globalSuccess}</span>
        </div>
      )}
      {globalError && (
        <div className="clinic-alert clinic-alert-error">
          <AlertCircle size={18} />
          <span>{globalError}</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="cockpit-tabs-nav">
        <button
          type="button"
          className={`cockpit-tab-btn ${activeTab === 'bookings' ? 'active' : ''}`}
          onClick={() => setActiveTab('bookings')}
        >
          <Calendar size={17} />
          <span>Bookings</span>
          <span className="cockpit-tab-badge">{shiftMetrics.total}</span>
        </button>

        <button
          type="button"
          className={`cockpit-tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Clock size={17} />
          <span>Operating Hours</span>
          <span className={`cockpit-mode-pill ${!isTimingsEnabled ? 'off' : isBookingEnabled ? 'on' : 'warning'}`}>
            {!isTimingsEnabled ? 'Timings Off' : isBookingEnabled ? 'AI Booking Active' : 'Reception Referral'}
          </span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: BOOKINGS QUEUE                                                     */}
      {/* ========================================================================= */}
      {activeTab === 'bookings' && (
        <div className="bookings-view-stack">
          {/* Metrics Ribbon */}
          <div className="shift-metrics-grid">
            <div className="metric-card metric-total">
              <div className="metric-card-header">
                <span className="metric-label">Total</span>
                <Calendar size={18} className="metric-icon" />
              </div>
              <div className="metric-val">{shiftMetrics.total}</div>
              <span className="metric-sub">{allDatesMode ? 'All dates' : selectedDate}</span>
            </div>

            <div className="metric-card metric-confirmed">
              <div className="metric-card-header">
                <span className="metric-label">Confirmed</span>
                <CheckCircle2 size={18} className="metric-icon" />
              </div>
              <div className="metric-val">{shiftMetrics.confirmed}</div>
              <span className="metric-sub">Upcoming appointments</span>
            </div>

            <div className="metric-card metric-completed">
              <div className="metric-card-header">
                <span className="metric-label">Completed</span>
                <Check size={18} className="metric-icon" />
              </div>
              <div className="metric-val">{shiftMetrics.completed}</div>
              <span className="metric-sub">Attended consultations</span>
            </div>

            <div className="metric-card metric-cancelled">
              <div className="metric-card-header">
                <span className="metric-label">Cancelled & No-Show</span>
                <XCircle size={18} className="metric-icon" />
              </div>
              <div className="metric-val">{shiftMetrics.cancelled + shiftMetrics.no_show}</div>
              <span className="metric-sub">{shiftMetrics.cancelled} cancelled · {shiftMetrics.no_show} no-show</span>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="cockpit-filter-bar">
            <div className="filter-left-cluster">
              <div className="quick-date-group">
                <button
                  type="button"
                  className={`date-pill ${!allDatesMode && selectedDate === getOffsetDateString(-1) ? 'active' : ''}`}
                  onClick={() => {
                    setAllDatesMode(false);
                    setSelectedDate(getOffsetDateString(-1));
                  }}
                >
                  Yesterday
                </button>
                <button
                  type="button"
                  className={`date-pill ${!allDatesMode && selectedDate === getTodayString() ? 'active' : ''}`}
                  onClick={() => {
                    setAllDatesMode(false);
                    setSelectedDate(getTodayString());
                  }}
                >
                  Today
                </button>
                <button
                  type="button"
                  className={`date-pill ${!allDatesMode && selectedDate === getOffsetDateString(1) ? 'active' : ''}`}
                  onClick={() => {
                    setAllDatesMode(false);
                    setSelectedDate(getOffsetDateString(1));
                  }}
                >
                  Tomorrow
                </button>
                <button
                  type="button"
                  className={`date-pill ${allDatesMode ? 'active' : ''}`}
                  onClick={() => setAllDatesMode(!allDatesMode)}
                >
                  All Dates
                </button>
              </div>

              {!allDatesMode && (
                <div className="date-picker-wrap">
                  <input
                    type="date"
                    className="date-native-input"
                    value={selectedDate}
                    onChange={(e) => {
                      setAllDatesMode(false);
                      setSelectedDate(e.target.value);
                    }}
                  />
                </div>
              )}

              <div className="filter-dropdown-wrap">
                <select
                  className="filter-select"
                  value={branchFilter}
                  onChange={(e) => setBranchFilter(e.target.value)}
                >
                  <option value="all">All Branches</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="filter-dropdown-wrap">
                <select
                  className="filter-select"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Statuses</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="no_show">No Show</option>
                </select>
              </div>
            </div>

            <div className="filter-right-cluster">
              <div className="cockpit-search-wrap">
                <Search size={15} className="search-icon" />
                <input
                  type="text"
                  className="cockpit-search-input"
                  placeholder="Search by name, phone, procedure..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="search-clear-btn"
                    onClick={() => setSearchQuery('')}
                  >
                    <X size={13} />
                  </button>
                )}
              </div>

              <button
                type="button"
                className="btn-refresh"
                onClick={loadBookings}
                disabled={loadingBookings}
                title="Refresh Bookings"
              >
                <RefreshCw size={15} className={loadingBookings ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>

          {/* Bookings Table */}
          <div className="appointments-table-card">
            {loadingBookings ? (
              <div className="table-loading-container">
                <Loader2 size={32} className="animate-spin text-accent" />
                <p>Loading appointments...</p>
              </div>
            ) : appointments.length === 0 ? (
              <div className="table-empty-container">
                <CalendarClock size={40} className="text-dim" />
                <h3>No Appointments Found</h3>
                <p>
                  {searchQuery
                    ? `No bookings match "${searchQuery}".`
                    : allDatesMode
                    ? 'No appointments recorded yet.'
                    : `No appointments scheduled for ${selectedDate}.`}
                </p>
                <button
                  type="button"
                  className="btn-empty-book"
                  onClick={() => setQuickBookOpen(true)}
                >
                  <Plus size={15} /> Book Appointment
                </button>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="cockpit-table">
                  <thead>
                    <tr>
                      <th>Time & Date</th>
                      <th>Patient</th>
                      <th>Branch & Treatment</th>
                      <th>Booked Via</th>
                      <th>Status</th>
                      <th>Notes</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appointments.map((appt) => {
                      const isUpdating = updatingStatusId === appt.id;
                      const isVoice = appt.booked_by === 'voice_agent';

                      return (
                        <tr key={appt.id} className={`table-row-${appt.status}`}>
                          {/* Time & Date */}
                          <td className="cell-time">
                            <div className="time-display-pill">
                              <Clock size={13} />
                              <span>{appt.appointment_time}</span>
                            </div>
                            <span className="date-sub-display">{appt.appointment_date}</span>
                          </td>

                          {/* Patient */}
                          <td className="cell-patient">
                            <div className="patient-name-row">
                              <span className="patient-name">{appt.patient_name}</span>
                            </div>
                            <div className="patient-phone-row">
                              <Phone size={12} className="text-dim" />
                              <a href={`tel:${appt.phone_number}`} className="phone-link">
                                {appt.phone_number}
                              </a>
                            </div>
                          </td>

                          {/* Branch & Treatment */}
                          <td className="cell-branch">
                            <span className="branch-badge">
                              <Building2 size={12} /> {appt.branch_name}
                            </span>
                            {appt.procedure_of_interest ? (
                              <span className="procedure-tag">{appt.procedure_of_interest}</span>
                            ) : (
                              <span className="procedure-empty">General Consultation</span>
                            )}
                          </td>

                          {/* Booked Via */}
                          <td className="cell-source">
                            {isVoice ? (
                              <span className="booked-source-tag source-ai">
                                <Bot size={13} /> AI Assistant
                              </span>
                            ) : (
                              <span className="booked-source-tag source-staff">
                                <User size={13} /> Staff
                              </span>
                            )}
                          </td>

                          {/* Status */}
                          <td className="cell-status">
                            {isUpdating ? (
                              <div className="status-updating">
                                <Loader2 size={14} className="animate-spin" /> Updating...
                              </div>
                            ) : (
                              <div className="status-pill-toggle-group">
                                <button
                                  type="button"
                                  className={`pill-status-btn status-btn-confirmed ${
                                    appt.status === 'confirmed' ? 'selected' : ''
                                  }`}
                                  onClick={() => handleStatusChange(appt.id, 'confirmed')}
                                >
                                  Confirmed
                                </button>
                                <button
                                  type="button"
                                  className={`pill-status-btn status-btn-completed ${
                                    appt.status === 'completed' ? 'selected' : ''
                                  }`}
                                  onClick={() => handleStatusChange(appt.id, 'completed')}
                                >
                                  Done
                                </button>
                                <button
                                  type="button"
                                  className={`pill-status-btn status-btn-cancelled ${
                                    appt.status === 'cancelled' ? 'selected' : ''
                                  }`}
                                  onClick={() => handleStatusChange(appt.id, 'cancelled')}
                                >
                                  Cancelled
                                </button>
                                <button
                                  type="button"
                                  className={`pill-status-btn status-btn-noshow ${
                                    appt.status === 'no_show' ? 'selected' : ''
                                  }`}
                                  onClick={() => handleStatusChange(appt.id, 'no_show')}
                                >
                                  No Show
                                </button>
                              </div>
                            )}
                          </td>

                          {/* Notes */}
                          <td className="cell-notes">
                            <span className="notes-display" title={appt.notes}>
                              {appt.notes || <span className="text-dim italic">—</span>}
                            </span>
                          </td>

                          {/* Actions: Edit & Delete */}
                          <td className="cell-actions text-right">
                            <div className="table-actions-cluster">
                              <button
                                type="button"
                                className="btn-action-edit"
                                onClick={() => openEditModal(appt)}
                                title="Edit Appointment"
                              >
                                <Pencil size={15} />
                              </button>
                              <button
                                type="button"
                                className="btn-action-delete"
                                onClick={() => handleDeleteAppointment(appt.id, appt.patient_name)}
                                title="Delete Appointment"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: OPERATING HOURS                                                    */}
      {/* ========================================================================= */}
      {activeTab === 'settings' && (
        <div className="settings-view-stack">
          {/* Branch Sessions Configurator */}
          {branches.length === 0 ? (
            <div className="clinic-empty-state card-empty">
              <Building2 size={32} className="text-dim" />
              <h3>No Clinic Locations Configured</h3>
              <p>Add at least one clinic location under "Clinic Details" to set hours.</p>
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
                      className={`branch-tab-btn ${selectedBranchId === b.id ? 'active' : ''}`}
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
                      onClick={handleSaveSettings}
                      disabled={savingSettings}
                    >
                      {savingSettings ? (
                        <>
                          <Loader2 size={13} className="animate-spin" /> Saving...
                        </>
                      ) : (
                        <>
                          <Save size={13} /> Save
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

      {/* ========================================================================= */}
      {/* EDIT APPOINTMENT MODAL                                                    */}
      {/* ========================================================================= */}
      {editingAppt && (
        <div className="modal-backdrop">
          <div className="quick-book-modal-card">
            <div className="modal-header">
              <div className="modal-title-group">
                <Pencil size={20} className="text-accent" />
                <div>
                  <h3 className="modal-title">Edit Appointment</h3>
                  <p className="modal-subtitle">Update patient details, date, time, or status.</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setEditingAppt(null)}
              >
                <X size={18} />
              </button>
            </div>

            {editError && (
              <div className="modal-alert-error">
                <AlertCircle size={16} />
                <span>{editError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="quick-book-form">
              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Patient Name *</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    value={editingAppt.patient_name}
                    onChange={(e) =>
                      setEditingAppt({ ...editingAppt, patient_name: e.target.value })
                    }
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Phone Number *</label>
                  <input
                    type="tel"
                    required
                    className="form-input"
                    value={editingAppt.phone_number}
                    onChange={(e) =>
                      setEditingAppt({ ...editingAppt, phone_number: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Branch *</label>
                  <select
                    className="form-input"
                    value={editingAppt.branch_id}
                    onChange={(e) =>
                      setEditingAppt({ ...editingAppt, branch_id: e.target.value })
                    }
                  >
                    {branches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Status</label>
                  <select
                    className="form-input"
                    value={editingAppt.status}
                    onChange={(e) =>
                      setEditingAppt({ ...editingAppt, status: e.target.value })
                    }
                  >
                    <option value="confirmed">Confirmed</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="no_show">No Show</option>
                  </select>
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Date *</label>
                  <input
                    type="date"
                    required
                    className="form-input"
                    value={editingAppt.appointment_date}
                    onChange={(e) =>
                      setEditingAppt({ ...editingAppt, appointment_date: e.target.value })
                    }
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Time *</label>
                  <select
                    className="form-input"
                    value={editingAppt.appointment_time}
                    onChange={(e) =>
                      setEditingAppt({ ...editingAppt, appointment_time: e.target.value })
                    }
                  >
                    {TIME_OPTIONS.map((t) => (
                      <option key={t.value} value={t.label}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Treatment / Procedure</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Liposuction, Hair Transplant"
                  value={editingAppt.procedure_of_interest}
                  onChange={(e) =>
                    setEditingAppt({ ...editingAppt, procedure_of_interest: e.target.value })
                  }
                />
              </div>

              <div className="form-group">
                <label className="form-label">Notes</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  placeholder="Additional notes..."
                  value={editingAppt.notes}
                  onChange={(e) =>
                    setEditingAppt({ ...editingAppt, notes: e.target.value })
                  }
                />
              </div>

              <div className="modal-actions-footer">
                <button
                  type="button"
                  className="btn-cancel-modal"
                  onClick={() => setEditingAppt(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-submit-modal"
                  disabled={editSaving}
                >
                  {editSaving ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Saving...
                    </>
                  ) : (
                    <>
                      <Check size={16} /> Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* NEW APPOINTMENT MODAL                                                     */}
      {/* ========================================================================= */}
      {quickBookOpen && (
        <div className="modal-backdrop">
          <div className="quick-book-modal-card">
            <div className="modal-header">
              <div className="modal-title-group">
                <CalendarClock size={20} className="text-accent" />
                <div>
                  <h3 className="modal-title">New Appointment</h3>
                  <p className="modal-subtitle">Enter patient details to schedule an appointment.</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setQuickBookOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            {bookingError && (
              <div className="modal-alert-error">
                <AlertCircle size={16} />
                <span>{bookingError}</span>
              </div>
            )}

            <form onSubmit={handleQuickBookSubmit} className="quick-book-form">
              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Patient Name *</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. Suman Mukherjee"
                    value={bookingForm.patient_name}
                    onChange={(e) =>
                      setBookingForm({ ...bookingForm, patient_name: e.target.value })
                    }
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Phone Number *</label>
                  <input
                    type="tel"
                    required
                    className="form-input"
                    placeholder="e.g. 9876543210"
                    value={bookingForm.phone_number}
                    onChange={(e) =>
                      setBookingForm({ ...bookingForm, phone_number: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Clinic Branch *</label>
                  <select
                    className="form-input"
                    value={bookingForm.branch_id}
                    onChange={(e) =>
                      setBookingForm({ ...bookingForm, branch_id: e.target.value })
                    }
                  >
                    {branches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Treatment / Procedure</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Liposuction, Hair Transplant"
                    value={bookingForm.procedure_of_interest}
                    onChange={(e) =>
                      setBookingForm({ ...bookingForm, procedure_of_interest: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Date *</label>
                  <input
                    type="date"
                    required
                    className="form-input"
                    value={bookingForm.appointment_date}
                    onChange={(e) =>
                      setBookingForm({ ...bookingForm, appointment_date: e.target.value })
                    }
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Time *</label>
                  <select
                    className="form-input"
                    value={bookingForm.appointment_time}
                    onChange={(e) =>
                      setBookingForm({ ...bookingForm, appointment_time: e.target.value })
                    }
                  >
                    {TIME_OPTIONS.map((t) => (
                      <option key={t.value} value={t.label}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Notes (Optional)</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  placeholder="Special requests or medical notes..."
                  value={bookingForm.notes}
                  onChange={(e) =>
                    setBookingForm({ ...bookingForm, notes: e.target.value })
                  }
                />
              </div>

              <div className="modal-actions-footer">
                <button
                  type="button"
                  className="btn-cancel-modal"
                  onClick={() => setQuickBookOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-submit-modal"
                  disabled={bookingSaving}
                >
                  {bookingSaving ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Verifying...
                    </>
                  ) : (
                    <>
                      <Check size={16} /> Book Appointment
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
