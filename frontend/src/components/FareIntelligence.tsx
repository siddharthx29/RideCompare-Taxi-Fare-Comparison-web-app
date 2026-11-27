import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, FileImage, Flag, RefreshCw, ShieldAlert } from 'lucide-react';
import { apiFetch } from '../utils/api';
import { LocationAutocompleteInput } from './LocationAutocompleteInput';
import { MapView } from './MapView';
import type { MapSelectionMode } from './MapView';
import type { LocationInfo } from '../types/ride';
import { reverseGeocodeLocation } from '../utils/locationService';

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

const PROVIDER_CATEGORIES: Record<string, string[]> = {
  Uber: ['UberX', 'Uber Go', 'Uber Moto', 'Uber Auto', 'Uber Premier', 'Uber Black', 'Uber XL', 'Uber Electric', 'Uber Intercity'],
  Ola: ['Mini', 'Prime Sedan', 'Prime SUV', 'Prime Play', 'Auto', 'Bike', 'Electric', 'Outstation'],
  Rapido: ['Bike', 'Auto', 'Cab', 'Cab XL'],
  Lyft: ['Standard', 'Lyft XL', 'Lyft Black', 'Lyft Lux', 'Lyft Electric'],
  Bolt: ['Bolt', 'Bolt XL', 'Bolt Green', 'Bolt Business', 'Bolt Electric'],
  Grab: ['JustGrab', 'GrabCar', 'GrabTaxi', 'GrabBike', 'GrabCar Premium', 'GrabFamily'],
  FreeNow: ['Taxi', 'Car', 'XL', 'Electric', 'Accessible'],
  'Black Cab': ['Standard Hackney Cab', 'Accessible Cab', 'Electric Black Cab'],
  Waymo: ['Standard Robotaxi', 'Waymo One'],
  Careem: ['Hala Taxi', 'Economy', 'Comfort', 'Comfort XL', 'Max', 'Bike'],
  'Dubai Taxi': ['Standard Taxi', 'Family Taxi', 'Ladies Taxi', 'Airport Taxi', 'Limousine'],
  'CDG Zig': ['Standard Taxi', 'Comfort', 'MaxiCab', 'Limousine'],
  'GO Taxi': ['Standard Taxi', 'Nihon Kotsu', 'Taxi XL'],
  Kakao: ['Blue', 'Venti', 'Black', 'Mobility'],
  'Xanh SM': ['Standard EV', 'Premium EV', '7-Seater EV'],
  G7: ['G7 Taxi', 'G7 Access', 'G7 Green', 'G7 XL'],
  'Curb Taxi': ['Yellow Cab', 'Accessible Taxi', 'Airport Taxi'],
  DiDi: ['Express', 'Premium', 'Taxi', 'SUV', 'Electric', 'Bike'],
  'inDrive': ['Economy', 'Comfort', 'XL', 'Taxi', 'Bike'],
  'Yandex Go': ['Economy', 'Comfort', 'Comfort+', 'Business', 'Minivan', 'Taxi', 'EV'],
  Maxim: ['Economy', 'Comfort', 'Business', 'Taxi', 'Delivery'],
  Gett: ['Taxi', 'Executive', 'XL', 'Accessible'],
  CMT: ['Taxi', 'Black Cab', 'Accessible Taxi'],
  'Addison Lee': ['Standard', 'Executive', 'XL', 'Accessible'],
  'Regulated Local Taxi': ['Sedan', 'Hatchback', 'SUV', 'Auto', 'Bike', 'Taxi', 'Airport Taxi'],
  Other: ['Standard Cab', 'Hatchback', 'Sedan', 'SUV', 'Auto', 'Bike', 'Electric', 'Minivan', 'Accessible', 'Taxi', 'Airport Transfer', 'Outstation'],
};

const PROVIDER_OPTIONS = Object.keys(PROVIDER_CATEGORIES);
const CURRENCY_OPTIONS = [
  ['INR', '₹ - INR'], ['USD', '$ - USD'], ['EUR', '€ - EUR'], ['GBP', '£ - GBP'],
  ['AED', 'AED'], ['SGD', 'SGD'], ['JPY', '¥ - JPY'], ['AUD', 'A$ - AUD'],
  ['CAD', 'C$ - CAD'], ['NZD', 'NZ$ - NZD'], ['CHF', 'CHF'], ['CNY', '¥ - CNY'],
  ['KRW', '₩ - KRW'], ['HKD', 'HK$ - HKD'], ['THB', '฿ - THB'], ['MYR', 'RM - MYR'],
  ['IDR', 'Rp - IDR'], ['PHP', '₱ - PHP'], ['VND', '₫ - VND'], ['ZAR', 'R - ZAR'],
  ['BRL', 'R$ - BRL'], ['MXN', 'MX$ - MXN'], ['ARS', '$ - ARS'], ['TRY', '₺ - TRY'],
];

function currencySymbol(currency: string): string {
  return ({ INR: '₹', USD: '$', EUR: '€', GBP: '£', JPY: '¥', CNY: '¥', KRW: '₩', SGD: 'S$', AED: 'AED ', THB: '฿', MYR: 'RM ', PHP: '₱', VND: '₫', ZAR: 'R', BRL: 'R$', MXN: 'MX$', ARS: '$', TRY: '₺' } as Record<string, string>)[currency] || currency;
}

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
  const [pickupLocation, setPickupLocation] = useState<LocationInfo | null>(null);
  const [destinationLocation, setDestinationLocation] = useState<LocationInfo | null>(null);
  const [mapSelectionMode, setMapSelectionMode] = useState<MapSelectionMode>(null);
  const [form, setForm] = useState({
    provider: 'Uber',
    currency: 'INR',
    pickupLocation: '',
    destinationLocation: '',
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

  const updateProvider = (provider: string) => {
    const firstCategory = PROVIDER_CATEGORIES[provider]?.[0] || 'Standard Cab';
    setForm((current) => ({ ...current, provider, vehicleCategory: firstCategory }));
  };

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

  const handleMapLocationSelect = async (
    mode: Exclude<MapSelectionMode, null>,
    coordinates: [number, number]
  ) => {
    const [lat, lng] = coordinates;
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
    const reversed = await reverseGeocodeLocation(lat, lng);
    const location: LocationInfo = reversed || {
      label: `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
      lat,
      lng,
    };
    if (mode === 'pickup') {
      setPickupLocation(location);
      setForm((current) => ({ ...current, pickupLocation: location.label }));
    } else {
      setDestinationLocation(location);
      setForm((current) => ({ ...current, destinationLocation: location.label }));
    }
    setMapSelectionMode(null);
  };

  const useCurrentLocation = (mode: Exclude<MapSelectionMode, null>) => {
    if (!navigator.geolocation) {
      setMessage('Current-location access is not supported by this browser.');
      return;
    }
    setMapSelectionMode(mode);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        await handleMapLocationSelect(mode, [position.coords.latitude, position.coords.longitude]);
      },
      () => {
        setMapSelectionMode(null);
        setMessage('Location access was unavailable. Search for a place or select a map pin.');
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!pickupLocation || !destinationLocation) {
      setMessage('Select both the pickup and destination using location search or the map.');
      return;
    }
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
          pickupCoordinates: [pickupLocation.lat, pickupLocation.lng],
          destinationCoordinates: [destinationLocation.lat, destinationLocation.lng],
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
      setPickupLocation(null);
      setDestinationLocation(null);
      setForm((current) => ({ ...current, pickupLocation: '', destinationLocation: '' }));
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

  const inputClass = 'w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-color)]';
  const labelClass = 'flex flex-col gap-1.5 text-xs font-semibold text-[var(--text-secondary)]';

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Fare Intelligence</h1>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Contribute observations, review evidence, and understand price confidence.</p>
        </div>
        <div className="flex rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-1">
          <button onClick={() => setActiveTab('submit')} className={`rounded-lg px-3 py-2 text-xs font-bold ${activeTab === 'submit' ? 'bg-[var(--accent-color)] text-black' : 'text-[var(--text-secondary)]'}`}>Submit & Reports</button>
          <button onClick={() => { setActiveTab('history'); void loadMySubmissions(); }} className={`rounded-lg px-3 py-2 text-xs font-bold ${activeTab === 'history' ? 'bg-[var(--accent-color)] text-black' : 'text-[var(--text-secondary)]'}`}>Recent Reports</button>
        </div>
      </div>
      {activeTab === 'history' ? (
        <div className="glass-panel rounded-2xl p-5 md:p-7">
          <h2 className="text-xl font-bold">Recent Fare Reports</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Reports contributed from this device are shown here. No account or login is required.</p>
          {loadingHistory ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">Loading recent reports...</p> : mySubmissions.length === 0 ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">No fare reports have been submitted from this device.</p> : <div className="mt-5 grid gap-3">{mySubmissions.map((report) => <article key={report.id} className="rounded-xl border border-[var(--border-color)] p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">{report.provider} · {currencySymbol(report.currency)}{report.submittedFare}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{report.pickupLocation} → {report.destinationLocation}</p><p className="mt-1 text-[10px] text-[var(--text-secondary)]">{new Date(report.createdAt || report.quotationTimestamp).toLocaleString()}</p></div><span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${statusStyles[report.status] || statusStyles.COMMUNITY_REPORTED}`}>{report.status.replaceAll('_', ' ')}</span></div><p className="mt-3 text-xs text-[var(--text-secondary)]">{Math.round(report.confidenceScore * 100)}% confidence · {report.explanation}</p><button onClick={() => void removeSubmission(report.id)} className="mt-3 rounded-lg border border-red-500/30 px-2 py-1 text-[10px] text-red-400">Remove report</button></article>)}</div>}
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
          <LocationAutocompleteInput
            label="Pickup location"
            placeholder="Search pickup area, landmark or address"
            value={form.pickupLocation}
            onChangeText={(text) => update('pickupLocation', text)}
            selectedLocation={pickupLocation}
            onSelectLocation={(location) => setPickupLocation(location)}
            nearbyLocation={destinationLocation}
            showLocateButton
            onLocate={() => useCurrentLocation('pickup')}
            isLocating={mapSelectionMode === 'pickup'}
            required
          />
          <LocationAutocompleteInput
            label="Drop-off location"
            placeholder="Search destination area, landmark or address"
            value={form.destinationLocation}
            onChangeText={(text) => update('destinationLocation', text)}
            selectedLocation={destinationLocation}
            onSelectLocation={(location) => setDestinationLocation(location)}
            nearbyLocation={pickupLocation}
            showLocateButton
            onLocate={() => useCurrentLocation('destination')}
            isLocating={mapSelectionMode === 'destination'}
            required
          />
          <div className="md:col-span-2 h-[300px] overflow-hidden rounded-xl border border-[var(--border-color)]">
            <MapView
              sourceCoords={pickupLocation ? [pickupLocation.lat, pickupLocation.lng] : null}
              destCoords={destinationLocation ? [destinationLocation.lat, destinationLocation.lng] : null}
              routeGeometry={null}
              selectionMode={mapSelectionMode}
              onSelectionModeChange={setMapSelectionMode}
              onMapLocationSelect={handleMapLocationSelect}
            />
          </div>
          <label className={labelClass}>
            <span>Taxi platform</span>
            <select
              className={inputClass}
              value={form.provider}
              onChange={(event) => updateProvider(event.target.value)}
            >
              {PROVIDER_OPTIONS.map((provider) => <option key={provider} value={provider}>{provider}</option>)}
            </select>
          </label>
          <label className={labelClass}>
            <span>Vehicle category</span>
            <select
              required
              className={inputClass}
              value={form.vehicleCategory}
              onChange={(event) => update('vehicleCategory', event.target.value)}
            >
              {(PROVIDER_CATEGORIES[form.provider] || PROVIDER_CATEGORIES.Other).map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </label>
          <label className={labelClass}>
            <span>Currency</span>
            <select className={inputClass} value={form.currency} onChange={(event) => update('currency', event.target.value)}>
              {CURRENCY_OPTIONS.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
          </label>
          <label className={labelClass}>
            <span>Exact fare ({form.currency})</span>
            <input required type="number" min="1" step="0.01" className={inputClass} value={form.submittedFare} onChange={(event) => update('submittedFare', event.target.value)} />
          </label>
          <label className={labelClass}><span>Quotation time</span><input required type="datetime-local" className={inputClass} value={form.quotationTimestamp} onChange={(e) => update('quotationTimestamp', e.target.value)} /></label>
          <label className={labelClass}><span>Distance (km)</span><input required type="number" min="0.1" step="0.1" className={inputClass} value={form.estimatedDistanceKm} onChange={(e) => update('estimatedDistanceKm', e.target.value)} /></label>
          <label className={labelClass}><span>Duration (minutes)</span><input required type="number" min="1" step="1" className={inputClass} value={form.estimatedDurationMin} onChange={(e) => update('estimatedDurationMin', e.target.value)} /></label>
          <label className={labelClass}><span>Surge multiplier (optional)</span><input type="number" min="0" step="0.1" className={inputClass} value={form.surgeMultiplier} onChange={(e) => update('surgeMultiplier', e.target.value)} /></label>
          <label className={labelClass}><span>Additional fees</span><input type="number" min="0" step="1" className={inputClass} value={form.additionalFees} onChange={(e) => update('additionalFees', e.target.value)} /></label>
          <div className={labelClass}>
            <span>Evidence screenshot (optional)</span>
            <label className="flex h-[42px] cursor-pointer items-center gap-2 rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-primary)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--accent-color)]">
              <FileImage size={16} />
              <span className="truncate">{screenshotName || 'Upload screenshot'}</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => void uploadScreenshot(e.target.files?.[0])} />
            </label>
          </div>
          <div className="md:col-span-2 pt-1">
            <button disabled={submitting} className="w-full rounded-xl bg-[var(--accent-color)] px-4 py-3 text-sm font-bold text-black hover:opacity-90 disabled:opacity-50 cursor-pointer">
              {submitting ? 'Submitting...' : 'Submit Fare for Verification'}
            </button>
          </div>
        </form>
        <p className="mt-4 text-[11px] leading-relaxed text-[var(--text-secondary)]">Submitted fares are subject to automated validation and community verification. Unverified submissions will not be displayed as confirmed live prices.</p>
        {message && <p className="mt-3 rounded-xl bg-[var(--bg-primary)] px-3 py-2 text-xs text-[var(--accent-color)]">{message}</p>}
      </div>

      <div className="glass-panel rounded-2xl p-5 md:p-7">
        <div className="flex items-center justify-between"><div><h2 className="text-xl font-bold">Community Fare Reports</h2><p className="mt-1 text-xs text-[var(--text-secondary)]">Reported observations are separate from live provider pricing.</p></div><button onClick={() => void loadReports()} className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]" title="Refresh reports"><RefreshCw size={16} /></button></div>
        {loadingReports ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">Loading reports...</p> : reports.length === 0 ? <p className="py-8 text-center text-sm text-[var(--text-secondary)]">No community reports yet.</p> : <div className="mt-5 grid gap-3">{reports.map((report) => <article key={report.id} className="rounded-xl border border-[var(--border-color)] p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">{report.provider} · {report.vehicleCategory}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{report.pickupLocation} → {report.destinationLocation}</p></div><span className={`rounded-full border px-2 py-1 text-[10px] font-bold ${statusStyles[report.status] || statusStyles.COMMUNITY_REPORTED}`}>{report.status.replaceAll('_', ' ')}</span></div><div className="mt-3 flex flex-wrap items-center gap-4 text-sm"><strong>{currencySymbol(report.currency)}{report.submittedFare}</strong><span className="text-xs text-[var(--text-secondary)]">{report.evidenceCount} supporting observations · {Math.round(report.confidenceScore * 100)}% confidence</span>{report.hasScreenshot && <span className="flex items-center gap-1 text-xs text-blue-400"><FileImage size={13} /> evidence attached</span>}</div><p className="mt-2 text-xs leading-relaxed text-[var(--text-secondary)]">{report.explanation}</p><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => void vote(report.id, 'CONFIRM')} className="flex items-center gap-1 rounded-lg border border-emerald-500/30 px-2 py-1 text-[10px] text-emerald-400"><CheckCircle2 size={12} /> Confirm ({report.votes?.CONFIRM || 0})</button><button onClick={() => void vote(report.id, 'MISMATCH')} className="flex items-center gap-1 rounded-lg border border-amber-500/30 px-2 py-1 text-[10px] text-amber-300"><Flag size={12} /> Price does not match ({report.votes?.MISMATCH || 0})</button><button onClick={() => void vote(report.id, 'SUSPICIOUS')} className="rounded-lg border border-red-500/30 px-2 py-1 text-[10px] text-red-400">Report suspicious</button></div></article>)}</div>}
      </div>
        </>
      )}
    </div>
  );
}
