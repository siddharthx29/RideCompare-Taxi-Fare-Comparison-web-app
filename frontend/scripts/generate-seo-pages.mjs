import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');
const distDir = path.join(frontendDir, 'dist');
const publicDir = path.join(frontendDir, 'public');
const contentPath = path.join(frontendDir, 'src', 'data', 'seoContent.json');

const seoContent = JSON.parse(fs.readFileSync(contentPath, 'utf-8'));
const { siteUrl, siteName, routes, posts } = seoContent;

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderShell({ title, description, canonicalPath, jsonLd, bodyHtml }) {
  const canonicalUrl = `${siteUrl}${canonicalPath}`;
  const schemas = Array.isArray(jsonLd) ? jsonLd : [jsonLd];
  const schemaTags = schemas
    .filter(Boolean)
    .map((s) => `<script type="application/ld+json">${JSON.stringify(s)}</script>`)
    .join('\n    ');

  return `<!doctype html>
<html lang="en" class="dark">
  <head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-8ELP550YGK"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-8ELP550YGK');
    </script>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/png" href="/logo.png" />
    <title>${escapeHtml(title)}</title>
    <meta name="description" content="${escapeHtml(description)}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="${escapeHtml(canonicalUrl)}" />
    <meta property="og:type" content="article" />
    <meta property="og:url" content="${escapeHtml(canonicalUrl)}" />
    <meta property="og:title" content="${escapeHtml(title)}" />
    <meta property="og:description" content="${escapeHtml(description)}" />
    <meta property="og:image" content="${siteUrl}/logo.png" />
    <meta property="og:site_name" content="${escapeHtml(siteName)}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${escapeHtml(title)}" />
    <meta name="twitter:description" content="${escapeHtml(description)}" />
    <meta name="twitter:image" content="${siteUrl}/logo.png" />
    ${schemaTags}
    <style>
      :root { color-scheme: dark; }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #0c0d0f; color: #f4f5f6; line-height: 1.6; }
      a { color: #ff8055; text-decoration: none; }
      a:hover { text-decoration: underline; }
      header { background: #111414; border-bottom: 1px solid #292b30; padding: 14px 20px; }
      .nav-wrap { max-width: 980px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
      .brand { font-weight: 800; color: #e1e3e2; font-size: 1.05rem; }
      nav { display: flex; gap: 16px; font-size: 0.875rem; font-weight: 600; }
      nav a { color: #dfc0b1; }
      main { max-width: 980px; margin: 0 auto; padding: 28px 20px 48px; }
      .card { background: #141619; border: 1px solid #292b30; border-radius: 14px; padding: 22px; margin-bottom: 18px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
      .badge { display: inline-block; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; padding: 4px 10px; border-radius: 999px; border: 1px solid #292b30; color: #9a9fa7; }
      h1 { font-size: 1.9rem; line-height: 1.2; margin: 12px 0; }
      h2 { font-size: 1.2rem; margin: 0 0 10px; }
      h3 { font-size: 1rem; margin: 0 0 6px; }
      p, li { color: #c4c8cf; font-size: 0.95rem; }
      table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.88rem; }
      th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #292b30; }
      th { color: #9a9fa7; font-size: 0.78rem; text-transform: uppercase; }
      .price { color: #ff8055; font-weight: 700; white-space: nowrap; }
      .green { color: #5adda4; font-weight: 700; }
      .cta { display: inline-block; background: #e86d10; color: #fff; font-weight: 700; font-size: 0.88rem; padding: 11px 18px; border-radius: 10px; margin-top: 10px; }
      .cta:hover { text-decoration: none; opacity: 0.92; }
      footer { border-top: 1px solid #292b30; padding: 22px 20px; text-align: center; font-size: 0.78rem; color: #9a9fa7; }
    </style>
  </head>
  <body>
    <header>
      <div class="nav-wrap">
        <a href="/" class="brand">RideCompare</a>
        <nav>
          <a href="/">Compare Rides</a>
          <a href="/routes">Route Fares</a>
          <a href="/blog">Guides &amp; Blog</a>
        </nav>
      </div>
    </header>
    <main>
      ${bodyHtml}
    </main>
    <footer>
      <p>RideCompare — Prices shown are estimates based on statutory rate cards and historical demand. Actual fare is shown in the provider app.</p>
    </footer>
  </body>
</html>`;
}

function writePage(relPath, html) {
  const fullPath = path.join(distDir, relPath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(fullPath, html, 'utf-8');
}

// 1. Generate /routes/index.html
const routesIndexHtml = renderShell({
  title: 'Popular Taxi Fare Routes in India — RideCompare',
  description: 'Browse typical taxi fare ranges, distances, and cheapest cab or auto services across popular airport and city routes in Kerala, Bangalore, Mumbai, Goa, and Kolkata.',
  canonicalPath: '/routes',
  jsonLd: [
    {
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Popular Taxi & Cab Routes',
      url: `${siteUrl}/routes`,
      description: 'Compare typical taxi fare ranges, distances, and cheapest services across Indian airport and city routes.'
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: `${siteUrl}/` },
        { '@type': 'ListItem', position: 2, name: 'Route Fares', item: `${siteUrl}/routes` }
      ]
    }
  ],
  bodyHtml: `
    <span class="badge">Route Fare Guides</span>
    <h1>Popular Taxi &amp; Cab Routes</h1>
    <p>Compare typical fare ranges, road distances, and which ride service is usually cheapest across high-demand airport and city corridors.</p>
    <a href="/" class="cta">Open Live Fare Calculator &rarr;</a>
    <div class="grid" style="margin-top:22px;">
      ${routes.map((r) => `
        <div class="card" style="margin-bottom:0;">
          <span class="badge">${escapeHtml(r.region)} · ${r.distanceKm} km</span>
          <h2 style="margin-top:10px;"><a href="/routes/${escapeHtml(r.slug)}">${escapeHtml(r.h1)}</a></h2>
          <p>${escapeHtml(r.summary)}</p>
          <p><strong>Usually Cheapest:</strong> <span class="green">${escapeHtml(r.cheapestService)}</span> (${escapeHtml(r.cheapestRange)})</p>
        </div>
      `).join('')}
    </div>
  `
});
writePage(path.join('routes', 'index.html'), routesIndexHtml);

// 2. Generate /routes/<slug>/index.html
for (const route of routes) {
  const minPrice = Math.min(...route.services.map((s) => s.minFare));
  const maxPrice = Math.max(...route.services.map((s) => s.maxFare));
  const related = route.relatedRoutes
    .map((slug) => routes.find((r) => r.slug === slug))
    .filter(Boolean);

  const jsonLd = [
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: `${siteUrl}/` },
        { '@type': 'ListItem', position: 2, name: 'Route Fares', item: `${siteUrl}/routes` },
        { '@type': 'ListItem', position: 3, name: route.h1, item: `${siteUrl}/routes/${route.slug}` }
      ]
    },
    {
      '@context': 'https://schema.org',
      '@type': 'Service',
      name: route.h1,
      description: route.metaDescription,
      areaServed: { '@type': 'AdministrativeArea', name: route.region },
      provider: { '@type': 'Organization', name: siteName, url: siteUrl },
      offers: {
        '@type': 'AggregateOffer',
        priceCurrency: 'INR',
        lowPrice: minPrice,
        highPrice: maxPrice,
        offerCount: route.services.length
      }
    },
    ...(route.faqs?.length
      ? [{
          '@context': 'https://schema.org',
          '@type': 'FAQPage',
          mainEntity: route.faqs.map((f) => ({
            '@type': 'Question',
            name: f.question,
            acceptedAnswer: { '@type': 'Answer', text: f.answer }
          }))
        }]
      : [])
  ];

  const html = renderShell({
    title: route.title,
    description: route.metaDescription,
    canonicalPath: `/routes/${route.slug}`,
    jsonLd,
    bodyHtml: `
      <span class="badge">${escapeHtml(route.origin)} &rarr; ${escapeHtml(route.destination)}</span>
      <h1>${escapeHtml(route.h1)}</h1>
      <p>${escapeHtml(route.summary)}</p>
      <div class="grid" style="margin:18px 0;">
        <div class="card" style="margin-bottom:0;">
          <span class="badge">Distance &amp; Time</span>
          <p style="font-size:1.25rem;font-weight:800;color:#fff;margin:8px 0 2px;">${route.distanceKm} km</p>
          <p style="margin:0;">~${route.durationMins} mins typical drive</p>
        </div>
        <div class="card" style="margin-bottom:0;">
          <span class="badge">Usually Cheapest</span>
          <p class="green" style="font-size:1.15rem;margin:8px 0 2px;">${escapeHtml(route.cheapestService)}</p>
          <p style="margin:0;">Est. ${escapeHtml(route.cheapestRange)}</p>
        </div>
        <div class="card" style="margin-bottom:0;">
          <span class="badge">Peak Surge Hours</span>
          <p style="font-size:1rem;font-weight:700;color:#fff;margin:8px 0 2px;">${escapeHtml(route.peakHours)}</p>
          <p style="margin:0;">Expect dynamic multipliers</p>
        </div>
      </div>

      <div class="card">
        <h2>Estimated Fare Ranges by Service</h2>
        <table>
          <thead>
            <tr><th>Service</th><th>Category</th><th>Typical Range (Estimate)</th><th>Notes</th></tr>
          </thead>
          <tbody>
            ${route.services.map((s) => `
              <tr>
                <td><strong>${escapeHtml(s.provider)}</strong></td>
                <td>${escapeHtml(s.category)}</td>
                <td class="price">&#8377;${s.minFare.toLocaleString('en-IN')} &ndash; &#8377;${s.maxFare.toLocaleString('en-IN')}</td>
                <td>${escapeHtml(s.notes)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <a href="/" class="cta">Compare Live Estimates on RideCompare &rarr;</a>
      </div>

      <div class="card">
        <h2>Local Route &amp; Toll Notes</h2>
        <p>${escapeHtml(route.routeNotes)}</p>
      </div>

      ${route.faqs?.length ? `
        <div class="card">
          <h2>Frequently Asked Questions</h2>
          ${route.faqs.map((f) => `
            <div style="margin-top:12px;">
              <h3>${escapeHtml(f.question)}</h3>
              <p style="margin:4px 0 0;">${escapeHtml(f.answer)}</p>
            </div>
          `).join('')}
        </div>
      ` : ''}

      ${related.length ? `
        <div class="card">
          <h2>Related Route Guides</h2>
          <ul>
            ${related.map((r) => `<li><a href="/routes/${escapeHtml(r.slug)}">${escapeHtml(r.h1)}</a> (${r.distanceKm} km · ${escapeHtml(r.cheapestRange)})</li>`).join('')}
          </ul>
        </div>
      ` : ''}
    `
  });

  writePage(path.join('routes', route.slug, 'index.html'), html);
}

// 3. Generate /blog/index.html
const blogIndexHtml = renderShell({
  title: 'RideCompare Guides & Blog — Cab Comparisons, Airport Tips & Surge Pricing',
  description: 'Read practical guides on Uber vs Ola vs Rapido in Kerala, how surge pricing works, GoaMiles vs tourist taxis, and airport cab tips across India.',
  canonicalPath: '/blog',
  jsonLd: [
    {
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'RideCompare Guides & Blog',
      url: `${siteUrl}/blog`,
      description: 'Practical guides on ride-hailing comparisons, airport transfers, and surge pricing.'
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: `${siteUrl}/` },
        { '@type': 'ListItem', position: 2, name: 'Guides & Blog', item: `${siteUrl}/blog` }
      ]
    }
  ],
  bodyHtml: `
    <span class="badge">RideCompare Guides</span>
    <h1>Taxi Fare &amp; Travel Guides</h1>
    <p>Data-backed comparisons on Uber, Ola, Rapido, Namma Yatri, Kerala Savari, GoaMiles, and how to beat dynamic surge pricing.</p>
    <div class="grid" style="margin-top:22px;">
      ${posts.map((p) => `
        <div class="card" style="margin-bottom:0;">
          <span class="badge">${escapeHtml(p.category)} · ${p.readTimeMins} min read</span>
          <h2 style="margin-top:10px;"><a href="/blog/${escapeHtml(p.slug)}">${escapeHtml(p.title)}</a></h2>
          <p>${escapeHtml(p.excerpt)}</p>
        </div>
      `).join('')}
    </div>
  `
});
writePage(path.join('blog', 'index.html'), blogIndexHtml);

// 4. Generate /blog/<slug>/index.html
for (const post of posts) {
  const related = (post.relatedRoutes || [])
    .map((slug) => routes.find((r) => r.slug === slug))
    .filter(Boolean);

  const html = renderShell({
    title: `${post.title} — RideCompare`,
    description: post.metaDescription,
    canonicalPath: `/blog/${post.slug}`,
    jsonLd: [
      {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        headline: post.title,
        description: post.metaDescription,
        datePublished: post.publishedAt,
        dateModified: post.updatedAt,
        author: { '@type': 'Organization', name: siteName },
        publisher: { '@type': 'Organization', name: siteName, url: siteUrl },
        mainEntityOfPage: { '@type': 'WebPage', '@id': `${siteUrl}/blog/${post.slug}` }
      },
      {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: `${siteUrl}/` },
          { '@type': 'ListItem', position: 2, name: 'Guides & Blog', item: `${siteUrl}/blog` },
          { '@type': 'ListItem', position: 3, name: post.title, item: `${siteUrl}/blog/${post.slug}` }
        ]
      }
    ],
    bodyHtml: `
      <span class="badge">${escapeHtml(post.category)} · ${post.readTimeMins} min read · Updated ${escapeHtml(post.updatedAt)}</span>
      <h1>${escapeHtml(post.title)}</h1>
      <p>${escapeHtml(post.excerpt)}</p>
      <div class="card">
        ${post.sections.map((s) => `
          <section style="margin-bottom:20px;">
            <h2>${escapeHtml(s.heading)}</h2>
            ${s.paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join('')}
            ${s.bullets?.length ? `<ul>${s.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join('')}</ul>` : ''}
          </section>
        `).join('')}
        <a href="/" class="cta">Compare Rides Now &rarr;</a>
      </div>
      ${related.length ? `
        <div class="card">
          <h2>Related Route Fare Pages</h2>
          <ul>
            ${related.map((r) => `<li><a href="/routes/${escapeHtml(r.slug)}">${escapeHtml(r.h1)}</a> (${r.distanceKm} km · ${escapeHtml(r.cheapestRange)})</li>`).join('')}
          </ul>
        </div>
      ` : ''}
    `
  });

  writePage(path.join('blog', post.slug, 'index.html'), html);
}

// 5. Generate sitemap.xml in both dist/ and public/
const today = new Date().toISOString().slice(0, 10);
const urls = [
  { loc: `${siteUrl}/`, lastmod: today, changefreq: 'daily', priority: '1.0' },
  { loc: `${siteUrl}/routes`, lastmod: today, changefreq: 'weekly', priority: '0.9' },
  { loc: `${siteUrl}/blog`, lastmod: today, changefreq: 'weekly', priority: '0.9' },
  ...routes.map((r) => ({ loc: `${siteUrl}/routes/${r.slug}`, lastmod: today, changefreq: 'weekly', priority: '0.8' })),
  ...posts.map((p) => ({ loc: `${siteUrl}/blog/${p.slug}`, lastmod: p.updatedAt || today, changefreq: 'monthly', priority: '0.8' }))
];

const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url>
    <loc>${escapeHtml(u.loc)}</loc>
    <lastmod>${u.lastmod}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`).join('\n')}
</urlset>
`;

writePage('sitemap.xml', sitemapXml);
fs.writeFileSync(path.join(publicDir, 'sitemap.xml'), sitemapXml, 'utf-8');

console.log(`Generated ${routes.length} route pages, ${posts.length} blog posts, and sitemap.xml (${urls.length} URLs).`);
