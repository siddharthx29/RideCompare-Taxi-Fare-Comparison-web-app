import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Locate, ArrowUpDown, Search, Loader2, AlertCircle } from 'lucide-react';
import { apiFetch } from '../utils/api';

import type { LocationInfo } from '../types/ride';

interface SearchPanelProps {
  selectedSource: LocationInfo | null;
  selectedDest: LocationInfo | null;
  onSourceSelect: (loc: LocationInfo | null) => void;
  onDestSelect: (loc: LocationInfo | null) => void;
  onSearch: (source: LocationInfo, destination: LocationInfo) => void;
  loading: boolean;
}

interface GeocodeResult {
  name?: string;
  displayName?: string;
  display_name?: string;
  lat: string | number;
  lng?: string | number;
  lon?: string | number;
  address?: Record<string, string>;
}

const suggestionCache = new Map<string, GeocodeResult[]>();

const locationContext = (location: LocationInfo | null): string => {
  const address = location?.address || {};
  return [
    address.city || address.town || address.municipality || address.village || address.suburb,
    address.state,
    address.country
  ].filter(Boolean).join(', ');
};

export const SearchPanel: React.FC<SearchPanelProps> = ({
  selectedSource,
  selectedDest,
  onSourceSelect,
  onDestSelect,
  onSearch,
  loading
}) => {
  const [sourceInput, setSourceInput] = useState('');
  const [destInput, setDestInput] = useState('');
  
  const [sourceSuggestions, setSourceSuggestions] = useState<GeocodeResult[]>([]);
  const [destSuggestions, setDestSuggestions] = useState<GeocodeResult[]>([]);

  const [geolocating, setGeolocating] = useState(false);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [destLoading, setDestLoading] = useState(false);

  const [sourceError, setSourceError] = useState<string | null>(null);
  const [destError, setDestError] = useState<string | null>(null);

  const [showSourceOverlay, setShowSourceOverlay] = useState(false);
  const [showDestOverlay, setShowDestOverlay] = useState(false);

  const [sourceHighlightIdx, setSourceHighlightIdx] = useState<number>(-1);
  const [destHighlightIdx, setDestHighlightIdx] = useState<number>(-1);

  const sourceRef = useRef<HTMLDivElement>(null);
  const destRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (sourceRef.current && !sourceRef.current.contains(event.target as Node)) {
        setShowSourceOverlay(false);
      }
      if (destRef.current && !destRef.current.contains(event.target as Node)) {
        setShowDestOverlay(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchSuggestions = async (
    val: string,
    nearby: LocationInfo | null,
    signal: AbortSignal,
    setSuggests: (arr: GeocodeResult[]) => void,
    setLoading: (b: boolean) => void,
    setError: (err: string | null) => void,
    setHighlight: (index: number) => void
  ) => {
    setHighlight(-1);
    const trimmedVal = val.trim();
    if (trimmedVal.length < 3) {
      setSuggests([]);
      setError(trimmedVal ? 'Enter at least 3 characters to search.' : null);
      return;
    }
    const context = locationContext(nearby);
    const cacheKey = `${trimmedVal.toLocaleLowerCase().replace(/\s+/g, ' ')}|${context.toLocaleLowerCase()}`;
    const cached = suggestionCache.get(cacheKey);
    if (cached) {
      setSuggests(cached);
      setError(cached.length ? null : 'No exact location found. Try adding the city or nearby landmark.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ q: trimmedVal });
      if (context) params.set('context', context);
      if (nearby) {
        params.set('near_lat', String(nearby.lat));
        params.set('near_lon', String(nearby.lng));
      }
      const response = await apiFetch(`/api/geocode?${params.toString()}`, { signal });
      const data = await response.json() as GeocodeResult[];
      if (signal.aborted) return;
      suggestionCache.set(cacheKey, data);
      if (!data || data.length === 0) {
        setError('No exact location found. Try adding the city or nearby landmark.');
        setSuggests([]);
      } else {
        setSuggests(data.slice(0, 5));
        setError(null);
      }
    } catch {
      if (!signal.aborted) {
        setSuggests([]);
        setError('Location search is temporarily unavailable. Please try again.');
      }
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const delayDebounce = setTimeout(() => {
      if (sourceInput && (!selectedSource || sourceInput !== selectedSource.label)) {
        void fetchSuggestions(sourceInput, selectedDest, controller.signal, setSourceSuggestions, setSourceLoading, setSourceError, setSourceHighlightIdx);
      }
    }, 450);
    return () => {
      clearTimeout(delayDebounce);
      controller.abort();
    };
  }, [sourceInput, selectedSource, selectedDest]);

  useEffect(() => {
    const controller = new AbortController();
    const delayDebounce = setTimeout(() => {
      if (destInput && (!selectedDest || destInput !== selectedDest.label)) {
        void fetchSuggestions(destInput, selectedSource, controller.signal, setDestSuggestions, setDestLoading, setDestError, setDestHighlightIdx);
      }
    }, 450);
    return () => {
      clearTimeout(delayDebounce);
      controller.abort();
    };
  }, [destInput, selectedDest, selectedSource]);

  const handleCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    setGeolocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const response = await apiFetch(`/api/geocode/reverse?lat=${latitude}&lon=${longitude}`);
          let addressLabel = `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;
          let address: Record<string, string> | undefined;
          if (response.ok) {
            const data = await response.json() as GeocodeResult;
            if (data.display_name) addressLabel = data.display_name;
            if (data.address) address = data.address;
          }

          const locationData = {
            label: addressLabel,
            lat: latitude,
            lng: longitude,
            address
          };

          onSourceSelect(locationData);
          setSourceInput(addressLabel);
          setShowSourceOverlay(false);
          setSourceError(null);
        } catch {
          const fallback = {
            label: `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
            lat: latitude,
            lng: longitude
          };
          onSourceSelect(fallback);
          setSourceInput(fallback.label);
          setSourceError(null);
        } finally {
          setGeolocating(false);
        }
      },
      () => {
        setGeolocating(false);
      },
      { enableHighAccuracy: true, timeout: 6000 }
    );
  };

  const handleSwap = () => {
    const tempSource = selectedSource;
    const tempDest = selectedDest;
    onSourceSelect(tempDest);
    onDestSelect(tempSource);
    setSourceInput(tempDest?.label || '');
    setDestInput(tempSource?.label || '');
    setSourceSuggestions([]);
    setDestSuggestions([]);
    setSourceHighlightIdx(-1);
    setDestHighlightIdx(-1);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSource) {
      setSourceError('Select a valid search result before comparing fares.');
      setShowSourceOverlay(true);
      return;
    }
    if (!selectedDest) {
      setDestError('Select a valid search result before comparing fares.');
      setShowDestOverlay(true);
      return;
    }
    onSearch(selectedSource, selectedDest);
  };

  const handleSelectSourceItem = (item: GeocodeResult) => {
    const label = item.displayName || item.display_name || 'Selected Location';
    const lat = Number(item.lat);
    const lng = Number(item.lng ?? item.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
    onSourceSelect({ label, lat, lng, address: item.address });
    setSourceInput(label);
    setShowSourceOverlay(false);
  };

  const handleSelectDestItem = (item: GeocodeResult) => {
    const label = item.displayName || item.display_name || 'Selected Location';
    const lat = Number(item.lat);
    const lng = Number(item.lng ?? item.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
    onDestSelect({ label, lat, lng, address: item.address });
    setDestInput(label);
    setShowDestOverlay(false);
  };

  const handleSourceKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSourceOverlay || sourceSuggestions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSourceHighlightIdx(prev => (prev + 1) % sourceSuggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSourceHighlightIdx(prev => (prev - 1 + sourceSuggestions.length) % sourceSuggestions.length);
    } else if (e.key === 'Enter') {
      if (sourceHighlightIdx >= 0 && sourceHighlightIdx < sourceSuggestions.length) {
        e.preventDefault();
        handleSelectSourceItem(sourceSuggestions[sourceHighlightIdx]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setShowSourceOverlay(false);
    }
  };

  const handleDestKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showDestOverlay || destSuggestions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setDestHighlightIdx(prev => (prev + 1) % destSuggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setDestHighlightIdx(prev => (prev - 1 + destSuggestions.length) % destSuggestions.length);
    } else if (e.key === 'Enter') {
      if (destHighlightIdx >= 0 && destHighlightIdx < destSuggestions.length) {
        e.preventDefault();
        handleSelectDestItem(destSuggestions[destHighlightIdx]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setShowDestOverlay(false);
    }
  };

  return (
    <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-2xl shadow-md transition-all duration-300">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Source Address Input */}
        <div className="relative" ref={sourceRef}>
          <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
            Pickup Location
          </label>
          <div className="relative flex items-center">
            <span className="absolute left-3.5 text-indigo-500">
              {sourceLoading ? <Loader2 size={16} className="animate-spin" /> : <MapPin size={18} />}
            </span>
            <input
              type="text"
              value={sourceInput}
              onChange={(e) => {
                const val = e.target.value;
                setSourceInput(val);
                setShowSourceOverlay(true);
                if (!selectedSource || val !== selectedSource.label) {
                  onSourceSelect(null);
                }
              }}
              onFocus={() => setShowSourceOverlay(true)}
              onKeyDown={handleSourceKeyDown}
              placeholder="Search pickup city, building or station..."
              className="w-full pl-10 pr-12 py-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-[var(--text-primary)] placeholder-slate-400 dark:placeholder-slate-500 font-medium transition-all"
              required
            />
            <button
              type="button"
              onClick={handleCurrentLocation}
              disabled={geolocating}
              className="absolute right-3 p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition-colors"
              title="Detect Current Location"
            >
              {geolocating ? <Loader2 size={16} className="animate-spin text-indigo-600" /> : <Locate size={16} />}
            </button>
          </div>

          {showSourceOverlay && (sourceSuggestions.length > 0 || sourceLoading || sourceError) && (
            <ul className="absolute left-0 right-0 z-50 mt-1 max-h-56 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg divide-y divide-[var(--border-color)]">
              {sourceLoading && sourceSuggestions.length === 0 && (
                <li className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-indigo-500" />
                  <span>Searching locations...</span>
                </li>
              )}
              {sourceError && !sourceLoading && (
                <li className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <AlertCircle size={14} className="text-slate-400" />
                  <span>{sourceError}</span>
                </li>
              )}
              {!sourceLoading && sourceSuggestions.map((item, idx) => {
                const label = item.displayName || item.display_name || item.name || '';
                return (
                  <li
                    key={idx}
                    onClick={() => handleSelectSourceItem(item)}
                    className={`px-4 py-2.5 text-xs font-medium cursor-pointer flex gap-2 items-start transition-all duration-150 text-[var(--text-primary)] ${
                      idx === sourceHighlightIdx
                        ? 'bg-[var(--bg-primary)] border-l-4 border-indigo-500 pl-3 font-semibold'
                        : 'hover:bg-[var(--bg-primary)] border-l-4 border-transparent'
                    }`}
                  >
                    <MapPin size={14} className="mt-0.5 text-indigo-500 shrink-0" />
                    <span>{label}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Swap Button */}
        <div className="flex justify-center -my-2.5 relative z-10">
          <button
            type="button"
            onClick={handleSwap}
            className="p-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] hover:text-indigo-500 hover:shadow-md hover:scale-105 rounded-full shadow-sm transition-all"
            title="Swap Locations"
          >
            <ArrowUpDown size={14} />
          </button>
        </div>

        {/* Destination Address Input */}
        <div className="relative" ref={destRef}>
          <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
            Destination Location
          </label>
          <div className="relative flex items-center">
            <span className="absolute left-3.5 text-indigo-500">
              {destLoading ? <Loader2 size={16} className="animate-spin" /> : <MapPin size={18} />}
            </span>
            <input
              type="text"
              value={destInput}
              onChange={(e) => {
                const val = e.target.value;
                setDestInput(val);
                setShowDestOverlay(true);
                if (!selectedDest || val !== selectedDest.label) {
                  onDestSelect(null);
                }
              }}
              onFocus={() => setShowDestOverlay(true)}
              onKeyDown={handleDestKeyDown}
              placeholder="Search destination city, building or station..."
              className="w-full pl-10 pr-4 py-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-[var(--text-primary)] placeholder-slate-400 dark:placeholder-slate-500 font-medium transition-all"
              required
            />
          </div>

          {showDestOverlay && (destSuggestions.length > 0 || destLoading || destError) && (
            <ul className="absolute left-0 right-0 z-50 mt-1 max-h-56 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg divide-y divide-[var(--border-color)]">
              {destLoading && destSuggestions.length === 0 && (
                <li className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-indigo-500" />
                  <span>Searching locations...</span>
                </li>
              )}
              {destError && !destLoading && (
                <li className="px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <AlertCircle size={14} className="text-slate-400" />
                  <span>{destError}</span>
                </li>
              )}
              {!destLoading && destSuggestions.map((item, idx) => {
                const label = item.displayName || item.display_name || item.name || '';
                return (
                  <li
                    key={idx}
                    onClick={() => handleSelectDestItem(item)}
                    className={`px-4 py-2.5 text-xs font-medium cursor-pointer flex gap-2 items-start transition-all duration-150 text-[var(--text-primary)] ${
                      idx === destHighlightIdx
                        ? 'bg-[var(--bg-primary)] border-l-4 border-indigo-500 pl-3 font-semibold'
                        : 'hover:bg-[var(--bg-primary)] border-l-4 border-transparent'
                    }`}
                  >
                    <MapPin size={14} className="mt-0.5 text-indigo-500 shrink-0" />
                    <span>{label}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Action Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full mt-2 py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-semibold rounded-xl shadow-md hover:shadow-indigo-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
        >
          {loading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              <span>Analyzing Routes & Fares...</span>
            </>
          ) : (
            <>
              <Search size={18} />
              <span>Compare Real-Time Fares</span>
            </>
          )}
        </button>
      </form>
      <p className="mt-3 text-center text-[10px] text-[var(--text-secondary)]">
        Search data © <a className="underline" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>
      </p>
    </div>
  );
};
