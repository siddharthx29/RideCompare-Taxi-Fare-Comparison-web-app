import seoContent from './seoContent.json';

export interface RouteServiceEstimate {
  provider: string;
  category: string;
  minFare: number;
  maxFare: number;
  currency: string;
  notes: string;
}

export interface RouteFaq {
  question: string;
  answer: string;
}

export interface SeoRoute {
  slug: string;
  title: string;
  metaDescription: string;
  h1: string;
  origin: string;
  destination: string;
  region: string;
  distanceKm: number;
  durationMins: number;
  cheapestService: string;
  cheapestRange: string;
  summary: string;
  routeNotes: string;
  peakHours: string;
  services: RouteServiceEstimate[];
  faqs: RouteFaq[];
  relatedRoutes: string[];
}

export interface BlogSection {
  heading: string;
  paragraphs: string[];
  bullets?: string[];
}

export interface SeoPost {
  slug: string;
  title: string;
  metaDescription: string;
  category: string;
  publishedAt: string;
  updatedAt: string;
  readTimeMins: number;
  excerpt: string;
  sections: BlogSection[];
  relatedRoutes: string[];
}

export const SITE_URL = seoContent.siteUrl;
export const SITE_NAME = seoContent.siteName;
export const SEO_ROUTES: SeoRoute[] = seoContent.routes;
export const SEO_POSTS: SeoPost[] = seoContent.posts;

export function findRouteBySlug(slug: string): SeoRoute | undefined {
  return SEO_ROUTES.find((r) => r.slug === slug);
}

export function findPostBySlug(slug: string): SeoPost | undefined {
  return SEO_POSTS.find((p) => p.slug === slug);
}
