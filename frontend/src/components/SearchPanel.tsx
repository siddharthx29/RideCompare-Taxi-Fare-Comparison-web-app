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

const DEFAULT_LANDMARKS: LocationInfo[] = [
  { label: "Connaught Place, New Delhi, Delhi, India", lat: 28.6328, lng: 77.2197 },
  { label: "Indira Gandhi International Airport, New Delhi, Delhi, India", lat: 28.5562, lng: 77.1000 },
  { label: "Bandra Kurla Complex, Mumbai, Maharashtra, India", lat: 19.0688, lng: 72.8704 },
  { label: "Marine Drive, Mumbai, Maharashtra, India", lat: 18.9432, lng: 72.8230 },
  { label: "Indiranagar, Bengaluru, Karnataka, India", lat: 12.971891, lng: 77.641151 },
  { label: "Kempegowda International Airport, Bengaluru, Karnataka, India", lat: 13.1986, lng: 77.7066 },
  { label: "Panaji, North Goa, Goa, India", lat: 15.4989, lng: 73.8278 },
  { label: "Baga Beach, North Goa, Goa, India", lat: 15.5553, lng: 73.7517 },
  { label: "Manohar International Airport (Mopa), Goa, India", lat: 15.7533, lng: 73.8690 },
  { label: "Park Street, Kolkata, West Bengal, India", lat: 22.5505, lng: 88.3527 },
  { label: "Howrah Railway Station, Kolkata, West Bengal, India", lat: 22.5857, lng: 88.3426 },
  { label: "MG Road, Kochi, Ernakulam, Kerala, India", lat: 9.9723, lng: 76.2784 },
  { label: "Cochin International Airport (CIAL), Kochi, Kerala, India", lat: 10.1518, lng: 76.3930 },
  { label: "Marina Beach, Chennai, Tamil Nadu, India", lat: 13.0500, lng: 80.2824 },
  { label: "Hitech City, Hyderabad, Telangana, India", lat: 17.4435, lng: 78.3772 }
];

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
  
  const [sourceSuggestions, setSourceSuggestions] = useState<any[]>([]);
  const [destSuggestions, setDestSuggestions] = useState<any[]>([]);

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
    if (selectedSource) {
      setSourceInput(selectedSource.label);
    } else if (!sourceLoading && !showSourceOverlay) {
      setSourceInput('');
    }
  }, [selectedSource]);

  useEffect(() => {
    if (selectedDest) {
      setDestInput(selectedDest.label);
    } else if (!destLoading && !showDestOverlay) {
      setDestInput('');
    }
  }, [selectedDest]);

  useEffect(() => {
    setSourceHighlightIdx(-1);
  }, [sourceSuggestions]);

  useEffect(() => {
    setDestHighlightIdx(-1);
  }, [destSuggestions]);

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
    setSuggests: (arr: any[]) => void,
    setLoading: (b: boolean) => void,
    setError: (err: string | null) => void
  ) => {
    const trimmedVal = val.trim();
    if (trimmedVal.length < 2) {
      setSuggests([]);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      let data: any[] = [];
      try {
        const response = await apiFetch(`/api/geocode?q=${encodeURIComponent(trimmedVal)}`);
        data = await response.json();
      } catch (backendErr: any) {
        try {
          const directUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(trimmedVal)}&addressdetails=1&limit=5&accept-language=en`;
          const response = await fetch(directUrl, {
            headers: { 'User-Agent': 'RideCompare-App/2.0.0 (contact@ridecompare.com)' }
          });
          if (response.ok) {
            data = await response.json();
          }
        } catch {}
      }

      if (!data || data.length === 0) {
        // Fallback filter from local landmarks
        const matches = DEFAULT_LANDMARKS.filter(l => 
          l.label.toLowerCase().includes(trimmedVal.toLowerCase())
        );
        if (matches.length > 0) {
          data = matches.map(m => ({
            displayName: m.label,
            display_name: m.label,
            lat: m.lat.toString(),
            lng: m.lng.toString(),
            lon: m.lng.toString()
          }));
        }
      }
      
      if (!data || data.length === 0) {
        setError('No matching places found. Try typing a city or landmark.');
        setSuggests([]);
      } else {
        setSuggests(data);
        setError(null);
      }
    } catch (err: any) {
      setError(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (sourceInput && (!selectedSource || sourceInput !== selectedSource.label)) {
        fetchSuggestions(sourceInput, setSourceSuggestions, setSourceLoading, setSourceError);
      }
    }, 300);
    return () => clearTimeout(delayDebounce);
  }, [sourceInput, selectedSource]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (destInput && (!selectedDest || destInput !== selectedDest.label)) {
        fetchSuggestions(destInput, setDestSuggestions, setDestLoading, setDestError);
      }
    }, 300);
    return () => clearTimeout(delayDebounce);
  }, [destInput, selectedDest]);

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
          const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1&accept-language=en`;
          const response = await fetch(url, {
            headers: { 'User-Agent': 'RideCompare-App/2.0.0 (contact@ridecompare.com)' }
          });
          
          let addressLabel = `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;
          if (response.ok) {
            const data = await response.json();
            if (data.display_name) addressLabel = data.display_name;
          }

          const locationData = {
            label: addressLabel,
            lat: latitude,
            lng: longitude
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
  };

  const resolveLocationFromInput = (input: string, suggestions: any[], defaultFallback: LocationInfo): LocationInfo => {
    if (suggestions.length > 0) {
      const top = suggestions[0];
      return {
        label: top.displayName || top.display_name || input,
        lat: parseFloat(top.lat),
        lng: parseFloat(top.lng || top.lon)
      };
    }
    const match = DEFAULT_LANDMARKS.find(l => l.label.toLowerCase().includes(input.toLowerCase()));
    if (match) return match;
    return { ...defaultFallback, label: input };
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let src = selectedSource;
    let dst = selectedDest;

    if (!src && sourceInput.trim()) {
      src = resolveLocationFromInput(sourceInput.trim(), sourceSuggestions, DEFAULT_LANDMARKS[0]);
      onSourceSelect(src);
    }
    if (!dst && destInput.trim()) {
      dst = resolveLocationFromInput(destInput.trim(), destSuggestions, DEFAULT_LANDMARKS[1]);
      onDestSelect(dst);
    }

    if (src && dst) {
      onSearch(src, dst);
    }
  };

  const handleSelectSourceItem = (item: any) => {
    const label = item.displayName || item.display_name || 'Selected Location';
    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lng || item.lon);
    onSourceSelect({ label, lat, lng });
    setSourceInput(label);
    setShowSourceOverlay(false);
  };

  const handleSelectDestItem = (item: any) => {
    const label = item.displayName || item.display_name || 'Selected Location';
    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lng || item.lon);
    onDestSelect({ label, lat, lng });
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
    </div>
  );
};
