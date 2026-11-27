import seoContent from './seoContent.json';
import generatedProgrammatic from './generatedProgrammaticPages.json';

export interface ProgrammaticPage {
  pageId: string;
  path: string;
  pageType: string;
  location: string | null;
  title: string;
  description: string;
  h1: string;
  intro: string;
  supportedServices: string[];
  rateHighlights?: { service: string; vehicleType: string; baseFare: string; perKmRate: string }[];
  sections: { heading: string; body: string }[];
  faqs?: { question: string; answer: string }[];
  breadcrumbs: { name: string; path: string }[];
  relatedLinks?: { label: string; path: string }[];
}

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

export const PROGRAMMATIC_PAGES: ProgrammaticPage[] =
  (generatedProgrammatic as { pages: ProgrammaticPage[] }).pages || [];

export function findProgrammaticPage(pathname: string): ProgrammaticPage | undefined {
  const clean = pathname.replace(/\/+$/, '') || '/';
  return PROGRAMMATIC_PAGES.find((p) => (p.path.replace(/\/+$/, '') || '/') === clean);
}
