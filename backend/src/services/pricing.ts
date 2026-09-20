import fs from 'fs';
import path from 'path';
import { RideProviderDetails, ComparisonResult } from './types';

// Fully populated hardcoded fallback config in case JSON fails to load
const fallbackFares = {
  "dynamicPricing": {
    "morningPeak": { "startHour": 7, "endHour": 10, "multiplier": 1.4 },
    "eveningPeak": { "startHour": 17, "endHour": 21, "multiplier": 1.5 },
    "nightCharges": { "startHour": 23, "endHour": 5, "multiplier": 1.25 }
  },
  "defaultCity": "Bangalore",
  "cities": {
    "Bangalore": {
      "toll": {
        "airportKeywords": ["airport", "kempegowda", "kia"],
        "charge": 120
      },
      "providers": {
        "Uber Go": { "baseFare": 50, "perKmRate": 14.0, "perMinRate": 2.0, "platformFee": 15, "vehicleType": "Cab", "etaMultiplier": 1.0, "rating": 4.6 },
        "Uber Premier": { "baseFare": 70, "perKmRate": 18.0, "perMinRate": 2.5, "platformFee": 20, "vehicleType": "Cab", "etaMultiplier": 0.95, "rating": 4.8 },
        "Rapido Bike": { "baseFare": 15, "perKmRate": 7.0, "perMinRate": 1.0, "platformFee": 5, "vehicleType": "Bike", "etaMultiplier": 0.8, "rating": 4.4 },
        "Rapido Auto": { "baseFare": 28, "perKmRate": 10.0, "perMinRate": 1.5, "platformFee": 10, "vehicleType": "Auto", "etaMultiplier": 1.05, "rating": 4.3 },
        "Ola Mini": { "baseFare": 48, "perKmRate": 14.5, "perMinRate": 2.2, "platformFee": 15, "vehicleType": "Cab", "etaMultiplier": 1.05, "rating": 4.2 },
        "Ola Prime": { "baseFare": 65, "perKmRate": 17.5, "perMinRate": 2.4, "platformFee": 18, "vehicleType": "Cab", "etaMultiplier": 1.0, "rating": 4.5 },
        "Local Taxi": { "baseFare": 60, "perKmRate": 16.0, "perMinRate": 0.0, "platformFee": 0, "vehicleType": "Cab", "etaMultiplier": 1.3, "rating": 3.5 }
      }
    }
  }
};

// Check multiple locations to locate the configuration file across dev, production, and Docker
const possiblePaths = [
  path.join(__dirname, '../config/fares.json'), // Dev: src/config/fares.json
  path.join(__dirname, '../../src/config/fares.json'), // Production: dist/services/../../src/config/fares.json
  path.join(process.cwd(), 'src/config/fares.json'), // Cwd-relative src/config
  path.join(process.cwd(), 'dist/config/fares.json'), // Cwd-relative dist/config
  path.join(process.cwd(), 'backend/src/config/fares.json'), // Root folder context
  path.join(process.cwd(), 'backend/dist/config/fares.json')
];

let fareConfig: any = fallbackFares;
let loaded = false;

for (const p of possiblePaths) {
  try {
    if (fs.existsSync(p)) {
      const content = fs.readFileSync(p, 'utf8');
      const parsed = JSON.parse(content);
      // Verify parsed config structure is valid
      if (parsed && parsed.cities && Object.keys(parsed.cities).length > 0) {
        fareConfig = parsed;
        loaded = true;
        console.log(`[Pricing Configuration] Loaded configuration file from: ${p}`);
        break;
      }
    }
  } catch (err) {
    // Continue loop
  }
}

if (!loaded) {
  console.warn('[Pricing Configuration] All fares.json paths failed or were empty. Using hardcoded Bangalore fallback configurations.');
}

export function detectCity(source: string, destination: string): string {
  const text = `${source} ${destination}`.toLowerCase();
  if (text.includes('kochi') || text.includes('cochin') || text.includes('ernakulam')) {
    return 'Kochi';
  }
  if (text.includes('chennai') || text.includes('madras')) {
    return 'Chennai';
  }
  if (text.includes('hyderabad')) {
    return 'Hyderabad';
  }
  if (text.includes('mumbai') || text.includes('bombay')) {
    return 'Mumbai';
  }
  if (text.includes('delhi') || text.includes('noida') || text.includes('gurgaon') || text.includes('ghaziabad') || text.includes('ncr')) {
    return 'Delhi';
  }
  return 'Bangalore'; // default
}

export function getSurgeMultiplier(): { multiplier: number, ruleName: string } {
  const now = new Date();
  
  // Convert current time to IST timezone
  const utcOffset = now.getTimezoneOffset() * 60000;
  const utcTime = now.getTime() + utcOffset;
  const istTime = new Date(utcTime + (3600000 * 5.5));
  const currentHour = istTime.getHours();

  const { dynamicPricing } = fareConfig;

  // Morning Peak: 7:00 AM – 10:00 AM
  if (currentHour >= dynamicPricing.morningPeak.startHour && currentHour < dynamicPricing.morningPeak.endHour) {
    return { multiplier: dynamicPricing.morningPeak.multiplier, ruleName: 'Morning Peak' };
  }
  
  // Evening Peak: 5:00 PM – 9:00 PM
  if (currentHour >= dynamicPricing.eveningPeak.startHour && currentHour < dynamicPricing.eveningPeak.endHour) {
    return { multiplier: dynamicPricing.eveningPeak.multiplier, ruleName: 'Evening Peak' };
  }

  // Night Charges: 11:00 PM – 5:00 AM
  if (currentHour >= dynamicPricing.nightCharges.startHour || currentHour < dynamicPricing.nightCharges.endHour) {
    return { multiplier: dynamicPricing.nightCharges.multiplier, ruleName: 'Night Charges' };
  }

  return { multiplier: 1.0, ruleName: 'Standard' };
}

function calculateHaversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

import { enrichFaresWithML } from './mlClient';

export async function calculateFaresAndScores(
  distanceKm: number,
  durationMins: number,
  source: string,
  destination: string,
  startLon: number,
  startLat: number,
  endLon: number,
  endLat: number,
  osrmSuccess: boolean = true
): Promise<ComparisonResult> {
  const city = detectCity(source, destination);
  
  // Safe extraction to prevent undefined crashes
  let cityData = fareConfig.cities[city] || fareConfig.cities[fareConfig.defaultCity];
  if (!cityData) {
    cityData = fallbackFares.cities.Bangalore;
  }
  
  const { multiplier: peakMultiplier, ruleName: surgeRuleName } = getSurgeMultiplier();

  // Straight-line vs road route calculations
  const straightLineDistance = calculateHaversineDistance(startLat, startLon, endLat, endLon);
  const detourDistance = Math.max(0, distanceKm - straightLineDistance);

  // Determine Airport Toll Estimate
  let tollEstimate = 0;
  if (cityData.toll) {
    const combinedText = `${source} ${destination}`.toLowerCase();
    const isAirport = cityData.toll.airportKeywords.some((kw: string) => combinedText.includes(kw));
    if (isAirport && distanceKm > 10) {
      tollEstimate = cityData.toll.charge;
    }
  }

  const pickupAddr = encodeURIComponent(source);
  const dropoffAddr = encodeURIComponent(destination);

  // Compile calculations for each provider defined in the city pricing config (Ground Truth Actual Fares)
  const providerKeys = Object.keys(cityData.providers);
  let baseProviders: RideProviderDetails[] = providerKeys.map((name) => {
    const cfg = cityData.providers[name];
    
    // Exact fare formula: (baseFare + (dist * rate) + (time * rate)) * peakMultiplier + platformFee + toll
    const dFare = distanceKm * cfg.perKmRate;
    const tFare = durationMins * cfg.perMinRate;
    const rawFare = (cfg.baseFare + dFare + tFare) * peakMultiplier + cfg.platformFee + tollEstimate;
    const actualFare = Math.round(rawFare);

    // Deep link patterns
    const appDeepLink = name.toLowerCase().includes('uber')
      ? `uber://?action=setPickup&pickup[formatted_address]=${pickupAddr}&dropoff[formatted_address]=${dropoffAddr}`
      : name.toLowerCase().includes('ola')
      ? `olacabs://app/launch?pickup=my_location`
      : name.toLowerCase().includes('rapido')
      ? `rapido://booking`
      : `taxifarecompare://booking`;

    const webLink = name.toLowerCase().includes('uber')
      ? `https://m.uber.com/ul/?action=setPickup&pickup[formatted_address]=${pickupAddr}&dropoff[formatted_address]=${dropoffAddr}`
      : name.toLowerCase().includes('ola')
      ? `https://www.olacabs.com/`
      : name.toLowerCase().includes('rapido')
      ? `https://www.rapido.bike/`
      : `https://www.google.com/search?q=local+taxi+booking+${city}`;

    // Confidence Level
    const confidence = !osrmSuccess ? 'Low' : (peakMultiplier > 1.0 ? 'Medium' : 'High');

    // Calculate dynamic ETA using provider multiplier
    const providerEta = Math.round(durationMins * (cfg.etaMultiplier || 1.0));

    // Unit costs
    const costPerKm = distanceKm > 0 ? Number((actualFare / distanceKm).toFixed(1)) : 0;
    const costPerMin = providerEta > 0 ? Number((actualFare / providerEta).toFixed(1)) : 0;

    return {
      provider: name,
      vehicleType: cfg.vehicleType,
      distanceKm: Number(distanceKm.toFixed(1)),
      etaMinutes: providerEta,
      actualFare,
      estimatedFare: actualFare, // alias for actual provider fare
      predictedFare: actualFare, // enriched below by ML
      predictionDiff: 0,
      predictionDiffPct: 0,
      surgeMultiplier: peakMultiplier,
      confidence,
      confidenceScore: confidence === 'High' ? 92 : (confidence === 'Medium' ? 78 : 55),
      confidenceLevel: confidence,
      clusterId: 0,
      clusterLabel: 'Standard City Transit',
      isAnomaly: false,
      smartScore: 0,
      costPerKm,
      costPerMin,
      efficiencyScore: 0,
      recommendationScore: 0,
      baseFare: cfg.baseFare,
      distanceFare: Number(dFare.toFixed(1)),
      durationFare: Number(tFare.toFixed(1)),
      platformFee: cfg.platformFee,
      tollEstimate,
      appDeepLink,
      webLink,
      isCheapest: false,
      isFastest: false,
      isMostEfficient: false,
      isBestValue: false
    };
  });

  // Enrich provider quotes through Machine Learning Subsystem
  const mlResult = await enrichFaresWithML(
    distanceKm,
    durationMins,
    source,
    destination,
    peakMultiplier,
    peakMultiplier > 1.3 ? 'Heavy' : 'Normal',
    surgeRuleName,
    osrmSuccess,
    baseProviders
  );

  let providers = mlResult.enrichedProviders;

  // Perform comparisons and score rankings
  if (providers.length > 0) {
    const fares = providers.map(p => p.actualFare);
    const times = providers.map(p => p.etaMinutes);

    const minFare = Math.min(...fares);
    const minTime = Math.min(...times);

    // Find category specific minimums
    const cabs = providers.filter(p => p.vehicleType === 'Cab');
    const autos = providers.filter(p => p.vehicleType === 'Auto');
    const bikes = providers.filter(p => p.vehicleType === 'Bike');

    const minFareCab = cabs.length > 0 ? Math.min(...cabs.map(c => c.actualFare)) : minFare;
    const minTimeCab = cabs.length > 0 ? Math.min(...cabs.map(c => c.etaMinutes)) : minTime;

    const minFareAuto = autos.length > 0 ? Math.min(...autos.map(a => a.actualFare)) : minFare;
    const minTimeAuto = autos.length > 0 ? Math.min(...autos.map(a => a.etaMinutes)) : minTime;

    const minFareBike = bikes.length > 0 ? Math.min(...bikes.map(b => b.actualFare)) : minFare;
    const minTimeBike = bikes.length > 0 ? Math.min(...bikes.map(b => b.etaMinutes)) : minTime;

    providers.forEach(p => {
      let typeMinFare = minFare;
      let typeMinTime = minTime;

      if (p.vehicleType === 'Cab') {
        typeMinFare = minFareCab;
        typeMinTime = minTimeCab;
      } else if (p.vehicleType === 'Auto') {
        typeMinFare = minFareAuto;
        typeMinTime = minTimeAuto;
      } else if (p.vehicleType === 'Bike') {
        typeMinFare = minFareBike;
        typeMinTime = minTimeBike;
      }

      const cfg = cityData.providers[p.provider];
      const rating = cfg ? cfg.rating : 4.0;

      // 1. Efficiency Score (40% travel time, 40% fare cost, 20% route efficiency)
      const fareEfficiency = p.actualFare > 0 ? (minFare / p.actualFare) : 1.0;
      const timeEfficiency = p.etaMinutes > 0 ? (minTime / p.etaMinutes) : 1.0;
      
      const rawRouteEfficiency = distanceKm > 0 ? (straightLineDistance / distanceKm) : 1.0;
      const routeMultiplier = p.vehicleType === 'Bike' ? 1.08 : (p.vehicleType === 'Auto' ? 1.02 : 1.0);
      const routeEfficiencyScore = Math.min(1.0, rawRouteEfficiency * routeMultiplier);

      const efficiencyScore = Math.round((timeEfficiency * 40) + (fareEfficiency * 40) + (routeEfficiencyScore * 20));
      p.efficiencyScore = efficiencyScore;

      // 2. Best Value Score (35% price, 35% time, 10% route, 20% comfort/rating)
      const ratingEfficiency = rating / 5.0;
      const rawScore = (fareEfficiency * 35) + (timeEfficiency * 35) + (routeEfficiencyScore * 10) + (ratingEfficiency * 20);
      p.recommendationScore = Math.round(rawScore);

      if (!p.smartScore) {
        p.smartScore = efficiencyScore;
      }
    });

    // Mark Highlights
    const lowestFare = Math.min(...providers.map(p => p.actualFare));
    const lowestETA = Math.min(...providers.map(p => p.etaMinutes));
    const highestEfficiency = Math.max(...providers.map(p => p.efficiencyScore));
    const highestBestValue = Math.max(...providers.map(p => p.smartScore || p.recommendationScore));

    providers.forEach(p => {
      if (p.actualFare === lowestFare) p.isCheapest = true;
      if (p.etaMinutes === lowestETA) p.isFastest = true;
      if (p.efficiencyScore === highestEfficiency) p.isMostEfficient = true;
      if ((p.smartScore || p.recommendationScore) === highestBestValue) p.isBestValue = true;
    });
  }

  // Sort providers strictly by cheapest actual fare (ascending)
  providers.sort((a, b) => a.actualFare - b.actualFare);

  // Recommendations summary
  const cheapest = providers.length > 0 
    ? providers.find(p => p.isCheapest)?.provider || providers[0].provider
    : 'None';
    
  const fastest = providers.length > 0 
    ? providers.find(p => p.isFastest)?.provider || providers[0].provider
    : 'None';

  const mostEfficient = providers.length > 0
    ? providers.find(p => p.isMostEfficient)?.provider || providers[0].provider
    : 'None';

  const bestValue = providers.length > 0 
    ? providers.find(p => p.isBestValue)?.provider || providers[0].provider
    : 'None';

  // Calculate recommendation reason and advantages for the recommended option
  let recommendationReason = '';
  let distanceAdvantage = '';
  let timeAdvantage = '';
  let costAdvantage = '';

  const recommended = providers.find(p => p.provider === mostEfficient) || providers[0];
  if (recommended && providers.length > 0) {
    const fares = providers.map(p => p.actualFare);
    const times = providers.map(p => p.etaMinutes);
    const maxFare = Math.max(...fares);
    const slowestETA = Math.max(...times);

    const sumFares = fares.reduce((a, b) => a + b, 0);
    const sumTimes = times.reduce((a, b) => a + b, 0);
    const avgFare = sumFares / providers.length;
    const avgTime = sumTimes / providers.length;

    const costDiff = avgFare - recommended.actualFare;
    const timeDiff = avgTime - recommended.etaMinutes;

    recommendationReason = `₹${Math.round(Math.abs(costDiff))} ${costDiff >= 0 ? 'cheaper' : 'more expensive'} than average • ${Math.round(Math.abs(timeDiff))} mins ${timeDiff >= 0 ? 'faster' : 'slower'} than alternatives • Efficiency Score: ${recommended.efficiencyScore}/100`;
    
    distanceAdvantage = `Direct road route of ${recommended.distanceKm.toFixed(1)} km with a minor detour of ${detourDistance.toFixed(1)} km from straight path.`;
    timeAdvantage = `Saves ${Math.round(slowestETA - recommended.etaMinutes)} minutes compared to the slowest transport alternative.`;
    costAdvantage = `₹${Math.round(maxFare - recommended.actualFare)} saved compared to the most expensive travel option.`;
  }

  // Dynamic Insights list
  const insights: string[] = [];
  if (providers.length > 1) {
    const minFareProvider = providers[0];
    const maxFareProvider = providers[providers.length - 1];
    
    if (minFareProvider && maxFareProvider && minFareProvider.provider !== maxFareProvider.provider) {
      const savings = maxFareProvider.actualFare - minFareProvider.actualFare;
      insights.push(`Save up to ₹${savings} by choosing ${minFareProvider.provider} instead of ${maxFareProvider.provider}.`);
    }

    const fastestProvider = providers.find(p => p.isFastest) || providers[0];
    const slowestProvider = providers.reduce((prev, curr) => prev.etaMinutes > curr.etaMinutes ? prev : curr);
    
    if (fastestProvider && slowestProvider && fastestProvider.provider !== slowestProvider.provider) {
      const timeSaved = slowestProvider.etaMinutes - fastestProvider.etaMinutes;
      insights.push(`${fastestProvider.provider} gets you there ${timeSaved} minutes faster than ${slowestProvider.provider}.`);
    }

    if (mostEfficient !== 'None') {
      insights.push(`${mostEfficient} is selected as the most efficient provider based on combined cost, speed, and direct road routing.`);
    }

    if (mlResult.pricingRegime) {
      insights.push(`Current Route Pricing Regime: ${mlResult.pricingRegime}.`);
    }

    if (mlResult.anomalyCount > 0) {
      insights.push(`⚠️ Anomaly Alert: ${mlResult.anomalyCount} provider fare(s) flagged with unusual pricing variance.`);
    }

    if (tollEstimate > 0) {
      insights.push(`Includes an estimated Airport Toll charge of ₹${tollEstimate} applied for ${city}.`);
    }
  }

  return {
    distanceKm: Number(distanceKm.toFixed(1)),
    durationMins: Math.round(durationMins),
    detectedCity: city,
    surgeRuleName,
    straightLineDistance: Number(straightLineDistance.toFixed(1)),
    detourDistance: Number(detourDistance.toFixed(1)),
    pricingRegime: mlResult.pricingRegime,
    fareSpread: mlResult.fareSpread,
    spreadPercentage: mlResult.spreadPercentage,
    anomalyCount: mlResult.anomalyCount,
    providers,
    recommendations: {
      cheapest,
      fastest,
      mostEfficient,
      bestValue,
      recommendationReason,
      distanceAdvantage,
      timeAdvantage,
      costAdvantage
    },
    insights,
    modelMetadata: mlResult.modelMetadata
  };
}
