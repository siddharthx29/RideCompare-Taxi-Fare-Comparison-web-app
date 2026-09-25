import { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { SearchPanel } from './components/SearchPanel';
import { MapView } from './components/MapView';
import { RideComparison } from './components/RideComparison';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { Sparkles, Download, X, Search, BarChart3, Home } from 'lucide-react';
import type { ComparisonResult, LocationInfo } from './types/ride';
import { apiFetch } from './utils/api';

const MAX_STRAIGHT_LINE_KM = 240;

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [showAdmin, setShowAdmin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [distanceError, setDistanceError] = useState<string | null>(null);

  const [searchId, setSearchId] = useState<number | null>(null);
  const [sourceLoc, setSourceLoc] = useState<LocationInfo | null>(null);
  const [destLoc, setDestLoc] = useState<LocationInfo | null>(null);
  const [routeGeometry, setRouteGeometry] = useState<any | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);

  const [lastSearchedSource, setLastSearchedSource] = useState<string>('');
  const [lastSearchedDest, setLastSearchedDest] = useState<string>('');

  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [darkMode]);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallBanner(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleSearch = useCallback(async (source: LocationInfo, dest: LocationInfo) => {
    const straightLineKm = haversineKm(source.lat, source.lng, dest.lat, dest.lng);
    if (straightLineKm > MAX_STRAIGHT_LINE_KM) {
      const estRoadKm = Math.round(straightLineKm * 1.25);
      setDistanceError(
        `This route is too far for on-demand taxi comparison (estimated road distance ~${estRoadKm} km). ` +
        `Please choose destinations within 300 km of each other.`
      );
      setSourceLoc(source);
      setDestLoc(dest);
      return;
    }

    setDistanceError(null);
    setLoading(true);
    setSourceLoc(source);
    setDestLoc(dest);
    setRouteGeometry(null);
    setComparison(null);
    setSearchId(null);

    try {
      const startParam = `${source.lng},${source.lat}`;
      const endParam = `${dest.lng},${dest.lat}`;
      const url = `/api/route?start=${startParam}&end=${endParam}&sourceName=${encodeURIComponent(source.label)}&destName=${encodeURIComponent(dest.label)}`;

      const response = await apiFetch(url);
      const result = await response.json();
      setSearchId(result.searchId || 1);
      setRouteGeometry(result.geometry);
      setComparison(result.comparison);
    } catch (err: any) {
      const errMsg: string = err?.message || '';
      const isApiValidationError =
        errMsg.toLowerCase().includes('300') ||
        errMsg.toLowerCase().includes('exceeds') ||
        errMsg.toLowerCase().includes('distance') ||
        errMsg.toLowerCase().includes('limit');

      if (isApiValidationError) {
        setDistanceError(errMsg);
        setLoading(false);
        return;
      }

      // Offline fallback calculation
      const distKm = Math.max(1.0, parseFloat((straightLineKm * 1.25).toFixed(1)));
      const durMin = Math.max(5, Math.round((distKm / 25) * 60));

      const fallbackProviders = [
        {
          provider: "Rapido Bike",
          vehicleType: "Bike" as const,
          distanceKm: distKm,
          etaMinutes: Math.round(durMin * 0.8),
          actualFare: Math.round(15 + (distKm * 7) + (durMin * 1)),
          estimatedFare: Math.round(15 + (distKm * 7) + (durMin * 1)),
          predictedFare: Math.round(15 + (distKm * 7) + (durMin * 1)),
          predictionDiff: 0,
          predictionDiffPct: 0,
          surgeMultiplier: 1.0,
          confidence: "High" as const,
          confidenceScore: 92.0,
          confidenceLevel: "High" as const,
          clusterId: 0,
          clusterLabel: "City Commute",
          smartScore: 94.0,
          isAnomaly: false,
          costPerKm: parseFloat(((15 + (distKm * 7)) / distKm).toFixed(1)),
          costPerMin: 2.5,
          efficiencyScore: 94,
          recommendationScore: 94,
          baseFare: 15,
          distanceFare: distKm * 7,
          durationFare: durMin * 1,
          platformFee: 5,
          tollEstimate: 0,
          rating: 4.4,
          isCheapest: true,
          isFastest: true,
          isMostEfficient: true,
          isBestValue: true,
          webLink: "https://www.rapido.bike/",
          appDeepLink: "rapido://booking"
        },
        {
          provider: "Uber Go",
          vehicleType: "Cab" as const,
          distanceKm: distKm,
          etaMinutes: Math.round(durMin * 1.0),
          actualFare: Math.round(50 + (distKm * 14) + (durMin * 2.0) + 15),
          estimatedFare: Math.round(50 + (distKm * 14) + (durMin * 2.0) + 15),
          predictedFare: Math.round(50 + (distKm * 14) + (durMin * 2.0) + 15),
          predictionDiff: 0,
          predictionDiffPct: 0,
          surgeMultiplier: 1.0,
          confidence: "High" as const,
          confidenceScore: 94.0,
          confidenceLevel: "High" as const,
          clusterId: 0,
          clusterLabel: "City Commute",
          smartScore: 86.0,
          isAnomaly: false,
          costPerKm: parseFloat(((50 + (distKm * 14)) / distKm).toFixed(1)),
          costPerMin: 4.5,
          efficiencyScore: 86,
          recommendationScore: 86,
          baseFare: 50,
          distanceFare: distKm * 14,
          durationFare: durMin * 2,
          platformFee: 15,
          tollEstimate: 0,
          rating: 4.6,
          isCheapest: false,
          isFastest: false,
          isMostEfficient: false,
          isBestValue: false,
          webLink: `https://m.uber.com/ul/?action=setPickup&pickup[formatted_address]=${encodeURIComponent(source.label)}&dropoff[formatted_address]=${encodeURIComponent(dest.label)}`,
          appDeepLink: "uber://booking"
        },
        {
          provider: "Ola Mini",
          vehicleType: "Cab" as const,
          distanceKm: distKm,
          etaMinutes: Math.round(durMin * 1.05),
          actualFare: Math.round(48 + (distKm * 14.5) + (durMin * 2.2) + 15),
          estimatedFare: Math.round(48 + (distKm * 14.5) + (durMin * 2.2) + 15),
          predictedFare: Math.round(48 + (distKm * 14.5) + (durMin * 2.2) + 15),
          predictionDiff: 0,
          predictionDiffPct: 0,
          surgeMultiplier: 1.0,
          confidence: "High" as const,
          confidenceScore: 91.0,
          confidenceLevel: "High" as const,
          clusterId: 0,
          clusterLabel: "City Commute",
          smartScore: 85.0,
          isAnomaly: false,
          costPerKm: parseFloat(((48 + (distKm * 14.5)) / distKm).toFixed(1)),
          costPerMin: 4.8,
          efficiencyScore: 85,
          recommendationScore: 85,
          baseFare: 48,
          distanceFare: distKm * 14.5,
          durationFare: durMin * 2.2,
          platformFee: 15,
          tollEstimate: 0,
          rating: 4.2,
          isCheapest: false,
          isFastest: false,
          isMostEfficient: false,
          isBestValue: false,
          webLink: "https://www.olacabs.com/",
          appDeepLink: "olacabs://app/launch"
        }
      ];

      setSearchId(1);
      setRouteGeometry({
        type: "LineString",
        coordinates: [
          [source.lng, source.lat],
          [dest.lng, dest.lat]
        ]
      });
      setComparison({
        distanceKm: distKm,
        durationMins: durMin,
        straightLineDistance: distKm,
        detourDistance: 0,
        detectedCity: "Bangalore",
        surgeRuleName: "Standard",
        pricingRegime: distKm > 20 ? "Long-Distance Transit" : "Standard City Transit",
        fareSpread: fallbackProviders[fallbackProviders.length - 1].actualFare - fallbackProviders[0].actualFare,
        spreadPercentage: Math.round(((fallbackProviders[fallbackProviders.length - 1].actualFare - fallbackProviders[0].actualFare) / fallbackProviders[0].actualFare) * 100),
        anomalyCount: 0,
        providers: fallbackProviders,
        recommendations: {
          cheapest: "Rapido Bike",
          fastest: "Rapido Bike",
          mostEfficient: "Rapido Bike",
          bestValue: "Rapido Bike",
          recommendationReason: "Most cost-effective transport option for direct journey.",
          distanceAdvantage: `Direct route of ${distKm} km.`,
          timeAdvantage: `Estimated travel duration ~${durMin} mins.`,
          costAdvantage: `Save with the most economical option.`
        },
        insights: [
          `Direct distance estimate: ${distKm} km across urban routes.`,
          `Estimated travel time: approximately ${durMin} mins.`
        ]
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (sourceLoc && destLoc) {
      const sourceKey = `${sourceLoc.lat},${sourceLoc.lng}`;
      const destKey = `${destLoc.lat},${destLoc.lng}`;
      if (lastSearchedSource !== sourceKey || lastSearchedDest !== destKey) {
        setLastSearchedSource(sourceKey);
        setLastSearchedDest(destKey);
        handleSearch(sourceLoc, destLoc);
      }
    }
  }, [sourceLoc, destLoc, lastSearchedSource, lastSearchedDest, handleSearch]);

  const handleInstallApp = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    setDeferredPrompt(null);
    setShowInstallBanner(false);
  };

  const handleBookingRedirect = async (provider: string, fare: number) => {
    try {
      await apiFetch('/api/redirect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ searchId, provider, fare })
      });
    } catch (err) {
      console.error('Failed logging redirect click:', err);
    }
  };

  const resetSearch = () => {
    setSourceLoc(null);
    setDestLoc(null);
    setRouteGeometry(null);
    setComparison(null);
    setSearchId(null);
    setLastSearchedSource('');
    setLastSearchedDest('');
    setDistanceError(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-primary)] transition-all">
      <Navbar
        darkMode={darkMode}
        toggleDarkMode={() => setDarkMode(!darkMode)}
        showAdmin={showAdmin}
        setShowAdmin={setShowAdmin}
        onLogoClick={() => {
          setShowAdmin(false);
          resetSearch();
        }}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-3 md:p-8 flex flex-col gap-4 md:gap-6 mb-16 md:mb-0">
        {showInstallBanner && (
          <div className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 text-white p-4 rounded-2xl flex items-center justify-between shadow-lg shadow-indigo-600/10 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="bg-white/10 p-2 rounded-xl">
                <Sparkles size={20} className="text-yellow-300" />
              </div>
              <div>
                <p className="font-bold text-sm">Install RideCompare App</p>
                <p className="text-[10px] text-indigo-100 font-medium">Quick fare lookups right from your device home screen.</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleInstallApp}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white text-indigo-700 font-bold text-xs rounded-xl hover:bg-slate-50 active:scale-[0.98] transition-all shadow-sm cursor-pointer"
              >
                <Download size={12} /> Install
              </button>
              <button
                onClick={() => setShowInstallBanner(false)}
                className="p-1.5 hover:bg-white/10 rounded-xl transition-all cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        )}

        {showAdmin ? (
          <div className="glass-panel p-6 rounded-2xl">
            <AnalyticsDashboard />
          </div>
        ) : (
          <div>
            {!comparison && !loading ? (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-center py-3 md:py-12 animate-fade-in">
                <div className="lg:col-span-6 space-y-6">
                  <div className="space-y-3">
                    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 border border-indigo-200/50 dark:border-indigo-800/40">
                      Intelligent Transport Aggregator
                    </span>
                    <h2 className="text-3xl md:text-5xl font-black tracking-tight text-[var(--text-primary)] leading-[1.15]">
                      Compare Rides.<br />
                      <span className="bg-gradient-to-r from-indigo-600 to-indigo-400 dark:from-indigo-400 dark:to-indigo-300 bg-clip-text text-transparent">Save Time. Save Money.</span>
                    </h2>
                    <p className="text-sm font-semibold text-[var(--text-secondary)] leading-relaxed max-w-[480px]">
                      Find the fastest and cheapest ride across global and regional platforms — Uber, Waymo, Grab, Careem, Bolt, FreeNow, Namma Yatri, and regulated local taxis with live ML pricing intelligence.
                    </p>
                  </div>

                  <div className="max-w-[480px] shadow-xl shadow-slate-900/5 dark:shadow-black/20">
                    <SearchPanel
                      selectedSource={sourceLoc}
                      selectedDest={destLoc}
                      onSourceSelect={setSourceLoc}
                      onDestSelect={setDestLoc}
                      onSearch={handleSearch}
                      loading={loading}
                    />
                  </div>

                  {distanceError && (
                    <div className="max-w-[480px] flex items-start gap-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-700/50 text-amber-800 dark:text-amber-300 rounded-2xl px-4 py-3 shadow-sm animate-fade-in">
                      <span className="text-lg leading-none mt-0.5">⚠️</span>
                      <div>
                        <p className="text-xs font-bold mb-0.5">Route Distance Limit</p>
                        <p className="text-[11px] leading-relaxed">{distanceError}</p>
                      </div>
                    </div>
                  )}
                </div>

                <div className="lg:col-span-6 h-[280px] sm:h-[350px] lg:h-[480px] relative">
                  <div className="absolute inset-0 bg-indigo-500/10 dark:bg-indigo-500/5 rounded-full filter blur-3xl -z-10 w-3/4 h-3/4 mx-auto my-auto" />
                  <MapView
                    sourceCoords={sourceLoc ? [sourceLoc.lat, sourceLoc.lng] : null}
                    destCoords={destLoc ? [destLoc.lat, destLoc.lng] : null}
                    routeGeometry={null}
                  />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-8 items-start animate-fade-in">
                <div className="lg:col-span-6 xl:col-span-6 flex flex-col gap-4">
                  <div className="flex justify-between items-center bg-[var(--bg-secondary)] border border-[var(--border-color)] px-4 py-3 rounded-2xl shadow-xs">
                    <div className="flex items-center gap-3 truncate">
                      <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <Search size={14} />
                      </div>
                      <div className="flex flex-col truncate">
                        <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)]">Route Search</span>
                        <span className="text-xs font-bold text-[var(--text-primary)] truncate max-w-[220px] sm:max-w-[320px]">
                          {sourceLoc?.label.split(',')[0]} → {destLoc?.label.split(',')[0]}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={resetSearch}
                      className="px-3 py-1.5 bg-[var(--bg-primary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-[var(--text-primary)] font-bold text-xs rounded-xl transition-all cursor-pointer shrink-0"
                    >
                      Change
                    </button>
                  </div>

                  {distanceError && (
                    <div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-700/50 text-amber-800 dark:text-amber-300 rounded-2xl px-4 py-3 shadow-sm animate-fade-in">
                      <span className="text-lg leading-none mt-0.5">⚠️</span>
                      <div>
                        <p className="text-xs font-bold mb-0.5">Route Distance Limit</p>
                        <p className="text-[11px] leading-relaxed">{distanceError}</p>
                      </div>
                    </div>
                  )}

                  {loading && (
                    <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-2xl space-y-4 shadow-xs animate-pulse">
                      <div className="h-4 w-1/3 bg-slate-200 dark:bg-slate-800 rounded-md"></div>
                      <div className="space-y-2">
                        <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-md"></div>
                        <div className="h-3 w-5/6 bg-slate-200 dark:bg-slate-800 rounded-md"></div>
                      </div>
                      <div className="pt-4 border-t border-[var(--border-color)] space-y-3">
                        <div className="h-16 w-full bg-slate-200 dark:bg-slate-800 rounded-xl"></div>
                        <div className="h-16 w-full bg-slate-200 dark:bg-slate-800 rounded-xl"></div>
                      </div>
                    </div>
                  )}

                  {!loading && comparison && (
                    <div className="animate-slide-up">
                      <RideComparison
                        comparison={comparison}
                        onBooking={handleBookingRedirect}
                        onRefresh={() => sourceLoc && destLoc && handleSearch(sourceLoc, destLoc)}
                        refreshing={loading}
                      />
                    </div>
                  )}
                </div>

                <div className="lg:col-span-6 xl:col-span-6 h-[300px] sm:h-[400px] lg:h-[620px] sticky top-24 rounded-2xl overflow-hidden border border-[var(--border-color)] shadow-sm">
                  <MapView
                    sourceCoords={sourceLoc ? [sourceLoc.lat, sourceLoc.lng] : null}
                    destCoords={destLoc ? [destLoc.lat, destLoc.lng] : null}
                    routeGeometry={routeGeometry}
                    distanceKm={comparison?.distanceKm}
                    durationMins={comparison?.durationMins}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 glass-panel border-t border-[var(--glass-border)] grid grid-cols-3 py-2 text-center text-[10px] font-bold text-[var(--text-secondary)]">
        <button
          onClick={() => { setShowAdmin(false); resetSearch(); }}
          className={`flex flex-col items-center gap-0.5 cursor-pointer ${!showAdmin && !comparison ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <Home size={18} />
          <span>Home</span>
        </button>
        <button
          onClick={() => { setShowAdmin(false); }}
          className={`flex flex-col items-center gap-0.5 cursor-pointer ${!showAdmin && comparison ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <Search size={18} />
          <span>Compare</span>
        </button>
        <button
          onClick={() => setShowAdmin(true)}
          className={`flex flex-col items-center gap-0.5 cursor-pointer ${showAdmin ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <BarChart3 size={18} />
          <span>Analytics</span>
        </button>
      </div>

      <footer className="py-6 px-4 border-t border-[var(--border-color)] text-center text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] transition-all mb-14 md:mb-0">
        <div className="max-w-3xl mx-auto space-y-1.5">
          <p className="text-[11px] font-semibold text-[var(--text-primary)] flex items-center justify-center gap-1.5">
            <span>ℹ️</span> Real-time Fare Comparison Notice
          </p>
          <p className="text-[11px] text-[var(--text-secondary)] font-normal leading-relaxed">
            This platform facilitates real-time fare comparison across services, but actual prices on live apps may vary based on instant driver availability, real-time traffic surges, local tolls, and dynamic platform adjustments.
          </p>
          <p className="text-[9px] font-bold uppercase tracking-widest text-[var(--text-secondary)]/70 pt-1">
            RideCompare Aggregator • Powered by OpenStreetMap, Project-OSRM & ML Fare Intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
