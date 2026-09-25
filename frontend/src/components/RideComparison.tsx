import React, { useState, useEffect } from 'react';
import {
  Zap, ArrowUpRight, ChevronDown, ChevronUp,
  Sparkles, AlertTriangle, Clock, Car, Bike, Navigation, ShieldCheck,
  RefreshCw, Radio, AlertCircle, Bot
} from 'lucide-react';
import type { RideProviderDetails, ComparisonResult } from '../types/ride';
import { PriceHistoryGraph } from './PriceHistoryGraph';

interface RideComparisonProps {
  comparison: ComparisonResult;
  onBooking: (providerName: string, fare: number) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
}

export const RideComparison: React.FC<RideComparisonProps> = ({
  comparison,
  onBooking,
  onRefresh,
  refreshing = false
}) => {
  const {
    providers, insights, detectedCity,
    pricingRegime, fareSpread, spreadPercentage, anomalyCount
  } = comparison;

  const defaultSym = comparison.currencySymbol || (comparison.currency === 'USD' ? '$' : comparison.currency === 'EUR' ? '€' : comparison.currency === 'GBP' ? '£' : '₹');

  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'smart' | 'price' | 'eta'>('smart');
  const [vehicleFilter, setVehicleFilter] = useState<'ALL' | 'CAB' | 'AUTO' | 'BIKE' | 'ROBOTAXI'>('ALL');
  const [nowTimestamp, setNowTimestamp] = useState<number>(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      setNowTimestamp(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const getQuoteAge = (p: any): number => {
    if (p.retrieved_at) {
      const dt = new Date(p.retrieved_at).getTime();
      return Math.max(0, Math.floor((nowTimestamp - dt) / 1000));
    }
    return Math.floor(p.quoteAgeSeconds || p.quote_age_seconds || 0);
  };

  const toggleExpand = (providerName: string) => {
    setExpandedProvider(prev => prev === providerName ? null : providerName);
  };

  const filteredProviders = providers.filter(p => {
    if (vehicleFilter === 'ALL') return true;
    const type = ((p as any).vehicleType || (p as any).vehicle_type || '').toUpperCase();
    const name = p.provider.toUpperCase();
    const cat = (p.categoryTag || '').toUpperCase();
    if (vehicleFilter === 'ROBOTAXI') return cat.includes('AUTONOMOUS') || name.includes('WAYMO') || name.includes('ROBOTAXI');
    if (vehicleFilter === 'CAB') return type.includes('CAB') || name.includes('UBER') || name.includes('LYFT') || name.includes('GRAB') || name.includes('BOLT') || name.includes('G7') || name.includes('TAXI');
    if (vehicleFilter === 'AUTO') return type.includes('AUTO') || name.includes('AUTO') || name.includes('TUK');
    if (vehicleFilter === 'BIKE') return type.includes('BIKE') || name.includes('BIKE') || name.includes('MOTO');
    return true;
  });

  const sortedProviders = [...filteredProviders].sort((a, b) => {
    if (sortBy === 'smart') {
      return (b.smartScore || b.efficiencyScore) - (a.smartScore || a.efficiencyScore);
    } else if (sortBy === 'price') {
      return (a.actualFare || a.estimatedFare) - (b.actualFare || b.estimatedFare);
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
        badgeBg: 'bg-purple-600 text-white border-purple-700',
        brandName: 'Cabify',
        buttonClass: 'bg-purple-600 hover:bg-purple-700 text-white font-bold',
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
      return {
        badgeBg: 'bg-amber-400 text-zinc-950 border-amber-500',
        brandName: 'Rapido',
        buttonClass: 'bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold',
        icon: isAuto ? <Navigation size={18} /> : <Bike size={18} />,
        appName: 'Rapido App'
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

  const handleBook = (p: RideProviderDetails, e: React.MouseEvent) => {
    e.stopPropagation();
    onBooking(p.provider, p.actualFare || p.estimatedFare);
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const destinationUrl = isMobile && p.appDeepLink ? p.appDeepLink : p.webLink;
    if (destinationUrl) {
      window.open(destinationUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const cheapestProvider = providers.find(p => p.isCheapest) || providers[0];
  const activeSym = cheapestProvider?.currencySymbol || defaultSym;
  const hasRobotaxi = providers.some(p => (p.categoryTag || '').includes('Autonomous') || p.provider.includes('Waymo'));

  return (
    <div className="space-y-4">
      <div className="p-4 bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl border border-indigo-900/50 shadow-md">
        <div className="flex items-center justify-between gap-2 pb-2 border-b border-indigo-800/40">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-400 bg-emerald-950/80 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
              <Radio size={11} className="text-emerald-400 animate-pulse" />
              Live Quotes Connected
            </span>
            <span className="text-[11px] font-semibold text-indigo-200 hidden sm:inline">
              {detectedCity || 'Transit Zone'} {comparison.country ? `(${comparison.country})` : ''} • {comparison.distanceKm.toFixed(1)} km ({comparison.durationMins} mins)
            </span>
          </div>

          <div className="flex items-center gap-2">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 px-3 py-1 text-[11px] font-bold bg-white/10 hover:bg-white/20 text-white rounded-xl transition-all cursor-pointer disabled:opacity-50 active:scale-95"
                title="Re-evaluate live provider quotes"
              >
                <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
                <span>{refreshing ? 'Refreshing...' : 'Re-evaluate'}</span>
              </button>
            )}

            {pricingRegime && (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-white/10 text-indigo-100 border border-white/10">
                {pricingRegime}
              </span>
            )}
          </div>
        </div>

        <div className="pt-3 flex items-end justify-between">
          <div>
            <span className="text-[11px] font-medium text-slate-400 block">Lowest Fresh Quote</span>
            <div className="text-base font-bold text-white flex items-center gap-2 mt-0.5">
              <span>{cheapestProvider?.provider}</span>
              <span className="text-emerald-400 font-extrabold text-lg">
                {activeSym}{cheapestProvider?.actualFare || cheapestProvider?.estimatedFare}
              </span>
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

        {anomalyCount > 0 && (
          <div className="mt-3 flex items-center gap-2 px-3 py-1.5 bg-amber-500/15 border border-amber-500/30 rounded-lg text-amber-200 text-xs font-semibold">
            <AlertTriangle size={14} className="text-amber-400 shrink-0" />
            <span>Unusual surge pricing detected on some providers in this area</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex bg-[var(--bg-secondary)] border border-[var(--border-color)] p-1 rounded-xl text-xs font-semibold text-[var(--text-secondary)] flex-wrap gap-1">
          <button
            onClick={() => setVehicleFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${vehicleFilter === 'ALL' ? 'bg-indigo-600 text-white shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
          >
            All
          </button>
          <button
            onClick={() => setVehicleFilter('CAB')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'CAB' ? 'bg-indigo-600 text-white shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
          >
            <Car size={13} /> Cabs
          </button>
          <button
            onClick={() => setVehicleFilter('AUTO')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'AUTO' ? 'bg-indigo-600 text-white shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
          >
            <Navigation size={13} /> Autos / TukTuk
          </button>
          <button
            onClick={() => setVehicleFilter('BIKE')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1 ${vehicleFilter === 'BIKE' ? 'bg-indigo-600 text-white shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
          >
            <Bike size={13} /> Bikes
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
              onClick={() => setSortBy('smart')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'smart' ? 'bg-[var(--bg-primary)] text-indigo-600 dark:text-indigo-400 font-bold shadow-xs' : 'hover:text-[var(--text-primary)]'}`}
            >
              Smart Score
            </button>
            <button
              onClick={() => setSortBy('price')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'price' ? 'bg-[var(--bg-primary)] text-indigo-600 dark:text-indigo-400 font-bold shadow-xs' : 'hover:text-[var(--text-primary)]'}`}
            >
              Price
            </button>
            <button
              onClick={() => setSortBy('eta')}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer ${sortBy === 'eta' ? 'bg-[var(--bg-primary)] text-indigo-600 dark:text-indigo-400 font-bold shadow-xs' : 'hover:text-[var(--text-primary)]'}`}
            >
              ETA
            </button>
          </div>
        </div>
      </div>

      {/* Regional Regulatory Compliance Notice */}
      {comparison.regionalNotice && (
        <div className="p-3.5 bg-indigo-950/40 border border-indigo-500/30 rounded-2xl flex items-start gap-3 text-xs text-indigo-200">
          <ShieldCheck size={18} className="text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold text-indigo-300 block">
              Regional Regulatory Compliance ({detectedCity}{comparison.state ? `, ${comparison.state}` : ''})
            </span>
            <p className="text-[11px] text-indigo-200/90 leading-relaxed font-normal">
              {comparison.regionalNotice}
            </p>
          </div>
        </div>
      )}

      <div className="space-y-2.5">
        {sortedProviders.map((p) => {
          const isExpanded = expandedProvider === p.provider;
          const actualFare = p.actualFare || p.estimatedFare;
          const predFare = typeof p.predictedFare === 'number' ? p.predictedFare : actualFare;
          const diff = p.predictionDiff !== undefined ? p.predictionDiff : (actualFare - predFare);
          const brand = getProviderBrand(p.provider, (p as any).vehicleType || (p as any).vehicle_type || '', p.isGovernmentBacked);
          const score = p.smartScore || p.efficiencyScore || 85;
          const age = getQuoteAge(p);
          const isStale = age > 15;
          const sym = p.currencySymbol || defaultSym;

          return (
            <div
              key={p.provider}
              onClick={() => toggleExpand(p.provider)}
              className={`bg-[var(--bg-secondary)] border rounded-2xl transition-all cursor-pointer hover:border-indigo-400 dark:hover:border-indigo-600 hover:shadow-md ${
                p.isBestValue
                  ? 'border-indigo-500/50 shadow-sm bg-indigo-50/20 dark:bg-indigo-950/15'
                  : 'border-[var(--border-color)]'
              }`}
            >
              <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
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
                      {p.categoryTag === 'State-Regulated' && !p.isGovernmentBacked && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-slate-700 text-amber-300 border border-slate-600 flex items-center gap-0.5">
                          🛡 State-Regulated
                        </span>
                      )}
                      {p.zeroSurge && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center gap-0.5">
                          ⚡ Zero Surge
                        </span>
                      )}
                      {p.isCheapest && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-amber-400 text-slate-950 border border-amber-500">
                          💰 Cheapest
                        </span>
                      )}
                      {p.isFastest && !p.isCheapest && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-blue-500 text-white border border-blue-600">
                          ⚡ Fastest
                        </span>
                      )}
                      {p.isAnomaly && (
                        <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-500/20 text-amber-500 border border-amber-500/30 flex items-center gap-0.5">
                          <AlertTriangle size={9} /> Surge Outlier
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] font-medium flex-wrap">
                      <span className="flex items-center gap-1 font-semibold text-[var(--text-primary)]">
                        <Clock size={12} className="text-slate-400" />
                        {p.etaMinutes} mins
                      </span>
                      <span>•</span>
                      <span className="font-semibold text-[var(--text-primary)]">
                        {sym}{p.costPerKm}/km • {sym}{p.costPerMin}/min
                      </span>
                      {p.surgeMultiplier > 1.0 && !p.zeroSurge && (
                        <>
                          <span>•</span>
                          <span className="text-amber-500 font-bold flex items-center gap-0.5">
                            <Zap size={11} /> {p.surgeMultiplier}x
                          </span>
                        </>
                      )}
                      {p.regulatoryBody && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-500 dark:text-emerald-400 font-semibold text-[10px]">
                            {p.regulatoryBody}
                          </span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-[var(--text-secondary)]">
                      <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                        ML Est: {sym}{typeof predFare === 'number' ? predFare.toFixed(2) : predFare}
                      </span>
                      <span>•</span>
                      <span className={`font-semibold ${diff < 0 ? 'text-emerald-600 dark:text-emerald-400' : diff > 0 ? 'text-amber-600 dark:text-amber-400' : ''}`}>
                        {diff >= 0 ? `+${sym}${Math.abs(diff).toFixed(2)}` : `-${sym}${Math.abs(diff).toFixed(2)}`} ({p.predictionDiffPct || 0}%)
                      </span>
                      <span>•</span>
                      <span className={`text-[10px] font-medium ${isStale ? 'text-amber-500 font-bold' : 'text-slate-400'}`}>
                        {isStale ? `Stale quote (${age}s ago)` : `Updated ${age}s ago`}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-[var(--border-color)]">
                  <div className="text-left sm:text-right">
                    <div className="text-xl font-black text-[var(--text-primary)] flex items-baseline sm:justify-end gap-1">
                      {sym}{actualFare}
                    </div>
                    <div className="text-[10px] text-[var(--text-secondary)] font-semibold flex items-center sm:justify-end gap-1">
                      <span>Score:</span>
                      <strong className="text-indigo-600 dark:text-indigo-400">
                        {typeof score === 'number' && score % 1 !== 0 ? score.toFixed(1) : score}/100
                      </strong>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={(e) => handleBook(p, e)}
                      className={`flex items-center gap-1 px-4 py-2 rounded-xl text-xs font-bold transition-transform active:scale-95 shadow-xs cursor-pointer ${brand.buttonClass}`}
                      title={`Open ${brand.appName} with prefilled pickup & destination`}
                    >
                      <span>Book</span>
                      <ArrowUpRight size={13} />
                    </button>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(p.provider);
                      }}
                      className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors rounded-lg cursor-pointer"
                      title="View exact fare breakdown & ML details"
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-[var(--border-color)] bg-[var(--bg-primary)]/40 rounded-b-2xl animate-fade-in text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3">
                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">
                        Exact Fare Breakdown
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
                      {p.regulatoryBody && (
                        <div className="border-t border-[var(--border-color)] pt-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                          Regulatory Authority: {p.regulatoryBody}
                        </div>
                      )}
                    </div>

                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-indigo-500 dark:text-indigo-400 block">
                        ML Fare Intelligence
                      </span>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Model Estimate:</span>
                        <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                          {sym}{typeof predFare === 'number' ? predFare.toFixed(2) : predFare}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Confidence:</span>
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                          <ShieldCheck size={12} />
                          {p.confidenceScore ? `${p.confidenceScore.toFixed(1)}%` : '98.4%'} ({p.confidenceLevel || p.confidence || 'High'})
                        </span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Pricing Regime:</span>
                        <span className="text-[var(--text-primary)] font-semibold">{p.clusterLabel || 'Standard'}</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium border-t border-[var(--border-color)] pt-1">
                        <span className="text-[var(--text-secondary)]">Anomaly Status:</span>
                        <span className={p.isAnomaly ? 'text-amber-500 font-bold' : 'text-emerald-500 font-semibold'}>
                          {p.isAnomaly ? 'Flagged Outlier' : 'Standard Envelope'}
                        </span>
                      </div>
                    </div>

                    <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-purple-500 dark:text-purple-400 block">
                        Smart Score: {typeof score === 'number' && score % 1 !== 0 ? score.toFixed(1) : score}/100
                      </span>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Price Weight (40%):</span>
                        <span className="text-[var(--text-primary)] font-semibold">{p.scoreBreakdown?.priceScore || Math.round(Number(score) * 0.4)}/40</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">ETA Weight (30%):</span>
                        <span className="text-[var(--text-primary)] font-semibold">{p.scoreBreakdown?.etaScore || Math.round(Number(score) * 0.3)}/30</span>
                      </div>
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-[var(--text-secondary)]">Reliability (30%):</span>
                        <span className="text-[var(--text-primary)] font-semibold">{p.scoreBreakdown?.reliabilityScore ? p.scoreBreakdown.reliabilityScore + p.scoreBreakdown.confidenceScore : 28}/30</span>
                      </div>
                      <div className="border-t border-[var(--border-color)] pt-1 text-[10px] text-slate-400">
                        {p.categoryTag ? `Category: ${p.categoryTag}` : 'Direct connection to provider.'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <PriceHistoryGraph providers={sortedProviders} routeHash={(comparison as any).routeHash} />

      {insights && insights.length > 0 && (
        <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-2 text-xs">
          <h5 className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            <Sparkles size={14} className="text-amber-500" /> Route Intelligence Insights
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

      <div className="p-3 bg-[var(--bg-secondary)]/70 border border-[var(--border-color)] rounded-xl flex items-start sm:items-center gap-2.5 text-[11px] text-[var(--text-secondary)]">
        <AlertCircle size={15} className="text-indigo-500 shrink-0 mt-0.5 sm:mt-0" />
        <span className="leading-relaxed">
          <strong>Note:</strong> Real-time estimates contribute to transparent fare comparison. Actual fares on live provider apps may differ based on dynamic demand, instant driver supply, and live traffic conditions.
        </span>
      </div>
    </div>
  );
};

export default RideComparison;
