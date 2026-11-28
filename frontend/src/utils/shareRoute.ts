import type { LocationInfo } from '../types/ride';

export function buildRouteShareUrl(
  primary?: LocationInfo | null,
  secondary?: LocationInfo | null
): string {
  const base = 'https://ridecompare.world/';
  const params = new URLSearchParams();
  if (primary && Number.isFinite(primary.lat) && Number.isFinite(primary.lng)) {
    params.set('from', primary.placeName || primary.label);
    params.set('flat', primary.lat.toFixed(6));
    params.set('flng', primary.lng.toFixed(6));
  }
  if (secondary && Number.isFinite(secondary.lat) && Number.isFinite(secondary.lng)) {
    params.set('to', secondary.placeName || secondary.label);
    params.set('tlat', secondary.lat.toFixed(6));
    params.set('tlng', secondary.lng.toFixed(6));
  }
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

export function buildLocationShareText(
  primary?: LocationInfo | null,
  secondary?: LocationInfo | null,
  fallbackLabel?: string
): { text: string; url: string } {
  const url = buildRouteShareUrl(primary, secondary);
  if (primary && secondary) {
    return {
      text: `Compare cab, auto & bike fares on RideCompare.world:\n${primary.placeName || primary.label} → ${secondary.placeName || secondary.label}\n${url}`,
      url,
    };
  }
  const name = primary?.placeName || primary?.label || fallbackLabel || 'this area';
  return {
    text: `Compare rides near ${name} on RideCompare.world:\n${url}`,
    url,
  };
}

export function shareToWhatsApp(text: string): void {
  const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
  window.open(url, '_blank', 'noopener,noreferrer');
}

export function shareToMessages(text: string): void {
  const isIOS = typeof navigator !== 'undefined' && /iPad|iPhone|iPod/i.test(navigator.userAgent);
  const href = isIOS
    ? `sms:&body=${encodeURIComponent(text)}`
    : `sms:?body=${encodeURIComponent(text)}`;
  window.location.href = href;
}

export async function copyShareValue(value: string): Promise<boolean> {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    return false;
  }
  return false;
}

export async function shareToInstagramDM(text: string): Promise<boolean> {
  const copied = await copyShareValue(text);
  window.open('https://www.instagram.com/direct/inbox/', '_blank', 'noopener,noreferrer');
  return copied;
}

export async function triggerNativeShare(title: string, text: string, url: string): Promise<boolean> {
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
      await navigator.share({ title, text, url });
      return true;
    }
  } catch {
    return false;
  }
  return false;
}
