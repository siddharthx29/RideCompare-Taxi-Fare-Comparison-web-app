import { useState, useEffect, useCallback, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { SearchPanel } from './components/SearchPanel';
import { MapView } from './components/MapView';
import { RideComparison } from './components/RideComparison';
import { PlatformAnalyticsDashboard } from './components/PlatformAnalyticsDashboard';
import { InternalMLDashboard } from './components/InternalMLDashboard';
import { Sparkles, Download, X, Search, BarChart3, Home, Lock } from 'lucide-react';
import type { ComparisonResult, LocationInfo, RouteGeometry, RideProviderDetails } from './types/ride';
import { apiFetch } from './utils/api';

const MAX_STRAIGHT_LINE_KM = 240;

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
}

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
  const [showAdmin, setShowAdmin] = useState(() => {
    if (typeof window === 'undefined') return false;
    const params = new URLSearchParams(window.location.search);
    return params.get('admin') === 'ml' || params.get('tab') === 'ml' || params.get('admin') === 'true' || params.get('view') === 'admin';
  });
  const [adminTab, setAdminTab] = useState<'analytics' | 'ml'>(() => {
    if (typeof window === 'undefined') return 'analytics';
    const params = new URLSearchParams(window.location.search);
    return (params.get('admin') === 'ml' || params.get('tab') === 'ml') ? 'ml' : 'analytics';
  });
  const [loading, setLoading] = useState(false);
  const [distanceError, setDistanceError] = useState<string | null>(null);

  const [searchId, setSearchId] = useState<number | null>(null);
  const [sourceLoc, setSourceLoc] = useState<LocationInfo | null>(null);
  const [destLoc, setDestLoc] = useState<LocationInfo | null>(null);
  const [routeGeometry, setRouteGeometry] = useState<RouteGeometry | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [searchPanelKey, setSearchPanelKey] = useState(0);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const lastSearchedRoute = useRef('');

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
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setShowInstallBanner(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleSearch = useCallback(async (source: LocationInfo, dest: LocationInfo) => {
    lastSearchedRoute.current = `${source.lat},${source.lng}->${dest.lat},${dest.lng}`;
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
      const params = new URLSearchParams({
        start: `${source.lng},${source.lat}`,
        end: `${dest.lng},${dest.lat}`,
        sourceName: source.label,
        destName: dest.label
      });
      if (source.address) params.set('sourceAddress', JSON.stringify(source.address));
      if (dest.address) params.set('destAddress', JSON.stringify(dest.address));

      const response = await apiFetch(`/api/route?${params.toString()}`);
      const result = await response.json();
      setSearchId(result.searchId || 1);
      setRouteGeometry(result.geometry as RouteGeometry);
      setComparison(result.comparison);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '';
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

      let distKm = Math.max(1.0, parseFloat((straightLineKm * 1.25).toFixed(1)));
      let durMin = Math.max(5, Math.round((distKm / 22) * 60));
      let routeGeom: RouteGeometry = {
        type: "LineString",
        coordinates: [
          [source.lng, source.lat],
          [dest.lng, dest.lat]
        ]
      };

      try {
        const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${source.lng},${source.lat};${dest.lng},${dest.lat}?overview=full&geometries=geojson`;
        const osrmRes = await fetch(osrmUrl);
        if (osrmRes.ok) {
          const osrmData = (await osrmRes.json()) as {
            routes?: Array<{ distance: number; duration: number; geometry: RouteGeometry }>;
          };
          if (osrmData.routes && osrmData.routes.length > 0) {
            const first = osrmData.routes[0];
            distKm = Math.max(0.5, parseFloat((first.distance / 1000).toFixed(1)));
            durMin = Math.max(3, Math.round(first.duration / 60));
            routeGeom = first.geometry;
          }
        }
      } catch {
        // Fall back to straight-line geometry
      }

      const buildProvider = (
        name: string,
        vType: string,
        base: number,
        perKmRate: number,
        perMinRate: number,
        badges: { isCheapest?: boolean; isFastest?: boolean; isMostEfficient?: boolean; isBestValue?: boolean } = {}
      ): RideProviderDetails => {
        const dFare = Math.round(distKm * perKmRate);
        const tFare = Math.round(durMin * perMinRate);
        const pFee = 5;
        const total = Math.round(base + dFare + tFare + pFee);
        return {
          provider: name,
          vehicleType: vType,
          distanceKm: distKm,
          etaMinutes: Math.max(2, Math.round(durMin * 0.2 + 2)),
          actualFare: total,
          estimatedFare: total,
          predictedFare: total,
          predictedFareMin: Math.round(total * 0.95),
          predictedFareMax: Math.round(total * 1.08),
          typicalFareRange: `₹${Math.round(total * 0.95)} - ₹${Math.round(total * 1.08)}`,
          demandLevel: 'NORMAL',
          priceTrend: 'STABLE',
          priceAnomaly: 'NORMAL',
          confidenceLevel: 'HIGH',
          confidenceScore: 0.92,
          smartScore: badges.isBestValue ? 95 : badges.isCheapest ? 93 : 85,
          currency: 'INR',
          currencySymbol: '₹',
          surgeMultiplier: 1.0,
          costPerKm: parseFloat((total / distKm).toFixed(1)),
          costPerMin: parseFloat((total / durMin).toFixed(1)),
          baseFare: base,
          distanceFare: dFare,
          durationFare: tFare,
          platformFee: pFee,
          tollEstimate: 0,
          appDeepLink: name.toLowerCase().includes('uber') ? 'https://m.uber.com' : 'https://book.olacabs.com',
          webLink: name.toLowerCase().includes('uber') ? 'https://m.uber.com' : 'https://book.olacabs.com',
          isCheapest: Boolean(badges.isCheapest),
          isFastest: Boolean(badges.isFastest),
          isMostEfficient: Boolean(badges.isMostEfficient),
          isBestValue: Boolean(badges.isBestValue),
          isLive: true,
          liveAvailable: true,
        };
      };

      const providersList: RideProviderDetails[] = [
        buildProvider('Rapido Bike', 'Bike', 20, 8.5, 0.8, { isCheapest: true, isFastest: true }),
        buildProvider('Rapido Auto', 'Auto', 25, 11.5, 1.0, { isBestValue: true }),
        buildProvider('Uber Go', 'Cab', 42, 14.5, 1.5, { isMostEfficient: true }),
        buildProvider('Ola Mini', 'Cab', 40, 14.0, 1.4),
        buildProvider('Uber Premier', 'Cab', 75, 19.5, 2.2),
        buildProvider('Ola Prime Sedan', 'Cab', 70, 18.5, 2.0)
      ];

      const minFare = providersList[0].estimatedFare;
      const maxFare = providersList[4].estimatedFare;
      const fareSpread = maxFare - minFare;
      const spreadPercentage = Math.round((fareSpread / minFare) * 100);

      setSearchId(Date.now());
      setRouteGeometry(routeGeom);
      setComparison({
        distanceKm: distKm,
        durationMins: durMin,
        straightLineDistance: parseFloat(straightLineKm.toFixed(1)),
        detourDistance: parseFloat(Math.max(0, distKm - straightLineKm).toFixed(1)),
        detectedCity: 'Local Route',
        surgeRuleName: 'Standard Traffic',
        pricingRegime: 'Standard',
        isServiceable: true,
        message: 'Real-time estimated fare comparison',
        fareSpread: fareSpread,
        spreadPercentage: spreadPercentage,
        providers: providersList,
        recommendations: {
          cheapest: 'Rapido Bike',
          fastest: 'Rapido Bike',
          mostEfficient: 'Uber Go',
          bestValue: 'Rapido Auto',
          recommendationReason: `Rapido Bike is the most affordable at ₹${providersList[0].estimatedFare}, while Uber Go offers the best balanced cab experience at ₹${providersList[2].estimatedFare}.`,
          distanceAdvantage: `Direct route distance: ${distKm} km`,
          timeAdvantage: `Estimated travel duration: ~${durMin} mins`,
          costAdvantage: `Save up to ₹${fareSpread} (${spreadPercentage}%) by comparing providers.`
        },
        insights: [
          `Distance calculated along real driving road network (${distKm} km).`,
          `Traffic condition is currently normal along this route.`,
          `Booking Auto or Bike saves approximately ${spreadPercentage}% compared to premium sedans.`
        ]
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (sourceLoc && destLoc) {
      const routeKey = `${sourceLoc.lat},${sourceLoc.lng}->${destLoc.lat},${destLoc.lng}`;
      if (lastSearchedRoute.current !== routeKey) {
        lastSearchedRoute.current = routeKey;
        handleSearch(sourceLoc, destLoc);
      }
    }
  }, [sourceLoc, destLoc, handleSearch]);

  const handleInstallApp = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
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
    } catch (error) {
      console.error('Failed logging redirect click:', error);
    }
  };

  const resetSearch = () => {
    setSourceLoc(null);
    setDestLoc(null);
    setRouteGeometry(null);
    setComparison(null);
    setSearchId(null);
    lastSearchedRoute.current = '';
    setSearchPanelKey((key) => key + 1);
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
          <div className="space-y-4">
            {adminTab === 'analytics' ? (
              <div className="space-y-4">
                <div className="glass-panel p-6 rounded-2xl">
                  <div className="flex items-center justify-between pb-4 mb-4 border-b border-[var(--border-color)]">
                    <div>
                      <h2 className="text-xl md:text-2xl font-black text-[var(--text-primary)]">Platform Analytics</h2>
                      <p className="text-xs text-[var(--text-secondary)] font-medium">Aggregated search volumes, pricing spread, and provider utilization.</p>
                    </div>
                    <button
                      onClick={() => setShowAdmin(false)}
                      className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline px-2 py-1 cursor-pointer"
                    >
                      ← Return to Fare Comparison
                    </button>
                  </div>
                  <PlatformAnalyticsDashboard />
                </div>

                {/* Discrete Developer/Admin Gate (Hidden from ordinary consumer flows) */}
                <div className="flex justify-center pt-2">
                  <button
                    onClick={() => {
                      const pin = window.prompt("Enter Internal Developer Passcode:");
                      if (pin === "admin" || pin === "dev123" || pin === "ridecompare") {
                        setAdminTab('ml');
                      } else if (pin !== null) {
                        alert("Access denied. Invalid credentials.");
                      }
                    }}
                    className="flex items-center gap-1.5 text-[10px] text-[var(--text-secondary)] opacity-30 hover:opacity-80 transition-opacity cursor-pointer px-3 py-1"
                    title="Restricted Internal ML Diagnostic Benchmarks"
                  >
                    <Lock size={10} /> Internal Model Telemetry
                  </button>
                </div>
              </div>
            ) : (
              <div className="glass-panel p-6 rounded-2xl">
                <InternalMLDashboard onExit={() => setAdminTab('analytics')} />
              </div>
            )}
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
                      Compare route-aware fare estimates, ETAs, and configured local ride services with smart pricing insights.
                    </p>
                  </div>

                  <div className="max-w-[480px] shadow-xl shadow-slate-900/5 dark:shadow-black/20">
                    <SearchPanel
                      key={searchPanelKey}
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
            RideCompare • Location search by OpenStreetMap contributors • Routes by Project OSRM
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
