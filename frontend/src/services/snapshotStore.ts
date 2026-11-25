import type { FareQuote } from '../types/fare';

const STORAGE_KEY = 'fare-surge-tracker:snapshots';
const MAX_ENTRIES = 500;

export interface FareSnapshot {
  pickupLabel: string;
  dropLabel: string;
  routeKey: string;
  quotes: FareQuote[];
  capturedAt: string;
}

export function loadSnapshots(): FareSnapshot[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveSnapshot(snapshot: FareSnapshot): FareSnapshot[] {
  const snapshots = [...loadSnapshots(), snapshot].slice(-MAX_ENTRIES);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshots));
  return snapshots;
}
