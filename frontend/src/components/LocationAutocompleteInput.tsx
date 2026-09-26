import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Locate, Loader2, AlertCircle, Building2, Plane, Train, GraduationCap, ShoppingBag } from 'lucide-react';
import type { LocationInfo } from '../types/ride';
import { searchLocations, type GeocodeResult } from '../utils/locationService';

interface LocationAutocompleteInputProps {
  label: string;
  placeholder: string;
  value: string;
  onChangeText: (text: string) => void;
  selectedLocation: LocationInfo | null;
  onSelectLocation: (loc: LocationInfo | null) => void;
  nearbyLocation?: LocationInfo | null;
  showLocateButton?: boolean;
  onLocate?: () => void;
  isLocating?: boolean;
  inputError?: string | null;
  onClearError?: () => void;
  id?: string;
  required?: boolean;
}

export const LocationAutocompleteInput: React.FC<LocationAutocompleteInputProps> = ({
  label,
  placeholder,
  value,
  onChangeText,
  selectedLocation,
  onSelectLocation,
  nearbyLocation = null,
  showLocateButton = false,
  onLocate,
  isLocating = false,
  inputError = null,
  onClearError,
  id,
  required = true
}) => {
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showOverlay, setShowOverlay] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const activeControllerRef = useRef<AbortController | null>(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setShowOverlay(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search with AbortController cancellation
  useEffect(() => {
    const trimmed = value.trim();
    if (trimmed.length < 2 || (selectedLocation && value === selectedLocation.label)) {
      return;
    }

    // Cancel any previous in-flight request
    if (activeControllerRef.current) {
      activeControllerRef.current.abort();
    }
    const controller = new AbortController();
    activeControllerRef.current = controller;

    // Fast 300ms debounce
    const timer = setTimeout(async () => {
      setLoading(true);
      setErrorMsg(null);
      setHighlightIdx(-1);

      try {
        const results = await searchLocations(trimmed, nearbyLocation, controller.signal);
        if (!controller.signal.aborted) {
          setLoading(false);
          setSuggestions(results);
          if (results.length === 0) {
            setErrorMsg('No places found. Try a nearby landmark, area, or city.');
          } else {
            setErrorMsg(null);
          }
        }
      } catch {
        if (!controller.signal.aborted) {
          setLoading(false);
          setSuggestions([]);
          setErrorMsg('No places found. Try a nearby landmark, area, or city.');
        }
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, selectedLocation, nearbyLocation]);

  const handleSelect = (item: GeocodeResult) => {
    const lat = Number(item.lat);
    const lng = Number(item.lng ?? item.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

    const chosenLabel = item.displayName || item.display_name || item.primaryText || item.name || 'Selected Location';
    const loc: LocationInfo = {
      label: chosenLabel,
      lat,
      lng,
      address: item.address,
      placeName: item.primaryText || item.name,
      locality: item.secondaryText,
      city: item.address?.city || item.address?.town,
      state: item.address?.state,
      country: item.address?.country
    };

    onSelectLocation(loc);
    onChangeText(chosenLabel);
    setSuggestions([]);
    setShowOverlay(false);
    setErrorMsg(null);
    if (onClearError) onClearError();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showOverlay || suggestions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIdx(prev => (prev + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIdx(prev => (prev - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === 'Enter') {
      if (highlightIdx >= 0 && highlightIdx < suggestions.length) {
        e.preventDefault();
        handleSelect(suggestions[highlightIdx]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setShowOverlay(false);
    }
  };

  // Icon helper based on category/type
  const getPlaceIcon = (item: GeocodeResult) => {
    const cat = `${item.category || ''} ${item.name || ''}`.toLowerCase();
    if (cat.includes('airport') || cat.includes('aerodrome')) return <Plane size={14} className="mt-0.5 text-sky-500 shrink-0" />;
    if (cat.includes('railway') || cat.includes('station') || cat.includes('metro')) return <Train size={14} className="mt-0.5 text-amber-500 shrink-0" />;
    if (cat.includes('mall') || cat.includes('shopping') || cat.includes('commercial')) return <ShoppingBag size={14} className="mt-0.5 text-pink-500 shrink-0" />;
    if (cat.includes('university') || cat.includes('college') || cat.includes('school')) return <GraduationCap size={14} className="mt-0.5 text-emerald-500 shrink-0" />;
    if (cat.includes('hospital') || cat.includes('hotel') || cat.includes('building')) return <Building2 size={14} className="mt-0.5 text-indigo-500 shrink-0" />;
    return <MapPin size={14} className="mt-0.5 text-indigo-500 shrink-0" />;
  };

  const activeError = inputError || errorMsg;

  return (
    <div className="relative" ref={containerRef}>
      <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
        {label}
      </label>
      <div className="relative flex items-center">
        <span className="absolute left-3.5 text-indigo-500 pointer-events-none">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <MapPin size={18} />}
        </span>
        <input
          id={id}
          type="text"
          value={value}
          onChange={(e) => {
            const val = e.target.value;
            onChangeText(val);
            setShowOverlay(true);
            if (onClearError) onClearError();
            if (!selectedLocation || val !== selectedLocation.label) {
              onSelectLocation(null);
            }
            if (val.trim().length < 2) {
              setSuggestions([]);
              setErrorMsg(null);
            }
          }}
          onFocus={() => setShowOverlay(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-10 pr-12 py-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-[var(--text-primary)] placeholder-slate-400 dark:placeholder-slate-500 font-medium transition-all"
          required={required}
          autoComplete="off"
        />

        {showLocateButton && (
          <button
            type="button"
            onClick={onLocate}
            disabled={isLocating}
            className="absolute right-3 p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition-colors cursor-pointer"
            title="Detect Current Location"
          >
            {isLocating ? <Loader2 size={16} className="animate-spin text-indigo-600" /> : <Locate size={16} />}
          </button>
        )}
      </div>

      {showOverlay && (suggestions.length > 0 || loading || activeError) && (
        <ul className="absolute left-0 right-0 z-50 mt-1 max-h-56 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg divide-y divide-[var(--border-color)]">
          {loading && suggestions.length === 0 && (
            <li className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-2">
              <Loader2 size={14} className="animate-spin text-indigo-500" />
              <span>Searching places &amp; addresses...</span>
            </li>
          )}

          {activeError && !loading && suggestions.length === 0 && (
            <li className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <AlertCircle size={14} className="text-amber-500 shrink-0" />
              <span>{activeError}</span>
            </li>
          )}

          {suggestions.map((item, idx) => {
            const primary = item.primaryText || item.name || item.displayName || 'Location';
            const secondary = item.secondaryText;
            const isHighlighted = idx === highlightIdx;

            return (
              <li
                key={idx}
                onClick={() => handleSelect(item)}
                className={`px-4 py-2.5 text-xs font-medium cursor-pointer flex gap-2.5 items-start transition-all duration-150 text-[var(--text-primary)] ${
                  isHighlighted
                    ? 'bg-[var(--bg-primary)] border-l-4 border-indigo-500 pl-3 font-semibold'
                    : 'hover:bg-[var(--bg-primary)] border-l-4 border-transparent'
                }`}
              >
                {getPlaceIcon(item)}
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="font-semibold text-[var(--text-primary)] truncate text-xs">
                    {primary}
                  </span>
                  {secondary && (
                    <span className="text-[11px] text-[var(--text-secondary)] truncate">
                      {secondary}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
