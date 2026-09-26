import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Locate, Loader2, AlertCircle, Building2, Plane, Train, GraduationCap, ShoppingBag, X } from 'lucide-react';
import type { LocationInfo } from '../types/ride';
import {
  suggestLocations,
  retrieveLocation,
  generateSessionToken,
  type MapboxSuggestion,
} from '../utils/locationService';

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
  const [suggestions, setSuggestions] = useState<MapboxSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [retrieving, setRetrieving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showOverlay, setShowOverlay] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const activeControllerRef = useRef<AbortController | null>(null);
  const sessionTokenRef = useRef<string>(generateSessionToken());

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

  // Debounced Mapbox Search Box /suggest with AbortController cancellation
  useEffect(() => {
    const trimmed = value.trim();
    if (trimmed.length < 2 || (selectedLocation && value === selectedLocation.label)) {
      return;
    }

    // Cancel any previous in-flight suggest request
    if (activeControllerRef.current) {
      activeControllerRef.current.abort();
    }
    const controller = new AbortController();
    activeControllerRef.current = controller;

    // 300ms debounce
    const timer = setTimeout(async () => {
      setLoading(true);
      setErrorMsg(null);
      setHighlightIdx(-1);

      try {
        const results = await suggestLocations(
          trimmed,
          sessionTokenRef.current,
          nearbyLocation,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setLoading(false);
          setSuggestions(results);
          if (results.length === 0) {
            setErrorMsg('Unable to find this location. Try entering a nearby landmark, street, or city.');
          } else {
            setErrorMsg(null);
          }
        }
      } catch (err: unknown) {
        if (!controller.signal.aborted) {
          setLoading(false);
          setSuggestions([]);
          const errText = err instanceof Error ? err.message : String(err || '');
          if (
            errText.includes('Network Connection Error') ||
            errText.includes('Failed to fetch') ||
            errText.includes('NetworkError')
          ) {
            const isLocal = typeof window !== 'undefined' && 
              (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
            setErrorMsg(
              isLocal
                ? 'Backend server unreachable. Please make sure the FastAPI server is running on port 5000.'
                : 'Backend API unreachable. Please check your connection or disable Vercel Deployment Protection (SSO) in Settings.'
            );
          } else {
            setErrorMsg('Unable to find this location. Try entering a nearby landmark, street, or city.');
          }
        }
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, selectedLocation, nearbyLocation]);

  const handleSelect = async (item: MapboxSuggestion) => {
    const chosenLabel = item.displayName || item.display_name || item.primaryText || item.name || 'Selected Location';

    // If item already contains valid coordinates (e.g. from local/db cache)
    const lat = Number(item.latitude ?? item.lat);
    const lng = Number(item.longitude ?? item.lng ?? item.lon);

    if (Number.isFinite(lat) && Number.isFinite(lng) && (lat !== 0 || lng !== 0)) {
      const loc: LocationInfo = {
        label: chosenLabel,
        lat,
        lng,
        address: item.address,
        placeName: item.primaryText || item.name,
        locality: item.secondaryText,
        city: item.city || item.address?.city || item.address?.town,
        state: item.state || item.address?.state,
        country: item.country || item.address?.country
      };
      onSelectLocation(loc);
      onChangeText(chosenLabel);
      setSuggestions([]);
      setShowOverlay(false);
      setErrorMsg(null);
      if (onClearError) onClearError();
      sessionTokenRef.current = generateSessionToken();
      return;
    }

    // Call Mapbox Search Box /retrieve to resolve exact coordinates & address
    setRetrieving(true);
    setLoading(true);
    try {
      const resolved = await retrieveLocation(item.mapbox_id || '', sessionTokenRef.current);
      if (resolved) {
        onSelectLocation(resolved);
        onChangeText(resolved.label);
        setSuggestions([]);
        setShowOverlay(false);
        setErrorMsg(null);
        if (onClearError) onClearError();
      } else {
        setErrorMsg('Unable to load location details. Please try another selection.');
      }
    } catch {
      setErrorMsg('Unable to load location details. Please try another selection.');
    } finally {
      setRetrieving(false);
      setLoading(false);
      // Session finished: generate new session token for subsequent search
      sessionTokenRef.current = generateSessionToken();
    }
  };

  const handleClear = () => {
    if (activeControllerRef.current) {
      activeControllerRef.current.abort();
    }
    onChangeText('');
    onSelectLocation(null);
    setSuggestions([]);
    setShowOverlay(false);
    setErrorMsg(null);
    if (onClearError) onClearError();
    sessionTokenRef.current = generateSessionToken();
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

  // Icon helper based on category/feature type
  const getPlaceIcon = (item: MapboxSuggestion) => {
    const cat = `${item.category || ''} ${item.feature_type || ''} ${item.name || ''}`.toLowerCase();
    if (cat.includes('airport') || cat.includes('aerodrome')) return <Plane size={14} className="mt-0.5 text-sky-500 shrink-0" />;
    if (cat.includes('railway') || cat.includes('station') || cat.includes('metro') || cat.includes('train')) return <Train size={14} className="mt-0.5 text-amber-500 shrink-0" />;
    if (cat.includes('mall') || cat.includes('shopping') || cat.includes('commercial') || cat.includes('shop')) return <ShoppingBag size={14} className="mt-0.5 text-pink-500 shrink-0" />;
    if (cat.includes('university') || cat.includes('college') || cat.includes('school') || cat.includes('education')) return <GraduationCap size={14} className="mt-0.5 text-emerald-500 shrink-0" />;
    if (cat.includes('hospital') || cat.includes('hotel') || cat.includes('building')) return <Building2 size={14} className="mt-0.5 text-indigo-500 shrink-0" />;
    return <MapPin size={14} className="mt-0.5 text-indigo-500 shrink-0" />;
  };

  const activeError = inputError || errorMsg;
  const isBusy = loading || retrieving;

  return (
    <div className="relative" ref={containerRef}>
      <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
        {label}
      </label>
      <div className="relative flex items-center">
        <span className="absolute left-3.5 text-indigo-500 pointer-events-none">
          {isBusy ? <Loader2 size={16} className="animate-spin text-indigo-600" /> : <MapPin size={18} />}
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
          className="w-full pl-10 pr-20 py-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-[var(--text-primary)] placeholder-slate-400 dark:placeholder-slate-500 font-medium transition-all"
          required={required}
          autoComplete="off"
        />

        {/* Action buttons (Clear and Locate) */}
        <div className="absolute right-2 flex items-center gap-1">
          {value.trim().length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              title="Clear input"
            >
              <X size={15} />
            </button>
          )}

          {showLocateButton && (
            <button
              type="button"
              onClick={onLocate}
              disabled={isLocating}
              className="p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition-colors cursor-pointer"
              title="Detect Current Location"
            >
              {isLocating ? <Loader2 size={16} className="animate-spin text-indigo-600" /> : <Locate size={16} />}
            </button>
          )}
        </div>
      </div>

      {showOverlay && (suggestions.length > 0 || isBusy || activeError) && (
        <ul className="absolute left-0 right-0 z-50 mt-1 max-h-56 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg divide-y divide-[var(--border-color)]">
          {isBusy && suggestions.length === 0 && (
            <li className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-2">
              <Loader2 size={14} className="animate-spin text-indigo-500" />
              <span>{retrieving ? 'Retrieving location details...' : 'Searching places & addresses...'}</span>
            </li>
          )}

          {activeError && !isBusy && suggestions.length === 0 && (
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
                key={item.mapbox_id || idx}
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
