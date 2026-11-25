import { REGIONAL_RIDE_PROFILES, SURGE_CONFIG } from '../config/pricing';
import type { FareProvider } from './FareProvider';
import type { FareQuote, LatLng } from '../types/fare';

export function calculateDistanceKm(pickup: LatLng, drop: LatLng): number {
  const earthRadiusKm = 6371;
  const toRadians = (degrees: number) => degrees * Math.PI / 180;
  const latitudeDelta = toRadians(drop.lat - pickup.lat);
  const longitudeDelta = toRadians(drop.lng - pickup.lng);
  const latitude1 = toRadians(pickup.lat);
  const latitude2 = toRadians(drop.lat);
  const haversine =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(latitude1) * Math.cos(latitude2) * Math.sin(longitudeDelta / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

export function pseudoRandom(seed: number): number {
  const value = Math.sin(seed * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

export function isRainyDay(at: Date): boolean {
  const daySeed = at.getFullYear() * 10000 + (at.getMonth() + 1) * 100 + at.getDate();
  return pseudoRandom(daySeed) < SURGE_CONFIG.rainChance;
}

export function calculateSurgeMultiplier(at: Date, rainyOverride?: boolean): number {
  let multiplier = 1;
  const peak = SURGE_CONFIG.peakWindows.find(
    window => at.getHours() >= window.startHour && at.getHours() < window.endHour
  );
  if (peak) multiplier = peak.multiplier;

  if (rainyOverride ?? isRainyDay(at)) {
    multiplier *= SURGE_CONFIG.rainMultiplier;
  }

  const fiveMinuteSeed = Math.floor(at.getTime() / (SURGE_CONFIG.jitterIntervalMinutes * 60 * 1000));
  const jitter = 0.9 + pseudoRandom(fiveMinuteSeed) * 0.2;
  multiplier *= jitter;

  return Math.min(SURGE_CONFIG.surgeCap, Math.max(1, Number(multiplier.toFixed(2))));
}

export function calculateBaseFare(distanceKm: number, minimumFare: number, perKm: number): number {
  return Math.max(minimumFare, Number((distanceKm * perKm).toFixed(2)));
}

export class MockFareProvider implements FareProvider {
  async getFareEstimate(pickup: LatLng, drop: LatLng, at: Date): Promise<FareQuote[]> {
    const distanceKm = calculateDistanceKm(pickup, drop);
    const surgeMultiplier = calculateSurgeMultiplier(at);
    const pickupInside = (profile: (typeof REGIONAL_RIDE_PROFILES)[number]) =>
      pickup.lat >= profile.bounds.south &&
      pickup.lat <= profile.bounds.north &&
      pickup.lng >= profile.bounds.west &&
      pickup.lng <= profile.bounds.east;
    const profile = REGIONAL_RIDE_PROFILES.find(pickupInside) || REGIONAL_RIDE_PROFILES[0];

    return profile.rideTypes.map((ride, index) => {
      const baseFare = calculateBaseFare(distanceKm, ride.minimumFare, ride.perKm);
      const finalFare = Number((baseFare * surgeMultiplier).toFixed(2));
      const randomEta = pseudoRandom(
        at.getTime() / (SURGE_CONFIG.jitterIntervalMinutes * 60 * 1000) + index * 31
      );
      const etaRange = SURGE_CONFIG.maximumEtaMinutes - SURGE_CONFIG.minimumEtaMinutes;
      const eta = SURGE_CONFIG.minimumEtaMinutes +
        Math.floor(randomEta * (etaRange + 1)) +
        Math.ceil(Math.max(0, surgeMultiplier - 1) * 1.5);

      return {
        provider: ride.provider,
        rideType: ride.name,
        baseFare,
        surgeMultiplier,
        finalFare,
        etaMinutes: Math.min(SURGE_CONFIG.maximumEtaMinutes, eta),
        capturedAt: at.toISOString(),
        currency: profile.currency,
        currencySymbol: profile.currencySymbol,
      };
    });
  }
}
