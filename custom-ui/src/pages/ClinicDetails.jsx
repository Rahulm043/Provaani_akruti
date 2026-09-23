import React, { useState, useEffect } from 'react';
import {
  Building2,
  Stethoscope,
  MapPin,
  Phone,
  Mail,
  FileText,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { fetchClinicSettings, saveClinicSettings } from '../utils/api.js';

export default function ClinicDetails() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isDirty, setIsDirty] = useState(false);

  const [formData, setFormData] = useState({
    clinic_name: '',
    doctor_name: '',
    doctor_credentials: '',
    official_reception: '',
    email: '',
    procedures: '',
    special_notes: '',
    branches: [],
    appointment_config: { enabled: true, allow_booking: true, schedule: {} },
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
        setFormData({
          clinic_name: data.settings.clinic_name || '',
          doctor_name: data.settings.doctor_name || '',
          doctor_credentials: data.settings.doctor_credentials || '',
          official_reception: data.settings.official_reception || '',
          email: data.settings.email || '',
          procedures: data.settings.procedures || '',
          special_notes: data.settings.special_notes || '',
          branches: data.settings.branches || [],
          appointment_config: data.settings.appointment_config || { enabled: true, allow_booking: true, schedule: {} },
        });
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
    setFormData((prev) => ({
      ...prev,
      branches: [
        ...prev.branches,
        {
          id: newId,
          name: `Branch ${prev.branches.length + 1}`,
          address: '',
          landmark: '',
          phone: '',
        },
      ],
    }));
    setIsDirty(true);
  }

  function removeBranch(index) {
    setFormData((prev) => {
      const updated = prev.branches.filter((_, i) => i !== index);
      return { ...prev, branches: updated };
    });
    setIsDirty(true);
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
      await saveClinicSettings(formData);
      setSuccessMsg('Clinic settings saved and voice agent recompiled successfully!');
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
            Manage your practice profile, doctor credentials, locations, and services.
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
                  placeholder="e.g. Akruti Aesthetics & Plastic Surgery Clinic"
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
                Special rules or guidelines (e.g. consultation fees, registration requirements, holiday closures).
              </p>
            </div>
          </div>

          <div className="clinic-field-group">
            <label className="clinic-label">Additional Practice Information</label>
            <textarea
              className="clinic-textarea"
              rows={3}
              placeholder="e.g. Prior appointment booking required. Consultation fee is ₹800. Walk-ins subject to availability."
              value={formData.special_notes}
              onChange={(e) => handleChange('special_notes', e.target.value)}
            />
          </div>
        </section>
      </form>
    </div>
  );
}
