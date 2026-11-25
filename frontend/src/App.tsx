import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import { Navbar } from './components/Navbar';
import { SearchPanel } from './components/SearchPanel';
import { MapView } from './components/MapView';
import { RideComparison } from './components/RideComparison';
import { About } from './components/About';
import { RoutesIndexPage, RouteDetailPage, BlogIndexPage, BlogPostPage } from './components/SeoPages';
import type { MapSelectionMode } from './components/MapView';
import { Download, X, Search, BarChart3, Home, Lock } from 'lucide-react';
import type { ComparisonResult, LocationInfo, RouteGeometry, RideProviderDetails } from './types/ride';
import { apiFetch } from './utils/api';
import { reverseGeocodeLocation } from './utils/locationService';

const PlatformAnalyticsDashboard = lazy(() =>
  import('./components/PlatformAnalyticsDashboard').then((m) => ({ default: m.PlatformAnalyticsDashboard }))
);
const InternalMLDashboard = lazy(() =>
  import('./components/InternalMLDashboard').then((m) => ({ default: m.InternalMLDashboard }))
);
const RateCardAdmin = lazy(() =>
  import('./components/RateCardAdmin').then((m) => ({ default: m.RateCardAdmin }))
);
const FareSurgeTracker = lazy(() =>
  import('./components/FareSurgeTracker').then((m) => ({ default: m.FareSurgeTracker }))
);
const FareIntelligence = lazy(() =>
  import('./components/FareIntelligence').then((m) => ({ default: m.FareIntelligence }))
);

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
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window === 'undefined') return true;
    const saved = localStorage.getItem('ridecompare.theme');
    return saved ? saved === 'dark' : true;
  });
  const [showAdmin, setShowAdmin] = useState(() => {
    if (typeof window === 'undefined') return false;
    const params = new URLSearchParams(window.location.search);
    return params.get('admin') === 'ml' || params.get('tab') === 'ml' || params.get('admin') === 'true' || params.get('view') === 'admin';
  });
  const [showSurgeTracker, setShowSurgeTracker] = useState(() => {
    if (typeof window === 'undefined') return false;
    return new URLSearchParams(window.location.search).get('view') === 'surge';
  });
  const [showFareIntelligence, setShowFareIntelligence] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [currentPath, setCurrentPath] = useState(() =>
    typeof window === 'undefined' ? '/' : window.location.pathname.replace(/\/+$/, '') || '/'
  );

  const navigateTo = useCallback((path: string) => {
    const normalized = path.replace(/\/+$/, '') || '/';
    if (typeof window !== 'undefined' && window.location.pathname !== normalized) {
      window.history.pushState({}, '', normalized);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    setCurrentPath(normalized);
  }, []);

  useEffect(() => {
    const onPopState = () => {
      setCurrentPath(window.location.pathname.replace(/\/+$/, '') || '/');
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);
  const [adminTab, setAdminTab] = useState<'rate-cards' | 'analytics' | 'ml'>(() => {
    if (typeof window === 'undefined') return 'rate-cards';
    const params = new URLSearchParams(window.location.search);
    if (params.get('admin') === 'ml' || params.get('tab') === 'ml') return 'ml';
    if (params.get('tab') === 'analytics') return 'analytics';
    return 'rate-cards';
  });
  const [loading, setLoading] = useState(false);
  const [distanceError, setDistanceError] = useState<string | null>(null);

  const [searchId, setSearchId] = useState<number | null>(null);
  const [sourceLoc, setSourceLoc] = useState<LocationInfo | null>(null);
  const [destLoc, setDestLoc] = useState<LocationInfo | null>(null);
  const [mapSelectionMode, setMapSelectionMode] = useState<MapSelectionMode>(null);
  const [routeGeometry, setRouteGeometry] = useState<RouteGeometry | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [searchPanelKey, setSearchPanelKey] = useState(0);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const lastSearchedRoute = useRef('');

  const handleMapLocationSelect = useCallback(async (
    mode: Exclude<MapSelectionMode, null>,
    coords: [number, number]
  ) => {
    const [lat, lng] = coords;
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      return;
    }

    try {
      const location = await reverseGeocodeLocation(lat, lng);
      const resolved = location || {
        label: `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
        lat,
        lng,
        address: {}
      };
      if (mode === 'pickup') {
        setSourceLoc(resolved);
      } else {
        setDestLoc(resolved);
      }
      setSearchPanelKey(key => key + 1);
    } finally {
      setMapSelectionMode(null);
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
    }
    root.style.colorScheme = darkMode ? 'dark' : 'light';
    localStorage.setItem('ridecompare.theme', darkMode ? 'dark' : 'light');
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

  const handleSearch = useCallback(async (source: LocationInfo, dest: LocationInfo, departAt?: string) => {
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
      // 1. Query Statutory Fare & Availability Engine (/api/estimate)
      const estimateRes = await apiFetch('/api/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pickup: { lat: source.lat, lng: source.lng, address: source.label },
          drop: { lat: dest.lat, lng: dest.lng, address: dest.label },
          depart_at: departAt || new Date().toISOString()
        })
      });

      if (estimateRes.status === 422) {
        const errPayload = await estimateRes.json().catch(() => ({}));
        const msg = errPayload.detail?.message || errPayload.message || 'Ride services are not available in this area.';
        setDistanceError(msg);
        setComparison(null);
        setLoading(false);
        return;
      }

      if (!estimateRes.ok) {
        const errPayload = await estimateRes.json().catch(() => ({}));
        const msg = errPayload.detail?.message || errPayload.detail || errPayload.message || 'Failed to estimate ride fares.';
        setDistanceError(typeof msg === 'string' ? msg : JSON.stringify(msg));
        setComparison(null);
        setLoading(false);
        return;
      }

      const data = await estimateRes.json();

      const providersList: RideProviderDetails[] = (data.available_services || []).map((s: any) => ({
        provider: s.service,
        vehicleType: s.vehicle_category || 'Cab',
        distanceKm: data.distance_km,
        etaMinutes: s.eta_minutes || 5,
        actualFare: s.realtime_rate || null,
        estimatedFare: s.realtime_rate || Math.round((s.low + s.high) / 2),
        fareMin: s.low,
        fareMax: s.high,
        fare_min: s.low,
        fare_max: s.high,
        low: s.low,
        high: s.high,
        realtime_rate: s.realtime_rate || Math.round((s.low + s.high) / 2),
        current_surge: s.current_surge || 1.0,
        currency: s.currency,
        currencySymbol: s.currency_symbol || '₹',
        surgeMultiplier: s.current_surge || s.surge_high || 1.0,
        legal_surge_cap: s.legal_surge_cap,
        costPerKm: Math.round(s.low / Math.max(1, data.distance_km)),
        costPerMin: Math.round(s.low / Math.max(1, data.duration_min)),
        baseFare: 0,
        distanceFare: 0,
        durationFare: 0,
        platformFee: 0,
        tollEstimate: 0,
        appDeepLink: s.deeplink,
        deeplink: s.deeplink,
        webLink: s.web_link,
        isCheapest: s.is_cheapest,
        isFastest: s.is_fastest,
        isMostEfficient: false,
        isBestValue: s.is_cheapest,
        rate_card_verified_at: s.rate_card_verified_at,
        is_verified: s.is_verified,
        eligibility: 'DIRECT'
      }));

      const compResult: ComparisonResult = {
        distanceKm: data.distance_km,
        durationMins: data.duration_min,
        detectedCity: data.region_name || data.region,
        state: data.state,
        country: data.country,
        currency: providersList[0]?.currency || 'INR',
        currencySymbol: providersList[0]?.currencySymbol || '₹',
        isServiceable: data.reason_code !== 'OUT_OF_COVERAGE',
        message: data.notice || (data.fallback?.type === 'auto' ? data.fallback.message : undefined),
        notice: data.notice,
        reason_code: data.reason_code,
        fallback: data.fallback,
        disclaimer: data.disclaimer || 'Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes.',
        surgeRuleName: data.available_services?.[0]?.surge_period || 'Statutory Fare Engine',
        straightLineDistance: data.distance_km,
        detourDistance: 0,
        pricingRegime: 'Regulated Transport Rate Cards & Surge Caps',
        fareSpread: providersList.length > 1
          ? Math.max(0, (providersList[providersList.length - 1].high || 0) - (providersList[0].low || 0))
          : 0,
        spreadPercentage: 0,
        providers: providersList,
        directProviders: providersList,
        recommendations: {
          cheapest: providersList[0]?.provider || '',
          fastest: providersList.find(p => p.isFastest)?.provider || providersList[0]?.provider || '',
          mostEfficient: providersList[0]?.provider || '',
          bestValue: providersList[0]?.provider || '',
          recommendationReason: 'Prices estimated from statutory rate cards and legal aggregator caps.',
          distanceAdvantage: '',
          timeAdvantage: '',
          costAdvantage: ''
        },
        insights: [
          `Fares computed from verified rate cards under ${data.region_name || 'Regional'} transport guidelines.`,
          `Legal surge capped strictly at ${data.legal_surge_cap || 2.0}x base rate.`
        ]
      };

      setComparison(compResult);

      // 2. Fetch turn-by-turn geometry for the map
      try {
        const routeRes = await apiFetch(`/api/route?start=${source.lng},${source.lat}&end=${dest.lng},${dest.lat}`);
        if (routeRes.ok) {
          const routeData = await routeRes.json();
          if (routeData.geometry) {
            setRouteGeometry(routeData.geometry as RouteGeometry);
          }
        }
      } catch {
        setRouteGeometry({
          type: 'LineString',
          coordinates: [
            [source.lng, source.lat],
            [dest.lng, dest.lat]
          ]
        });
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '';
      setDistanceError(
        `Fare search could not be completed: ${errMsg || 'the service is unavailable'}. ` +
        'Please check that the backend is running.'
      );
      setComparison(null);
      setRouteGeometry(null);
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
        showSurgeTracker={showSurgeTracker}
        setShowSurgeTracker={setShowSurgeTracker}
        showFareIntelligence={showFareIntelligence}
        setShowFareIntelligence={setShowFareIntelligence}
        showAbout={showAbout}
        setShowAbout={setShowAbout}
        currentPath={currentPath}
        onNavigate={navigateTo}
        onLogoClick={() => {
          setShowAdmin(false);
          setShowSurgeTracker(false);
          setShowFareIntelligence(false);
          setShowAbout(false);
          navigateTo('/');
          resetSearch();
        }}
      />

      <main className={`flex-1 w-full flex flex-col mb-16 md:mb-0 ${showSurgeTracker ? '' : 'max-w-7xl mx-auto p-4 md:p-10 gap-4 md:gap-8'}`}>
        {showInstallBanner && (
          <div className="w-full border border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-primary)] p-4 rounded-xl flex items-center justify-between shadow-sm animate-fade-in">
            <div className="flex items-center gap-3">
              <div>
                <p className="font-bold text-sm">Install RideCompare App</p>
                <p className="text-[10px] text-[var(--text-secondary)] font-medium">Quick fare lookups from your device home screen.</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleInstallApp}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--accent-color)] text-white font-bold text-xs rounded-lg hover:bg-[var(--accent-hover)] transition-colors cursor-pointer"
              >
                <Download size={12} /> Install
              </button>
              <button
                onClick={() => setShowInstallBanner(false)}
                className="p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] rounded-lg transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        )}

        {currentPath === '/routes' ? (
          <RoutesIndexPage onNavigate={navigateTo} />
        ) : currentPath.startsWith('/routes/') ? (
          <RouteDetailPage slug={currentPath.replace('/routes/', '')} onNavigate={navigateTo} />
        ) : currentPath === '/blog' ? (
          <BlogIndexPage onNavigate={navigateTo} />
        ) : currentPath.startsWith('/blog/') ? (
          <BlogPostPage slug={currentPath.replace('/blog/', '')} onNavigate={navigateTo} />
        ) : showAbout ? (
          <About />
        ) : showFareIntelligence ? (
          <Suspense fallback={<div className="p-8 text-center text-xs text-[var(--text-secondary)]">Loading Fare Intelligence...</div>}>
            <FareIntelligence />
          </Suspense>
        ) : showSurgeTracker ? (
          <Suspense fallback={<div className="p-8 text-center text-xs text-[var(--text-secondary)]">Loading Surge Tracker...</div>}>
            <FareSurgeTracker />
          </Suspense>
        ) : showAdmin ? (
          <div className="space-y-4">
            <div className="glass-panel p-6 rounded-2xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-[var(--border-color)] gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => setAdminTab('rate-cards')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${adminTab === 'rate-cards'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-white'
                      }`}
                  >
                    Statutory Rate Cards & Statuses
                  </button>
                  <button
                    onClick={() => setAdminTab('analytics')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${adminTab === 'analytics'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-white'
                      }`}
                  >
                    Platform Analytics
                  </button>
                  <button
                    onClick={() => {
                      const pin = window.prompt("Enter Internal Developer Passcode:");
                      if (pin === "admin" || pin === "dev123" || pin === "ridecompare") {
                        setAdminTab('ml');
                      } else if (pin !== null) {
                        alert("Access denied. Invalid credentials.");
                      }
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1 ${adminTab === 'ml'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-white'
                      }`}
                  >
                    <Lock size={11} /> Model Telemetry
                  </button>
                </div>
                <button
                  onClick={() => setShowAdmin(false)}
                  className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline px-2 py-1 cursor-pointer"
                >
                  ← Return to Fare Comparison
                </button>
              </div>

              <Suspense fallback={<div className="p-6 text-center text-xs text-[var(--text-secondary)]">Loading dashboard...</div>}>
                {adminTab === 'rate-cards' ? (
                  <RateCardAdmin />
                ) : adminTab === 'analytics' ? (
                  <PlatformAnalyticsDashboard />
                ) : (
                  <InternalMLDashboard onExit={() => setAdminTab('rate-cards')} />
                )}
              </Suspense>
            </div>
          </div>
        ) : (
          <div>
            {!comparison && !loading ? (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6 lg:gap-8 items-start py-3 md:py-12 animate-fade-in">
                <div className="md:col-span-6 space-y-6">
                  <div className="space-y-4">
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-semibold tracking-wide bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)]">
                      Ride comparison
                    </span>
                    <h2 className="text-4xl md:text-6xl font-bold tracking-[-0.05em] text-[var(--text-primary)] leading-[1.05]">
                      Compare Rides.<br />
                      <span className="text-[var(--text-secondary)]">Save time and money.</span>
                    </h2>
                    <p className="text-sm font-medium text-[var(--text-secondary)] leading-relaxed max-w-[480px]">
                      Compare route-aware fare estimates, ETAs, and configured local ride services in one place.
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

                <div className="md:col-span-6 h-[380px] sm:h-[440px] lg:h-[520px] relative md:sticky md:top-24">
                  <div className="absolute inset-0 bg-indigo-500/10 dark:bg-indigo-500/5 rounded-full filter blur-3xl -z-10 w-3/4 h-3/4 mx-auto my-auto" />
                  <MapView
                    sourceCoords={sourceLoc ? [sourceLoc.lat, sourceLoc.lng] : null}
                    destCoords={destLoc ? [destLoc.lat, destLoc.lng] : null}
                    routeGeometry={null}
                    selectionMode={mapSelectionMode}
                    onSelectionModeChange={setMapSelectionMode}
                    onMapLocationSelect={handleMapLocationSelect}
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
                    selectionMode={mapSelectionMode}
                    onSelectionModeChange={setMapSelectionMode}
                    onMapLocationSelect={handleMapLocationSelect}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 glass-panel border-t border-[var(--glass-border)] grid grid-cols-3 py-2 text-center text-[10px] font-bold text-[var(--text-secondary)]">
        <button
          onClick={() => { setShowAdmin(false); setShowSurgeTracker(false); setShowFareIntelligence(false); setShowAbout(false); resetSearch(); }}
          className={`flex flex-col items-center gap-0.5 cursor-pointer ${!showAdmin && !comparison ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <Home size={18} />
          <span>Home</span>
        </button>
        <button
          onClick={() => { setShowAdmin(false); setShowSurgeTracker(false); setShowFareIntelligence(false); setShowAbout(false); }}
          className={`flex flex-col items-center gap-0.5 cursor-pointer ${!showAdmin && comparison ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <Search size={18} />
          <span>Compare</span>
        </button>
        <button
          onClick={() => {
            setShowAdmin(false);
            setShowSurgeTracker(false);
            setShowFareIntelligence(true);
            setShowAbout(false);
          }}
          className={`flex flex-col items-center gap-0.5 cursor-pointer ${showFareIntelligence ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <BarChart3 size={18} />
          <span>Fare Intelligence</span>
        </button>
      </div>

      <footer id="about" className="py-6 px-4 border-t border-[var(--border-color)] text-center text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] transition-all mb-14 md:mb-0">
        <div className="max-w-4xl mx-auto space-y-3">
          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] font-semibold">
            <a href="/routes" onClick={(e) => { e.preventDefault(); navigateTo('/routes'); }} className="hover:text-[var(--accent-color)]">
              All Route Fares
            </a>
            <a href="/routes/kochi-airport-to-alappuzha-taxi-fare" onClick={(e) => { e.preventDefault(); navigateTo('/routes/kochi-airport-to-alappuzha-taxi-fare'); }} className="hover:text-[var(--accent-color)]">
              Kochi Airport to Alappuzha
            </a>
            <a href="/routes/bangalore-airport-to-koramangala-taxi-fare" onClick={(e) => { e.preventDefault(); navigateTo('/routes/bangalore-airport-to-koramangala-taxi-fare'); }} className="hover:text-[var(--accent-color)]">
              Bangalore Airport to Koramangala
            </a>
            <a href="/blog" onClick={(e) => { e.preventDefault(); navigateTo('/blog'); }} className="hover:text-[var(--accent-color)]">
              Travel &amp; Fare Guides
            </a>
            <a href="/blog/uber-vs-ola-vs-rapido-in-kerala" onClick={(e) => { e.preventDefault(); navigateTo('/blog/uber-vs-ola-vs-rapido-in-kerala'); }} className="hover:text-[var(--accent-color)]">
              Uber vs Ola vs Rapido in Kerala
            </a>
            <a href="/blog/how-surge-pricing-works" onClick={(e) => { e.preventDefault(); navigateTo('/blog/how-surge-pricing-works'); }} className="hover:text-[var(--accent-color)]">
              How Surge Pricing Works
            </a>
          </div>
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
