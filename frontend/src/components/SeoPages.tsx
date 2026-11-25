import { useEffect } from 'react';
import { ArrowLeft, ArrowRight, BookOpen, Clock, IndianRupee, MapPin, Navigation, Route as RouteIcon, ShieldCheck } from 'lucide-react';
import { SEO_POSTS, SEO_ROUTES, findPostBySlug, findRouteBySlug, type SeoPost, type SeoRoute } from '../data/seoData';

interface SeoNavigationProps {
  onNavigate: (path: string) => void;
}

function useDocumentMeta(title: string, description: string) {
  useEffect(() => {
    document.title = title;
    const meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.setAttribute('content', description);
    }
  }, [title, description]);
}

export function RoutesIndexPage({ onNavigate }: SeoNavigationProps) {
  useDocumentMeta(
    'Popular Taxi Fare Routes in India — RideCompare',
    'Browse typical taxi fare ranges, distances, and cheapest cab or auto services across popular airport and city routes in Kerala, Bangalore, Mumbai, Goa, and Kolkata.'
  );

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-color)] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            <RouteIcon size={12} /> Route Fare Guides
          </span>
          <h1 className="mt-3 text-3xl font-bold text-[var(--text-primary)]">Popular Taxi & Cab Routes</h1>
          <p className="mt-2 max-w-2xl text-sm text-[var(--text-secondary)]">
            Explore typical fare ranges, road distances, and which ride service is usually cheapest on high-demand airport and city corridors.
          </p>
        </div>
        <button
          onClick={() => onNavigate('/')}
          className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-color)] px-4 py-2.5 text-xs font-bold text-white hover:opacity-90 cursor-pointer"
        >
          Open Live Fare Calculator <ArrowRight size={14} />
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {SEO_ROUTES.map((route) => (
          <a
            key={route.slug}
            href={`/routes/${route.slug}`}
            onClick={(e) => {
              e.preventDefault();
              onNavigate(`/routes/${route.slug}`);
            }}
            className="group flex flex-col justify-between rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-5 transition-all hover:border-[var(--accent-color)]"
          >
            <div>
              <div className="flex items-center justify-between gap-2 text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                <span>{route.region}</span>
                <span>{route.distanceKm} km · {route.durationMins} min</span>
              </div>
              <h2 className="mt-2 text-base font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-color)]">
                {route.h1}
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-[var(--text-secondary)] line-clamp-2">
                {route.summary}
              </p>
            </div>
            <div className="mt-4 border-t border-[var(--border-color)] pt-3 flex items-center justify-between text-xs">
              <div>
                <span className="block text-[10px] uppercase text-[var(--text-secondary)]">Usually Cheapest</span>
                <span className="font-bold text-emerald-500">{route.cheapestService}</span>
              </div>
              <div className="text-right">
                <span className="block text-[10px] uppercase text-[var(--text-secondary)]">Est. Range</span>
                <span className="font-bold text-[var(--text-primary)]">{route.cheapestRange}</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export function RouteDetailPage({ slug, onNavigate }: SeoNavigationProps & { slug: string }) {
  const route: SeoRoute | undefined = findRouteBySlug(slug);

  useDocumentMeta(
    route ? route.title : 'Route Not Found — RideCompare',
    route ? route.metaDescription : 'Compare taxi fares across Uber, Ola, Rapido, and local services.'
  );

  if (!route) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-8 text-center">
        <h1 className="text-2xl font-bold">Route guide not found</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">Browse all available route fare guides or run a custom search.</p>
        <div className="mt-4 flex justify-center gap-3">
          <button onClick={() => onNavigate('/routes')} className="rounded-xl border border-[var(--border-color)] px-4 py-2 text-xs font-bold cursor-pointer">
            All Routes
          </button>
          <button onClick={() => onNavigate('/')} className="rounded-xl bg-[var(--accent-color)] px-4 py-2 text-xs font-bold text-white cursor-pointer">
            Compare Live Fares
          </button>
        </div>
      </div>
    );
  }

  const related = route.relatedRoutes
    .map((s) => findRouteBySlug(s))
    .filter((r): r is SeoRoute => Boolean(r));

  return (
    <article className="mx-auto w-full max-w-4xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-secondary)]">
        <button
          onClick={() => onNavigate('/routes')}
          className="inline-flex items-center gap-1.5 font-semibold hover:text-[var(--text-primary)] cursor-pointer"
        >
          <ArrowLeft size={14} /> All Route Guides
        </button>
        <span>{route.region} · Updated 2026</span>
      </div>

      <section className="glass-panel rounded-2xl p-6 md:p-8">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-color)] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
          <MapPin size={12} /> {route.origin} → {route.destination}
        </span>
        <h1 className="mt-3 text-3xl font-bold text-[var(--text-primary)]">{route.h1}</h1>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">{route.summary}</p>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
            <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase text-[var(--text-secondary)]">
              <Navigation size={13} /> Road Distance
            </span>
            <p className="mt-1 text-xl font-bold text-[var(--text-primary)]">{route.distanceKm} km</p>
            <p className="text-[11px] text-[var(--text-secondary)]">~{route.durationMins} mins typical drive</p>
          </div>
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
            <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase text-[var(--text-secondary)]">
              <IndianRupee size={13} /> Usually Cheapest
            </span>
            <p className="mt-1 text-lg font-bold text-emerald-500">{route.cheapestService}</p>
            <p className="text-[11px] text-[var(--text-secondary)]">Est. {route.cheapestRange}</p>
          </div>
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
            <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase text-[var(--text-secondary)]">
              <Clock size={13} /> Peak Surge Hours
            </span>
            <p className="mt-1 text-sm font-bold text-[var(--text-primary)]">{route.peakHours}</p>
            <p className="text-[11px] text-[var(--text-secondary)]">Expect 1.2x–1.6x dynamic pricing</p>
          </div>
        </div>

        <div className="mt-6">
          <button
            onClick={() => onNavigate('/')}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-color)] px-5 py-3 text-xs font-bold text-white hover:opacity-90 cursor-pointer"
          >
            Compare Live Estimate for This Route <ArrowRight size={14} />
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6">
        <h2 className="text-lg font-bold text-[var(--text-primary)]">Estimated Fare Ranges by Service</h2>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          All prices are estimates based on statutory rate cards and typical demand. Actual fare is shown in the provider app.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                <th className="py-2.5 pr-4 font-bold">Service</th>
                <th className="py-2.5 pr-4 font-bold">Category</th>
                <th className="py-2.5 pr-4 font-bold">Typical Range (Estimate)</th>
                <th className="py-2.5 font-bold">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {route.services.map((svc, idx) => (
                <tr key={`${svc.provider}-${idx}`}>
                  <td className="py-3 pr-4 font-bold text-[var(--text-primary)]">{svc.provider}</td>
                  <td className="py-3 pr-4 text-[var(--text-secondary)]">{svc.category}</td>
                  <td className="py-3 pr-4 font-bold text-[var(--accent-color)]">
                    ₹{svc.minFare.toLocaleString('en-IN')} – ₹{svc.maxFare.toLocaleString('en-IN')}
                  </td>
                  <td className="py-3 text-[var(--text-secondary)]">{svc.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6">
        <h2 className="flex items-center gap-2 text-base font-bold text-[var(--text-primary)]">
          <ShieldCheck size={18} className="text-emerald-500" /> Local Route & Toll Notes
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{route.routeNotes}</p>
      </section>

      {route.faqs.length > 0 && (
        <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 space-y-4">
          <h2 className="text-base font-bold text-[var(--text-primary)]">Frequently Asked Questions</h2>
          {route.faqs.map((faq, idx) => (
            <div key={idx} className="border-t border-[var(--border-color)] pt-3 first:border-t-0 first:pt-0">
              <h3 className="text-sm font-bold text-[var(--text-primary)]">{faq.question}</h3>
              <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">{faq.answer}</p>
            </div>
          ))}
        </section>
      )}

      {related.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-bold text-[var(--text-primary)]">Related Route Guides</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {related.map((r) => (
              <a
                key={r.slug}
                href={`/routes/${r.slug}`}
                onClick={(e) => {
                  e.preventDefault();
                  onNavigate(`/routes/${r.slug}`);
                }}
                className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 hover:border-[var(--accent-color)]"
              >
                <p className="text-xs font-bold text-[var(--text-primary)]">{r.h1}</p>
                <p className="mt-1 text-[11px] text-[var(--text-secondary)]">{r.distanceKm} km · {r.cheapestRange}</p>
              </a>
            ))}
          </div>
        </section>
      )}
    </article>
  );
}

export function BlogIndexPage({ onNavigate }: SeoNavigationProps) {
  useDocumentMeta(
    'RideCompare Guides & Blog — Cab Comparisons, Airport Tips & Surge Pricing',
    'Read practical guides on Uber vs Ola vs Rapido in Kerala, how surge pricing works, GoaMiles vs tourist taxis, and airport cab tips across India.'
  );

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-color)] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            <BookOpen size={12} /> RideCompare Guides
          </span>
          <h1 className="mt-3 text-3xl font-bold text-[var(--text-primary)]">Taxi Fare & Travel Guides</h1>
          <p className="mt-2 max-w-2xl text-sm text-[var(--text-secondary)]">
            Data-backed comparisons on Uber, Ola, Rapido, Namma Yatri, Kerala Savari, GoaMiles, and how to beat dynamic surge pricing.
          </p>
        </div>
        <button
          onClick={() => onNavigate('/routes')}
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-color)] px-4 py-2.5 text-xs font-bold text-[var(--text-primary)] hover:border-[var(--accent-color)] cursor-pointer"
        >
          Browse Route Fares <ArrowRight size={14} />
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {SEO_POSTS.map((post) => (
          <a
            key={post.slug}
            href={`/blog/${post.slug}`}
            onClick={(e) => {
              e.preventDefault();
              onNavigate(`/blog/${post.slug}`);
            }}
            className="group flex flex-col justify-between rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 transition-all hover:border-[var(--accent-color)]"
          >
            <div>
              <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                <span className="text-[var(--accent-color)]">{post.category}</span>
                <span>{post.readTimeMins} min read</span>
              </div>
              <h2 className="mt-2 text-lg font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-color)]">
                {post.title}
              </h2>
              <p className="mt-2 text-xs leading-relaxed text-[var(--text-secondary)]">{post.excerpt}</p>
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-[var(--border-color)] pt-3 text-xs font-semibold text-[var(--text-secondary)]">
              <span>Updated {post.updatedAt}</span>
              <span className="inline-flex items-center gap-1 text-[var(--accent-color)]">
                Read guide <ArrowRight size={13} />
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export function BlogPostPage({ slug, onNavigate }: SeoNavigationProps & { slug: string }) {
  const post: SeoPost | undefined = findPostBySlug(slug);

  useDocumentMeta(
    post ? `${post.title} — RideCompare` : 'Guide Not Found — RideCompare',
    post ? post.metaDescription : 'RideCompare guides on cab comparisons and surge pricing.'
  );

  if (!post) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-8 text-center">
        <h1 className="text-2xl font-bold">Guide not found</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">Explore all RideCompare articles or compare fares directly.</p>
        <div className="mt-4 flex justify-center gap-3">
          <button onClick={() => onNavigate('/blog')} className="rounded-xl border border-[var(--border-color)] px-4 py-2 text-xs font-bold cursor-pointer">
            All Guides
          </button>
          <button onClick={() => onNavigate('/')} className="rounded-xl bg-[var(--accent-color)] px-4 py-2 text-xs font-bold text-white cursor-pointer">
            Compare Live Fares
          </button>
        </div>
      </div>
    );
  }

  const related = post.relatedRoutes
    .map((s) => findRouteBySlug(s))
    .filter((r): r is SeoRoute => Boolean(r));

  return (
    <article className="mx-auto w-full max-w-3xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-secondary)]">
        <button
          onClick={() => onNavigate('/blog')}
          className="inline-flex items-center gap-1.5 font-semibold hover:text-[var(--text-primary)] cursor-pointer"
        >
          <ArrowLeft size={14} /> All Guides
        </button>
        <span>{post.category} · {post.readTimeMins} min read · Updated {post.updatedAt}</span>
      </div>

      <header className="glass-panel rounded-2xl p-6 md:p-8">
        <h1 className="text-2xl md:text-3xl font-bold text-[var(--text-primary)] leading-tight">{post.title}</h1>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">{post.excerpt}</p>
      </header>

      <div className="space-y-6 rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 md:p-8">
        {post.sections.map((sec, idx) => (
          <section key={idx} className="space-y-2.5">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">{sec.heading}</h2>
            {sec.paragraphs.map((p, pIdx) => (
              <p key={pIdx} className="text-sm leading-relaxed text-[var(--text-secondary)]">{p}</p>
            ))}
            {sec.bullets && sec.bullets.length > 0 && (
              <ul className="list-disc space-y-1.5 pl-5 text-sm text-[var(--text-secondary)]">
                {sec.bullets.map((b, bIdx) => (
                  <li key={bIdx}>{b}</li>
                ))}
              </ul>
            )}
          </section>
        ))}

        <div className="border-t border-[var(--border-color)] pt-5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-[var(--text-secondary)]">
            Want to check live estimates for your exact pickup and drop?
          </p>
          <button
            onClick={() => onNavigate('/')}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent-color)] px-4 py-2.5 text-xs font-bold text-white hover:opacity-90 cursor-pointer"
          >
            Compare Rides Now <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {related.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-bold text-[var(--text-primary)]">Related Route Fare Pages</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {related.map((r) => (
              <a
                key={r.slug}
                href={`/routes/${r.slug}`}
                onClick={(e) => {
                  e.preventDefault();
                  onNavigate(`/routes/${r.slug}`);
                }}
                className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 hover:border-[var(--accent-color)]"
              >
                <p className="text-xs font-bold text-[var(--text-primary)]">{r.h1}</p>
                <p className="mt-1 text-[11px] text-[var(--text-secondary)]">{r.distanceKm} km · {r.cheapestRange}</p>
              </a>
            ))}
          </div>
        </section>
      )}
    </article>
  );
}
