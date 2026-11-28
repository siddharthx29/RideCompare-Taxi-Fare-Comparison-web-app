import React, { useState, useEffect } from 'react';
import {
  Zap, ArrowUpRight, ChevronDown, ChevronUp,
  Clock, Car, Bike, Navigation, ShieldCheck,
  RefreshCw, AlertCircle, Bot, TrendingUp,
  Activity, CheckCircle2, Route, AlertTriangle,
  ArrowRight, ShieldAlert, Layers
} from 'lucide-react';
import type { RideProviderDetails, ComparisonResult } from '../types/ride';
import { PriceHistoryGraph } from './PriceHistoryGraph';

interface RideComparisonProps {
  comparison: ComparisonResult;
  onBooking: (providerName: string, fare: number) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
  onSuggestPrice?: (provider: RideProviderDetails, suggestedFare: number) => Promise<boolean>;
}

export const RideComparison: React.FC<RideComparisonProps> = ({
  comparison,
  onBooking,
  onRefresh,
  refreshing = false,
  onSuggestPrice,
}) => {
  const {
    providers, insights, detectedCity,
    pricingRegime, fareSpread, spreadPercentage,
    directProviders, excludedProviders, partialProviders,
    multimodalOption, agentReasoning, routeClassification
  } = comparison;

  const defaultSym = comparison.currencySymbol || (comparison.currency === 'USD' ? '$' : comparison.currency === 'EUR' ? '€' : comparison.currency === 'GBP' ? '£' : '₹');

  // Segregate direct viable rides from excluded / partial rides
  const directList = (directProviders && directProviders.length > 0)
    ? directProviders
    : providers.filter(p => p.eligibility !== 'UNSUPPORTED' && p.eligibility !== 'PARTIAL');
  const excludedList = (excludedProviders && excludedProviders.length > 0)
    ? excludedProviders
    : providers.filter(p => p.eligibility === 'UNSUPPORTED');
  const partialList = (partialProviders && partialProviders.length > 0)
    ? partialProviders
    : providers.filter(p => p.eligibility === 'PARTIAL');

  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'recommended' | 'category' | 'price' | 'eta'>('recommended');
  const [vehicleFilter, setVehicleFilter] = useState<'ALL' | 'CAB' | 'AUTO' | 'BIKE' | 'ROBOTAXI'>('ALL');
  const [nowTimestamp, setNowTimestamp] = useState(0);
  const [showAuditDrawer, setShowAuditDrawer] = useState(true);
  const [suggestKey, setSuggestKey] = useState<string | null>(null);
  const [suggestAmount, setSuggestAmount] = useState('');
  const [suggestSaving, setSuggestSaving] = useState(false);
  const [suggestSubmitted, setSuggestSubmitted] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const timer = setInterval(() => {
      setNowTimestamp(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const getQuoteAge = (p: RideProviderDetails): number => {
    if (p.retrieved_at) {
      const dt = new Date(p.retrieved_at).getTime();
      if (nowTimestamp === 0) return p.quoteAgeSeconds || 0;
      return Math.max(0, Math.floor((nowTimestamp - dt) / 1000));
    }
    return Math.floor(p.quoteAgeSeconds || 0);
  };

  const toggleExpand = (providerName: string) => {
    setExpandedProvider(prev => prev === providerName ? null : providerName);
  };

  // Base list of rides: verified direct rides (or fallback if none verified)
  const baseProviders = directList.length > 0 ? directList : providers;
  const observedSnapshots = baseProviders
    .filter(p => p.referenceSnapshot)
    .map(p => p.referenceSnapshot as NonNullable<RideProviderDetails['referenceSnapshot']>);

  const getVehicleCategory = (p: RideProviderDetails): 'BIKE' | 'AUTO' | 'CAB' | 'ROBOTAXI' => {
    const type = (p.vehicleType || '').toUpperCase();
    const name = (p.provider || '').toUpperCase();
    const cat = (p.categoryTag || '').toUpperCase();
    if (cat.includes('AUTONOMOUS') || name.includes('WAYMO') || name.includes('ROBOTAXI')) return 'ROBOTAXI';
    if (type.includes('BIKE') || name.includes('BIKE') || name.includes('MOTO')) return 'BIKE';
    if (type.includes('AUTO') || name.includes('AUTO') || name.includes('TUK')) return 'AUTO';
    return 'CAB';
  };

  const categoryCounts = {
    ALL: baseProviders.length,
    CAB: baseProviders.filter(p => getVehicleCategory(p) === 'CAB').length,
    AUTO: baseProviders.filter(p => getVehicleCategory(p) === 'AUTO').length,
    BIKE: baseProviders.filter(p => getVehicleCategory(p) === 'BIKE').length,
  };

  const filteredProviders = baseProviders.filter(p => {
    if (vehicleFilter === 'ALL') return true;
    return getVehicleCategory(p) === vehicleFilter;
  });

  const sortedProviders = [...filteredProviders].sort((a, b) => {
    const fareForSort = (provider: RideProviderDetails) =>
      Number.isFinite(provider.actualFare)
        ? Number(provider.actualFare)
        : Number.isFinite(provider.estimatedFare)
        ? Number(provider.estimatedFare)
        : Number(provider.predictedFare || Number.POSITIVE_INFINITY);
    if (sortBy === 'category') {
      const rank: Record<string, number> = { BIKE: 0, AUTO: 1, CAB: 2, ROBOTAXI: 3 };
      const diff = (rank[getVehicleCategory(a)] ?? 9) - (rank[getVehicleCategory(b)] ?? 9);
      return diff !== 0 ? diff : fareForSort(a) - fareForSort(b);
    }
    if (sortBy === 'recommended') {
      return (
        Number(b.isBestValue) - Number(a.isBestValue)
        || Number(b.isCheapest) - Number(a.isCheapest)
        || fareForSort(a) - fareForSort(b)
        || a.etaMinutes - b.etaMinutes
      );
    } else if (sortBy === 'price') {
      return fareForSort(a) - fareForSort(b);
    } else {
      return a.etaMinutes - b.etaMinutes;
    }
  });

  const getProviderBrand = (name: string, vehicleType: string, isGovt?: boolean) => {
    const lowercase = name.toLowerCase();

    // Autonomous / Waymo
    if (lowercase.includes('waymo')) {
      return {
        badgeBg: 'bg-emerald-950 text-emerald-400 border-emerald-500/50',
        brandName: 'Waymo',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: <Bot size={18} className="text-emerald-300 animate-pulse" />,
        appName: 'Waymo One App'
      };
    }

    // Grab Southeast Asia
    if (lowercase.includes('grab')) {
      const isBike = lowercase.includes('bike');
      return {
        badgeBg: 'bg-emerald-600 text-white border-emerald-700',
        brandName: 'Grab',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: isBike ? <Bike size={18} /> : <Car size={18} />,
        appName: 'Grab Superapp'
      };
    }

    // Gojek
    if (lowercase.includes('gojek')) {
      const isBike = lowercase.includes('ride') || lowercase.includes('bike');
      return {
        badgeBg: 'bg-emerald-700 text-white border-emerald-800',
        brandName: 'Gojek',
        buttonClass: 'bg-emerald-700 hover:bg-emerald-800 text-white font-bold',
        icon: isBike ? <Bike size={18} /> : <Car size={18} />,
        appName: 'Gojek App'
      };
    }

    // Xanh SM Vietnam (VinFast Pure EV)
    if (lowercase.includes('xanh sm') || lowercase.includes('vinfast')) {
      return {
        badgeBg: 'bg-teal-500 text-white border-teal-600',
        brandName: 'Xanh SM (VinFast)',
        buttonClass: 'bg-teal-600 hover:bg-teal-700 text-white font-bold',
        icon: <Zap size={18} className="text-amber-300" />,
        appName: 'Taxi Xanh SM App'
      };
    }

    // Japan: GO App & S.RIDE
    if (lowercase.includes('go app') || lowercase.includes('nihon kotsu')) {
      return {
        badgeBg: 'bg-blue-600 text-white border-blue-700',
        brandName: 'GO Taxi Japan',
        buttonClass: 'bg-blue-600 hover:bg-blue-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'GO App'
      };
    }
    if (lowercase.includes('s.ride') || lowercase.includes('mk taxi')) {
      return {
        badgeBg: 'bg-amber-600 text-white border-amber-700',
        brandName: 'S.RIDE Tokyo',
        buttonClass: 'bg-amber-600 hover:bg-amber-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'S.RIDE App'
      };
    }

    // South Korea: Kakao T
    if (lowercase.includes('kakao')) {
      return {
        badgeBg: 'bg-yellow-400 text-zinc-950 border-yellow-500 font-extrabold',
        brandName: 'Kakao T',
        buttonClass: 'bg-yellow-400 hover:bg-yellow-500 text-zinc-950 font-bold',
        icon: <Car size={18} />,
        appName: 'Kakao T App'
      };
    }

    // UAE / Middle East: Dubai Taxi & Careem
    if (lowercase.includes('dubai taxi') || lowercase.includes('dtc') || lowercase.includes('rta')) {
      return {
        badgeBg: 'bg-red-600 text-white border-red-700',
        brandName: 'Dubai Taxi DTC',
        buttonClass: 'bg-red-600 hover:bg-red-700 text-white font-bold',
        icon: <ShieldCheck size={18} />,
        appName: 'DTC App'
      };
    }
    if (lowercase.includes('careem') || lowercase.includes('hala')) {
      return {
        badgeBg: 'bg-emerald-500 text-white border-emerald-600',
        brandName: 'Careem / Hala',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'Careem Super App'
      };
    }

    // Singapore: ComfortDelGro CDG Zig
    if (lowercase.includes('comfortdelgro') || lowercase.includes('cdg zig')) {
      return {
        badgeBg: 'bg-blue-700 text-white border-blue-800',
        brandName: 'CDG Zig Taxi',
        buttonClass: 'bg-blue-700 hover:bg-blue-800 text-white font-bold',
        icon: <ShieldCheck size={18} />,
        appName: 'CDG Zig App'
      };
    }

    // London Black Cab
    if (lowercase.includes('black cab') || lowercase.includes('tfl')) {
      return {
        badgeBg: 'bg-zinc-950 text-amber-400 border-amber-500/40 font-bold',
        brandName: 'TfL Black Cab',
        buttonClass: 'bg-zinc-900 hover:bg-black text-amber-400 font-bold border border-amber-500/30',
        icon: <Car size={18} />,
        appName: 'Gett / TfL Hail'
      };
    }

    // Paris Taxis G7
    if (lowercase.includes('g7') || lowercase.includes('parisiens')) {
      return {
        badgeBg: 'bg-rose-600 text-white border-rose-700',
        brandName: 'Taxis G7',
        buttonClass: 'bg-rose-600 hover:bg-rose-700 text-white font-bold',
        icon: <ShieldCheck size={18} />,
        appName: 'G7 Taxi App'
      };
    }

    // Spain / LatAm: Cabify
    if (lowercase.includes('cabify')) {
      return {
        badgeBg: 'bg-slate-700 text-white border-slate-600',
        brandName: 'Cabify',
        buttonClass: 'bg-slate-700 hover:bg-slate-600 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'Cabify App'
      };
    }

    // Brazil: 99
    if (lowercase.includes('99pop') || lowercase.includes('99taxi')) {
      return {
        badgeBg: 'bg-yellow-500 text-zinc-950 border-yellow-600 font-extrabold',
        brandName: '99 Brazil',
        buttonClass: 'bg-yellow-500 hover:bg-yellow-600 text-zinc-950 font-bold',
        icon: <Car size={18} />,
        appName: '99 App'
      };
    }

    // Australia: 13CABS
    if (lowercase.includes('13cabs')) {
      return {
        badgeBg: 'bg-orange-600 text-white border-orange-700',
        brandName: '13CABS',
        buttonClass: 'bg-orange-600 hover:bg-orange-700 text-white font-bold',
        icon: <ShieldCheck size={18} />,
        appName: '13CABS App'
      };
    }

    // FreeNow Europe
    if (lowercase.includes('freenow')) {
      return {
        badgeBg: 'bg-red-500 text-white border-red-600',
        brandName: 'FreeNow',
        buttonClass: 'bg-red-600 hover:bg-red-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'FreeNow App'
      };
    }

    // Bolt Europe & Africa
    if (lowercase.includes('bolt')) {
      return {
        badgeBg: 'bg-emerald-500 text-white border-emerald-600',
        brandName: 'Bolt',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'Bolt App'
      };
    }

    // Lyft
    if (lowercase.includes('lyft')) {
      return {
        badgeBg: 'bg-pink-600 text-white border-pink-700',
        brandName: 'Lyft',
        buttonClass: 'bg-pink-600 hover:bg-pink-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'Lyft App'
      };
    }

    // Revel EV
    if (lowercase.includes('revel')) {
      return {
        badgeBg: 'bg-sky-500 text-white border-sky-600',
        brandName: 'Revel EV',
        buttonClass: 'bg-sky-600 hover:bg-sky-700 text-white font-bold',
        icon: <Zap size={18} />,
        appName: 'Revel App'
      };
    }

    // India Govt / Open Mobility
    if (lowercase.includes('kerala savari')) {
      return {
        badgeBg: 'bg-emerald-700 text-white border-emerald-800',
        brandName: 'Kerala Savari',
        buttonClass: 'bg-emerald-700 hover:bg-emerald-800 text-white',
        icon: <ShieldCheck size={18} />,
        appName: 'Kerala Savari Portal'
      };
    }
    if (lowercase.includes('goamiles') || lowercase.includes('gtdc')) {
      return {
        badgeBg: 'bg-sky-600 text-white border-sky-700',
        brandName: 'GoaMiles / GTDC',
        buttonClass: 'bg-sky-600 hover:bg-sky-700 text-white',
        icon: <Car size={18} />,
        appName: 'GoaMiles App'
      };
    }
    if (lowercase.includes('yatri sathi')) {
      return {
        badgeBg: 'bg-teal-600 text-white border-teal-700',
        brandName: 'Yatri Sathi',
        buttonClass: 'bg-teal-600 hover:bg-teal-700 text-white',
        icon: <Navigation size={18} />,
        appName: 'Yatri Sathi App'
      };
    }
    if (lowercase.includes('namma yatri') || lowercase.includes('mana yatri')) {
      return {
        badgeBg: 'bg-amber-500 text-zinc-950 border-amber-600 font-bold',
        brandName: lowercase.includes('mana') ? 'Mana Yatri' : 'Namma Yatri',
        buttonClass: 'bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold',
        icon: <Navigation size={18} />,
        appName: 'Open Mobility App'
      };
    }
    if (lowercase.includes('red taxi') || lowercase.includes('fast track')) {
      return {
        badgeBg: 'bg-red-600 text-white border-red-700',
        brandName: lowercase.includes('red') ? 'Red Taxi' : 'Fast Track',
        buttonClass: 'bg-red-600 hover:bg-red-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'Taxi Booking'
      };
    }
    if (lowercase.includes('kaali peeli') || lowercase.includes('cool cab') || lowercase.includes('yellow taxi') || lowercase.includes('medallion') || lowercase.includes('metered')) {
      return {
        badgeBg: 'bg-yellow-500 text-zinc-950 border-yellow-600 font-bold',
        brandName: 'Metered Taxi',
        buttonClass: 'bg-zinc-800 hover:bg-zinc-900 text-yellow-400 font-bold border border-yellow-500/30',
        icon: <Car size={18} />,
        appName: 'Meter Taxi Stand'
      };
    }
    if (lowercase.includes('uber')) {
      return {
        badgeBg: 'bg-black text-white border-zinc-800',
        brandName: 'Uber',
        buttonClass: 'bg-black hover:bg-zinc-800 text-white dark:bg-white dark:text-black dark:hover:bg-zinc-200 font-bold',
        icon: <Car size={18} />,
        appName: 'Uber App'
      };
    }
    if (lowercase.includes('ola')) {
      return {
        badgeBg: 'bg-emerald-500 text-white border-emerald-600',
        brandName: 'Ola',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'Ola App'
      };
    }
    if (lowercase.includes('rapido')) {
      const isAuto = vehicleType.toLowerCase().includes('auto') || lowercase.includes('auto');
      const isCab = vehicleType.toLowerCase().includes('cab') || vehicleType.toLowerCase().includes('sedan') || lowercase.includes('cab');
      return {
        badgeBg: 'bg-amber-400 text-zinc-950 border-amber-500 font-extrabold',
        brandName: isCab ? 'Rapido Cabs' : isAuto ? 'Rapido Auto' : 'Rapido Bike',
        buttonClass: 'bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold',
        icon: isCab ? <Car size={18} /> : isAuto ? <Navigation size={18} /> : <Bike size={18} />,
        appName: isCab ? 'Rapido Cabs' : isAuto ? 'Rapido Auto' : 'Rapido Bike'
      };
    }
    if (lowercase.includes('indrive')) {
      return {
        badgeBg: 'bg-emerald-600 text-white border-emerald-700 font-extrabold',
        brandName: 'inDrive',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: <Car size={18} />,
        appName: 'inDrive App'
      };
    }
    if (isGovt) {
      return {
        badgeBg: 'bg-emerald-600 text-white border-emerald-700',
        brandName: 'State Regulated',
        buttonClass: 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold',
        icon: <ShieldCheck size={18} />,
        appName: 'Official Transit'
      };
    }
    return {
      badgeBg: 'bg-indigo-600 text-white border-indigo-700',
      brandName: 'Transit Fleet',
      buttonClass: 'bg-indigo-600 hover:bg-indigo-700 text-white font-bold',
      icon: <Car size={18} />,
      appName: 'Direct Booking'
    };
  };

  const hasValidDeepLink = (p: RideProviderDetails): boolean => {
    const deep = p.deeplink || p.appDeepLink || '';
    const web = p.webLink || '';
    if (deep.startsWith('tel:') || web === 'https://ridecompare.world') return false;
    return Boolean(
      deep.includes('lat') ||
      deep.includes('pickup') ||
      web.includes('lat') ||
      web.includes('pickup')
    );
  };

  const handleBook = (p: RideProviderDetails, e: React.MouseEvent) => {
    e.stopPropagation();
    onBooking(p.provider, p.low ?? p.fareMin ?? 0);
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const deep = p.deeplink || p.appDeepLink || '';
    const web = p.webLink || '';

    if (isMobile && deep) {
      window.location.href = deep;
      if (web) {
        window.setTimeout(() => {
          if (!document.hidden) {
            window.open(web, '_blank', 'noopener,noreferrer');
          }
        }, 1200);
      }
      return;
    }

    const desktopUrl = web || deep;
    if (desktopUrl) {
      window.open(desktopUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const cheapestProvider = baseProviders.find(p => p.isCheapest) || baseProviders[0];
  const activeSym = cheapestProvider?.currencySymbol || defaultSym;
  const hasRobotaxi = providers.some(p => (p.categoryTag || '').includes('Autonomous') || p.provider.includes('Waymo'));
  const routeType = routeClassification?.route_type || (comparison.distanceKm > 60 ? 'OUTSTATION' : comparison.distanceKm > 25 ? 'INTERCITY' : 'LOCAL');

  const formatRouteTypeLabel = (type: string) => {
    switch (type) {
      case 'OUTSTATION': return 'Outstation Long-Distance';
      case 'INTERCITY': return 'Intercity Transit';
      case 'AIRPORT_TRANSFER': return 'Airport Corridor';
      case 'MEDIUM_DISTANCE': return 'Regional / Suburb';
      case 'SHORT_DISTANCE': return 'Short Distance';
      case 'LOCAL': return 'Local City Route';
      default: return type.replace('_', ' ');
    }
  };

  // Case D Check: Intercity or Outstation ride
  if (comparison.reason_code === 'INTERCITY_TRIP') {
    return (
      <div className="p-6 bg-[var(--bg-secondary)] border border-amber-500/40 rounded-2xl text-center space-y-4 shadow-sm animate-fade-in">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-500/15 text-amber-500 flex items-center justify-center">
          <Route size={28} />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-bold text-[var(--text-primary)]">Intercity / Outstation Journey Detected</h3>
          <p className="text-sm text-[var(--text-secondary)] max-w-lg mx-auto leading-relaxed">
            {comparison.notice || 'Pickup and drop are in different cities or regions. Standard city-ride fares do not apply for intercity/outstation trips.'}
          </p>
        </div>
        <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl inline-flex items-center gap-4 text-xs text-[var(--text-secondary)]">
          <span>Distance: <strong className="text-[var(--text-primary)]">{comparison.distanceKm} km</strong></span>
          <span>•</span>
          <span>Estimated Duration: <strong className="text-[var(--text-primary)]">~{comparison.durationMins} mins</strong></span>
        </div>
        <div className="pt-2 text-xs text-amber-400/90 font-medium">
          Please check dedicated intercity / outstation options or intercity bus/rail connections for this route.
        </div>
        <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl text-center text-xs text-[var(--text-secondary)] font-medium">
          Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes.
        </div>
      </div>
    );
  }

  // Case B Check: Metered auto / local taxi only (no ride-hailing apps available)
  if (comparison.fallback?.type === 'auto' || comparison.reason_code === 'METERED_AUTO_ONLY') {
    const fb = comparison.fallback;
    const lowFare = fb?.low ?? fb?.estimate?.low ?? 30;
    const highFare = fb?.high ?? fb?.estimate?.high ?? 60;
    const currencySym = comparison.currencySymbol || '₹';
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-start gap-3">
          <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={20} />
          <div>
            <h4 className="text-sm font-bold text-[var(--text-primary)]">
              No Ride-Hailing Apps Operate Here
            </h4>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              {fb?.message || 'No ride-hailing apps operate here. Typical metered auto fare estimate:'}
            </p>
          </div>
        </div>

        <div className="p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-amber-500/20 text-amber-500 flex items-center justify-center font-bold">
                <Navigation size={22} />
              </div>
              <div>
                <h4 className="font-extrabold text-base text-[var(--text-primary)]">
                  {fb?.service || 'Normal auto / local taxi'}
                </h4>
                <span className="text-xs text-[var(--text-secondary)]">
                  {fb?.ride_type || 'Auto Rickshaw (Metered)'} • Government Notified Tariff
                </span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Estimate</span>
              <span className="text-2xl font-black text-emerald-500">
                {currencySym}{lowFare} – {currencySym}{highFare}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 border-t border-[var(--border-color)] text-xs">
            <div>
              <span className="text-[10px] text-[var(--text-secondary)] block">Minimum Fare</span>
              <span className="font-bold text-[var(--text-primary)]">{currencySym}{fb?.min_fare ?? 30}</span>
            </div>
            <div>
              <span className="text-[10px] text-[var(--text-secondary)] block">Rate per km</span>
              <span className="font-bold text-[var(--text-primary)]">{currencySym}{fb?.per_km ?? 15} / km</span>
            </div>
            <div>
              <span className="text-[10px] text-[var(--text-secondary)] block">Route Distance</span>
              <span className="font-bold text-[var(--text-primary)]">{comparison.distanceKm} km (~{comparison.durationMins} min)</span>
            </div>
          </div>
        </div>

        <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl text-center text-xs text-[var(--text-secondary)] font-medium">
          Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="p-4 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-2xl border border-[var(--border-color)]">
        <div className="flex items-center justify-between gap-2 pb-3 border-b border-[var(--border-color)] flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--text-primary)] bg-[var(--bg-primary)] px-2.5 py-1 rounded-full border border-[var(--border-color)]">
              <Route size={12} />
              {formatRouteTypeLabel(routeType)}
            </span>
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-500">
              <ShieldCheck size={12} />
              Route verified
            </span>
            <span className="text-[11px] text-[var(--text-secondary)] hidden sm:inline">
              {detectedCity || 'Transit Zone'} {comparison.country ? `(${comparison.country})` : ''} • {comparison.distanceKm.toFixed(1)} km ({comparison.durationMins} mins)
            </span>
          </div>

          <div className="flex items-center gap-2">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold bg-[var(--bg-primary)] hover:border-[var(--text-secondary)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg transition-all cursor-pointer disabled:opacity-50"
                title="Refresh fare estimates"
              >
                <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
                <span>{refreshing ? 'Refreshing...' : 'Re-evaluate'}</span>
              </button>
            )}

            {pricingRegime && (
              <span className="px-2.5 py-1 rounded-full text-[10px] text-[var(--text-secondary)] border border-[var(--border-color)]">
                {pricingRegime}
              </span>
            )}
          </div>
        </div>

        {agentReasoning && (
          <div className="my-3 flex items-center justify-between gap-3 text-[11px] text-[var(--text-secondary)]">
            <span className="truncate">
              {agentReasoning.headline || agentReasoning.auditSummary}
            </span>
            <span className="shrink-0 text-emerald-500 font-semibold">
              {directList.length} available
            </span>
          </div>
        )}

        <div className="pt-2 flex items-end justify-between">
          <div>
            <span className="text-[11px] font-medium text-slate-400 block">
              Lowest Estimated Fare (Statutory Rate Cards)
            </span>
            <div className="text-base font-bold text-white flex items-center gap-2 mt-0.5">
              <span>{cheapestProvider?.provider}</span>
              {cheapestProvider && (
                <span className="text-[var(--text-primary)] font-bold text-lg">
                  Estimate: {activeSym}{cheapestProvider.low ?? cheapestProvider.fareMin} – {activeSym}{cheapestProvider.high ?? cheapestProvider.fareMax}
                </span>
              )}
            </div>
          </div>

          {fareSpread > 0 && (
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Fare Variance</span>
              <span className="text-xs font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-700/50 px-2 py-0.5 rounded-md inline-block mt-0.5">
                Save up to {activeSym}{fareSpread} ({spreadPercentage}%)
              </span>
            </div>
          )}
        </div>

      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex bg-[var(--bg-secondary)] border border-[var(--border-color)] p-1 rounded-xl text-xs font-semibold text-[var(--text-secondary)] flex-wrap gap-1">
          <button
            onClick={() => setVehicleFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${vehicleFilter === 'ALL' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
          >
            All ({categoryCounts.ALL})
          </button>
          <button
            onClick={() => setVehicleFilter('CAB')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'CAB' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
          >
            <Car size={13} /> Cabs ({categoryCounts.CAB})
          </button>
          <button
            onClick={() => setVehicleFilter('AUTO')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'AUTO' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
          >
            <Navigation size={13} /> Autos ({categoryCounts.AUTO})
          </button>
          <button
            onClick={() => setVehicleFilter('BIKE')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'BIKE' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
          >
            <Bike size={13} /> Bikes ({categoryCounts.BIKE})
          </button>
          {hasRobotaxi && (
            <button
              onClick={() => setVehicleFilter('ROBOTAXI')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'ROBOTAXI' ? 'bg-emerald-600 text-white shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
            >
              <Bot size={13} /> Robotaxi
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 text-xs text-[var(--text-secondary)] font-medium">
          <span className="text-[11px] mr-1">Sort:</span>
          <div className="flex bg-[var(--bg-secondary)] border border-[var(--border-color)] p-0.5 rounded-lg">
            <button
              onClick={() => setSortBy('recommended')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'recommended' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
            >
              Recommended
            </button>
            <button
              onClick={() => setSortBy('category')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'category' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
            >
              Type
            </button>
            <button
              onClick={() => setSortBy('price')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'price' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
            >
              Price
            </button>
            <button
              onClick={() => setSortBy('eta')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'eta' ? 'bg-[var(--text-primary)] text-[var(--bg-primary)]' : 'hover:text-[var(--text-primary)]'}`}
            >
              ETA
            </button>
          </div>
        </div>
      </div>

      {/* Regional Regulatory Compliance Notice */}
      {comparison.regionalNotice && (
        <div className="px-3 py-2.5 border border-[var(--border-color)] rounded-xl flex items-start gap-2.5 text-xs text-[var(--text-secondary)]">
          <ShieldCheck size={15} className="shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-[var(--text-primary)] block">
              {detectedCity}{comparison.state ? `, ${comparison.state}` : ''}
            </span>
            <p className="mt-0.5 text-[10px] leading-relaxed">
              {comparison.regionalNotice}
            </p>
          </div>
        </div>
      )}

      {observedSnapshots.length > 0 && (
        <div className="p-3.5 rounded-2xl border border-amber-500/25 bg-amber-500/[0.07]">
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="block text-xs font-black text-amber-500">Screenshot Fare Reference</span>
              <p className="mt-1 text-[10px] leading-relaxed text-[var(--text-secondary)]">
                User-observed Uber states; route estimates below remain separate and are not live provider quotes.
              </p>
            </div>
            <span className="shrink-0 rounded-full border border-amber-500/30 px-2 py-1 text-[9px] font-bold text-amber-500">
              OBSERVED
            </span>
          </div>
          <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
            {observedSnapshots.map((snapshot, index) => (
              <div key={`${snapshot.providerCategory}-${index}`} className="min-w-[175px] rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2">
                <span className="block text-[10px] font-black text-[var(--text-primary)]">{snapshot.providerCategory}</span>
                <span className="mt-1 block text-sm font-extrabold text-amber-500">
                  ₹{snapshot.displayFare}
                  {snapshot.promotionDisplayFare && ` · promo ₹${snapshot.promotionDisplayFare}`}
                </span>
                <span className="mt-1 block text-[9px] text-[var(--text-secondary)]">
                  {snapshot.capturedTime || 'User screenshot'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        {sortedProviders.length === 0 && (
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5 text-sm font-semibold text-[var(--text-secondary)] space-y-1.5">
            <div className="text-[var(--text-primary)] font-bold flex items-center gap-1.5">
              <AlertCircle size={16} className="text-amber-500" />
              {vehicleFilter === 'BIKE'
                ? `No Bike Taxis Eligible for ${formatRouteTypeLabel(routeType)}`
                : vehicleFilter === 'AUTO'
                ? `No Auto-Rickshaws Eligible for ${formatRouteTypeLabel(routeType)}`
                : 'No Direct Rides Verified'}
            </div>
            <p className="text-xs font-normal leading-relaxed">
              {vehicleFilter === 'BIKE'
                ? `Bike taxis (e.g. Rapido Bike) are restricted to short-distance urban journeys (< 18 km) for passenger safety and regulatory limits. On this ${comparison.distanceKm.toFixed(1)} km journey, bike taxis are excluded. Check the Feasibility Audit below.`
                : vehicleFilter === 'AUTO'
                ? `Auto-rickshaws are restricted to local municipal trips (< 32 km) and do not support long-distance / outstation transit.`
                : comparison.message || 'No direct ride services verified for this filter.'}
            </p>
          </div>
        )}
        {sortedProviders.map((p, idx) => {
          const cardKey = `${p.provider}-${p.vehicleType}-${idx}`;
          const isExpanded = expandedProvider === cardKey;
          const hasLivePrice = p.liveAvailable !== false && p.actualFare !== null && p.actualFare !== undefined;
          const liveFare = p.actualFare;
          const brand = getProviderBrand(p.provider, p.vehicleType, p.isGovernmentBacked);
          const age = getQuoteAge(p);
          const isStale = Boolean(p.isStale) || age > 30;
          const sym = p.currencySymbol || defaultSym;
          const diffPct = p.predictionDiffPct !== undefined ? p.predictionDiffPct : 0;
          const demand = p.demandLevel || (p.surgeMultiplier >= 1.3 ? 'High' : p.surgeMultiplier > 1.05 ? 'Moderate' : 'Normal');
          const trend = p.priceTrend || 'Stable / Increasing';
          const sMult = p.surgeMultiplier || 1.0;
          const isZeroSurge = Boolean(p.zeroSurge);
          const vTypeLower = (p.vehicleType || '').toLowerCase();
          const isBike = vTypeLower.includes('bike') || vTypeLower.includes('moto');
          const isAuto = vTypeLower.includes('auto') || vTypeLower.includes('tuk');

          // Statutorily computed fare range (Estimate) + Real-time Dynamic Rate
          const liveMin = p.low ?? p.fareMin ?? Math.round((p.estimatedFare || 100) * 0.9);
          const liveMax = p.high ?? p.fareMax ?? Math.round((p.estimatedFare || 100) * 1.2);
          const realtimeRate = p.realtime_rate || p.actualFare || Math.round((liveMin + liveMax) / 2);
          const inBetweenPercent = Math.max(8, Math.min(92, Math.round(((realtimeRate - liveMin) / Math.max(1, liveMax - liveMin)) * 100)));

          const demandStatus = isZeroSurge
            ? { label: 'Zero-Surge Regulated', badgeClass: 'text-amber-500 bg-amber-500/15 border-amber-500/30', barGradient: 'from-amber-400 via-emerald-400 to-emerald-500' }
            : sMult >= 1.35
              ? { label: 'Peak Surge Demand', badgeClass: 'text-rose-500 bg-rose-500/15 border-rose-500/30', barGradient: 'from-amber-400 via-rose-500 to-rose-600' }
              : sMult > 1.05
                ? { label: 'Moderate Demand', badgeClass: 'text-amber-500 bg-amber-500/15 border-amber-500/30', barGradient: 'from-emerald-400 via-amber-400 to-amber-500' }
                : { label: 'Standard Demand', badgeClass: 'text-emerald-500 bg-emerald-500/15 border-emerald-500/30', barGradient: 'from-emerald-500 to-teal-500' };

          const typicalRange = `${sym}${liveMin}–${sym}${liveMax}`;

          return (
            <div
              key={cardKey}
              onClick={() => toggleExpand(cardKey)}
              className={`bg-[var(--bg-secondary)] border rounded-xl transition-all cursor-pointer hover:border-[var(--accent-color)]/50 overflow-hidden ${
                p.isBestValue
                  ? 'border-[var(--accent-color)]/40'
                  : 'border-[var(--border-color)]'
              }`}
            >
              <div className="p-3.5 space-y-3">
                {/* Header Row: Brand & In-Between Live Price / Status */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm shadow-xs shrink-0 ${brand.badgeBg}`}>
                      {brand.icon}
                    </div>

                    <div className="truncate space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-extrabold text-sm text-[var(--text-primary)] truncate">
                          {p.provider}
                        </h4>
                        {p.categoryTag === 'Autonomous Robotaxi' && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-emerald-700 text-white border border-emerald-800 flex items-center gap-0.5">
                            🤖 Autonomous Robotaxi
                          </span>
                        )}
                        {p.categoryTag === '100% Pure Electric Fleet' && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-teal-600 text-white border border-teal-700 flex items-center gap-0.5">
                            ⚡ 100% EV
                          </span>
                        )}
                        {p.isGovernmentBacked && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-emerald-600 text-white border border-emerald-700 flex items-center gap-0.5">
                            🏛 Govt-Backed
                          </span>
                        )}
                        {p.categoryTag === 'Open Mobility' && !p.isGovernmentBacked && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-blue-600 text-white border border-blue-700 flex items-center gap-0.5">
                            🌐 Open Mobility
                          </span>
                        )}
                        {p.zeroSurge && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center gap-0.5">
                            ⚡ Zero Surge
                          </span>
                        )}
                        {p.isCheapest && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-amber-400 text-slate-950 border border-amber-500">
                            💰 Lowest Rate
                          </span>
                        )}
                        {p.isFastest && !p.isCheapest && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-blue-500 text-white border border-blue-600">
                            ⚡ Fastest
                          </span>
                        )}
                        {p.routeSupported !== false && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-emerald-950 text-emerald-400 border border-emerald-500/40 flex items-center gap-0.5">
                            <CheckCircle2 size={10} className="text-emerald-400" /> Verified Direct
                          </span>
                        )}
                        {p.rate_card_verified_at && (
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border flex items-center gap-0.5 ${
                            p.is_verified
                              ? 'bg-emerald-950 text-emerald-400 border-emerald-500/40'
                              : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                          }`}>
                            {p.is_verified ? '✓ Verified' : '⚠ Unverified'} Rate Card ({p.rate_card_verified_at})
                          </span>
                        )}
                        {p.suitabilityLevel && (
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-extrabold flex items-center gap-0.5 ${
                            p.suitabilityLevel === 'HIGH'
                              ? 'bg-indigo-950 text-indigo-300 border border-indigo-500/40'
                              : p.suitabilityLevel === 'MEDIUM'
                              ? 'bg-amber-950 text-amber-300 border border-amber-500/40'
                              : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                          }`}>
                            Suitability: {p.suitabilityLevel}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] font-medium flex-wrap">
                        <span className="flex items-center gap-1 font-semibold text-[var(--text-primary)]">
                          <Clock size={12} className="text-slate-400" />
                          ETA: {p.etaMinutes} min
                        </span>
                        <span>•</span>
                        <span className="font-semibold text-[var(--text-primary)]">
                          Distance: {p.distanceKm} km
                        </span>
                        {p.costPerKm > 0 && (
                          <>
                            <span>•</span>
                            <span>{sym}{p.costPerKm}/km</span>
                          </>
                        )}
                        {p.surgeMultiplier > 1.0 && !p.zeroSurge && (
                          <>
                            <span>•</span>
                            <span className="text-amber-500 font-bold flex items-center gap-0.5">
                              <Zap size={11} /> {p.surgeMultiplier}x surge
                            </span>
                          </>
                        )}
                      </div>

                    </div>
                  </div>

                  {/* Regulated Fare Range Block (Always Range + Real-time Rate) */}
                  <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-[var(--border-color)]">
                    <div className="text-left sm:text-right space-y-0.5">
                      <div className="flex items-center sm:justify-end gap-1.5 flex-wrap">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                          Estimate
                        </span>
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                          Live: ~{sym}{realtimeRate}
                        </span>
                      </div>
                      <div className="text-xl sm:text-2xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
                        {sym}{liveMin} – {sym}{liveMax}
                      </div>
                      <span className="text-[10px] text-[var(--text-secondary)] font-medium block">
                        {p.surgeMultiplier > 1.0 ? `Surge ${p.surgeMultiplier}x applied` : 'Standard rate card band'}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {onSuggestPrice && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSuggestKey(suggestKey === cardKey ? null : cardKey);
                            setSuggestAmount(String(realtimeRate));
                          }}
                          className="px-2.5 py-2 rounded-xl text-[11px] font-semibold border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-color)] cursor-pointer"
                          title="Suggest a corrected fare for this ride"
                        >
                          {suggestSubmitted[cardKey] ? '✓ Sent' : 'Suggest Price'}
                        </button>
                      )}
                      {hasValidDeepLink(p) && (
                        <button
                          onClick={(e) => handleBook(p, e)}
                          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-transform active:scale-95 shadow-xs cursor-pointer ${brand.buttonClass}`}
                          title={`Open ${brand.appName} with route pre-filled`}
                        >
                          <span>Open in app</span>
                          <ArrowUpRight size={13} />
                        </button>
                      )}

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpand(cardKey);
                        }}
                        className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors rounded-lg cursor-pointer"
                        title="View fare details"
                      >
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>
                </div>

                {suggestKey === cardKey && onSuggestPrice && (
                  <div
                    onClick={(e) => e.stopPropagation()}
                    className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)]"
                  >
                    <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
                      Observed / Desired Fare ({sym}):
                    </span>
                    <input
                      type="number"
                      min={1}
                      value={suggestAmount}
                      onChange={(e) => setSuggestAmount(e.target.value)}
                      className="w-24 px-2.5 py-1 rounded-lg bg-[var(--bg-dashboard)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-color)]"
                    />
                    <button
                      type="button"
                      disabled={suggestSaving || !(Number(suggestAmount) > 0)}
                      onClick={async () => {
                        const val = Number(suggestAmount);
                        if (!(val > 0)) return;
                        setSuggestSaving(true);
                        const ok = await onSuggestPrice(p, val);
                        setSuggestSaving(false);
                        if (ok) {
                          setSuggestSubmitted((prev) => ({ ...prev, [cardKey]: true }));
                          setSuggestKey(null);
                        }
                      }}
                      className="px-3 py-1 rounded-lg bg-[var(--accent-color)] text-[var(--accent-ink)] text-xs font-bold disabled:opacity-50 cursor-pointer"
                    >
                      {suggestSaving ? 'Sending...' : 'Submit'}
                    </button>
                  </div>
                )}

                {/* Demand & Surge Range Bar */}
                <div className="p-2.5 rounded-xl bg-[var(--bg-primary)]/70 border border-[var(--border-color)] space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-semibold flex-wrap gap-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1">
                        <Zap size={11} className={sMult > 1.0 ? 'text-amber-500' : 'text-emerald-500'} />
                        {p.vehicleType} Estimate Range:
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${demandStatus.badgeClass}`}>
                        {isZeroSurge ? 'Zero Surge Guaranteed' : `${sMult}x Surge • ${demandStatus.label}`}
                      </span>
                      {p.legal_surge_cap && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold border border-slate-700 bg-slate-800 text-slate-300">
                          Legal Cap: {p.legal_surge_cap}x
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)]">
                      Estimate: <strong className="text-[var(--text-primary)]">{sym}{liveMin} – {sym}{liveMax}</strong>
                    </div>
                  </div>

                  <div className="relative pt-3 pb-1">
                    <div className="h-2 w-full bg-[var(--bg-secondary)] rounded-full overflow-hidden relative border border-[var(--border-color)]">
                      <div 
                        className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-indigo-500 opacity-80 rounded-full"
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div 
                      className="absolute top-0 flex flex-col items-center -translate-x-1/2 transition-all duration-300 pointer-events-none"
                      style={{ left: `${inBetweenPercent}%` }}
                    >
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-slate-900 text-emerald-400 dark:bg-white dark:text-slate-900 shadow-xs border border-emerald-500/40">
                        {sym}{realtimeRate}
                      </span>
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full ring-2 ring-white dark:ring-slate-900 mt-0.5 animate-pulse" />
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-[9px] font-bold text-[var(--text-secondary)] px-0.5">
                    <span>Low: {sym}{liveMin}</span>
                    <span className="text-[10px] font-medium text-[var(--text-secondary)]/90">
                      Real-time live rate: <strong className="text-emerald-400">{sym}{realtimeRate}</strong> ({p.surgeMultiplier}x surge demand)
                    </span>
                    <span>High: {sym}{liveMax}</span>
                  </div>
                </div>

                {/* Price context */}
                <div className="p-3 rounded-xl bg-[var(--bg-primary)]/80 border border-[var(--border-color)] space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <span className="text-[10px] font-black uppercase tracking-wider text-[var(--text-secondary)]">
                      Price context
                    </span>
                    {p.mlInsight ? (
                      <span className="text-[11px] font-medium text-[var(--text-secondary)] italic">
                        "{p.mlInsight}"
                      </span>
                    ) : (
                      <span className="text-[11px] font-medium text-[var(--text-secondary)] italic">
                        {hasLivePrice
                          ? (diffPct >= 5
                              ? `Current price is approximately ${diffPct}% above recent historical range.`
                              : diffPct <= -5
                                ? `Current price is ${Math.abs(diffPct)}% below typical historical average.`
                                : 'Current price aligns with typical historical fares.')
                          : 'Estimated fare — not a live provider price.'}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-[var(--border-color)]/70 text-xs">
                    <div>
                      <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] block">Typical Fare</span>
                      <span className="font-extrabold text-[var(--text-primary)]">{typicalRange}</span>
                    </div>

                    <div>
                      <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] block">Current vs Typical</span>
                      {hasLivePrice ? (
                        <span className={`font-extrabold ${diffPct > 5 ? 'text-amber-500' : diffPct < -5 ? 'text-emerald-500' : 'text-[var(--text-primary)]'}`}>
                          ~{Math.abs(diffPct)}% {diffPct >= 0 ? 'above typical' : 'below typical'}
                        </span>
                      ) : (
                        <span className="font-medium text-[var(--text-secondary)]">Baseline estimate</span>
                      )}
                    </div>

                    <div>
                      <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] block">Demand</span>
                      <span className={`font-extrabold ${demand === 'High' ? 'text-rose-500 dark:text-rose-400' : demand === 'Moderate' ? 'text-amber-500' : 'text-emerald-500'}`}>
                        {demand}
                      </span>
                    </div>

                    <div>
                      <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] block">Trend</span>
                      <span className="font-extrabold text-[var(--text-primary)] flex items-center gap-1">
                        <TrendingUp size={11} className={trend.includes('Increasing') ? 'text-amber-500' : 'text-emerald-500'} />
                        {trend}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-[var(--border-color)] bg-[var(--bg-primary)]/40 rounded-b-2xl animate-fade-in text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3">
                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">
                        Fare Components
                      </span>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Base Fare:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{sym}{p.baseFare}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Distance Rate:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{sym}{p.distanceFare}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Time Rate:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{sym}{p.durationFare}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium border-t border-[var(--border-color)] pt-1">
                        <span className="text-[var(--text-secondary)]">Platform Fee:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{sym}{p.platformFee}</span>
                      </div>
                      {p.tollEstimate > 0 && (
                        <div className="flex justify-between text-xs font-medium">
                          <span className="text-[var(--text-secondary)]">Toll / Airport Surcharge:</span>
                          <span className="text-[var(--text-primary)] font-semibold">{sym}{p.tollEstimate}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-xs font-medium border-t border-[var(--border-color)] pt-1">
                        <span className="text-[var(--text-secondary)]">Demand & Surge Factor:</span>
                        <span className={`font-bold ${sMult > 1.0 ? 'text-amber-500' : 'text-emerald-500'}`}>
                          {isZeroSurge ? 'Zero Surge (1.0x)' : `${sMult}x (${demandStatus.label})`}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Live In-Between Rate:</span>
                        <span className="text-emerald-600 dark:text-emerald-400 font-black">{sym}{liveMin} – {sym}{liveMax}</span>
                      </div>
                      {p.regulatoryBody && (
                        <div className="border-t border-[var(--border-color)] pt-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                          Regulatory Authority: {p.regulatoryBody}
                        </div>
                      )}
                    </div>

                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-rose-500 dark:text-rose-400 block flex items-center gap-1">
                        <Activity size={12} /> Pricing Pressure & Demand
                      </span>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Demand Level:</span>
                        <span className="text-[var(--text-primary)] font-bold">{p.demand_level || p.demandLevel || 'NORMAL'}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Pressure Score:</span>
                        <span className="text-indigo-400 font-extrabold">{(p.pricing_pressure_score ?? p.pricingPressureScore ?? 1.0).toFixed(1)} / 4.0</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Confidence:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{p.confidence_text || `${Math.round((p.confidenceScore ?? 0.8) * 100)}% confidence`}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Estimation Layer:</span>
                        <span className="text-slate-300 font-semibold capitalize">{(p.source_type || p.sourceType || 'ml_estimate').replace('_', ' ')}</span>
                      </div>
                      <p className="border-t border-[var(--border-color)] pt-1 text-[10px] text-[var(--text-secondary)] italic">
                        {p.reason || p.demandReason || 'Standard baseline demand conditions for this area.'}
                      </p>
                    </div>

                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-indigo-500 dark:text-indigo-400 block">
                        Price assessment
                      </span>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Pricing Regime:</span>
                        <span className="text-[var(--text-primary)] font-semibold">
                          {p.clusterLabel || 'Standard Transit'}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Anomaly Assessment:</span>
                        <span className={`font-semibold ${p.priceAnomaly === 'Above normal' ? 'text-amber-500' : 'text-emerald-500'}`}>
                          {p.priceAnomaly || 'Normal'}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Inference Confidence:</span>
                        <span className="text-[var(--text-primary)] font-semibold">
                          {p.confidenceLevel || 'High'} ({p.confidenceScore || 90}%)
                        </span>
                      </div>
                      <p className="border-t border-[var(--border-color)] pt-1 text-[10px] text-[var(--text-secondary)]">
                        {p.anomalyReason || 'Pricing behavior is within standard historical bounds for this route.'}
                      </p>
                    </div>

                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-emerald-500 block flex items-center gap-1">
                        <ShieldCheck size={12} /> Route Feasibility & Suitability Audit
                      </span>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Eligibility Status:</span>
                        <span className="text-emerald-400 font-bold">{p.eligibility || 'DIRECT'}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Vehicle Suitability:</span>
                        <span className="text-indigo-400 font-bold">{p.suitabilityLevel || 'HIGH'} ({p.suitabilityScore || 90}%)</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Coverage Confidence:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{p.coverageConfidence || 'HIGH'}</span>
                      </div>
                      {p.eligibilityReason && (
                        <p className="border-t border-[var(--border-color)] pt-1 text-[10px] text-emerald-300">
                          {p.eligibilityReason}
                        </p>
                      )}
                    </div>

                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block">Service Information</span>
                      <div className="text-xs text-[var(--text-primary)]">
                        {p.categoryTag ? `Category: ${p.categoryTag}` : 'Provider fleet quote'}
                      </div>
                      <div className="text-[10px] text-[var(--text-secondary)]">
                        Source: {p.isLive
                          ? 'Authorized live provider quote'
                          : 'Approximate fare — verify in the provider app'}
                      </div>
                      {p.regulatoryBody && <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">{p.regulatoryBody}</div>}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Multimodal Transit Option (Combined Journey) */}
      {multimodalOption && (
        <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-3 shadow-sm">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-500/50">
                <Layers size={16} />
              </span>
              <div>
                <h4 className="text-sm font-extrabold text-cyan-200">
                  {multimodalOption.title || 'Multimodal Combined Transit Alternative'}
                </h4>
                <p className="text-[11px] text-cyan-300/80">
                  {multimodalOption.summary}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/40">
                {multimodalOption.transfer_count} Transfer Required
              </span>
              <span className="text-sm font-black text-cyan-300">
                Est. {multimodalOption.currency_symbol || defaultSym}{multimodalOption.total_estimated_fare}
              </span>
            </div>
          </div>

          <div className="space-y-2 pt-1">
            {multimodalOption.legs.map((leg, lIdx) => (
              <div key={lIdx} className="p-2.5 bg-black/30 border border-cyan-500/20 rounded-xl flex items-center justify-between gap-3 text-xs flex-wrap">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="w-5 h-5 rounded-full bg-cyan-900 text-cyan-200 flex items-center justify-center font-bold text-[10px] shrink-0">
                    {leg.leg_number}
                  </span>
                  <div>
                    <span className="font-bold text-white block">
                      {leg.provider} ({leg.vehicle_type})
                    </span>
                    <span className="text-[11px] text-slate-300 flex items-center gap-1">
                      <span>{leg.from_location}</span>
                      <ArrowRight size={10} className="text-cyan-400" />
                      <span>{leg.to_location}</span>
                    </span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-bold text-cyan-300">
                    {leg.currency_symbol || defaultSym}{leg.estimated_fare}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    {leg.distance_km} km • ~{leg.duration_mins} mins
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-1 border-t border-cyan-800/40 flex items-center justify-between text-[10px] text-cyan-300/80 font-medium">
            <span>✓ Complete transfers explicitly indicated — never concealed.</span>
            <span>Total travel time: ~{multimodalOption.total_duration_mins} mins</span>
          </div>
        </div>
      )}

      {/* Excluded services and route coverage */}
      {excludedList.length > 0 && (
        <div className="bg-[var(--bg-secondary)] border border-rose-500/30 rounded-2xl overflow-hidden shadow-xs">
          <div
            onClick={() => setShowAuditDrawer(!showAuditDrawer)}
            className="p-3.5 bg-rose-950/20 hover:bg-rose-950/30 transition-colors cursor-pointer flex items-center justify-between gap-2 border-b border-rose-500/20"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <span className="p-1 rounded-lg bg-rose-950 text-rose-400 border border-rose-500/40 shrink-0">
                <ShieldAlert size={16} />
              </span>
              <div className="truncate">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold text-rose-300">
                    Route coverage
                  </h4>
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-600/40">
                    {excludedList.length} Excluded
                  </span>
                </div>
                <p className="text-[11px] text-[var(--text-secondary)] truncate">
                  Disqualified services that cannot safely, realistically, or legally complete this entire journey
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[10px] font-semibold text-rose-400 hidden sm:inline">
                Priority 1: Route Feasibility &gt; Price
              </span>
              {showAuditDrawer ? <ChevronUp size={16} className="text-rose-400" /> : <ChevronDown size={16} className="text-rose-400" />}
            </div>
          </div>

          {showAuditDrawer && (
            <div className="p-3.5 space-y-2.5 bg-black/10">
              <div className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                RideCompare evaluates <strong>route feasibility and service coverage before price optimization</strong>. The ride services below were detected or queried but excluded from direct recommendations:
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {excludedList.map((p, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-[var(--bg-primary)] border border-rose-500/20 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0"></span>
                        <span className="text-xs font-bold text-[var(--text-primary)]">
                          {p.provider}
                        </span>
                        <span className="text-[10px] font-medium text-[var(--text-secondary)]">
                          ({p.vehicleType})
                        </span>
                      </div>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-rose-950 text-rose-300 border border-rose-600/40">
                        ✕ Excluded
                      </span>
                    </div>

                    <div className="text-[11px] text-rose-400/90 bg-rose-950/30 p-2 rounded-lg border border-rose-500/20 font-medium">
                      {p.eligibilityReason || 'Route exceeds vehicle operational limits or falls outside provider service area.'}
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-[var(--text-secondary)] pt-1">
                      <span>Vehicle Suitability: <strong className="text-rose-400">{p.suitabilityLevel || 'UNSUITABLE'}</strong></span>
                      {p.actualFare && (
                        <span>API Rate: {p.currencySymbol || defaultSym}{p.actualFare} (Excluded)</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Partial Providers Notice if any */}
      {partialList.length > 0 && (
        <div className="p-3 bg-amber-950/20 border border-amber-500/30 rounded-2xl flex items-start gap-2.5 text-xs text-amber-200">
          <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-amber-300 block">
              Partial Coverage Services ({partialList.length})
            </span>
            <p className="text-[11px] text-amber-200/90 leading-relaxed font-normal">
              Services like {partialList.map(p => p.provider).join(', ')} operate only in local zones or sub-sections of this journey and cannot complete the direct route. They have been separated from direct recommendations.
            </p>
          </div>
        </div>
      )}

      <PriceHistoryGraph providers={sortedProviders} />

      {insights && insights.length > 0 && (
        <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-2 text-xs">
          <h5 className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            Route notes
          </h5>
          <ul className="space-y-1 text-[var(--text-secondary)] font-medium">
            {insights.map((insight, idx) => (
              <li key={idx} className="flex gap-2 items-start">
                <span className="text-indigo-500 mt-0.5">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Mandatory Legal Disclaimer Footer */}
      <footer className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl text-center text-xs text-[var(--text-secondary)] font-medium">
        Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes.
      </footer>
    </div>
  );
};

export default RideComparison;
