import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, AlertTriangle, CheckCircle2,
  Edit2, Save, X, Plus, Upload, Download, RefreshCw, FileText
} from 'lucide-react';
import { apiFetch } from '../utils/api';

interface RateCard {
  id: number;
  city: string;
  service: string;
  ride_type: string;
  vehicle_category: string;
  currency: string;
  base_fare: number;
  per_km: number;
  per_min: number;
  min_fare: number;
  booking_fee: number;
  free_km: number;
  long_distance_threshold: number;
  long_distance_rate: number;
  night_multiplier: number;
  tax_pct: number;
  source_url: string;
  last_verified_date: string;
  is_verified: boolean;
  updated_at: string;
}

interface ServiceStatusItem {
  id: number;
  region_id: string;
  service_name: string;
  status: 'active' | 'suspended' | 'unavailable';
  status_reason?: string;
  last_updated: string;
}

export const RateCardAdmin: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'cards' | 'status' | 'import'>('cards');
  const [rateCards, setRateCards] = useState<RateCard[]>([]);
  const [serviceStatuses, setServiceStatuses] = useState<ServiceStatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterCity, setFilterCity] = useState('');
  const [editingCard, setEditingCard] = useState<RateCard | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState('');
  const [importJsonText, setImportJsonText] = useState('');
  const [importStatus, setImportStatus] = useState<string | null>(null);

  const fetchRateCards = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/admin/rate-cards');
      if (res.ok) {
        const data = await res.json();
        setRateCards(data.rate_cards || []);
      }
    } catch (err) {
      console.error('Failed to load rate cards', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchServiceStatuses = async () => {
    try {
      const res = await apiFetch('/api/admin/service-statuses');
      if (res.ok) {
        const data = await res.json();
        setServiceStatuses(data.service_statuses || []);
      }
    } catch (err) {
      console.error('Failed to load service statuses', err);
    }
  };

  useEffect(() => {
    fetchRateCards();
    fetchServiceStatuses();
  }, []);

  const handleSaveCard = async () => {
    if (!editingCard) return;
    try {
      const res = await apiFetch(`/api/admin/rate-cards/${editingCard.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_fare: editingCard.base_fare,
          per_km: editingCard.per_km,
          per_min: editingCard.per_min,
          min_fare: editingCard.min_fare,
          booking_fee: editingCard.booking_fee,
          tax_pct: editingCard.tax_pct,
          night_multiplier: editingCard.night_multiplier,
          source_url: editingCard.source_url,
          last_verified_date: editingCard.last_verified_date,
          is_verified: editingCard.is_verified,
        }),
      });
      if (res.ok) {
        setSaveSuccessMsg(`Rate card #${editingCard.id} updated successfully!`);
        setEditingCard(null);
        fetchRateCards();
        setTimeout(() => setSaveSuccessMsg(''), 4000);
      }
    } catch (err) {
      alert(`Save failed: ${err}`);
    }
  };

  const handleToggleStatus = async (
    regionId: string,
    serviceName: string,
    newStatus: 'active' | 'suspended' | 'unavailable',
    reason?: string
  ) => {
    try {
      const res = await apiFetch('/api/admin/service-status', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          region_id: regionId,
          service_name: serviceName,
          status: newStatus,
          status_reason: reason || (newStatus === 'suspended' ? 'Suspended by regulator' : 'Normal operation'),
        }),
      });
      if (res.ok) {
        fetchServiceStatuses();
        setSaveSuccessMsg(`Service ${serviceName} in ${regionId} flipped to ${newStatus}`);
        setTimeout(() => setSaveSuccessMsg(''), 4000);
      }
    } catch (err) {
      alert(`Status update failed: ${err}`);
    }
  };

  const handleImportJson = async () => {
    try {
      const parsed = JSON.parse(importJsonText);
      const items = Array.isArray(parsed) ? parsed : [parsed];
      const res = await apiFetch('/api/admin/rate-cards/import-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(items),
      });
      if (res.ok) {
        const data = await res.json();
        setImportStatus(`Success! Imported ${data.created} new rate cards, updated ${data.updated} existing.`);
        fetchRateCards();
      } else {
        setImportStatus('Server rejected import. Verify field format.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setImportStatus(`Invalid JSON: ${msg}`);
    }
  };

  const filteredCards = rateCards.filter(
    (c) => !filterCity || c.city.toLowerCase().includes(filterCity.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Admin Title & Sub-tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h2 className="text-xl md:text-2xl font-black text-[var(--text-primary)] flex items-center gap-2">
            <ShieldCheck className="text-emerald-500" />
            Statutory Rate Card & Aggregator Admin
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Manage legal tariffs, verified statutory rate cards, and flip aggregator regulatory statuses (active/suspended).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab('cards')}
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              activeSubTab === 'cards'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)]'
            }`}
          >
            Rate Cards ({rateCards.length})
          </button>
          <button
            onClick={() => setActiveSubTab('status')}
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              activeSubTab === 'status'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)]'
            }`}
          >
            Service Statuses ({serviceStatuses.length})
          </button>
          <button
            onClick={() => setActiveSubTab('import')}
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              activeSubTab === 'import'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)]'
            }`}
          >
            JSON / CSV Import
          </button>
        </div>
      </div>

      {saveSuccessMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 size={16} />
          {saveSuccessMsg}
        </div>
      )}

      {/* Subtab 1: Rate Cards */}
      {activeSubTab === 'cards' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Filter by city (e.g. Bengaluru, Kochi, Mumbai)..."
                value={filterCity}
                onChange={(e) => setFilterCity(e.target.value)}
                className="px-3 py-1.5 text-xs rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] w-72"
              />
              {filterCity && (
                <button
                  onClick={() => setFilterCity('')}
                  className="text-xs text-[var(--text-secondary)] hover:text-white"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchRateCards}
                className="p-1.5 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg text-[var(--text-secondary)] hover:text-white"
                title="Refresh"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={() => {
                  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(rateCards, null, 2));
                  const downloadAnchor = document.createElement('a');
                  downloadAnchor.setAttribute('href', dataStr);
                  downloadAnchor.setAttribute('download', 'rate_cards_export.json');
                  document.body.appendChild(downloadAnchor);
                  downloadAnchor.click();
                  downloadAnchor.remove();
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-secondary)] rounded-xl text-xs font-semibold hover:text-white cursor-pointer"
              >
                <Download size={13} /> Export JSON
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[var(--border-color)]">
            <table className="w-full text-left text-xs text-[var(--text-secondary)]">
              <thead className="bg-[var(--bg-secondary)] text-[var(--text-primary)] border-b border-[var(--border-color)]">
                <tr>
                  <th className="p-3 font-bold">City</th>
                  <th className="p-3 font-bold">Service & Type</th>
                  <th className="p-3 font-bold">Base / Min</th>
                  <th className="p-3 font-bold">Per Km / Min</th>
                  <th className="p-3 font-bold">Booking Fee</th>
                  <th className="p-3 font-bold">Status</th>
                  <th className="p-3 font-bold">Last Verified</th>
                  <th className="p-3 font-bold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)] bg-[var(--bg-primary)]">
                {filteredCards.map((c) => (
                  <tr key={c.id} className="hover:bg-[var(--bg-secondary)]/50">
                    <td className="p-3 font-bold text-[var(--text-primary)]">{c.city}</td>
                    <td className="p-3">
                      <div className="font-semibold text-[var(--text-primary)]">{c.service}</div>
                      <div className="text-[10px] text-[var(--text-secondary)]">{c.ride_type} ({c.vehicle_category})</div>
                    </td>
                    <td className="p-3 font-medium">
                      {c.currency} {c.base_fare} / {c.currency} {c.min_fare}
                    </td>
                    <td className="p-3 font-medium">
                      {c.currency} {c.per_km}/km · {c.currency} {c.per_min}/min
                    </td>
                    <td className="p-3 font-medium">{c.currency} {c.booking_fee}</td>
                    <td className="p-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.is_verified
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                            : 'bg-amber-950 text-amber-400 border border-amber-500/40'
                        }`}
                      >
                        {c.is_verified ? '✓ Verified' : '⚠ Unverified'}
                      </span>
                    </td>
                    <td className="p-3 text-[10px]">{c.last_verified_date || 'Unrecorded'}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => setEditingCard({ ...c })}
                        className="p-1.5 text-indigo-400 hover:text-indigo-300 rounded-lg hover:bg-indigo-950/40 cursor-pointer"
                        title="Edit rate card"
                      >
                        <Edit2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Subtab 2: Aggregator Regulatory Status Flipping */}
      {activeSubTab === 'status' && (
        <div className="space-y-4">
          <p className="text-xs text-[var(--text-secondary)]">
            Flip license status for aggregators per city (e.g. when transport authorities temporarily suspend aggregator operations or licenses).
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {serviceStatuses.map((st) => (
              <div
                key={`${st.region_id}-${st.service_name}`}
                className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-extrabold text-sm text-[var(--text-primary)]">
                      {st.service_name}
                    </h4>
                    <span className="text-[10px] text-[var(--text-secondary)] uppercase font-semibold">
                      Region: {st.region_id}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      st.status === 'active'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                        : st.status === 'suspended'
                        ? 'bg-rose-950 text-rose-400 border border-rose-500/40'
                        : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                    }`}
                  >
                    {st.status.toUpperCase()}
                  </span>
                </div>

                {st.status_reason && (
                  <p className="text-[11px] text-[var(--text-secondary)] italic bg-[var(--bg-primary)] p-2 rounded-lg border border-[var(--border-color)]">
                    {st.status_reason}
                  </p>
                )}

                <div className="pt-2 flex items-center justify-between border-t border-[var(--border-color)] text-xs">
                  <span className="text-[10px] text-[var(--text-secondary)]">Change Status:</span>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => handleToggleStatus(st.region_id, st.service_name, 'active')}
                      className={`px-2 py-1 rounded text-[10px] font-bold cursor-pointer ${
                        st.status === 'active'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-[var(--bg-primary)] text-slate-400 hover:text-white border border-[var(--border-color)]'
                      }`}
                    >
                      Active
                    </button>
                    <button
                      onClick={() => {
                        const reason = window.prompt(
                          `Reason for suspending ${st.service_name} in ${st.region_id}:`,
                          'Transport department compliance / licence review'
                        );
                        if (reason !== null) {
                          handleToggleStatus(st.region_id, st.service_name, 'suspended', reason);
                        }
                      }}
                      className={`px-2 py-1 rounded text-[10px] font-bold cursor-pointer ${
                        st.status === 'suspended'
                          ? 'bg-rose-600 text-white'
                          : 'bg-[var(--bg-primary)] text-slate-400 hover:text-white border border-[var(--border-color)]'
                      }`}
                    >
                      Suspend
                    </button>
                    <button
                      onClick={() => handleToggleStatus(st.region_id, st.service_name, 'unavailable', 'Service does not operate')}
                      className={`px-2 py-1 rounded text-[10px] font-bold cursor-pointer ${
                        st.status === 'unavailable'
                          ? 'bg-zinc-700 text-white'
                          : 'bg-[var(--bg-primary)] text-slate-400 hover:text-white border border-[var(--border-color)]'
                      }`}
                    >
                      Unavailable
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Subtab 3: JSON Import */}
      {activeSubTab === 'import' && (
        <div className="p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-4">
          <div className="flex items-center gap-2">
            <Upload className="text-emerald-500" size={20} />
            <div>
              <h3 className="font-bold text-sm text-[var(--text-primary)]">Bulk Import Rate Cards (JSON)</h3>
              <p className="text-xs text-[var(--text-secondary)]">Paste a JSON array of rate cards to create new ones or update existing tariffs.</p>
            </div>
          </div>

          <textarea
            rows={10}
            value={importJsonText}
            onChange={(e) => setImportJsonText(e.target.value)}
            placeholder={`[
  {
    "city": "Bengaluru",
    "service": "Uber",
    "ride_type": "UberGo",
    "vehicle_category": "Cab",
    "currency": "INR",
    "base_fare": 50,
    "per_km": 16,
    "per_min": 1.5,
    "booking_fee": 15,
    "min_fare": 80,
    "tax_pct": 5.0,
    "is_verified": true,
    "last_verified_date": "2026-03-01",
    "source_url": "https://transport.karnataka.gov.in"
  }
]`}
            className="w-full p-3 font-mono text-xs rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-hidden"
          />

          {importStatus && (
            <div className={`p-3 rounded-xl text-xs font-semibold ${importStatus.startsWith('Success') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}`}>
              {importStatus}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={() => setImportJsonText('')}
              className="px-4 py-2 bg-[var(--bg-primary)] text-[var(--text-secondary)] rounded-xl text-xs font-semibold cursor-pointer"
            >
              Clear
            </button>
            <button
              onClick={handleImportJson}
              disabled={!importJsonText.trim()}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
            >
              Import Rate Cards
            </button>
          </div>
        </div>
      )}

      {/* Rate Card Edit Modal */}
      {editingCard && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
              <div>
                <h3 className="font-extrabold text-base text-[var(--text-primary)]">
                  Edit Rate Card: {editingCard.service} ({editingCard.ride_type})
                </h3>
                <span className="text-xs text-[var(--text-secondary)]">{editingCard.city} · ID: #{editingCard.id}</span>
              </div>
              <button
                onClick={() => setEditingCard(null)}
                className="text-[var(--text-secondary)] hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Base Fare ({editingCard.currency})</label>
                <input
                  type="number"
                  value={editingCard.base_fare}
                  onChange={(e) => setEditingCard({ ...editingCard, base_fare: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Minimum Fare ({editingCard.currency})</label>
                <input
                  type="number"
                  value={editingCard.min_fare}
                  onChange={(e) => setEditingCard({ ...editingCard, min_fare: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Rate Per Km ({editingCard.currency})</label>
                <input
                  type="number"
                  step="0.5"
                  value={editingCard.per_km}
                  onChange={(e) => setEditingCard({ ...editingCard, per_km: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Rate Per Minute ({editingCard.currency})</label>
                <input
                  type="number"
                  step="0.1"
                  value={editingCard.per_min}
                  onChange={(e) => setEditingCard({ ...editingCard, per_min: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Booking / Platform Fee ({editingCard.currency})</label>
                <input
                  type="number"
                  value={editingCard.booking_fee}
                  onChange={(e) => setEditingCard({ ...editingCard, booking_fee: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Tax Percentage (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={editingCard.tax_pct}
                  onChange={(e) => setEditingCard({ ...editingCard, tax_pct: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div className="col-span-2">
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Source / Tariff Notification URL</label>
                <input
                  type="text"
                  value={editingCard.source_url || ''}
                  onChange={(e) => setEditingCard({ ...editingCard, source_url: e.target.value })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-secondary)] block font-semibold">Last Verified Date (YYYY-MM-DD)</label>
                <input
                  type="date"
                  value={editingCard.last_verified_date || ''}
                  onChange={(e) => setEditingCard({ ...editingCard, last_verified_date: e.target.value })}
                  className="w-full mt-1 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                />
              </div>

              <div className="flex items-center gap-2 pt-4">
                <input
                  type="checkbox"
                  id="is_verified_chk"
                  checked={editingCard.is_verified}
                  onChange={(e) => setEditingCard({ ...editingCard, is_verified: e.target.checked })}
                  className="w-4 h-4 rounded text-emerald-600 focus:ring-0"
                />
                <label htmlFor="is_verified_chk" className="font-bold text-xs text-[var(--text-primary)] cursor-pointer">
                  Mark as Verified by Admin
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[var(--border-color)]">
              <button
                onClick={() => setEditingCard(null)}
                className="px-4 py-2 bg-[var(--bg-primary)] text-[var(--text-secondary)] rounded-xl text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveCard}
                className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer"
              >
                <Save size={13} /> Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RateCardAdmin;
