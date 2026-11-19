import { useMemo, useState } from 'react';
import { Filter, Bolt, Hexagon, RefreshCw, MapPin } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { FareQuote, LatLng } from '../types/fare';
import { MockFareProvider } from '../services/MockFareProvider';
import { buildSurgeTimeline } from '../services/surgeTimeline';
import { loadSnapshots, saveSnapshot } from '../services/snapshotStore';

const CITY_COORDINATES: Record<string, LatLng> = {
  Bengaluru: { lat: 12.9716, lng: 77.5946 }, Bangalore: { lat: 12.9716, lng: 77.5946 },
  Delhi: { lat: 28.6139, lng: 77.2090 }, Mumbai: { lat: 19.0760, lng: 72.8777 },
  Kolkata: { lat: 22.5726, lng: 88.3639 }, Kochi: { lat: 9.9312, lng: 76.2673 },
  Chennai: { lat: 13.0827, lng: 80.2707 }, Pune: { lat: 18.5204, lng: 73.8567 },
  Hyderabad: { lat: 17.3850, lng: 78.4867 }, 'New York': { lat: 40.7128, lng: -74.0060 },
  'San Francisco': { lat: 37.7749, lng: -122.4194 }, London: { lat: 51.5074, lng: -0.1278 },
  Paris: { lat: 48.8566, lng: 2.3522 }, Berlin: { lat: 52.5200, lng: 13.4050 },
  Dubai: { lat: 25.2048, lng: 55.2708 }, Singapore: { lat: 1.3521, lng: 103.8198 },
  Tokyo: { lat: 35.6762, lng: 139.6503 }, Sydney: { lat: -33.8688, lng: 151.2093 },
  'São Paulo': { lat: -23.5505, lng: -46.6333 }, Toronto: { lat: 43.6532, lng: -79.3832 },
};

function geocodePlaceholder(text: string): LatLng {
  const match = Object.entries(CITY_COORDINATES).find(([city]) => text.toLowerCase().includes(city.toLowerCase()));
  if (match) return match[1];
  const hash = [...text].reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return { lat: 8 + (hash % 2200) / 100, lng: 72 + (hash % 1700) / 100 };
}

const provider = new MockFareProvider();

export function FareSurgeTracker() {
  const [pickupText, setPickupText] = useState('Bengaluru');
  const [dropText, setDropText] = useState('Indiranagar');
  const [quotes, setQuotes] = useState<FareQuote[]>([]);
  const [timeline, setTimeline] = useState<Array<{ time: string; multiplier: number; fare: number }>>([]);
  const [rideType, setRideType] = useState('Bike');
  const [loading, setLoading] = useState(false);
  const [savings, setSavings] = useState(0);
  const [snapshots, setSnapshots] = useState(() => loadSnapshots());

  const cheapest = useMemo(() => [...quotes].sort((a, b) => a.finalFare - b.finalFare)[0], [quotes]);
  const symbol = cheapest?.currencySymbol || '₹';

  const refresh = async () => {
    setLoading(true);
    const pickup = geocodePlaceholder(pickupText);
    const drop = geocodePlaceholder(dropText);
    const now = new Date();
    const estimates = await provider.getFareEstimate(pickup, drop, now);
    estimates.sort((a, b) => a.finalFare - b.finalFare);
    setQuotes(estimates);
    setTimeline(await buildSurgeTimeline(provider, pickup, drop, rideType, now));
    const later = await provider.getFareEstimate(pickup, drop, new Date(now.getTime() + 30 * 60 * 1000));
    const laterCheapest = [...later].sort((a, b) => a.finalFare - b.finalFare)[0];
    setSavings(Math.max(0, Math.round((estimates[0]?.finalFare || 0) - (laterCheapest?.finalFare || 0))));
    setSnapshots(saveSnapshot({
      pickupLabel: pickupText,
      dropLabel: dropText,
      routeKey: `${pickupText.trim().toLowerCase()}→${dropText.trim().toLowerCase()}`,
      quotes: estimates,
      capturedAt: now.toISOString(),
    }));
    setLoading(false);
  };

  const changeRideType = async (nextRideType: string) => {
    setRideType(nextRideType);
    if (!quotes.length) return;
    setTimeline(await buildSurgeTimeline(
      provider,
      geocodePlaceholder(pickupText),
      geocodePlaceholder(dropText),
      nextRideType,
      new Date()
    ));
  };

  return (
    <div className="min-h-[calc(100vh-64px)] pt-16 bg-[#111414] text-[#e1e3e2]">
      <div className="border-b border-[#303738] bg-[#191c1c] px-4 py-3 md:px-8">
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 animate-pulse rounded-full bg-[#5adda4]" />
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Surge &amp; Arbitrage Intelligence</h1>
              <p className="text-xs text-[#b8aaa2]">Simulated route telemetry and fare comparison. No live provider claims.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-lg bg-[#1d2020] p-1 text-[10px] font-bold uppercase tracking-wider">
              <button className="rounded px-3 py-2 text-[#ffb68e]">Live Session</button>
              <button className="px-3 py-2 text-[#b8aaa2]">24h Hist</button>
            </div>
            <button className="flex items-center gap-2 rounded-lg bg-[#1d2020] px-3 py-2 text-xs hover:bg-[#282a2a]">
              <Filter size={15} className="text-[#ffb68e]" /> Filter corridor
            </button>
            <button onClick={refresh} className="flex items-center gap-2 rounded-lg bg-[#e86d10] px-3 py-2 text-xs font-bold text-[#491c00]">
              <Bolt size={15} /> Run estimates
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 px-4 py-6 lg:grid-cols-12 md:px-8">
        <div className="flex flex-col gap-5 lg:col-span-7">
          <section className="rounded-xl border border-[#303738] bg-[#191c1c] p-4">
            <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto] md:items-end">
              <label className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#b8aaa2]">
                Pickup
                <div className="mt-2 flex items-center gap-2 rounded-lg border border-[#303738] bg-[#111414] px-3">
                  <MapPin size={14} className="text-[#5adda4]" />
                  <input value={pickupText} onChange={event => setPickupText(event.target.value)} className="h-11 w-full bg-transparent text-sm normal-case tracking-normal text-[#e1e3e2] outline-none" />
                </div>
              </label>
              <label className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#b8aaa2]">
                Destination
                <div className="mt-2 flex items-center gap-2 rounded-lg border border-[#303738] bg-[#111414] px-3">
                  <MapPin size={14} className="text-[#ffb68e]" />
                  <input value={dropText} onChange={event => setDropText(event.target.value)} className="h-11 w-full bg-transparent text-sm normal-case tracking-normal text-[#e1e3e2] outline-none" />
                </div>
              </label>
              <button onClick={refresh} disabled={loading} className="h-11 rounded-lg bg-[#ffb68e] px-5 text-xs font-bold text-[#542200] disabled:opacity-60">
                {loading ? 'Calculating...' : 'Get estimates'}
              </button>
            </div>
          </section>

          <section className="relative h-[420px] overflow-hidden rounded-xl border border-[#303738] bg-[#191c1c]">
            <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(223,192,177,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(223,192,177,.08)_1px,transparent_1px)] [background-size:32px_32px]" />
            <div className="absolute left-4 right-4 top-4 z-10 flex items-center justify-between rounded-lg border border-[#303738] bg-[#111414]/90 p-3 backdrop-blur-md">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider">
                <Hexagon size={17} className="text-[#ffb68e]" /> Hex-cell simulation matrix
              </div>
              <div className="hidden gap-2 sm:flex">
                <span className="rounded-full bg-[#24b47e]/15 px-2 py-1 text-[9px] font-bold text-[#5adda4]">1.0–1.2 Normal</span>
                <span className="rounded-full bg-[#e86d10]/15 px-2 py-1 text-[9px] font-bold text-[#ffb68e]">1.8–2.0 Surge</span>
              </div>
            </div>
            <div className="absolute inset-0 z-10 flex items-center justify-center">
              <div className="absolute left-[18%] top-[42%] rounded-lg border border-[#303738] bg-[#111414]/95 p-3 shadow-2xl">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#ffb68e]">Pickup corridor</span>
                <div className="mt-1 font-mono text-lg font-bold">{cheapest ? `${cheapest.surgeMultiplier.toFixed(2)}x` : '1.00x'}</div>
              </div>
              <div className="absolute right-[12%] top-[58%] rounded-lg border border-[#303738] bg-[#111414]/95 p-3 shadow-2xl">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#5adda4]">Drop corridor</span>
                <div className="mt-1 font-mono text-lg font-bold">Stable</div>
              </div>
              <div className="h-48 w-48 rounded-full border border-[#ffb68e]/20 bg-[#e86d10]/10 shadow-[0_0_80px_rgba(232,109,16,.12)]" />
            </div>
            <div className="absolute bottom-4 left-4 right-4 z-10 flex justify-between rounded-lg border border-[#303738] bg-[#111414]/90 p-3 text-xs text-[#b8aaa2]">
              <span>Simulated nodes: <strong className="text-[#e1e3e2]">1,420 hex grids</strong></span>
              <span className="hidden sm:inline">{snapshots.length} local snapshots</span>
            </div>
          </section>

          <section className="rounded-xl border border-[#303738] bg-[#191c1c] p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Surge Timeline</h2>
                <p className="text-xs text-[#b8aaa2]">Last 24 simulated hours</p>
              </div>
              <select value={rideType} onChange={event => void changeRideType(event.target.value)} className="rounded-lg border border-[#303738] bg-[#1d2020] px-3 py-2 text-xs text-[#e1e3e2]">
                {quotes.map(quote => <option key={quote.rideType}>{quote.rideType}</option>)}
                {!quotes.length && <option>Bike</option>}
              </select>
            </div>
            <div className="h-56">
              {timeline.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={timeline} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                    <CartesianGrid stroke="#303738" strokeDasharray="3 3" />
                    <XAxis dataKey="time" tick={{ fill: '#b8aaa2', fontSize: 10 }} interval={4} />
                    <YAxis domain={[1, 2]} tick={{ fill: '#b8aaa2', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#1d2020', border: '1px solid #303738', borderRadius: 8 }} />
                    <Line type="monotone" dataKey="multiplier" stroke="#ffb68e" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-[#303738] text-xs text-[#b8aaa2]">
                  Run estimates to generate a timeline
                </div>
              )}
            </div>
          </section>
        </div>

        <aside className="flex flex-col gap-5 lg:col-span-5">
          <section className="rounded-xl border border-[#303738] bg-[#191c1c] p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Top Corridors</h2>
                <p className="text-xs text-[#b8aaa2]">{pickupText || 'Pickup'} to {dropText || 'Destination'}</p>
              </div>
              <span className="rounded-full bg-[#1d2020] px-2 py-1 text-[9px] font-bold uppercase text-[#ffb68e]">Route estimate</span>
            </div>
            <div className="flex flex-col gap-2">
              {quotes.length ? quotes.map((quote, index) => (
                <div key={`${quote.provider}-${quote.rideType}`} className={`flex items-center justify-between rounded-lg border p-3 ${index === 0 ? 'border-[#e86d10]/50 bg-[#282a2a]' : 'border-transparent bg-[#1d2020]'}`}>
                  <div className="flex items-center gap-3">
                    <div className={`flex h-7 w-7 items-center justify-center rounded text-[10px] font-bold ${index === 0 ? 'bg-[#e86d10] text-[#491c00]' : 'bg-[#323535] text-[#e1e3e2]'}`}>
                      {quote.provider.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{quote.provider} {quote.rideType}</div>
                      <div className="text-xs text-[#b8aaa2]">ETA {quote.etaMinutes} min • simulated</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-mono text-sm font-bold ${index === 0 ? 'text-[#5adda4]' : ''}`}>{quote.currencySymbol || symbol}{quote.finalFare}</div>
                    <div className="text-[9px] font-bold uppercase text-[#ffb68e]">{quote.surgeMultiplier.toFixed(2)}x simulated</div>
                  </div>
                </div>
              )) : (
                <div className="rounded-lg border border-dashed border-[#303738] p-8 text-center text-xs text-[#b8aaa2]">
                  Run estimates to populate the provider matrix
                </div>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-[#303738] bg-[#191c1c] p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Surge Index Telemetry</h2>
              <span className="text-[9px] font-bold uppercase tracking-wider text-[#b8aaa2]">Simulated confidence</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-[#1d2020] p-3">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#b8aaa2]">Wait 30 min</span>
                <div className="mt-1 font-mono text-xl font-bold text-[#5adda4]">{savings > 0 ? `-${symbol}${savings}` : 'No saving'}</div>
                <span className="text-xs text-[#b8aaa2]">Projected only</span>
              </div>
              <div className="rounded-lg bg-[#1d2020] p-3">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#b8aaa2]">Peak multiplier</span>
                <div className="mt-1 font-mono text-xl font-bold text-[#ffb68e]">{cheapest ? `${cheapest.surgeMultiplier.toFixed(2)}x` : '—'}</div>
                <span className="text-xs text-[#b8aaa2]">Simulation</span>
              </div>
            </div>
            <button onClick={refresh} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#ffb68e] py-3 text-sm font-bold text-[#542200]">
              <RefreshCw size={15} /> Refresh simulated fares
            </button>
          </section>

          <div className="rounded-xl border border-[#303738] bg-[#191c1c] px-4 py-3 text-[10px] text-[#b8aaa2]">
            Estimates are simulated and not affiliated with any ride-hailing company.
          </div>
        </aside>
      </div>
    </div>
  );
}
