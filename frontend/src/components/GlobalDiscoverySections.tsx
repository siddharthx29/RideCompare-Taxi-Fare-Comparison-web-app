import React, { useState } from 'react';
import { Globe2, ShieldCheck, ExternalLink, MapPin, HelpCircle, CheckCircle2, ArrowRight } from 'lucide-react';
import { GLOBAL_OPERATORS, POPULAR_GLOBAL_DESTINATIONS, FAQ_ITEMS } from '../data/globalOperators';

interface GlobalDiscoverySectionsProps {
  onSelectDestinationCity: (city: string, coords: [number, number]) => void;
  onNavigatePath: (path: string) => void;
}

const REGIONS = ['All', 'India', 'United States', 'United Kingdom', 'Europe', 'Middle East', 'Southeast Asia', 'Japan', 'Australia', 'Africa', 'South America'] as const;

export const GlobalDiscoverySections: React.FC<GlobalDiscoverySectionsProps> = ({
  onSelectDestinationCity,
  onNavigatePath,
}) => {
  const [selectedRegion, setSelectedRegion] = useState<string>('All');
  const [operatorQuery, setOperatorQuery] = useState('');

  const filteredOperators = GLOBAL_OPERATORS.filter((op) => {
    const regionOk = selectedRegion === 'All' || op.region === selectedRegion;
    const q = operatorQuery.trim().toLowerCase();
    const queryOk =
      !q ||
      op.name.toLowerCase().includes(q) ||
      op.country.toLowerCase().includes(q) ||
      op.cities.some((c) => c.toLowerCase().includes(q));
    return regionOk && queryOk;
  });

  return (
    <div className="space-y-12 mt-12">
      {/* Popular Global Destinations */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--accent-color)]">
              Global Coverage
            </span>
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">Popular Destinations</h2>
          </div>
          <button
            type="button"
            onClick={() => onNavigatePath('/routes')}
            className="text-xs font-semibold text-[var(--accent-color)] hover:underline inline-flex items-center gap-1 cursor-pointer"
          >
            View all corridors <ArrowRight size={13} />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {POPULAR_GLOBAL_DESTINATIONS.map((dest) => (
            <div
              key={dest.city}
              className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-4 flex flex-col justify-between gap-3 hover:border-[var(--accent-color)]/60 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    <MapPin size={14} className="text-[var(--accent-color)]" />
                    {dest.city}, {dest.country}
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] mt-1">{dest.route}</p>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => onSelectDestinationCity(dest.city, dest.coords)}
                  className="px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px] font-semibold text-[var(--text-primary)] hover:border-[var(--accent-color)] cursor-pointer"
                >
                  Focus Map
                </button>
                <button
                  type="button"
                  onClick={() => onNavigatePath(dest.path)}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-[var(--accent-color)] hover:underline cursor-pointer"
                >
                  City Guide
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Authorised Operator Verification Directory */}
      <section className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-[var(--accent-color)]">
              <ShieldCheck size={13} /> Authorised Operator Verification
            </span>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] mt-1">
              Global Taxi Provider Directory
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Operators are listed strictly by actual geographic coverage and public transport licence status.
            </p>
          </div>
          <input
            type="text"
            value={operatorQuery}
            onChange={(e) => setOperatorQuery(e.target.value)}
            placeholder="Filter by city, country, or operator..."
            className="w-full md:w-72 px-3.5 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-color)]"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {REGIONS.map((reg) => (
            <button
              key={reg}
              type="button"
              onClick={() => setSelectedRegion(reg)}
              className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
                selectedRegion === reg
                  ? 'bg-[var(--accent-color)] text-[var(--accent-ink)] border-[var(--accent-color)]'
                  : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
              }`}
            >
              {reg}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredOperators.map((op) => (
            <div key={op.id} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">{op.name}</h3>
                  <p className="text-[11px] text-[var(--text-secondary)]">{op.country} · {op.cities.slice(0, 3).join(', ')}</p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${
                  op.verificationStatus === 'Government Registered' || op.verificationStatus === 'Verified Operator'
                    ? 'bg-[var(--accent-color)]/15 text-[var(--accent-color)] border border-[var(--accent-color)]/40'
                    : 'bg-[var(--bg-dashboard)] text-[var(--text-secondary)] border border-[var(--border-color)]'
                }`}>
                  {op.verificationStatus}
                </span>
              </div>
              <p className="text-[11px] text-[var(--text-secondary)]">{op.registrationDetails}</p>
              <p className="text-[11px] text-[var(--text-secondary)]">Licence: {op.licenceInfo}</p>
              <div className="flex items-center justify-between pt-2 border-t border-[var(--border-color)] text-[11px]">
                <span className="text-[var(--text-secondary)]">{op.availabilityMode} · {op.lastVerifiedDate}</span>
                <a
                  href={op.officialWebsite}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-semibold text-[var(--accent-color)] hover:underline"
                >
                  Official Site <ExternalLink size={11} />
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How RideCompare Works & Why Compare */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-6 space-y-4">
          <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Globe2 size={18} className="text-[var(--accent-color)]" />
            How RideCompare Works
          </h2>
          <ol className="space-y-3 text-xs text-[var(--text-secondary)]">
            <li className="flex gap-2.5"><span className="font-bold text-[var(--accent-color)]">01</span><span>Enter your pickup and destination anywhere in supported metro regions or detect GPS automatically.</span></li>
            <li className="flex gap-2.5"><span className="font-bold text-[var(--accent-color)]">02</span><span>Filter by vehicle type, passenger capacity, amenities, and operator verification status.</span></li>
            <li className="flex gap-2.5"><span className="font-bold text-[var(--accent-color)]">03</span><span>Compare transparent fare bands, pickup ETAs, and book directly on official provider platforms.</span></li>
          </ol>
        </div>

        <div className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-6 space-y-4">
          <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
            <CheckCircle2 size={18} className="text-[var(--accent-color)]" />
            Why Compare Rides?
          </h2>
          <ul className="space-y-3 text-xs text-[var(--text-secondary)]">
            <li>• Avoid peak surge spikes by comparing app cabs against regulated metered taxis and autos.</li>
            <li>• Verify whether an operator holds government registration or partner verification before riding.</li>
            <li>• Zero fabricated quotes: live estimates and indicative ranges are always clearly separated.</li>
          </ul>
        </div>
      </section>

      {/* FAQ */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
          <HelpCircle size={18} className="text-[var(--accent-color)]" />
          Frequently Asked Questions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FAQ_ITEMS.map((item) => (
            <div key={item.q} className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-4 space-y-1.5">
              <h3 className="text-sm font-bold text-[var(--text-primary)]">{item.q}</h3>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
