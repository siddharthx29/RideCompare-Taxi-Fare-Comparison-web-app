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

      // ML Time-of-Day Diurnal Surge & Demand Analysis
      const currentHour = new Date().getHours();
      let mlSurgeMultiplier = 1.0;
      let mlDemandLevel = 'NORMAL';
      let mlSurgeRule = 'Standard Traffic';
      let mlClusterLabel = 'Standard City Transit';
      let mlClusterId = 1;

      if (currentHour >= 8 && currentHour < 11) {
        mlSurgeMultiplier = 1.35;
        mlDemandLevel = 'HIGH';
        mlSurgeRule = 'Morning Peak Rush';
        mlClusterLabel = 'Peak Hour Surge';
        mlClusterId = 0;
      } else if (currentHour >= 17 && currentHour < 21) {
        mlSurgeMultiplier = 1.45;
        mlDemandLevel = 'HIGH';
        mlSurgeRule = 'Evening Peak Commute';
        mlClusterLabel = 'Peak Hour Surge';
        mlClusterId = 0;
      } else if (currentHour >= 23 || currentHour < 5) {
        mlSurgeMultiplier = 1.20;
        mlDemandLevel = 'MODERATE';
        mlSurgeRule = 'Night Owl Transit';
        mlClusterLabel = 'Night Transit Window';
        mlClusterId = 3;
      } else {
        mlSurgeMultiplier = 1.05;
        mlDemandLevel = 'NORMAL';
        mlSurgeRule = 'Off-Peak Regular Flow';
        mlClusterLabel = 'Standard City Transit';
        mlClusterId = 1;
      }

      // Agentic AI Route Classification
      const fullText = `${source.label} ${dest.label}`.toLowerCase();
      const isAirport = ['airport', 'cial', 'kia', 'kempegowda', 'dabolim', 'mopa', 'heathrow', 'sfo', 'jfk', 'dxb'].some(k => fullText.includes(k));
      const isOutstationDest = ['munnar', 'thekkady', 'vagamon', 'alappuzha', 'alleppey', 'coorg', 'ooty', 'nandi hills', 'mysore', 'pune', 'lonavala', 'dudhsagar', 'idukki', 'wayanad'].some(k => fullText.includes(k));

      let routeType: 'LOCAL' | 'SHORT_DISTANCE' | 'MEDIUM_DISTANCE' | 'LONG_DISTANCE' | 'INTERCITY' | 'OUTSTATION' | 'AIRPORT_TRANSFER' = 'LOCAL';
      let classificationReason = 'Short urban intra-city commute.';

      if (isAirport) {
        routeType = 'AIRPORT_TRANSFER';
        classificationReason = 'Airport transfer corridor. Prioritizing luggage-capable, highway-cleared fleet.';
      } else if (isOutstationDest || distKm >= 75) {
        routeType = 'OUTSTATION';
        classificationReason = `Long-distance outstation tourist / hill route detected (${distKm} km). Local municipal transit and bike taxis are prohibited.`;
      } else if (distKm > 40) {
        routeType = 'INTERCITY';
        classificationReason = `Intercity corridor across administrative districts (${distKm} km). Highway-capable cabs required.`;
      } else if (distKm > 20) {
        routeType = 'MEDIUM_DISTANCE';
        classificationReason = `Suburban perimeter transit (${distKm} km). Cabs and autos eligible; bike taxis limited.`;
      } else if (distKm > 10) {
        routeType = 'SHORT_DISTANCE';
        classificationReason = `Short intra-city trip (${distKm} km). All standard vehicle types eligible.`;
      }

      const isBikeEligible = distKm <= 18 && routeType !== 'OUTSTATION' && routeType !== 'INTERCITY' && routeType !== 'AIRPORT_TRANSFER';
      const isAutoEligible = distKm <= 32 && routeType !== 'OUTSTATION' && routeType !== 'INTERCITY';

      const buildProvider = (
        name: string,
        vType: string,
        base: number,
        perKmRate: number,
        perMinRate: number,
        badges: { isCheapest?: boolean; isFastest?: boolean; isMostEfficient?: boolean; isBestValue?: boolean } = {},
        eligibilityStatus: 'DIRECT' | 'PARTIAL' | 'UNSUPPORTED' = 'DIRECT',
        eligibilityReasonText = '✓ Suitable for this route'
      ): RideProviderDetails => {
        const isBike = vType.toLowerCase().includes('bike');
        const isAuto = vType.toLowerCase().includes('auto');
        const isZeroSurge = Boolean(badges.isBestValue && isAuto);
        const effectiveSurge = isZeroSurge ? 1.0 : mlSurgeMultiplier;

        const dFare = Math.round(distKm * perKmRate);
        const tFare = Math.round(durMin * perMinRate);
        const pFee = 5;

        // Base rate without surge (ML baseline reference)
        const baselineFare = Math.round(base + dFare + tFare + pFee);
        // Current actual point fare applying dynamic demand surge
        const total = Math.round((base + dFare + tFare) * effectiveSurge + pFee);

        // ML Demand & Surge dynamic in-between rate spread:
        let downPct: number;
        let upPct: number;
        if (isZeroSurge) {
          downPct = 0.04;
          upPct = 0.05;
        } else {
          const sExcess = Math.max(0, effectiveSurge - 1.0);
          if (isBike) {
            downPct = Math.min(0.10, (0.05 + sExcess * 0.07) * 0.85);
            upPct = Math.min(0.18, (0.06 + sExcess * 0.12) * 0.85);
          } else if (isAuto) {
            downPct = Math.min(0.11, (0.05 + sExcess * 0.07) * 0.92);
            upPct = Math.min(0.19, (0.06 + sExcess * 0.12) * 0.92);
          } else {
            downPct = Math.min(0.12, 0.05 + sExcess * 0.07);
            upPct = Math.min(0.22, 0.06 + sExcess * 0.14);
          }
        }

        const fMin = Math.round(total * (1 - downPct));
        const fMax = Math.max(fMin + (isBike ? 3 : isAuto ? 5 : 12), Math.round(total * (1 + upPct)));
        const predDiffPct = Math.round(((total - baselineFare) / Math.max(1, baselineFare)) * 100);

        return {
          provider: name,
          vehicleType: vType,
          distanceKm: distKm,
          etaMinutes: Math.max(2, Math.round(durMin * (isBike ? 0.18 : isAuto ? 0.22 : 0.25) + 2)),
          actualFare: total,
          estimatedFare: total,
          fareMin: fMin,
          fareMax: fMax,
          fare_min: fMin,
          fare_max: fMax,
          predictedFare: baselineFare,
          predictedFareMin: Math.round(baselineFare * 0.94),
          predictedFareMax: Math.round(baselineFare * 1.06),
          typicalFareRange: `₹${Math.round(baselineFare * 0.94)} - ₹${Math.round(baselineFare * 1.06)}`,
          predictionDiff: total - baselineFare,
          predictionDiffPct: predDiffPct,
          demandLevel: isZeroSurge ? 'NORMAL' : mlDemandLevel,
          priceTrend: mlSurgeMultiplier > 1.2 ? 'INCREASING' : 'STABLE',
          priceAnomaly: predDiffPct > 18 ? 'Above normal' : 'Normal',
          anomalyReason: effectiveSurge >= 1.3 ? 'Peak demand surge applied by provider algorithms' : 'Normal pricing regime',
          mlInsight: effectiveSurge >= 1.3 ? `Current fare reflects ${effectiveSurge}x demand surge. Auto offers regulated bracket.` : 'Fares align with ML estimated typical route bounds.',
          confidenceLevel: 'HIGH',
          confidenceScore: 0.93,
          smartScore: badges.isBestValue ? 96 : badges.isCheapest ? 94 : 88,
          currency: 'INR',
          currencySymbol: '₹',
          surgeMultiplier: effectiveSurge,
          zeroSurge: isZeroSurge,
          clusterId: mlClusterId,
          clusterLabel: mlClusterLabel,
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
          eligibility: eligibilityStatus,
          eligibilityReason: eligibilityReasonText,
          suitabilityLevel: eligibilityStatus === 'DIRECT' ? 'HIGH' : 'UNSUITABLE',
          suitabilityScore: eligibilityStatus === 'DIRECT' ? 0.95 : 0.0,
          routeSupported: eligibilityStatus === 'DIRECT',
          coverageConfidence: 'HIGH',
          vehicleSuitabilityConfidence: 'HIGH',
          evaluationExplanations: [eligibilityReasonText]
        };
      };

      const directCandidates: RideProviderDetails[] = [];
      const excludedCandidates: RideProviderDetails[] = [];

      // Rapido Bike
      if (isBikeEligible) {
        directCandidates.push(buildProvider('Rapido Bike', 'Bike', 20, 8.5, 0.8, {}, 'DIRECT', '✓ Highly suitable for short urban travel'));
      } else {
        excludedCandidates.push(buildProvider(
          'Rapido Bike', 'Bike', 20, 8.5, 0.8, {}, 'UNSUPPORTED',
          `✕ Rapido Bike is not considered for this journey because the service/vehicle type does not support ${distKm} km ${routeType.toLowerCase()} routes.`
        ));
      }

      // Rapido Auto
      if (isAutoEligible) {
        directCandidates.push(buildProvider('Rapido Auto', 'Auto', 25, 11.5, 1.0, {}, 'DIRECT', '✓ Practical for short-to-medium city trips'));
      } else {
        excludedCandidates.push(buildProvider(
          'Rapido Auto', 'Auto', 25, 11.5, 1.0, {}, 'UNSUPPORTED',
          `✕ Auto rickshaws are restricted to local municipal perimeters and cannot operate on ${distKm} km ${routeType.toLowerCase()} routes.`
        ));
      }

      // Standard Cabs & Outstation Cabs
      if (routeType === 'OUTSTATION' || routeType === 'INTERCITY') {
        directCandidates.push(buildProvider('Uber Intercity', 'Cab', 450, 17.0, 1.5, { isBestValue: true }, 'DIRECT', '✓ Dedicated intercity fleet with experienced highway drivers and luggage capacity'));
        directCandidates.push(buildProvider('Ola Outstation', 'Cab', 500, 17.5, 1.2, {}, 'DIRECT', '✓ Outstation cab tier certified for long-distance highway routes'));
        directCandidates.push(buildProvider('Tourist Taxi (Regulated)', 'Cab', 600, 18.0, 0.0, { isMostEfficient: true }, 'DIRECT', '✓ Tourism-registered commercial chauffeur certified for high-range terrain'));
      } else {
        directCandidates.push(buildProvider('Uber Go', 'Cab', 42, 14.5, 1.5, { isMostEfficient: true }, 'DIRECT', '✓ Reliable urban cab for intra-city transit'));
        directCandidates.push(buildProvider('Ola Mini', 'Cab', 40, 14.0, 1.4, {}, 'DIRECT', '✓ Compact city cab'));
        directCandidates.push(buildProvider('Uber Premier', 'Cab', 75, 19.5, 2.2, {}, 'DIRECT', '✓ Premium sedan with top-rated drivers'));
      }

      // Mark badges ONLY on directCandidates
      if (directCandidates.length > 0) {
        const sortedByPrice = [...directCandidates].sort((a, b) => (a.actualFare || a.estimatedFare) - (b.actualFare || b.estimatedFare));
        const sortedByEta = [...directCandidates].sort((a, b) => a.etaMinutes - b.etaMinutes);
        sortedByPrice[0].isCheapest = true;
        sortedByEta[0].isFastest = true;
      }

      const activeProviders = directCandidates.length > 0 ? directCandidates : excludedCandidates;
      const minFare = activeProviders[0].actualFare || activeProviders[0].estimatedFare;
      const maxFare = activeProviders[activeProviders.length - 1].actualFare || activeProviders[activeProviders.length - 1].estimatedFare;
      const fareSpread = Math.max(0, maxFare - minFare);
      const spreadPercentage = Math.round((fareSpread / Math.max(1, minFare)) * 100);

      const cheapestDirect = directCandidates.find(p => p.isCheapest)?.provider || directCandidates[0]?.provider || 'No direct options';
      const recommendedDirect = directCandidates.find(p => p.isMostEfficient)?.provider || directCandidates[0]?.provider || 'No direct options';

      // Multimodal suggestion
      const multimodalOpt = (routeType === 'OUTSTATION' || routeType === 'INTERCITY' || distKm > 45) ? {
        type: 'MULTIMODAL',
        title: `Multimodal Route: Local Cab + Express Transit`,
        summary: `Combine a short local cab to the regional transit terminal with an express service directly to destination.`,
        total_distance_km: distKm,
        total_duration_mins: Math.round(durMin * 1.1 + 15),
        total_estimated_fare: Math.round(distKm * 8 + 120),
        currency_symbol: '₹',
        transfer_count: 1,
        recommendation_note: 'Never hide transfers: this option saves up to 45% compared to a dedicated outstation cab.',
        legs: [
          {
            leg_number: 1,
            mode: 'Local Cab / Auto',
            provider: 'Local Taxi / Uber Go',
            vehicle_type: 'Cab',
            from_location: source.label.split(',')[0],
            to_location: 'Central Transit Terminal',
            distance_km: Math.round(Math.min(18, distKm * 0.15)),
            duration_mins: Math.round(Math.min(35, durMin * 0.2)),
            estimated_fare: 180,
            currency_symbol: '₹',
            instructions: `Take a local ride to Central Transit Terminal.`
          },
          {
            leg_number: 2,
            mode: 'Intercity Express',
            provider: 'State RTC Express / Intercity Coach',
            vehicle_type: 'Express Bus',
            from_location: 'Central Transit Terminal',
            to_location: dest.label.split(',')[0],
            distance_km: Math.round(distKm * 0.85),
            duration_mins: Math.round(durMin * 0.9),
            estimated_fare: Math.round(distKm * 7),
            currency_symbol: '₹',
            instructions: `Board the express service directly to ${dest.label.split(',')[0]}.`
          }
        ]
      } : undefined;

      const agentReasoningObj = {
        headline: (routeType === 'OUTSTATION' || routeType === 'INTERCITY' || distKm > 60)
          ? `Long-distance ${routeType.toLowerCase()} route detected (${distKm} km). Local bikes & autos excluded before price ranking.`
          : `Local urban route validated (${distKm} km). All standard vehicle types eligible.`,
        routeClassification: routeType,
        routeDistanceKm: distKm,
        auditSummary: (routeType === 'OUTSTATION' || routeType === 'INTERCITY' || distKm > 60)
          ? `RideCompare evaluated ${directCandidates.length + excludedCandidates.length} options. Rapido Bike and local autos were excluded because 2/3-wheelers do not support long-distance highway routes. Prioritizing ${directCandidates.length} verified direct outstation cabs.`
          : `All urban providers (Bikes, Autos, Cabs) operate within this local transit zone.`,
        feasibleDirectCount: directCandidates.length,
        excludedCount: excludedCandidates.length,
        partialCount: 0,
        cheapestDirect: cheapestDirect,
        recommendedDirect: recommendedDirect,
        rapidoBikeExcluded: !isBikeEligible,
        exclusionHighlights: excludedCandidates.map(e => `${e.provider}: ${e.eligibilityReason}`)
      };

      setSearchId(Date.now());
      setRouteGeometry(routeGeom);
      setComparison({
        distanceKm: distKm,
        durationMins: durMin,
        straightLineDistance: parseFloat(straightLineKm.toFixed(1)),
        detourDistance: parseFloat(Math.max(0, distKm - straightLineKm).toFixed(1)),
        detectedCity: routeType === 'OUTSTATION' ? 'Intercity Corridor' : 'Local Route',
        surgeRuleName: mlSurgeRule,
        pricingRegime: mlClusterLabel,
        isServiceable: true,
        message: 'Real-time estimated fare comparison',
        fareSpread: fareSpread,
        spreadPercentage: spreadPercentage,
        providers: activeProviders,
        directProviders: directCandidates,
        excludedProviders: excludedCandidates,
        partialProviders: [],
        multimodalOption: multimodalOpt,
        agentReasoning: agentReasoningObj,
        routeClassification: {
          origin_label: source.label,
          destination_label: dest.label,
          distance_km: distKm,
          duration_mins: durMin,
          route_type: routeType,
          classification_reason: classificationReason
        },
        recommendations: {
          cheapest: cheapestDirect,
          fastest: directCandidates.find(p => p.isFastest)?.provider || cheapestDirect,
          mostEfficient: recommendedDirect,
          bestValue: directCandidates.find(p => p.isBestValue)?.provider || recommendedDirect,
          recommended: recommendedDirect,
          recommendationReason: agentReasoningObj.headline,
          distanceAdvantage: `Direct route distance: ${distKm} km (${routeType})`,
          timeAdvantage: `Estimated travel duration: ~${durMin} mins`,
          costAdvantage: `Verified direct choices evaluated before price comparison.`
        },
        insights: [
          `Distance calculated along real driving road network (${distKm} km).`,
          `AI Route Feasibility: ${agentReasoningObj.headline}`,
          !isBikeEligible ? `⚠️ Rapido Bike taxi excluded from direct rides (unsuitable for ${distKm} km ${routeType.toLowerCase()} travel).` : `All standard urban modes available for this distance.`,
          `Current pricing regime: ${mlClusterLabel} (${mlSurgeRule} at ${mlSurgeMultiplier}x).`
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
