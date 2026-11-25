import type { FareQuote, LatLng } from '../types/fare';

export interface FareProvider {
  getFareEstimate(pickup: LatLng, drop: LatLng, at: Date): Promise<FareQuote[]>;
}
