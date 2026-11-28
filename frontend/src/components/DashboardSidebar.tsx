import React from 'react';
import {
  Home, Compass, Navigation, Bookmark, History, Bell, Settings, User,
  Locate, SlidersHorizontal, RotateCcw, Check
} from 'lucide-react';
import type { LocationInfo, RideProviderDetails } from '../types/ride';

export interface DashboardFilters {
  minPrice: number;
  maxPrice: number;
  vehicleTypes: string[];
  passengerCount: number;
  amenities: string[];
  verification: string[];
}

export const DEFAULT_DASHBOARD_FILTERS: DashboardFilters = {
  minPrice: 0,
  maxPrice: 5000,
  vehicleTypes: [],
  passengerCount: 1,
  amenities: [],
  verification: [],
};

interface DashboardSidebarProps {
  activeNav: string;
  onSelectNav: (nav: string) => void;
  sourceLoc: LocationInfo | null;
  destLoc: LocationInfo | null;
  onDetectLocation: () => void;
  filters: DashboardFilters;
  onChangeFilters: (next: DashboardFilters) => void;
  onApplyFilters: () => void;
  onResetFilters: () => void;
  providers: RideProviderDetails[];
}

const NAV_ITEMS = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'compare', label: 'Compare Rides', icon: Compass },
  { id: 'nearby', label: 'Nearby Taxis', icon: Navigation },
  { id: 'favourites', label: 'Favourites', icon: Bookmark },
  { id: 'recent', label: 'Recent Searches', icon: History },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'profile', label: 'Profile', icon: User },
];

const VEHICLE_TYPES = ['Sedan', 'Hatchback', 'SUV', 'Premium', 'Electric vehicle', 'Minivan', 'Motorcycle'];
const AMENITIES = ['Air conditioning', 'Wi-Fi', 'Child seats', 'Luggage space', 'Phone charging', 'Wheelchair accessibility'];
const VERIFICATION_OPTIONS = ['Verified operators only', 'Government-registered operators', 'Partner-verified providers'];

export const DashboardSidebar: React.FC<DashboardSidebarProps> = ({
  activeNav,
  onSelectNav,
  sourceLoc,
  destLoc,
  onDetectLocation,
  filters,
  onChangeFilters,
  onApplyFilters,
  onResetFilters,
  providers,
}) => {
  const toggleItem = (list: string[], item: string): string[] =>
    list.includes(item) ? list.filter((x) => x !== item) : [...list, item];

  // Build 8-bucket price histogram from live providers
  const prices = providers.map((p) => Number(p.low ?? p.fareMin ?? p.estimatedFare ?? 0)).filter((v) => v > 0);
  const minP = prices.length ? Math.min(...prices) : 0;
  const maxP = prices.length ? Math.max(...prices) : 1000;
  const span = Math.max(1, maxP - minP);
  const buckets = Array.from({ length: 8 }, (_, idx) => {
    if (!prices.length) return idx === 2 ? 0.5 : idx === 4 ? 0.8 : 0.25;
    const lo = minP + (span * idx) / 8;
    const hi = minP + (span * (idx + 1)) / 8;
    const count = prices.filter((v) => v >= lo && (idx === 7 ? v <= hi : v < hi)).length;
    return Math.max(0.18, count / Math.max(1, prices.length));
  });

  return (
    <aside className="bg-[var(--bg-dashboard)] border border-[var(--border-color)] rounded-2xl p-4 space-y-5">
      {/* Minimalistic Sidebar Navigation */}
      <div className="space-y-1">
        <p className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          Workspace
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-1 gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeNav === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectNav(item.id)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                  active
                    ? 'bg-[var(--accent-color)] text-[var(--accent-ink)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-card)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Icon size={14} />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="border-t border-[var(--border-color)] pt-4 space-y-4">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[var(--text-primary)]">
            <SlidersHorizontal size={13} className="text-[var(--accent-color)]" />
            Comparison Filters
          </span>
          <button
            type="button"
            onClick={onResetFilters}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
          >
            <RotateCcw size={11} /> Reset
          </button>
        </div>

        {/* Location Summary + Detect */}
        <div className="space-y-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Location</p>
          <p className="text-xs text-[var(--text-primary)] truncate">
            <span className="text-[var(--text-secondary)]">Pickup: </span>
            {sourceLoc?.label || 'Not selected'}
          </p>
          <p className="text-xs text-[var(--text-primary)] truncate">
            <span className="text-[var(--text-secondary)]">Drop: </span>
            {destLoc?.label || 'Not selected'}
          </p>
          <button
            type="button"
            onClick={onDetectLocation}
            className="w-full mt-1 inline-flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-dashboard)] text-[11px] font-semibold text-[var(--text-primary)] hover:border-[var(--accent-color)] cursor-pointer"
          >
            <Locate size={12} className="text-[var(--accent-color)]" />
            Detect my current location
          </button>
        </div>

        {/* Price Range + Interactive Histogram */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-bold text-[var(--text-primary)]">Price Range</span>
            <span className="text-[var(--text-secondary)]">{filters.minPrice} – {filters.maxPrice}</span>
          </div>
          <div className="flex items-end gap-1 h-10 px-1 pt-1 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl">
            {buckets.map((ratio, idx) => (
              <div
                key={idx}
                className="flex-1 rounded-t bg-[var(--accent-color)]/75 transition-all"
                style={{ height: `${Math.round(ratio * 100)}%` }}
              />
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              min={0}
              value={filters.minPrice}
              onChange={(e) => onChangeFilters({ ...filters, minPrice: Math.max(0, Number(e.target.value) || 0) })}
              placeholder="Min"
              className="w-full px-2.5 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-color)]"
            />
            <input
              type="number"
              min={0}
              value={filters.maxPrice}
              onChange={(e) => onChangeFilters({ ...filters, maxPrice: Math.max(0, Number(e.target.value) || 5000) })}
              placeholder="Max"
              className="w-full px-2.5 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-color)]"
            />
          </div>
        </div>

        {/* Vehicle Type */}
        <div className="space-y-2">
          <p className="text-[11px] font-bold text-[var(--text-primary)]">Vehicle Type</p>
          <div className="flex flex-wrap gap-1.5">
            {VEHICLE_TYPES.map((vt) => {
              const selected = filters.vehicleTypes.includes(vt);
              return (
                <button
                  key={vt}
                  type="button"
                  onClick={() => onChangeFilters({ ...filters, vehicleTypes: toggleItem(filters.vehicleTypes, vt) })}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-colors cursor-pointer ${
                    selected
                      ? 'bg-[var(--accent-color)] text-[var(--accent-ink)] border-[var(--accent-color)]'
                      : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  {vt}
                </button>
              );
            })}
          </div>
        </div>

        {/* Passenger Capacity */}
        <div className="space-y-2">
          <p className="text-[11px] font-bold text-[var(--text-primary)]">Passenger Capacity</p>
          <div className="grid grid-cols-6 gap-1">
            {[1, 2, 3, 4, 5, 6].map((cap) => (
              <button
                key={cap}
                type="button"
                onClick={() => onChangeFilters({ ...filters, passengerCount: cap })}
                className={`py-1.5 rounded-lg text-[11px] font-bold border transition-colors cursor-pointer ${
                  filters.passengerCount === cap
                    ? 'bg-[var(--accent-color)] text-[var(--accent-ink)] border-[var(--accent-color)]'
                    : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
                }`}
              >
                {cap === 6 ? '6+' : cap}
              </button>
            ))}
          </div>
        </div>

        {/* Additional Amenities */}
        <div className="space-y-1.5">
          <p className="text-[11px] font-bold text-[var(--text-primary)]">Additional Amenities</p>
          {AMENITIES.map((am) => {
            const checked = filters.amenities.includes(am);
            return (
              <button
                key={am}
                type="button"
                onClick={() => onChangeFilters({ ...filters, amenities: toggleItem(filters.amenities, am) })}
                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px] text-[var(--text-primary)] hover:border-[var(--accent-color)]/50 cursor-pointer"
              >
                <span>{am}</span>
                <span className={`w-4 h-4 rounded flex items-center justify-center border ${
                  checked ? 'bg-[var(--accent-color)] border-[var(--accent-color)] text-[var(--accent-ink)]' : 'border-[var(--border-color)]'
                }`}>
                  {checked && <Check size={11} />}
                </span>
              </button>
            );
          })}
        </div>

        {/* Operator Verification */}
        <div className="space-y-1.5">
          <p className="text-[11px] font-bold text-[var(--text-primary)]">Operator Verification</p>
          {VERIFICATION_OPTIONS.map((opt) => {
            const checked = filters.verification.includes(opt);
            return (
              <button
                key={opt}
                type="button"
                onClick={() => onChangeFilters({ ...filters, verification: toggleItem(filters.verification, opt) })}
                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px] text-[var(--text-primary)] hover:border-[var(--accent-color)]/50 cursor-pointer"
              >
                <span className="truncate pr-2">{opt}</span>
                <span className={`w-4 h-4 rounded flex items-center justify-center border shrink-0 ${
                  checked ? 'bg-[var(--accent-color)] border-[var(--accent-color)] text-[var(--accent-ink)]' : 'border-[var(--border-color)]'
                }`}>
                  {checked && <Check size={11} />}
                </span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onApplyFilters}
          className="w-full py-2.5 rounded-xl bg-[var(--accent-color)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] font-bold text-xs transition-colors cursor-pointer"
        >
          Apply Filters
        </button>
      </div>
    </aside>
  );
};
