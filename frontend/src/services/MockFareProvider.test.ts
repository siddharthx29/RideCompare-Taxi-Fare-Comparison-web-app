import { describe, expect, it } from 'vitest';
import {
  calculateBaseFare,
  calculateDistanceKm,
  calculateSurgeMultiplier,
} from './MockFareProvider';

describe('Mock fare calculations', () => {
  it('calculates base fare from distance and applies minimum fare', () => {
    expect(calculateBaseFare(2, 35, 11)).toBe(35);
    expect(calculateBaseFare(10, 35, 11)).toBe(110);
  });

  it('calculates haversine distance', () => {
    const distance = calculateDistanceKm(
      { lat: 12.9716, lng: 77.5946 },
      { lat: 12.9716, lng: 77.5946 }
    );
    expect(distance).toBe(0);
  });

  it('applies peak surge and clamps to the configured cap', () => {
    const morning = new Date('2026-11-18T09:00:00');
    expect(calculateSurgeMultiplier(morning, false)).toBeGreaterThanOrEqual(1);

    const extreme = new Date('2026-11-18T18:00:00');
    expect(calculateSurgeMultiplier(extreme, true)).toBeLessThanOrEqual(2);
  });
});
