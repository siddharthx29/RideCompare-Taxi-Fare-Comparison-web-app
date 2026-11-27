import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');
const rootDir = path.resolve(frontendDir, '..');
const distDir = path.join(frontendDir, 'dist');
const publicDir = path.join(frontendDir, 'public');
const contentPath = path.join(frontendDir, 'src', 'data', 'seoContent.json');
const coveragePath = path.join(rootDir, 'backend', 'app', 'config', 'service_coverage.json');
const faresPath = path.join(rootDir, 'backend', 'app', 'config', 'fares.json');
const generatedJsonPath = path.join(frontendDir, 'src', 'data', 'generatedProgrammaticPages.json');

const seoContent = JSON.parse(fs.readFileSync(contentPath, 'utf-8'));
const coverage = fs.existsSync(coveragePath) ? JSON.parse(fs.readFileSync(coveragePath, 'utf-8')) : { regions: {} };
const fares = fs.existsSync(faresPath) ? JSON.parse(fs.readFileSync(faresPath, 'utf-8')) : { cities: {} };
const { siteUrl, siteName, routes, posts } = seoContent;

function slugify(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildProgrammaticPages() {
  const regions = coverage.regions || {};
  const fareCities = fares.cities || {};
  const supportedCities = [];

  for (const [cityName, reg] of Object.entries(regions)) {
    const providers = reg.providers || [];
    if (!providers.length) continue;
    const cityFares = fareCities[cityName] || {};
    supportedCities.push({
      cityName,
      slug: slugify(cityName),
      providers,
      quoteNames: reg.quote_names || Object.keys(cityFares.providers || {}),
      state: cityFares.state || '',
      country: cityFares.country || reg.country_code || '',
      currencySymbol: cityFares.currencySymbol || '₹',
      regionalNotice: cityFares.regionalNotice || '',
      airportKeywords: (cityFares.toll && cityFares.toll.airportKeywords) || [],
      airportToll: (cityFares.toll && cityFares.toll.charge) || null,
      fareProviders: cityFares.providers || {},
      intercity: Boolean(reg.intercity),
      outstationDestinations: reg.outstation_destinations || []
    });
  }

  const pages = [
    {
      pageId: 'pillar-compare-cab-fares',
      path: '/compare-cab-fares/',
      pageType: 'pillar',
      location: null,
      title: 'Compare Cab Fares Online Across Uber, Ola, Rapido & Local Taxis — RideCompare',
      description: 'Compare estimated cab, auto, and bike-taxi fares across Uber, Ola, Rapido, Namma Yatri, Kerala Savari, and GoaMiles in one place.',
      h1: 'Compare Cab & Taxi Fares Online',
      intro: 'RideCompare calculates route-aware fare estimates using verified statutory rate cards and regional geofencing so you can compare available ride services side by side before booking.',
      supportedServices: ['Uber', 'Ola', 'Rapido', 'Namma Yatri', 'Kerala Savari', 'GoaMiles', 'Yatri Sathi'],
      sections: [
        { heading: 'How RideCompare Estimates Ride Fares', body: 'Enter your pickup and drop-off points to measure road distance and estimated travel time, then inspect base fares, per-km rates, and regulated surge caps across every active provider in your city.' },
        { heading: 'Zero Scraping & Transparent Estimates', body: 'All prices are presented as estimate ranges derived from statutory rate cards and demand models, with direct deep links to open the official provider app.' }
      ],
      faqs: [
        { question: 'Which cab service is cheapest in India?', answer: 'For solo commutes, bike taxis like Rapido Bike or Uber Moto are usually cheapest. For autos and cabs, zero-commission apps like Namma Yatri, Kerala Savari, and Yatri Sathi often undercut private aggregators during surge hours.' }
      ],
      breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Compare Cab Fares', path: '/compare-cab-fares/' }],
      relatedLinks: supportedCities.slice(0, 6).map((c) => ({ label: `Taxi Fare in ${c.cityName}`, path: `/cab-fare/${c.slug}/` }))
    },
    {
      pageId: 'pillar-taxi-fare-calculator',
      path: '/taxi-fare-calculator/',
      pageType: 'pillar',
      location: null,
      title: 'Taxi Fare Calculator — Estimate Cab, Auto & Bike Ride Costs | RideCompare',
      description: 'Use RideCompare’s route-aware taxi fare calculator to estimate cab, auto-rickshaw, and bike-taxi costs using statutory per-km rate cards.',
      h1: 'Online Taxi Fare Calculator',
      intro: 'Calculate estimated taxi, auto-rickshaw, and bike-taxi fares for any supported city route using road routing and regional transport tariffs.',
      supportedServices: ['Uber', 'Ola', 'Rapido', 'Namma Yatri', 'Kerala Savari', 'GoaMiles'],
      sections: [
        { heading: 'What Goes Into a Fare Estimate', body: 'Each calculation accounts for base fare, per-kilometre rate, ride duration, airport toll rules, and time-of-day peak multipliers capped by local transport rules.' },
        { heading: 'Supported Regions & Metered Fallbacks', body: 'Where app aggregators do not operate, RideCompare checks whether government metered autos or local taxis serve the area and displays regulated minimum meter estimates.' }
      ],
      faqs: [
        { question: 'How accurate is the taxi fare calculator?', answer: 'Estimates are grounded in published city rate cards and road distance via OSRM routing. Final fares in provider apps can differ due to live driver availability, traffic detours, and tolls.' }
      ],
      breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Taxi Fare Calculator', path: '/taxi-fare-calculator/' }],
      relatedLinks: [
        { label: 'Compare Cab Fares', path: '/compare-cab-fares/' },
        { label: 'Uber vs Ola', path: '/uber-vs-ola/' },
        { label: 'Uber vs Rapido', path: '/uber-vs-rapido/' }
      ]
    },
    {
      pageId: 'comparison-uber-vs-ola',
      path: '/uber-vs-ola/',
      pageType: 'comparison',
      location: null,
      title: 'Uber vs Ola Fare Comparison — Which Cab App Is Cheaper? | RideCompare',
      description: 'Compare Uber Go vs Ola Mini base fares, per-km rates, airport fees, and surge pricing across Indian cities before you book.',
      h1: 'Uber vs Ola: Price & Rate Card Comparison',
      intro: 'Both Uber and Ola use dynamic pricing, so neither app is cheapest on every trip. Comparing base tariffs, per-km rates, and peak multipliers helps you avoid overpaying.',
      supportedServices: ['Uber Go', 'Uber Premier', 'Ola Mini', 'Ola Prime'],
      sections: [
        { heading: 'Base Fare & Per-Kilometre Differences', body: 'In major Indian cities like Bangalore, Kochi, and Mumbai, Uber Go and Ola Mini base fares sit within a few rupees of each other, making surge multipliers and airport pickup fees the deciding factor.' },
        { heading: 'When to Check Alternatives', body: 'During heavy rain or 6 PM office rush, checking Namma Yatri, Kerala Savari, or Yatri Sathi alongside Uber and Ola frequently reveals lower zero-surge fares.' }
      ],
      faqs: [
        { question: 'Is Uber cheaper than Ola for airport rides?', answer: 'During off-peak hours they are usually close in price, though whichever app has fewer waiting drivers at the airport bay will apply higher surge.' }
      ],
      breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Uber vs Ola', path: '/uber-vs-ola/' }],
      relatedLinks: [
        { label: 'Uber vs Rapido', path: '/uber-vs-rapido/' },
        { label: 'Uber vs Ola vs Rapido in Kerala', path: '/blog/uber-vs-ola-vs-rapido-in-kerala' }
      ]
    },
    {
      pageId: 'comparison-uber-vs-rapido',
      path: '/uber-vs-rapido/',
      pageType: 'comparison',
      location: null,
      title: 'Uber vs Rapido (and Ola) — Bike, Auto & Cab Fare Comparison | RideCompare',
      description: 'Compare Uber Moto, Uber Auto, and Uber Go against Rapido Bike, Rapido Auto, and Ola across supported Indian cities.',
      h1: 'Uber vs Rapido: Bike, Auto & Cab Comparison',
      intro: 'Rapido specializes in fast, low-cost bike taxis and autos, while Uber covers bikes, autos, and AC cabs. Compare both before choosing your commute mode.',
      supportedServices: ['Rapido Bike', 'Rapido Auto', 'Uber Moto', 'Uber Auto', 'Uber Go'],
      sections: [
        { heading: 'Solo Commutes: Bike Taxis', body: 'For short 3–12 km city rides without luggage, Rapido Bike and Uber Moto typically cost less than half of an AC hatchback cab and cut through peak congestion.' },
        { heading: 'Autos & Cabs for Longer Trips', body: 'When travelling with luggage, in rain, or to airports, compare Uber Go, Ola Mini, and state-backed options like Kerala Savari or Namma Yatri.' }
      ],
      faqs: [
        { question: 'Is Rapido cheaper than Uber?', answer: 'For solo riders on bike taxis or short auto trips, Rapido is often the lowest-cost option, though Uber Moto frequently matches its per-km tariff.' }
      ],
      breadcrumbs: [{ name: 'Home', path: '/' }, { name: 'Uber vs Rapido', path: '/uber-vs-rapido/' }],
      relatedLinks: [
        { label: 'Uber vs Ola', path: '/uber-vs-ola/' },
        { label: 'How Surge Pricing Works', path: '/blog/how-surge-pricing-works' }
      ]
    }
  ];

  for (const city of supportedCities) {
    const rateHighlights = city.quoteNames.slice(0, 6).map((qn) => {
      const cfg = city.fareProviders[qn];
      if (!cfg) return null;
      return {
        service: qn,
        vehicleType: cfg.vehicleType || 'Cab',
        baseFare: `${city.currencySymbol}${cfg.baseFare}`,
        perKmRate: `${city.currencySymbol}${cfg.perKmRate}/km`
      };
    }).filter(Boolean);

    pages.push({
      pageId: `city-${city.slug}`,
      path: `/cab-fare/${city.slug}/`,
      pageType: 'city',
      location: city.cityName,
      title: `Taxi & Cab Fare in ${city.cityName} — Compare ${city.providers.slice(0, 3).join(', ')} | RideCompare`,
      description: `Compare estimated taxi, auto, and cab fares in ${city.cityName} across ${city.providers.join(', ')}. Check statutory rate cards and route estimates.`,
      h1: `Taxi & Cab Fare Comparison in ${city.cityName}`,
      intro: `RideCompare supports ${city.cityName} (${city.state || city.country}) with verified regional geofencing and rate cards for ${city.providers.join(', ')}.`,
      supportedServices: city.quoteNames,
      rateHighlights,
      sections: [
        {
          heading: `Active Ride Services in ${city.cityName}`,
          body: `Available ride options in ${city.cityName} include ${city.quoteNames.join(', ')}. ${city.regionalNotice || 'Enter your pickup and destination in RideCompare to compare estimated ranges sorted cheapest first.'}`
        },
        {
          heading: `Local Pricing & Intercity Rules in ${city.cityName}`,
          body: `Intra-city estimates use ${city.cityName}'s statutory base and per-km rate cards. ${city.intercity && city.outstationDestinations.length ? `Outstation coverage also supports popular destinations such as ${city.outstationDestinations.slice(0, 5).join(', ')}.` : 'Standard city-ride tariffs apply within the supported local geofence.'}`
        }
      ],
      faqs: [
        {
          question: `Which taxi apps operate in ${city.cityName}?`,
          answer: `RideCompare currently tracks ${city.providers.join(', ')} in ${city.cityName}, covering ${city.quoteNames.slice(0, 5).join(', ')}.`
        },
        {
          question: `How can I estimate a cab fare in ${city.cityName}?`,
          answer: `Use the RideCompare fare calculator to select your ${city.cityName} pickup and drop locations and compare estimated ranges sorted cheapest first.`
        }
      ],
      breadcrumbs: [
        { name: 'Home', path: '/' },
        { name: 'Cab Fares', path: '/compare-cab-fares/' },
        { name: city.cityName, path: `/cab-fare/${city.slug}/` }
      ],
      relatedLinks: [
        ...(city.airportKeywords.length ? [{ label: `${city.cityName} Airport Taxi Fare`, path: `/airport-taxi-fare/${city.slug}/` }] : []),
        { label: 'Taxi Fare Calculator', path: '/taxi-fare-calculator/' },
        { label: 'All Route Guides', path: '/routes' }
      ]
    });

    if (city.airportKeywords.length) {
      const tollNote = city.airportToll
        ? `Configured airport access/toll surcharge in rate cards: ${city.currencySymbol}${city.airportToll}.`
        : 'Check provider app details for any applicable airport entry or parking fees.';
      pages.push({
        pageId: `airport-${city.slug}`,
        path: `/airport-taxi-fare/${city.slug}/`,
        pageType: 'airport',
        location: city.cityName,
        title: `${city.cityName} Airport Taxi Fare — Compare ${city.providers.slice(0, 3).join(', ')} | RideCompare`,
        description: `Estimate ${city.cityName} airport to city taxi and cab fares across ${city.providers.join(', ')}. Includes airport toll rules and rate-card comparisons.`,
        h1: `${city.cityName} Airport Taxi & Cab Fare Guide`,
        intro: `Compare airport transfer estimates to and from ${city.cityName} airports (${city.airportKeywords.slice(0, 4).join(', ')}) across ${city.providers.join(', ')}.`,
        supportedServices: city.quoteNames,
        rateHighlights,
        sections: [
          {
            heading: `Airport Pickup Options in ${city.cityName}`,
            body: `Travellers arriving in ${city.cityName} can compare ${city.quoteNames.slice(0, 5).join(', ')} in RideCompare. ${tollNote}`
          },
          {
            heading: 'Tips to Avoid Airport Surge',
            body: 'Flight bank arrivals often trigger temporary demand spikes on private aggregator apps. Compare government-backed or zero-surge services where available before confirming.'
          }
        ],
        faqs: [
          {
            question: `How much is a taxi from ${city.cityName} Airport?`,
            answer: `Fares depend on drop-off distance and vehicle class. Enter your exact destination in RideCompare to see estimated ranges across ${city.providers.join(', ')}.`
          }
        ],
        breadcrumbs: [
          { name: 'Home', path: '/' },
          { name: 'Airport Taxi Fares', path: '/taxi-fare-calculator/' },
          { name: `${city.cityName} Airport`, path: `/airport-taxi-fare/${city.slug}/` }
        ],
        relatedLinks: [
          { label: `Taxi Fare in ${city.cityName}`, path: `/cab-fare/${city.slug}/` },
          { label: 'Compare Cab Fares', path: '/compare-cab-fares/' }
        ]
      });
    }
  }

  return pages;
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
    <meta property="og:type" content="website" />
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
      nav { display: flex; gap: 16px; font-size: 0.875rem; font-weight: 600; flex-wrap: wrap; }
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
          <a href="/compare-cab-fares/">Cab Fares</a>
          <a href="/taxi-fare-calculator/">Calculator</a>
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

// 0. Build and persist programmatic pages from service_coverage.json + fares.json
const programmaticPages = buildProgrammaticPages();
fs.writeFileSync(generatedJsonPath, JSON.stringify({ generatedAt: new Date().toISOString(), pages: programmaticPages }, null, 2), 'utf-8');

for (const page of programmaticPages) {
  const relDir = page.path.replace(/^\/|\/$/g, '');
  const jsonLd = [
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: page.breadcrumbs.map((b, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: b.name,
        item: `${siteUrl}${b.path}`
      }))
    },
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: page.title,
      description: page.description,
      url: `${siteUrl}${page.path}`,
      isPartOf: { '@type': 'WebSite', name: siteName, url: `${siteUrl}/` }
    },
    ...(page.pageType === 'pillar' || page.pageType === 'city' || page.pageType === 'airport'
      ? [{
          '@context': 'https://schema.org',
          '@type': 'SoftwareApplication',
          name: 'RideCompare Fare Calculator',
          applicationCategory: 'TravelApplication',
          operatingSystem: 'Web',
          url: `${siteUrl}${page.path}`,
          areaServed: page.location || 'Supported RideCompare Cities'
        }]
      : [])
  ];

  const rateTableHtml = page.rateHighlights?.length
    ? `<div class="card">
        <h2>Configured Statutory Rate Cards</h2>
        <table>
          <thead><tr><th>Service</th><th>Type</th><th>Base Fare</th><th>Per Km</th></tr></thead>
          <tbody>
            ${page.rateHighlights.map((r) => `<tr><td><strong>${escapeHtml(r.service)}</strong></td><td>${escapeHtml(r.vehicleType)}</td><td class="price">${escapeHtml(r.baseFare)}</td><td>${escapeHtml(r.perKmRate)}</td></tr>`).join('')}
          </tbody>
        </table>
      </div>`
    : '';

  const html = renderShell({
    title: page.title,
    description: page.description,
    canonicalPath: page.path,
    jsonLd,
    bodyHtml: `
      <span class="badge">${escapeHtml(page.location || page.pageType)}</span>
      <h1>${escapeHtml(page.h1)}</h1>
      <p>${escapeHtml(page.intro)}</p>
      <a href="/" class="cta">Open Live Fare Calculator &rarr;</a>
      ${rateTableHtml}
      <div class="card" style="margin-top:18px;">
        ${page.sections.map((s) => `<section style="margin-bottom:16px;"><h2>${escapeHtml(s.heading)}</h2><p>${escapeHtml(s.body)}</p></section>`).join('')}
      </div>
      ${page.faqs?.length ? `
        <div class="card">
          <h2>Frequently Asked Questions</h2>
          ${page.faqs.map((f) => `<div style="margin-top:10px;"><h3>${escapeHtml(f.question)}</h3><p>${escapeHtml(f.answer)}</p></div>`).join('')}
        </div>` : ''}
      ${page.relatedLinks?.length ? `
        <div class="card">
          <h2>Related Pages</h2>
          <ul>${page.relatedLinks.map((l) => `<li><a href="${escapeHtml(l.path)}">${escapeHtml(l.label)}</a></li>`).join('')}</ul>
        </div>` : ''}
    `
  });

  writePage(path.join(relDir, 'index.html'), html);
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
      '@type': 'WebPage',
      name: route.title,
      description: route.metaDescription,
      url: `${siteUrl}/routes/${route.slug}`
    }
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
        '@type': 'Article',
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
  ...programmaticPages.map((p) => ({
    loc: `${siteUrl}${p.path}`,
    lastmod: today,
    changefreq: 'weekly',
    priority: p.pageType === 'pillar' ? '0.9' : '0.85'
  })),
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

console.log(`Generated ${programmaticPages.length} programmatic SEO pages, ${routes.length} route pages, ${posts.length} blog posts, and sitemap.xml (${urls.length} URLs).`);
