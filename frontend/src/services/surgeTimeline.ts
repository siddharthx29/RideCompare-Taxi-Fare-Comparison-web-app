import type { FareProvider } from './FareProvider';
import type { LatLng } from '../types/fare';

export async function buildSurgeTimeline(
  provider: FareProvider,
  pickup: LatLng,
  drop: LatLng,
  rideType: string,
  now: Date
) {
  const points = [];
  for (let hoursAgo = 24; hoursAgo >= 0; hoursAgo -= 1) {
    const at = new Date(now.getTime() - hoursAgo * 60 * 60 * 1000);
    const quotes = await provider.getFareEstimate(pickup, drop, at);
    const quote = quotes.find(item => item.rideType === rideType);
    if (quote) {
      points.push({
        time: at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        multiplier: quote.surgeMultiplier,
        fare: quote.finalFare,
      });
    }
  }
  return points;
}
