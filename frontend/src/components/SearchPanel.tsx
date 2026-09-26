import React, { useState } from 'react';
import { ArrowUpDown, Search, Loader2 } from 'lucide-react';
import type { LocationInfo } from '../types/ride';
import { LocationAutocompleteInput } from './LocationAutocompleteInput';
import { reverseGeocodeLocation } from '../utils/locationService';

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
  const [sourceInput, setSourceInput] = useState(selectedSource?.label || '');
  const [destInput, setDestInput] = useState(selectedDest?.label || '');

  const [geolocating, setGeolocating] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [destError, setDestError] = useState<string | null>(null);

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSource) {
      setSourceError('Select a valid search result before comparing fares.');
      return;
    }
    if (!selectedDest) {
      setDestError('Select a valid search result before comparing fares.');
      return;
    }
    onSearch(selectedSource, selectedDest);
  };

  return (
    <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-2xl shadow-md transition-all duration-300">
      <form onSubmit={handleSubmit} className="space-y-4">
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
            className="p-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] hover:text-indigo-500 hover:shadow-md hover:scale-105 rounded-full shadow-sm transition-all cursor-pointer"
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

        {/* Action Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full mt-2 py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-semibold rounded-xl shadow-md hover:shadow-indigo-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
        >
          {loading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              <span>Analyzing Routes &amp; Fares...</span>
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
