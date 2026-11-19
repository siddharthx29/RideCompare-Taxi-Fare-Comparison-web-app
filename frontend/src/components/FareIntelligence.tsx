import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, FileImage, Flag, RefreshCw, ShieldAlert } from 'lucide-react';
import { apiFetch } from '../utils/api';

type Report = {
  id: number;
  provider: string;
  pickupLocation: string;
  destinationLocation: string;
  vehicleCategory: string;
  submittedFare: number;
  currency: string;
  quotationTimestamp: string;
  status: string;
  confidenceScore: number;
  predictedFare: number | null;
  explanation: string;
  evidenceCount: number;
  hasScreenshot: boolean;
  votes: Record<string, number>;
  createdAt?: string;
};

type FareIntelligenceTab = 'submit' | 'history';

const statusStyles: Record<string, string> = {
  VERIFIED: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  CORROBORATED: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  COMMUNITY_REPORTED: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  UNDER_REVIEW: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  REJECTED: 'bg-red-500/15 text-red-400 border-red-500/30',
};

function getDeviceFingerprint(): string {
  const key = 'ridecompare.fare-device';
  const stored = localStorage.getItem(key);
  if (stored) return stored;
  const fingerprint = `${crypto.randomUUID()}-${navigator.userAgent.length}-${screen.width}`;
  localStorage.setItem(key, fingerprint);
  return fingerprint;
}

export function FareIntelligence({ initialTab = 'submit' }: { initialTab?: FareIntelligenceTab }) {
  const [reports, setReports] = useState<Report[]>([]);
  const [mySubmissions, setMySubmissions] = useState<Report[]>([]);
  const [activeTab, setActiveTab] = useState<FareIntelligenceTab>(initialTab);
  const [loadingReports, setLoadingReports] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [screenshotName, setScreenshotName] = useState('');
  const [screenshotReference, setScreenshotReference] = useState<string | null>(null);
  const [form, setForm] = useState({
    provider: 'Uber',
    pickupLocation: '',
    destinationLocation: '',
    pickupLat: '12.9716',
    pickupLng: '77.5946',
    destinationLat: '12.9352',
    destinationLng: '77.6245',
    vehicleCategory: 'Cab',
    submittedFare: '',
    quotationTimestamp: new Date().toISOString().slice(0, 16),
    estimatedDistanceKm: '',
    estimatedDurationMin: '',
    surgeMultiplier: '',
    additionalFees: '0',
  });

  const deviceFingerprint = useMemo(() => getDeviceFingerprint(), []);

  const loadReports = async () => {
    setLoadingReports(true);
    try {
      const response = await apiFetch('/api/fares/community?limit=30');
      const data = await response.json() as { reports: Report[] };
      setReports(data.reports);
    } catch {
      setMessage('Community reports could not be loaded.');
    } finally {
      setLoadingReports(false);
    }
  };

  useEffect(() => {
    void loadReports();
  }, []);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const update = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const loadMySubmissions = async () => {
    setLoadingHistory(true);
    try {
      const response = await apiFetch(`/api/fares/mine?device_fingerprint=${encodeURIComponent(deviceFingerprint)}`);
      const data = await response.json() as { submissions: Report[] };
      setMySubmissions(data.submissions);
    } catch {
      setMessage('Your fare submissions could not be loaded.');
    } finally {
      setLoadingHistory(false);
    }
  };

  const uploadScreenshot = async (file: File | undefined) => {
    if (!file) return;
    setScreenshotName(file.name);
    const body = new FormData();
    body.append('file', file);
    try {
      const response = await apiFetch('/api/fares/screenshot', { method: 'POST', body });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail || 'Screenshot upload failed');
      const data = await response.json() as { reference: string };
      setScreenshotReference(data.reference);
    } catch (error) {
      setScreenshotName('');
      setScreenshotReference(null);
      setMessage(error instanceof Error ? error.message : 'Screenshot upload failed.');
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage('');
    try {
      const response = await apiFetch('/api/fares/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: form.provider,
          pickupLocation: form.pickupLocation,
          destinationLocation: form.destinationLocation,
          pickupCoordinates: [Number(form.pickupLat), Number(form.pickupLng)],
          destinationCoordinates: [Number(form.destinationLat), Number(form.destinationLng)],
          vehicleCategory: form.vehicleCategory,
          submittedFare: Number(form.submittedFare),
          currency: 'INR',
          quotationTimestamp: new Date(form.quotationTimestamp).toISOString(),
          estimatedDistanceKm: Number(form.estimatedDistanceKm),
          estimatedDurationMin: Number(form.estimatedDurationMin),
          surgeMultiplier: form.surgeMultiplier ? Number(form.surgeMultiplier) : null,
          additionalFees: Number(form.additionalFees),
          screenshotReference,
          deviceFingerprint,
        }),
      });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail || 'Submission failed');
      const report = await response.json() as Report;
      setReports((current) => [report, ...current]);
      setMySubmissions((current) => [report, ...current]);
      setMessage(`Submitted for verification: ${report.status.replaceAll('_', ' ')}. This is not a live provider quote.`);
      setForm((current) => ({ ...current, submittedFare: '', estimatedDistanceKm: '', estimatedDurationMin: '' }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const vote = async (id: number, voteType: string) => {
    try {
      await apiFetch(`/api/fares/verification/${id}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voteType, deviceFingerprint }),
      });
      await loadReports();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Vote could not be recorded.');
    }
  };

  const removeSubmission = async (id: number) => {
    if (!window.confirm('Remove this fare report from RideCompare?')) return;
    try {
      await apiFetch(`/api/fares/${id}?device_fingerprint=${encodeURIComponent(deviceFingerprint)}`, { method: 'DELETE' });
      setMySubmissions((current) => current.filter((report) => report.id !== id));
      setReports((current) => current.filter((report) => report.id !== id));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submission could not be removed.');
    }
  };

  const inputClass = 'w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-color)]';

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Fare Intelligence</h1>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Contribute observations, review evidence, and understand price confidence.</p>
        </div>
        <div className="flex rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-1">
          <button onClick={() => setActiveTab('submit')} className={`rounded-lg px-3 py-2 text-xs font-bold ${activeTab === 'submit' ? 'bg-[var(--accent-color)] text-black' : 'text-[var(--text-secondary)]'}`}>Submit & Reports</button>
          <button onClick={() => { setActiveTab('history'); void loadMySubmissions(); }} className={`rounded-lg px-3 py-2 text-xs font-bold ${activeTab === 'history' ? 'bg-[var(--accent-color)] text-black' : 'text-[var(--text-secondary)]'}`}>My Submissions</button>
        </div>
      </div>
      {activeTab === 'history' ? (
        <div className="glass-panel rounded-2xl p-5 md:p-7">
          <h2 className="text-xl font-bold">My Fare Submissions</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Only this browser profile can manage these anonymous device-scoped reports.</p>
          {loadingHistory ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">Loading your submissions...</p> : mySubmissions.length === 0 ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">You have not submitted any fares.</p> : <div className="mt-5 grid gap-3">{mySubmissions.map((report) => <article key={report.id} className="rounded-xl border border-[var(--border-color)] p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">{report.provider} · ₹{report.submittedFare}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{report.pickupLocation} → {report.destinationLocation}</p><p className="mt-1 text-[10px] text-[var(--text-secondary)]">{new Date(report.createdAt || report.quotationTimestamp).toLocaleString()}</p></div><span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${statusStyles[report.status] || statusStyles.COMMUNITY_REPORTED}`}>{report.status.replaceAll('_', ' ')}</span></div><p className="mt-3 text-xs text-[var(--text-secondary)]">{Math.round(report.confidenceScore * 100)}% confidence · {report.explanation}</p><button onClick={() => void removeSubmission(report.id)} className="mt-3 rounded-lg border border-red-500/30 px-2 py-1 text-[10px] text-red-400">Remove report</button></article>)}</div>}
        </div>
      ) : (
        <>
      <div className="glass-panel rounded-2xl p-5 md:p-7">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-orange-500/15 p-2 text-orange-400"><ShieldAlert size={20} /></div>
          <div>
            <h2 className="text-xl font-bold text-[var(--text-primary)]">Contribute a Live Fare</h2>
            <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">
              Share what you saw in a taxi app. Every submission is independently assessed and starts as unverified.
            </p>
          </div>
        </div>
        <form onSubmit={submit} className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="text-xs font-semibold">Pickup location<input required className={inputClass} value={form.pickupLocation} onChange={(e) => update('pickupLocation', e.target.value)} /></label>
          <label className="text-xs font-semibold">Drop-off location<input required className={inputClass} value={form.destinationLocation} onChange={(e) => update('destinationLocation', e.target.value)} /></label>
          <label className="text-xs font-semibold">Platform<select className={inputClass} value={form.provider} onChange={(e) => update('provider', e.target.value)}><option>Uber</option><option>Ola</option><option>Rapido</option></select></label>
          <label className="text-xs font-semibold">Vehicle category<input required className={inputClass} value={form.vehicleCategory} onChange={(e) => update('vehicleCategory', e.target.value)} /></label>
          <label className="text-xs font-semibold">Exact fare (INR)<input required type="number" min="1" className={inputClass} value={form.submittedFare} onChange={(e) => update('submittedFare', e.target.value)} /></label>
          <label className="text-xs font-semibold">Quotation time<input required type="datetime-local" className={inputClass} value={form.quotationTimestamp} onChange={(e) => update('quotationTimestamp', e.target.value)} /></label>
          <label className="text-xs font-semibold">Distance (km)<input required type="number" min="0.1" step="0.1" className={inputClass} value={form.estimatedDistanceKm} onChange={(e) => update('estimatedDistanceKm', e.target.value)} /></label>
          <label className="text-xs font-semibold">Duration (minutes)<input required type="number" min="1" step="1" className={inputClass} value={form.estimatedDurationMin} onChange={(e) => update('estimatedDurationMin', e.target.value)} /></label>
          <label className="text-xs font-semibold">Pickup coordinates (lat, lng)<div className="flex gap-2"><input required type="number" step="any" className={inputClass} value={form.pickupLat} onChange={(e) => update('pickupLat', e.target.value)} /><input required type="number" step="any" className={inputClass} value={form.pickupLng} onChange={(e) => update('pickupLng', e.target.value)} /></div></label>
          <label className="text-xs font-semibold">Drop-off coordinates (lat, lng)<div className="flex gap-2"><input required type="number" step="any" className={inputClass} value={form.destinationLat} onChange={(e) => update('destinationLat', e.target.value)} /><input required type="number" step="any" className={inputClass} value={form.destinationLng} onChange={(e) => update('destinationLng', e.target.value)} /></div></label>
          <label className="text-xs font-semibold">Surge multiplier (optional)<input type="number" min="0" step="0.1" className={inputClass} value={form.surgeMultiplier} onChange={(e) => update('surgeMultiplier', e.target.value)} /></label>
          <label className="text-xs font-semibold">Additional fees<input type="number" min="0" step="1" className={inputClass} value={form.additionalFees} onChange={(e) => update('additionalFees', e.target.value)} /></label>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-[var(--border-color)] p-3 text-xs font-semibold"><FileImage size={16} />{screenshotName || 'Optional screenshot'}<input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => void uploadScreenshot(e.target.files?.[0])} /></label>
          <button disabled={submitting} className="rounded-xl bg-[var(--accent-color)] px-4 py-3 text-sm font-bold text-black disabled:opacity-50">{submitting ? 'Submitting...' : 'Submit Fare for Verification'}</button>
        </form>
        <p className="mt-4 text-[11px] leading-relaxed text-[var(--text-secondary)]">Submitted fares are subject to automated validation and community verification. Unverified submissions will not be displayed as confirmed live prices.</p>
        {message && <p className="mt-3 rounded-xl bg-[var(--bg-primary)] px-3 py-2 text-xs text-[var(--accent-color)]">{message}</p>}
      </div>

      <div className="glass-panel rounded-2xl p-5 md:p-7">
        <div className="flex items-center justify-between"><div><h2 className="text-xl font-bold">Community Fare Reports</h2><p className="mt-1 text-xs text-[var(--text-secondary)]">Reported observations are separate from live provider pricing.</p></div><button onClick={() => void loadReports()} className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]" title="Refresh reports"><RefreshCw size={16} /></button></div>
        {loadingReports ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">Loading reports...</p> : reports.length === 0 ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">No community reports yet.</p> : <div className="mt-5 grid gap-3">{reports.map((report) => <article key={report.id} className="rounded-xl border border-[var(--border-color)] p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">{report.provider} · {report.vehicleCategory}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{report.pickupLocation} → {report.destinationLocation}</p></div><span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${statusStyles[report.status] || statusStyles.COMMUNITY_REPORTED}`}>{report.status.replaceAll('_', ' ')}</span></div><div className="mt-3 flex flex-wrap items-center gap-4 text-sm"><strong>₹{report.submittedFare}</strong><span className="text-xs text-[var(--text-secondary)]">{report.evidenceCount} supporting observations · {Math.round(report.confidenceScore * 100)}% confidence</span>{report.hasScreenshot && <span className="flex items-center gap-1 text-xs text-blue-400"><FileImage size={13} /> evidence attached</span>}</div><p className="mt-2 text-xs leading-relaxed text-[var(--text-secondary)]">{report.explanation}</p><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => void vote(report.id, 'CONFIRM')} className="flex items-center gap-1 rounded-lg border border-emerald-500/30 px-2 py-1 text-[10px] text-emerald-400"><CheckCircle2 size={12} /> Confirm ({report.votes?.CONFIRM || 0})</button><button onClick={() => void vote(report.id, 'MISMATCH')} className="flex items-center gap-1 rounded-lg border border-amber-500/30 px-2 py-1 text-[10px] text-amber-300"><Flag size={12} /> Price does not match ({report.votes?.MISMATCH || 0})</button><button onClick={() => void vote(report.id, 'SUSPICIOUS')} className="rounded-lg border border-red-500/30 px-2 py-1 text-[10px] text-red-400">Report suspicious</button></div></article>)}</div>}
      </div>
        </>
      )}
    </div>
  );
}
