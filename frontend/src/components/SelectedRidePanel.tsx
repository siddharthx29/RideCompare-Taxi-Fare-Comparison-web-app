import React, { useState } from 'react';
import { Car, ShieldCheck, Clock, MapPin, ArrowUpRight, Info, UserCheck } from 'lucide-react';
import { MapView, type MapSelectionMode } from './MapView';
import type { ComparisonResult, LocationInfo, RideProviderDetails, RouteGeometry } from '../types/ride';

interface SelectedRidePanelProps {
  sourceLoc: LocationInfo | null;
  destLoc: LocationInfo | null;
  mapCenter: [number, number] | null;
  currentLocationCoords: [number, number] | null;
  routeGeometry: RouteGeometry | null;
  mapSelectionMode: MapSelectionMode;
  onMapSelectionModeChange: (mode: MapSelectionMode) => void;
  onMapSelectLocation: (mode: Exclude<MapSelectionMode, null>, coords: [number, number]) => void;
  comparison: ComparisonResult | null;
  selectedRide: RideProviderDetails | null;
  onBookRide: (providerName: string, fare: number, link?: string) => void;
}

export const SelectedRidePanel: React.FC<SelectedRidePanelProps> = ({
  sourceLoc,
  destLoc,
  mapCenter,
  currentLocationCoords,
  routeGeometry,
  mapSelectionMode,
  onMapSelectionModeChange,
  onMapSelectLocation,
  comparison,
  selectedRide,
  onBookRide,
}) => {
  const [activeTab, setActiveTab] = useState<'track' | 'vehicle' | 'specs' | 'provider'>('track');

  const activeSym = comparison?.currencySymbol || selectedRide?.currencySymbol || '₹';
  const liveMin = selectedRide ? (selectedRide.low ?? selectedRide.fareMin ?? selectedRide.estimatedFare) : null;
  const liveMax = selectedRide ? (selectedRide.high ?? selectedRide.fareMax ?? selectedRide.estimatedFare) : null;
  const bookingUrl = selectedRide?.webLink || selectedRide?.appDeepLink;

  return (
    <aside className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-4 space-y-4">
      {/* Top Personalized Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border-color)] pb-3">
        <div className="min-w-0">
          <p className="text-xs font-bold text-[var(--text-primary)]">Welcome back, Traveller</p>
          <p className="text-[11px] text-[var(--text-secondary)] truncate">
            {sourceLoc?.label || 'Detecting current area'} → {destLoc?.label || 'Select destination'}
          </p>
        </div>
        <div className="w-9 h-9 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] flex items-center justify-center text-xs font-bold text-[var(--accent-color)] shrink-0">
          RC
        </div>
      </div>

      {/* Selected Ride Header Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-11 h-11 rounded-xl bg-[var(--bg-dashboard)] border border-[var(--border-color)] flex items-center justify-center shrink-0">
              <Car size={20} className="text-[var(--accent-color)]" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-[var(--text-primary)] truncate">
                {selectedRide?.provider || 'Select a ride option'}
              </p>
              <p className="text-[11px] text-[var(--text-secondary)]">
                {selectedRide ? `${selectedRide.vehicleType} • ${selectedRide.is_verified ? 'Verified Rate Card' : 'Indicative Estimate'}` : 'Compare fares to inspect details'}
              </p>
            </div>
          </div>
          {selectedRide && (
            <div className="text-right shrink-0">
              <p className="text-sm font-extrabold text-[var(--accent-color)]">
                {activeSym}{liveMin}{liveMax && liveMax !== liveMin ? ` – ${activeSym}${liveMax}` : ''}
              </p>
              <p className="text-[10px] text-[var(--text-secondary)]">
                {selectedRide.etaMinutes} min pickup
              </p>
            </div>
          )}
        </div>

        {/* 4 Tabs */}
        <div className="grid grid-cols-4 gap-1 bg-[var(--bg-dashboard)] p-1 rounded-xl border border-[var(--border-color)]">
          {[
            { id: 'track', label: 'Track' },
            { id: 'vehicle', label: 'Vehicle' },
            { id: 'specs', label: 'Specs' },
            { id: 'provider', label: 'Provider' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`py-1.5 rounded-lg text-[11px] font-semibold transition-colors cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-[var(--accent-color)] text-[var(--accent-ink)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'track' && (
          <div className="text-[11px] text-[var(--text-secondary)] flex items-start gap-2 pt-1">
            <Info size={13} className="text-[var(--accent-color)] shrink-0 mt-0.5" />
            <span>
              Real-time vehicle GPS tracking is available only after booking on an authorised provider app. Route distance and ETA below are live-computed.
            </span>
          </div>
        )}

        {activeTab === 'vehicle' && (
          <div className="text-xs space-y-1 pt-1">
            <p className="text-[var(--text-primary)] font-semibold">Category: {selectedRide?.vehicleType || 'Cab'}</p>
            <p className="text-[var(--text-secondary)] text-[11px]">
              Availability: {selectedRide ? (selectedRide.is_verified ? 'Available Now' : 'Estimated Availability') : 'Pending route'}
            </p>
          </div>
        )}

        {activeTab === 'specs' && (
          <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
            <div className="bg-[var(--bg-dashboard)] rounded-lg p-2 border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)] block">Surge Multiplier</span>
              <span className="font-bold text-[var(--text-primary)]">{selectedRide?.surgeMultiplier ?? 1.0}x</span>
            </div>
            <div className="bg-[var(--bg-dashboard)] rounded-lg p-2 border border-[var(--border-color)]">
              <span className="text-[var(--text-secondary)] block">Cost / km</span>
              <span className="font-bold text-[var(--text-primary)]">{activeSym}{selectedRide?.costPerKm ?? 0}/km</span>
            </div>
          </div>
        )}

        {activeTab === 'provider' && (
          <div className="text-[11px] space-y-1 pt-1">
            <p className="text-[var(--text-primary)] font-semibold flex items-center gap-1.5">
              <UserCheck size={13} className="text-[var(--accent-color)]" />
              {selectedRide?.provider || 'Authorised Mobility Partner'}
            </p>
            <p className="text-[var(--text-secondary)]">
              No fabricated driver names or plates are displayed. Official dispatch occurs directly via the provider platform.
            </p>
          </div>
        )}
      </div>

      {/* Interactive Map */}
      <div className="h-[235px] rounded-xl overflow-hidden border border-[var(--border-color)]">
        <MapView
          sourceCoords={sourceLoc ? [sourceLoc.lat, sourceLoc.lng] : null}
          destCoords={destLoc ? [destLoc.lat, destLoc.lng] : null}
          centerCoords={mapCenter}
          currentLocationCoords={currentLocationCoords}
          routeGeometry={routeGeometry}
          selectionMode={mapSelectionMode}
          onSelectionModeChange={onMapSelectionModeChange}
          onMapSelectLocation={onMapSelectLocation}
        />
      </div>

      {/* Bottom 2 Information Cards */}
      <div className="grid grid-cols-1 gap-3">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
            <MapPin size={11} className="text-[var(--accent-color)]" />
            Journey Information
          </p>
          <p className="text-xs text-[var(--text-primary)] truncate">Pickup: {sourceLoc?.label || 'Not set'}</p>
          <p className="text-xs text-[var(--text-primary)] truncate">Drop: {destLoc?.label || 'Not set'}</p>
          <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)] pt-1">
            <span>Distance: {comparison ? `${comparison.distanceKm.toFixed(1)} km` : '—'}</span>
            <span>Duration: {comparison ? `${comparison.durationMins} min` : '—'}</span>
          </div>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
            <ShieldCheck size={11} className="text-[var(--accent-color)]" />
            Booking Information
          </p>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-secondary)]">Provider</span>
            <span className="font-semibold text-[var(--text-primary)]">{selectedRide?.provider || '—'}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-secondary)]">Status</span>
            <span className="font-semibold text-[var(--accent-color)]">
              {selectedRide ? (selectedRide.is_verified ? 'Available Now' : 'Estimated Availability') : '—'}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)]">
            <span className="inline-flex items-center gap-1"><Clock size={11} /> Updated</span>
            <span>{selectedRide?.rate_card_verified_at || 'Live session'}</span>
          </div>
          {selectedRide && bookingUrl && (
            <button
              type="button"
              onClick={() => onBookRide(selectedRide.provider, Number(liveMin ?? 0), bookingUrl)}
              className="w-full mt-2 py-2 rounded-lg bg-[var(--accent-color)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] font-bold text-xs inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <span>Open Official Booking</span>
              <ArrowUpRight size={13} />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};
