export const SURGE_CONFIG = {
  surgeCap: 2,
  peakWindows: [
    { startHour: 8, endHour: 11, multiplier: 1.45 },
    { startHour: 17, endHour: 20, multiplier: 1.65 },
  ],
  rainMultiplier: 1.25,
  rainChance: 0.28,
  minimumEtaMinutes: 2,
  maximumEtaMinutes: 10,
  jitterIntervalMinutes: 5,
  rideTypes: [
    { name: 'Bike', minimumFare: 25, perKm: 7 },
    { name: 'Auto', minimumFare: 35, perKm: 11 },
    { name: 'Mini', minimumFare: 50, perKm: 14 },
    { name: 'Sedan', minimumFare: 75, perKm: 18 },
  ] as const,
};

export interface RegionalRideProfile {
  region: string;
  countryCode: string;
  currency: string;
  currencySymbol: string;
  bounds: { south: number; north: number; west: number; east: number };
  rideTypes: Array<{ provider: string; name: string; minimumFare: number; perKm: number }>;
}

export const REGIONAL_RIDE_PROFILES: RegionalRideProfile[] = [
  {
    region: 'India', countryCode: 'IN', currency: 'INR', currencySymbol: '₹',
    bounds: { south: 6.5, north: 37.1, west: 68.1, east: 97.5 },
    rideTypes: [
      { provider: 'Rapido', name: 'Bike', minimumFare: 25, perKm: 7 },
      { provider: 'Uber', name: 'Auto', minimumFare: 35, perKm: 11 },
      { provider: 'Uber', name: 'Mini', minimumFare: 50, perKm: 14 },
      { provider: 'Ola', name: 'Sedan', minimumFare: 75, perKm: 18 },
      { provider: 'Namma Yatri', name: 'Cab', minimumFare: 45, perKm: 13 },
    ],
  },
  {
    region: 'United States', countryCode: 'US', currency: 'USD', currencySymbol: '$',
    bounds: { south: 24.3, north: 49.5, west: -125.1, east: -66.8 },
    rideTypes: [
      { provider: 'Uber', name: 'UberX', minimumFare: 8, perKm: 2.1 },
      { provider: 'Lyft', name: 'Lyft Standard', minimumFare: 8, perKm: 2.0 },
      { provider: 'Uber', name: 'Uber Comfort', minimumFare: 12, perKm: 2.8 },
      { provider: 'Waymo', name: 'Waymo One', minimumFare: 10, perKm: 2.5 },
    ],
  },
  {
    region: 'United Kingdom', countryCode: 'GB', currency: 'GBP', currencySymbol: '£',
    bounds: { south: 49.8, north: 61.0, west: -8.7, east: 1.8 },
    rideTypes: [
      { provider: 'TfL', name: 'Black Cab', minimumFare: 5, perKm: 3.0 },
      { provider: 'Uber', name: 'UberX', minimumFare: 5, perKm: 1.8 },
      { provider: 'Bolt', name: 'Bolt', minimumFare: 4, perKm: 1.6 },
      { provider: 'FREE NOW', name: 'Taxi', minimumFare: 5, perKm: 2.2 },
    ],
  },
  {
    region: 'European Union', countryCode: 'EU', currency: 'EUR', currencySymbol: '€',
    bounds: { south: 35.0, north: 71.2, west: -10.0, east: 31.5 },
    rideTypes: [
      { provider: 'Uber', name: 'UberX', minimumFare: 6, perKm: 1.8 },
      { provider: 'Bolt', name: 'Bolt', minimumFare: 5, perKm: 1.6 },
      { provider: 'FREE NOW', name: 'Taxi', minimumFare: 6, perKm: 2.0 },
    ],
  },
  {
    region: 'Japan', countryCode: 'JP', currency: 'JPY', currencySymbol: '¥',
    bounds: { south: 24.0, north: 46.0, west: 122.0, east: 146.0 },
    rideTypes: [
      { provider: 'GO', name: 'Taxi', minimumFare: 500, perKm: 410 },
      { provider: 'Uber', name: 'Uber Taxi', minimumFare: 500, perKm: 410 },
    ],
  },
  {
    region: 'Singapore', countryCode: 'SG', currency: 'SGD', currencySymbol: 'S$',
    bounds: { south: 1.1, north: 1.5, west: 103.6, east: 104.1 },
    rideTypes: [
      { provider: 'ComfortDelGro', name: 'Taxi', minimumFare: 4, perKm: 1.4 },
      { provider: 'Grab', name: 'GrabCar', minimumFare: 5, perKm: 1.5 },
    ],
  },
  {
    region: 'UAE', countryCode: 'AE', currency: 'AED', currencySymbol: 'AED ',
    bounds: { south: 22.5, north: 26.3, west: 51.5, east: 56.6 },
    rideTypes: [
      { provider: 'Dubai Taxi', name: 'Taxi', minimumFare: 12, perKm: 2.5 },
      { provider: 'Careem', name: 'Careem Comfort', minimumFare: 15, perKm: 2.8 },
      { provider: 'Hala', name: 'Hala Taxi', minimumFare: 12, perKm: 2.4 },
    ],
  },
  {
    region: 'Southeast Asia', countryCode: 'SEA', currency: 'USD', currencySymbol: '$',
    bounds: { south: -11.0, north: 22.0, west: 95.0, east: 141.0 },
    rideTypes: [
      { provider: 'Grab', name: 'GrabCar', minimumFare: 3, perKm: 0.7 },
      { provider: 'Grab', name: 'GrabBike', minimumFare: 1.5, perKm: 0.35 },
    ],
  },
  {
    region: 'Australia', countryCode: 'AU', currency: 'AUD', currencySymbol: 'A$',
    bounds: { south: -44.0, north: -10.0, west: 112.0, east: 154.0 },
    rideTypes: [
      { provider: 'Uber', name: 'UberX', minimumFare: 6, perKm: 1.7 },
      { provider: 'DiDi', name: 'DiDi', minimumFare: 6, perKm: 1.6 },
      { provider: '13CABS', name: 'Taxi', minimumFare: 7, perKm: 2.0 },
    ],
  },
  {
    region: 'Canada', countryCode: 'CA', currency: 'CAD', currencySymbol: 'C$',
    bounds: { south: 41.0, north: 83.0, west: -141.0, east: -52.0 },
    rideTypes: [
      { provider: 'Uber', name: 'UberX', minimumFare: 7, perKm: 2.0 },
      { provider: 'Lyft', name: 'Lyft', minimumFare: 7, perKm: 1.9 },
    ],
  },
  {
    region: 'Brazil', countryCode: 'BR', currency: 'BRL', currencySymbol: 'R$',
    bounds: { south: -34.0, north: 5.4, west: -74.0, east: -34.0 },
    rideTypes: [
      { provider: 'Uber', name: 'UberX', minimumFare: 6, perKm: 2.2 },
      { provider: '99', name: '99POP', minimumFare: 5, perKm: 2.0 },
      { provider: 'Cabify', name: 'Cabify', minimumFare: 7, perKm: 2.4 },
    ],
  },
  {
    region: 'South Korea', countryCode: 'KR', currency: 'KRW', currencySymbol: '₩',
    bounds: { south: 33.0, north: 38.7, west: 124.0, east: 132.0 },
    rideTypes: [
      { provider: 'TADA', name: 'TADA', minimumFare: 4500, perKm: 900 },
      { provider: 'Uber', name: 'Uber Taxi', minimumFare: 4000, perKm: 850 },
      { provider: 'Kakao T', name: 'Kakao Taxi', minimumFare: 3800, perKm: 800 },
    ],
  },
  {
    region: 'South Africa', countryCode: 'ZA', currency: 'ZAR', currencySymbol: 'R',
    bounds: { south: -35.0, north: -22.0, west: 16.0, east: 33.0 },
    rideTypes: [
      { provider: 'Uber', name: 'UberGo', minimumFare: 25, perKm: 9 },
      { provider: 'Bolt', name: 'Bolt', minimumFare: 22, perKm: 8.5 },
    ],
  },
];
