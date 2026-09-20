import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { SearchPanel } from './components/SearchPanel';
import { MapView } from './components/MapView';
import { RideComparison } from './components/RideComparison';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { Sparkles, Download, X, Search, BarChart3, Home } from 'lucide-react';
import type { ComparisonResult } from '../../backend/src/services/types';
import { apiFetch } from './utils/api';

interface LocationInfo {
  label: string;
  lat: number;
  lng: number;
}

function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [showAdmin, setShowAdmin] = useState(false);
  const [loading, setLoading] = useState(false);

  // Search details states
  const [searchId, setSearchId] = useState<number | null>(null);
  const [sourceLoc, setSourceLoc] = useState<LocationInfo | null>(null);
  const [destLoc, setDestLoc] = useState<LocationInfo | null>(null);
  const [routeGeometry, setRouteGeometry] = useState<any | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);

  // Coords tracking for auto-routing cache triggers
  const [lastSearchedSource, setLastSearchedSource] = useState<string>('');
  const [lastSearchedDest, setLastSearchedDest] = useState<string>('');

  // PWA install states
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);

  // Sync dark mode class on document element
  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [darkMode]);

  // Listen for PWA install prompt
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallBanner(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  // Effect to automatically route when both pickup and destination locations are chosen
  useEffect(() => {
    if (sourceLoc && destLoc) {
      const sourceKey = `${sourceLoc.lat},${sourceLoc.lng}`;
      const destKey = `${destLoc.lat},${destLoc.lng}`;
      if (lastSearchedSource !== sourceKey || lastSearchedDest !== destKey) {
        if (import.meta.env.DEV) {
          console.log(`[Auto-Route Effect] Both locations selected. Triggering query: "${sourceLoc.label}" -> "${destLoc.label}"`);
        }
        setLastSearchedSource(sourceKey);
        setLastSearchedDest(destKey);
        handleSearch(sourceLoc, destLoc);
      }
    }
  }, [sourceLoc, destLoc, lastSearchedSource, lastSearchedDest]);

  const handleInstallApp = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`PWA Installation outcome: ${outcome}`);
    setDeferredPrompt(null);
    setShowInstallBanner(false);
  };

  const handleSearch = async (source: LocationInfo, dest: LocationInfo) => {
    if (import.meta.env.DEV) {
      console.log(`[Search Flow] Initiating route comparison search:`, { source, dest });
    }
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

      if (import.meta.env.DEV) {
        console.log(`[Search Flow] Querying relative API: ${url}`);
      }

      const response = await apiFetch(url);
      const result = await response.json();
      if (import.meta.env.DEV) {
        console.log(`[Search Flow] Search calculation results:`, result);
      }
      setSearchId(result.searchId);
      setRouteGeometry(result.geometry);
      setComparison(result.comparison);
    } catch (err: any) {
      console.error('[Search Flow] Routing error:', err);
      alert(`Routing error: ${err.message || err}. Using straight-line fallback approximations.`);
    } finally {
      setLoading(false);
    }
  };

  const handleBookingRedirect = async (provider: string, fare: number) => {
    try {
      if (import.meta.env.DEV) {
        console.log(`[Booking Redirect] User selected ${provider} (fare: ${fare}). Logging event...`);
      }
      await apiFetch('/api/redirect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          searchId,
          provider,
          fare
        })
      });
    } catch (err) {
      console.error('Failed logging redirect click:', err);
    }
  };

  const resetSearch = () => {
    if (import.meta.env.DEV) {
      console.log('[Search Flow] Resetting search terms and map view...');
    }
    setSourceLoc(null);
    setDestLoc(null);
    setRouteGeometry(null);
    setComparison(null);
    setSearchId(null);
    setLastSearchedSource('');
    setLastSearchedDest('');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-primary)] transition-all">
      {/* Navigation Header */}
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

      {/* Main Workspace Frame */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-3 md:p-8 flex flex-col gap-4 md:gap-6 mb-16 md:mb-0">
        
        {/* PWA Install Banner */}
        {showInstallBanner && (
          <div className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 text-white p-4 rounded-2xl flex items-center justify-between shadow-lg shadow-indigo-600/10 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="bg-white/10 p-2 rounded-xl">
                <Sparkles size={20} className="text-yellow-300" />
              </div>
              <div>
                <p className="font-bold text-sm">Install RideCompare App</p>
                <p className="text-[10px] text-indigo-100 font-medium">Access prices directly from your home screen on iOS and Android.</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={handleInstallApp}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white text-indigo-700 font-bold text-xs rounded-xl hover:bg-slate-50 active:scale-[0.98] transition-all shadow-sm"
              >
                <Download size={12} /> Install
              </button>
              <button 
                onClick={() => setShowInstallBanner(false)}
                className="p-1.5 hover:bg-white/10 rounded-xl transition-all"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        )}

        {showAdmin ? (
          /* Admin Analytics View */
          <div className="glass-panel p-6 rounded-2xl">
            <AnalyticsDashboard />
          </div>
        ) : (
          /* Ride Compare App Interface */
          <div>
            {!comparison && !loading ? (
              /* LANDING HERO VIEW (Before route search is triggered) */
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-center py-3 md:py-12 animate-fade-in">
                {/* Hero left details & search panel */}
                <div className="lg:col-span-6 space-y-6">
                  <div className="space-y-3">
                    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 border border-indigo-200/50 dark:border-indigo-800/40">
                      ⚡ Intelligent Transport Aggregator
                    </span>
                    <h2 className="text-3xl md:text-5xl font-black tracking-tight text-[var(--text-primary)] leading-[1.15]">
                      Compare Rides.<br />
                      <span className="bg-gradient-to-r from-indigo-600 to-indigo-400 dark:from-indigo-400 dark:to-indigo-300 bg-clip-text text-transparent">Save Time. Save Money.</span>
                    </h2>
                    <p className="text-sm font-semibold text-[var(--text-secondary)] leading-relaxed max-w-[480px]">
                      Find the fastest and cheapest ride across Uber, Rapido, Ola, and more in seconds. Calculate routes with precision mapping.
                    </p>
                  </div>

                  {/* Main Search Panel */}
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
                </div>

                {/* Hero right map container panel */}
                <div className="lg:col-span-6 h-[280px] sm:h-[350px] lg:h-[480px] relative">
                  {/* Glowing background ring decoration for startup aesthetic */}
                  <div className="absolute inset-0 bg-indigo-500/10 dark:bg-indigo-500/5 rounded-full filter blur-3xl -z-10 w-3/4 h-3/4 mx-auto my-auto" />
                  
                  {/* Interactive Map view */}
                  <MapView
                    sourceCoords={sourceLoc ? [sourceLoc.lat, sourceLoc.lng] : null}
                    destCoords={destLoc ? [destLoc.lat, destLoc.lng] : null}
                    routeGeometry={null}
                  />
                </div>
              </div>
            ) : (
              /* RESULTS SPLIT PANEL VIEW (After route search) */
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 items-stretch animate-fade-in">
                
                {/* Left side inputs and comparison cards */}
                <div className="lg:col-span-5 flex flex-col gap-6">
                  
                  {/* Header path details summary and return back */}
                  <div className="flex justify-between items-center bg-[var(--bg-secondary)] border border-[var(--border-color)] px-5 py-3 rounded-2xl">
                    <div className="flex flex-col truncate">
                      <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)]">Current Route</span>
                      <span className="text-xs font-bold text-[var(--text-primary)] truncate max-w-[260px]">
                        {sourceLoc?.label.split(',')[0]} → {destLoc?.label.split(',')[0]}
                      </span>
                    </div>
                    <button
                      onClick={resetSearch}
                      className="px-3 py-1.5 bg-[var(--bg-primary)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-[var(--text-primary)] font-bold text-[10px] rounded-xl transition-all flex items-center gap-1"
                    >
                      <Search size={12} /> Change
                    </button>
                  </div>

                  {/* Loader skeletons */}
                  {loading && (
                    <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-2xl space-y-4 shadow-sm animate-pulse">
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

                  {/* Comparisons rendering */}
                  {!loading && comparison && (
                    <div className="animate-slide-up">
                      <RideComparison
                        comparison={comparison}
                        onBooking={handleBookingRedirect}
                      />
                    </div>
                  )}
                </div>

                {/* Right side map routing render */}
                <div className="lg:col-span-7 h-[260px] sm:h-[350px] lg:h-[600px] sticky top-24">
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

      {/* MOBILE BOTTOM NAVIGATION PANEL */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 glass-panel border-t border-[var(--glass-border)] grid grid-cols-3 py-2 text-center text-[10px] font-bold text-[var(--text-secondary)]">
        <button 
          onClick={() => { setShowAdmin(false); resetSearch(); }}
          className={`flex flex-col items-center gap-0.5 ${!showAdmin && !comparison ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <Home size={18} />
          <span>Home</span>
        </button>
        <button 
          onClick={() => { setShowAdmin(false); }}
          className={`flex flex-col items-center gap-0.5 ${!showAdmin && comparison ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <Search size={18} />
          <span>Compare</span>
        </button>
        <button 
          onClick={() => setShowAdmin(true)}
          className={`flex flex-col items-center gap-0.5 ${showAdmin ? 'text-indigo-600 dark:text-indigo-400' : ''}`}
        >
          <BarChart3 size={18} />
          <span>Analytics</span>
        </button>
      </div>

      {/* Footer Branding */}
      <footer className="hidden md:block py-6 border-t border-[var(--border-color)] text-center text-[9px] font-bold uppercase tracking-widest text-[var(--text-secondary)] bg-[var(--bg-secondary)] transition-all">
        RideCompare Aggregator Portal • Powered by OpenStreetMap & OSRM Engine
      </footer>
    </div>
  );
}

export default App;
