export interface LatLng {
  lat: number;
  lng: number;
}

export interface FareQuote {
  provider: string;
  rideType: string;
  baseFare: number;
  surgeMultiplier: number;
  finalFare: number;
  etaMinutes: number;
  capturedAt: string;
  currency?: string;
  currencySymbol?: string;
}
