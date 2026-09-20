import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Locate, ArrowUpDown, Search, Loader2, AlertCircle } from 'lucide-react';
import { apiFetch } from '../utils/api';

interface LocationInfo {
  label: string;
  lat: number;
  lng: number;
}

interface SearchPanelProps {
  selectedSource: LocationInfo | null;
  selectedDest: LocationInfo | null;
  onSourceSelect: (loc: LocationInfo | null) => void;
  onDestSelect: (loc: LocationInfo | null) => void;
  onSearch: (source: LocationInfo, destination: LocationInfo) => void;
  loading: boolean;
}

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

  // Error States
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [destError, setDestError] = useState<string | null>(null);

  // Suggestion overlay toggles
  const [showSourceOverlay, setShowSourceOverlay] = useState(false);
  const [showDestOverlay, setShowDestOverlay] = useState(false);

  // Keyboard navigation highlights (-1 means none)
  const [sourceHighlightIdx, setSourceHighlightIdx] = useState<number>(-1);
  const [destHighlightIdx, setDestHighlightIdx] = useState<number>(-1);

  const sourceRef = useRef<HTMLDivElement>(null);
  const destRef = useRef<HTMLDivElement>(null);

  // Sync inputs with props (so resets, swaps, and outside updates reflect in the input value)
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

  // Reset highlight index when suggestions change
  useEffect(() => {
    setSourceHighlightIdx(-1);
  }, [sourceSuggestions]);

  useEffect(() => {
    setDestHighlightIdx(-1);
  }, [destSuggestions]);

  // Close overlays on click outside
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

  // Fetch suggestions helper
  const fetchSuggestions = async (
    val: string,
    setSuggests: (arr: any[]) => void,
    setLoading: (b: boolean) => void,
    setError: (err: string | null) => void
  ) => {
    const trimmedVal = val.trim();
    if (trimmedVal.length < 3) {
      setSuggests([]);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (import.meta.env.DEV) {
        console.log(`[Autocomplete Search] Fetching suggestions for: "${trimmedVal}"`);
      }
      
      let data;
      try {
        const response = await apiFetch(`/api/geocode?q=${encodeURIComponent(trimmedVal)}`);
        data = await response.json();
        if (data.error) {
          throw new Error(data.error);
        }
      } catch (backendErr: any) {
        console.warn('Backend geocoding failed or rate-limited. Falling back to direct Nominatim query.', backendErr);
        // Fallback: Query Nominatim directly from the client browser
        const directUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(trimmedVal)}&addressdetails=1&limit=5&accept-language=en`;
        const response = await fetch(directUrl, {
          headers: {
            'User-Agent': 'RideCompare-App/1.0.0 (contact@ridecompare.com)'
          }
        });
        if (!response.ok) {
          throw new Error(`Direct Nominatim query failed with status ${response.status}`);
        }
        data = await response.json();
      }
      
      if (!data || data.length === 0) {
        setError('No locations found. Try a different term.');
        setSuggests([]);
      } else {
        setSuggests(data);
        setError(null);
      }
    } catch (err: any) {
      console.error('Failed fetching address recommendations:', err);
      setError(err.message || 'Connection failed. Please check backend service.');
      setSuggests([]);
    } finally {
      setLoading(false);
    }
  };

  // Debounced input fetch suggestions (500ms delay)
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (sourceInput && (!selectedSource || sourceInput !== selectedSource.label)) {
        fetchSuggestions(sourceInput, setSourceSuggestions, setSourceLoading, setSourceError);
      }
    }, 500);
    return () => clearTimeout(delayDebounce);
  }, [sourceInput, selectedSource]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (destInput && (!selectedDest || destInput !== selectedDest.label)) {
        fetchSuggestions(destInput, setDestSuggestions, setDestLoading, setDestError);
      }
    }, 500);
    return () => clearTimeout(delayDebounce);
  }, [destInput, selectedDest]);

  // Geolocation trigger
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
          if (import.meta.env.DEV) {
            console.log(`[Geolocation] Detected coordinates: [${latitude}, ${longitude}]`);
          }
          // Reverse geocode to get human address
          const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1&accept-language=en`;
          const response = await fetch(url, {
            headers: {
              'User-Agent': 'RideCompare-App/1.0.0 (contact@ridecompare.com)'
            }
          });
          
          let addressLabel = 'Current Location';
          if (response.ok) {
            const data = await response.json();
            addressLabel = data.display_name || `Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;
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
        } catch (err) {
          console.error('Error reverse geocoding geolocation:', err);
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
      (error) => {
        console.error('Geolocation permission error:', error);
        alert('Could not retrieve your location. Please check your location sharing permissions.');
        setGeolocating(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const handleSwap = () => {
    if (import.meta.env.DEV) {
      console.log('[Autocomplete] Swapping source and destination...');
    }
    const tempSource = selectedSource;
    const tempDest = selectedDest;

    onSourceSelect(tempDest);
    onDestSelect(tempSource);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedSource && selectedDest) {
      onSearch(selectedSource, selectedDest);
    } else {
      alert('Please select valid locations from the suggestion list for both source and destination.');
    }
  };

  // Keyboard navigation event handlers
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
        const item = sourceSuggestions[sourceHighlightIdx];
        if (import.meta.env.DEV) {
          console.log(`[Keyboard Action] Selecting source item: "${item.display_name}"`);
        }
        onSourceSelect({
          label: item.display_name,
          lat: parseFloat(item.lat),
          lng: parseFloat(item.lon)
        });
        setSourceInput(item.display_name);
        setShowSourceOverlay(false);
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
        const item = destSuggestions[destHighlightIdx];
        if (import.meta.env.DEV) {
          console.log(`[Keyboard Action] Selecting dest item: "${item.display_name}"`);
        }
        onDestSelect({
          label: item.display_name,
          lat: parseFloat(item.lat),
          lng: parseFloat(item.lon)
        });
        setDestInput(item.display_name);
        setShowDestOverlay(false);
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
                // Clear selection if they alter the field
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
            {/* Geolocation Button */}
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

          {/* Source Suggestions Dropdown */}
          {showSourceOverlay && (sourceSuggestions.length > 0 || sourceLoading || sourceError) && (
            <ul className="absolute left-0 right-0 z-50 mt-1 max-h-56 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg divide-y divide-[var(--border-color)]">
              {sourceLoading && sourceSuggestions.length === 0 && (
                <li className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-indigo-500" />
                  <span>Searching locations...</span>
                </li>
              )}
              {sourceError && !sourceLoading && (
                <li className="px-4 py-3 text-xs font-semibold text-red-500 dark:text-red-400 flex items-center gap-2">
                  <AlertCircle size={14} className="text-red-500" />
                  <span>{sourceError}</span>
                </li>
              )}
              {!sourceLoading && !sourceError && sourceSuggestions.map((item, idx) => (
                <li
                  key={idx}
                  onClick={() => {
                    if (import.meta.env.DEV) {
                      console.log(`[Mouse Action] Selecting source item: "${item.display_name}"`);
                    }
                    onSourceSelect({
                      label: item.display_name,
                      lat: parseFloat(item.lat),
                      lng: parseFloat(item.lon)
                    });
                    setSourceInput(item.display_name);
                    setShowSourceOverlay(false);
                  }}
                  className={`px-4 py-2.5 text-xs font-medium cursor-pointer flex gap-2 items-start transition-all duration-150 text-[var(--text-primary)] ${
                    idx === sourceHighlightIdx
                      ? 'bg-[var(--bg-primary)] border-l-4 border-indigo-500 pl-3 font-semibold'
                      : 'hover:bg-[var(--bg-primary)] border-l-4 border-transparent'
                  }`}
                >
                  <MapPin size={14} className="mt-0.5 text-slate-400 shrink-0" />
                  <span>{item.display_name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Swap Buttons */}
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
                // Clear selection if they alter the field
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

          {/* Destination Suggestions Dropdown */}
          {showDestOverlay && (destSuggestions.length > 0 || destLoading || destError) && (
            <ul className="absolute left-0 right-0 z-50 mt-1 max-h-56 overflow-y-auto bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl shadow-lg divide-y divide-[var(--border-color)]">
              {destLoading && destSuggestions.length === 0 && (
                <li className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-indigo-500" />
                  <span>Searching locations...</span>
                </li>
              )}
              {destError && !destLoading && (
                <li className="px-4 py-3 text-xs font-semibold text-red-500 dark:text-red-400 flex items-center gap-2">
                  <AlertCircle size={14} className="text-red-500" />
                  <span>{destError}</span>
                </li>
              )}
              {!destLoading && !destError && destSuggestions.map((item, idx) => (
                <li
                  key={idx}
                  onClick={() => {
                    if (import.meta.env.DEV) {
                      console.log(`[Mouse Action] Selecting dest item: "${item.display_name}"`);
                    }
                    onDestSelect({
                      label: item.display_name,
                      lat: parseFloat(item.lat),
                      lng: parseFloat(item.lon)
                    });
                    setDestInput(item.display_name);
                    setShowDestOverlay(false);
                  }}
                  className={`px-4 py-2.5 text-xs font-medium cursor-pointer flex gap-2 items-start transition-all duration-150 text-[var(--text-primary)] ${
                    idx === destHighlightIdx
                      ? 'bg-[var(--bg-primary)] border-l-4 border-indigo-500 pl-3 font-semibold'
                      : 'hover:bg-[var(--bg-primary)] border-l-4 border-transparent'
                  }`}
                >
                  <MapPin size={14} className="mt-0.5 text-slate-400 shrink-0" />
                  <span>{item.display_name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Compare Button */}
        <button
          type="submit"
          disabled={loading || !selectedSource || !selectedDest}
          className="w-full bg-indigo-600 dark:bg-indigo-500 hover:bg-indigo-700 dark:hover:bg-indigo-600 text-white font-bold py-3 px-4 rounded-xl text-sm shadow-lg shadow-indigo-600/10 hover:shadow-indigo-600/20 active:scale-[0.99] transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              <span>Optimizing Routes...</span>
            </>
          ) : (
            <>
              <Search size={16} />
              <span>Compare Rides</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
