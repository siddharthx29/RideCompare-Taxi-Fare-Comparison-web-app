import React, { useState, useEffect } from 'react';
import { ArrowUpDown, Search, Loader2, History, Bookmark, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { LocationInfo } from '../types/ride';
import { LocationAutocompleteInput } from './LocationAutocompleteInput';
import { reverseGeocodeLocation, suggestLocations, retrieveLocation } from '../utils/locationService';
import { apiFetch } from '../utils/api';

interface SearchPanelProps {
  selectedSource: LocationInfo | null;
  selectedDest: LocationInfo | null;
  onSourceSelect: (loc: LocationInfo | null) => void;
  onDestSelect: (loc: LocationInfo | null) => void;
  onSearch: (source: LocationInfo, destination: LocationInfo, departAt?: string) => void;
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
  const [sourceInput, setSourceInput] = useState(selectedSource?.label || '');
  const [destInput, setDestInput] = useState(selectedDest?.label || '');

  useEffect(() => {
    if (selectedSource?.label) {
      setSourceInput(selectedSource.label);
      setSourceError(null);
    } else if (!selectedSource) {
      setSourceInput('');
    }
  }, [selectedSource]);

  useEffect(() => {
    if (selectedDest?.label) {
      setDestInput(selectedDest.label);
      setDestError(null);
    } else if (!selectedDest) {
      setDestInput('');
    }
  }, [selectedDest]);

  const [geolocating, setGeolocating] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [destError, setDestError] = useState<string | null>(null);
  const [departMode, setDepartMode] = useState<'now' | 'later'>('now');
  const [departTime, setDepartTime] = useState<string>('');
  const [coverageStatus, setCoverageStatus] = useState<{
    covered?: boolean;
    name?: string;
    servicesCount?: number;
    message?: string;
  } | null>(null);

  // Check coverage whenever pickup location changes
  useEffect(() => {
    if (!selectedSource?.lat || !selectedSource?.lng) {
      setCoverageStatus(null);
      return;
    }
    let isCancelled = false;
    apiFetch(`/api/coverage?lat=${selectedSource.lat}&lng=${selectedSource.lng}`)
      .then(res => res.json())
      .then(data => {
        if (!isCancelled) {
          if (data.covered) {
            setCoverageStatus({
              covered: true,
              name: data.name,
              servicesCount: data.active_services?.length || 0
            });
          } else {
            setCoverageStatus({
              covered: false,
              message: data.message || "Ride services are not available in this area."
            });
          }
        }
      })
      .catch(() => {
        if (!isCancelled) setCoverageStatus(null);
      });
    return () => { isCancelled = true; };
  }, [selectedSource]);
  const [recentLocations, setRecentLocations] = useState<LocationInfo[]>(() => {
    try {
      const recent = JSON.parse(localStorage.getItem('ridecompare.recent-locations') || '[]');
      return Array.isArray(recent) ? recent : [];
    } catch {
      return [];
    }
  });
  const [favouriteLocations, setFavouriteLocations] = useState<LocationInfo[]>(() => {
    try {
      const favourites = JSON.parse(localStorage.getItem('ridecompare.favourite-locations') || '[]');
      return Array.isArray(favourites) ? favourites : [];
    } catch {
      return [];
    }
  });
  const RECENT_KEY = 'ridecompare.recent-locations';
  const FAVOURITES_KEY = 'ridecompare.favourite-locations';

  const locationKey = (location: LocationInfo) =>
    location.placeId || `${location.lat.toFixed(5)},${location.lng.toFixed(5)}`;

  const selectSavedLocation = (location: LocationInfo, target: 'source' | 'destination') => {
    if (target === 'source') {
      onSourceSelect(location);
      setSourceInput(location.label);
    } else {
      onDestSelect(location);
      setDestInput(location.label);
    }
  };

  const toggleFavourite = (location: LocationInfo) => {
    const key = locationKey(location);
    const next = favouriteLocations.some(item => locationKey(item) === key)
      ? favouriteLocations.filter(item => locationKey(item) !== key)
      : [location, ...favouriteLocations].slice(0, 12);
    setFavouriteLocations(next);
    localStorage.setItem(FAVOURITES_KEY, JSON.stringify(next));
  };

  const rememberLocations = (locations: LocationInfo[]) => {
    const next = locations.reduce<LocationInfo[]>((items, location) => {
      if (!items.some(item => locationKey(item) === locationKey(location))) items.push(location);
      return items;
    }, [...recentLocations]).slice(-8).reverse();
    setRecentLocations(next);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  };

  const resolveLocationFromText = async (text: string, nearby?: LocationInfo | null): Promise<LocationInfo | null> => {
    const trimmed = text.trim();
    if (!trimmed) return null;
    try {
      const suggestions = await suggestLocations(trimmed, 'submit-session', nearby);
      if (suggestions && suggestions.length > 0) {
        const item = suggestions[0];
        const lat = Number(item.latitude ?? item.lat);
        const lng = Number(item.longitude ?? item.lng ?? item.lon);
        if (Number.isFinite(lat) && Number.isFinite(lng) && (lat !== 0 || lng !== 0)) {
          return {
            label: item.displayName || item.display_name || item.primaryText || item.name || trimmed,
            lat,
            lng,
            placeId: item.mapbox_id || (item.id ? String(item.id) : undefined),
            address: item.address,
            placeName: item.primaryText || item.name,
            locality: item.secondaryText,
            city: item.city || item.address?.city || item.address?.town,
            state: item.state || item.address?.state,
            country: item.country || item.address?.country,
            countryCode: item.country_code || item.address?.country_code,
            locationType: item.feature_type || item.category
          };
        }
        if (item.mapbox_id) {
          return await retrieveLocation(item.mapbox_id, 'submit-session');
        }
      }
    } catch (e) {
      console.warn('Auto resolve location failed:', e);
    }
    return null;
  };

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
          const revResult = await reverseGeocodeLocation(latitude, longitude);
          const locationData: LocationInfo = revResult || {
            label: `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
            lat: latitude,
            lng: longitude
          };

          onSourceSelect(locationData);
          setSourceInput(locationData.label);
          setSourceError(null);
        } catch {
          const fallback: LocationInfo = {
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
    const tempSourceInput = sourceInput;
    const tempDestInput = destInput;

    onSourceSelect(tempDest);
    onDestSelect(tempSource);
    setSourceInput(tempDestInput);
    setDestInput(tempSourceInput);
    setSourceError(null);
    setDestError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSourceError(null);
    setDestError(null);

    let src = selectedSource;
    let dst = selectedDest;

    if ((!src && sourceInput.trim()) || (!dst && destInput.trim())) {
      setResolving(true);
      try {
        if (!src && sourceInput.trim()) {
          src = await resolveLocationFromText(sourceInput, dst);
          if (src) onSourceSelect(src);
        }
        if (!dst && destInput.trim()) {
          dst = await resolveLocationFromText(destInput, src);
          if (dst) onDestSelect(dst);
        }
      } finally {
        setResolving(false);
      }
    }

    if (!src) {
      setSourceError('Please select or search a valid pickup location.');
      return;
    }
    if (!dst) {
      setDestError('Please select or search a valid destination location.');
      return;
    }
    rememberLocations([src, dst]);
    const departIso = departMode === 'later' && departTime ? new Date(departTime).toISOString() : undefined;
    onSearch(src, dst, departIso);
  };

  return (
    <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] p-5 rounded-2xl shadow-sm transition-all duration-300">
      <form onSubmit={handleSubmit} className="space-y-3">
        {(recentLocations.length > 0 || favouriteLocations.length > 0) && (
          <div className="space-y-3" aria-label="Saved locations">
            {recentLocations.length > 0 && (
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)]">
                    <History size={13} /> Recent searches
                  </span>
                  <button type="button" onClick={() => { setRecentLocations([]); localStorage.removeItem(RECENT_KEY); }} className="text-[11px] text-[var(--text-secondary)] hover:text-indigo-500">
                    Clear
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {recentLocations.map(location => (
                    <div key={`recent-${locationKey(location)}`} className="flex max-w-full items-center rounded-lg border border-[var(--border-color)]">
                      <button type="button" onClick={() => selectSavedLocation(location, 'source')} className="truncate px-2.5 py-1.5 text-xs text-[var(--text-primary)] hover:text-indigo-500">
                        {location.placeName || location.label}
                      </button>
                      <button type="button" onClick={() => toggleFavourite(location)} className="p-1.5 text-[var(--text-secondary)] hover:text-indigo-500" aria-label={`Favourite ${location.label}`}>
                        <Bookmark size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {favouriteLocations.length > 0 && (
              <div>
                <span className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)]">
                  <Bookmark size={13} /> Favourite locations
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {favouriteLocations.map(location => (
                    <button key={`favourite-${locationKey(location)}`} type="button" onClick={() => selectSavedLocation(location, 'source')} className="max-w-full truncate rounded-lg border border-[var(--border-color)] px-2.5 py-1.5 text-xs text-[var(--text-primary)] hover:border-indigo-400">
                      {location.placeName || location.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {/* Pickup Address Input */}
        <LocationAutocompleteInput
          id="pickup-location-input"
          label="Pickup Location"
          placeholder="Search pickup city, building, station, or landmark..."
          value={sourceInput}
          onChangeText={setSourceInput}
          selectedLocation={selectedSource}
          onSelectLocation={onSourceSelect}
          nearbyLocation={selectedDest}
          showLocateButton={true}
          onLocate={handleCurrentLocation}
          isLocating={geolocating}
          inputError={sourceError}
          onClearError={() => setSourceError(null)}
          required
        />

        {/* Swap Button */}
        <div className="flex justify-center -my-2.5 relative z-10">
          <button
            type="button"
            onClick={handleSwap}
            className="p-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] hover:text-[var(--accent-color)] hover:shadow-md hover:scale-105 rounded-full shadow-sm transition-all cursor-pointer"
            title="Swap Locations"
          >
            <ArrowUpDown size={14} />
          </button>
        </div>

        {/* Destination Address Input */}
        <LocationAutocompleteInput
          id="destination-location-input"
          label="Destination Location"
          placeholder="Search destination city, building, station, or landmark..."
          value={destInput}
          onChangeText={setDestInput}
          selectedLocation={selectedDest}
          onSelectLocation={onDestSelect}
          nearbyLocation={selectedSource}
          showLocateButton={false}
          inputError={destError}
          onClearError={() => setDestError(null)}
          required
        />

        {/* Departure Time Selection */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] p-2.5 rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-1.5">
              <Clock size={13} className="text-slate-400" />
              Departure Time
            </span>
            <div className="flex items-center bg-[var(--bg-primary)] p-0.5 rounded-lg border border-[var(--border-color)] text-[11px]">
              <button
                type="button"
                onClick={() => { setDepartMode('now'); setDepartTime(''); }}
                className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                  departMode === 'now'
                    ? 'bg-[var(--accent-color)] text-white shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Now
              </button>
              <button
                type="button"
                onClick={() => setDepartMode('later')}
                className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                  departMode === 'later'
                    ? 'bg-[var(--accent-color)] text-white shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Later
              </button>
            </div>
          </div>

          {departMode === 'later' && (
            <input
              type="datetime-local"
              value={departTime}
              onChange={(e) => setDepartTime(e.target.value)}
              className="w-full text-xs p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent-color)]"
            />
          )}
        </div>

        {/* Live Coverage Availability Indicator */}
        {coverageStatus && (
          <div className="text-xs">
            {coverageStatus.covered ? (
              <div className="flex items-center gap-1.5 text-emerald-500 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg">
                <CheckCircle2 size={14} />
                <span>Serving {coverageStatus.name} ({coverageStatus.servicesCount} services active)</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-amber-500 font-semibold bg-amber-500/10 border border-amber-500/20 px-3 py-2 rounded-lg">
                <AlertTriangle size={15} className="shrink-0" />
                <span>{coverageStatus.message}</span>
              </div>
            )}
          </div>
        )}

        {/* Action Button */}
        <button
          type="submit"
          disabled={loading || resolving || coverageStatus?.covered === false}
          className="w-full mt-2 py-3.5 px-4 bg-[var(--accent-color)] hover:bg-[var(--accent-hover)] active:scale-[0.99] text-white font-semibold rounded-xl shadow-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {loading || resolving ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              <span>{resolving ? 'Locating Places...' : 'Analyzing Routes & Fares...'}</span>
            </>
          ) : coverageStatus?.covered === false ? (
            <>
              <AlertTriangle size={18} />
              <span>Ride services unavailable in this area</span>
            </>
          ) : (
            <>
              <Search size={18} />
              <span>Compare rides</span>
            </>
          )}
        </button>
      </form>

      <p className="mt-3 text-center text-[10px] text-[var(--text-secondary)]">
        Location search powered by{' '}
        <a
          className="underline hover:text-indigo-500 transition-colors"
          href="https://www.mapbox.com"
          target="_blank"
          rel="noreferrer"
        >
          Mapbox Search Box &amp; Geocoding
        </a>
      </p>
    </div>
  );
};
