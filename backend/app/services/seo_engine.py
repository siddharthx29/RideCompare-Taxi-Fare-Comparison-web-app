import csv
import io
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.config import APP_DIR, ROOT_DIR, settings
from backend.app.models.db_models import SeoAuditLog, SeoKeyword, SeoPage

COVERAGE_PATH = APP_DIR / "config" / "service_coverage.json"
FARES_PATH = APP_DIR / "config" / "fares.json"
SEO_CONTENT_PATH = ROOT_DIR / "frontend" / "src" / "data" / "seoContent.json"

SEED_KEYWORDS: List[Dict[str, str]] = [
    # A. General keywords
    {"keyword": "Cab fare comparison", "category": "general", "intent": "commercial"},
    {"keyword": "Compare taxi prices", "category": "general", "intent": "commercial"},
    {"keyword": "Taxi fare calculator", "category": "general", "intent": "transactional"},
    {"keyword": "Compare cab prices online", "category": "general", "intent": "commercial"},
    {"keyword": "Cheapest cab service", "category": "general", "intent": "commercial"},
    {"keyword": "Online taxi fare estimate", "category": "general", "intent": "transactional"},
    # B. Competitor comparison
    {"keyword": "Uber vs Ola", "category": "competitor", "intent": "commercial"},
    {"keyword": "Uber vs Rapido", "category": "competitor", "intent": "commercial"},
    {"keyword": "Ola vs Rapido", "category": "competitor", "intent": "commercial"},
    {"keyword": "Uber fare comparison", "category": "competitor", "intent": "commercial"},
    {"keyword": "Compare Uber Ola Rapido prices", "category": "competitor", "intent": "commercial"},
    # C. Local keywords
    {"keyword": "Taxi fare in Goa", "category": "local", "intent": "commercial", "location": "Goa"},
    {"keyword": "Cab booking in Goa", "category": "local", "intent": "transactional", "location": "Goa"},
    {"keyword": "Taxi fare in Kochi", "category": "local", "intent": "commercial", "location": "Kochi"},
    {"keyword": "Cab fare in Bangalore", "category": "local", "intent": "commercial", "location": "Bangalore"},
    {"keyword": "Taxi fare in Mumbai", "category": "local", "intent": "commercial", "location": "Mumbai"},
    {"keyword": "Cab price comparison in Delhi", "category": "local", "intent": "commercial", "location": "Delhi"},
    # D. Route-based keywords
    {"keyword": "Airport taxi fare", "category": "route", "intent": "commercial"},
    {"keyword": "Airport to city cab fare", "category": "route", "intent": "commercial"},
    {"keyword": "City to airport taxi estimate", "category": "route", "intent": "transactional"},
    {"keyword": "Intercity cab fare comparison", "category": "route", "intent": "commercial"},
]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def normalize_keyword(keyword: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", keyword.lower()).split())


def load_coverage_and_fares() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8")) if COVERAGE_PATH.exists() else {"regions": {}}
    fares = json.loads(FARES_PATH.read_text(encoding="utf-8")) if FARES_PATH.exists() else {"cities": {}}
    return coverage, fares


def get_supported_cities() -> Dict[str, Dict[str, Any]]:
    """Return only locations that have active geofence coverage AND provider configurations."""
    coverage, fares = load_coverage_and_fares()
    regions = coverage.get("regions", {})
    fare_cities = fares.get("cities", {})
    supported: Dict[str, Dict[str, Any]] = {}

    for city_name, reg in regions.items():
        providers = reg.get("providers") or []
        if not providers:
            continue
        city_fares = fare_cities.get(city_name, {})
        supported[city_name] = {
            "region": reg,
            "fares": city_fares,
            "slug": _slugify(city_name),
            "providers": providers,
            "quote_names": reg.get("quote_names") or list((city_fares.get("providers") or {}).keys()),
            "airport_keywords": (city_fares.get("toll") or {}).get("airportKeywords") or [],
            "airport_toll": (city_fares.get("toll") or {}).get("charge"),
            "currency": city_fares.get("currency", "INR"),
            "currency_symbol": city_fares.get("currencySymbol", "₹"),
            "regional_notice": city_fares.get("regionalNotice", ""),
            "state": city_fares.get("state", ""),
            "country": city_fares.get("country", reg.get("country_code", "")),
            "intercity": bool(reg.get("intercity", False)),
            "outstation_destinations": reg.get("outstation_destinations", []),
        }
    return supported


def classify_intent(keyword: str) -> str:
    kw = keyword.lower()
    if any(t in kw for t in ("calculator", "estimate", "booking", "book", "fare from", "to ")):
        return "transactional"
    if any(t in kw for t in ("how ", "why ", "guide", "works", "best time")):
        return "informational"
    return "commercial"


def detect_location(keyword: str, supported_cities: Dict[str, Dict[str, Any]]) -> Optional[str]:
    kw = keyword.lower()
    for city_name, info in supported_cities.items():
        aliases = [city_name.lower()] + [a.lower() for a in info["region"].get("city_aliases", [])]
        if any(re.search(rf"\b{re.escape(alias)}\b", kw) for alias in aliases if alias):
            return city_name
    for known in ("delhi", "chennai", "hyderabad", "pune"):
        if re.search(rf"\b{known}\b", kw):
            return known.title()
    return None


def compute_opportunity_score(
    *,
    impressions: int,
    clicks: int,
    avg_position: Optional[float],
    search_volume: Optional[int],
    keyword_difficulty: Optional[float],
    has_supported_location: bool,
    is_mapped: bool,
) -> float:
    """
    Compute a deterministic opportunity score (0-100) using only real available signals.
    Never invents search volumes or rankings.
    """
    score = 20.0 if has_supported_location else 5.0
    if not is_mapped:
        score += 15.0
    if impressions > 0:
        ctr = clicks / impressions
        score += min(30.0, impressions / 20.0)
        if ctr < 0.025:
            score += 15.0
    if avg_position is not None and 5.0 <= avg_position <= 25.0:
        score += 20.0
    if search_volume is not None and search_volume > 0:
        score += min(25.0, search_volume / 200.0)
    if keyword_difficulty is not None:
        score += max(0.0, (50.0 - keyword_difficulty) * 0.2)
    return round(min(100.0, score), 2)


def build_seo_metadata(
    *,
    slug: str,
    title: str,
    description: str,
    h1: str,
    page_type: str,
    breadcrumbs: List[Dict[str, str]],
    location: Optional[str] = None,
    is_indexable: bool = True,
    published_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Central SEO metadata and JSON-LD generator. Never fabricates ratings, prices, or addresses."""
    canonical_path = slug if slug.startswith("/") else f"/{slug}"
    if not canonical_path.endswith("/") and not canonical_path.startswith(("/routes/", "/blog/")):
        canonical_path = f"{canonical_path}/"
    canonical_url = f"{settings.SITE_URL}{canonical_path}"

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": idx + 1,
                "name": b["name"],
                "item": f"{settings.SITE_URL}{b['path']}",
            }
            for idx, b in enumerate(breadcrumbs)
        ],
    }

    schemas: List[Dict[str, Any]] = [
        breadcrumb_ld,
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": description,
            "url": canonical_url,
            "isPartOf": {"@type": "WebSite", "name": "RideCompare", "url": f"{settings.SITE_URL}/"},
        },
    ]

    if page_type in {"pillar", "city", "airport"}:
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "SoftwareApplication",
                "name": "RideCompare Fare Calculator",
                "applicationCategory": "TravelApplication",
                "operatingSystem": "Web",
                "url": canonical_url,
                "areaServed": location or "Supported RideCompare Cities",
            }
        )
    elif page_type == "editorial":
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": h1,
                "description": description,
                "datePublished": published_at or datetime.utcnow().strftime("%Y-%m-%d"),
                "dateModified": updated_at or datetime.utcnow().strftime("%Y-%m-%d"),
                "author": {"@type": "Organization", "name": "RideCompare"},
                "publisher": {"@type": "Organization", "name": "RideCompare", "url": f"{settings.SITE_URL}/"},
                "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
            }
        )

    return {
        "title": title,
        "meta_description": description,
        "canonical_url": canonical_url,
        "robots": "index, follow" if is_indexable else "noindex, follow",
        "og_title": title,
        "og_description": description,
        "og_image": f"{settings.SITE_URL}/logo.png",
        "twitter_card": "summary_large_image",
        "breadcrumbs": breadcrumbs,
        "structured_data": schemas,
    }


def validate_page_quality(page_data: Dict[str, Any], supported_cities: Dict[str, Dict[str, Any]]) -> Tuple[float, List[str]]:
    """Quality and policy gate: prevents thin, duplicate, or unsupported-location pages from auto-publishing."""
    issues: List[str] = []
    title = page_data.get("seo_title", "")
    desc = page_data.get("meta_description", "")
    h1 = page_data.get("h1", "")
    location = page_data.get("location")
    content = page_data.get("content", {})

    if not h1 or len(h1.strip()) < 8:
        issues.append("Missing or too short H1.")
    if len(title) < 20 or len(title) > 75:
        issues.append("SEO title length outside recommended 20-75 characters.")
    if len(desc) < 60 or len(desc) > 175:
        issues.append("Meta description length outside recommended 60-175 characters.")
    if location and location not in supported_cities:
        issues.append(f"Location '{location}' has no functional RideCompare coverage.")

    sections = content.get("sections", [])
    faqs = content.get("faqs", [])
    text_blob = " ".join([
        content.get("intro", ""),
        " ".join(s.get("body", "") for s in sections),
        " ".join(f.get("answer", "") for f in faqs),
    ]).strip()
    if len(text_blob.split()) < 75:
        issues.append("Content below minimum 75-word usefulness threshold.")

    score = max(0.0, 100.0 - len(issues) * 25.0)
    return score, issues


def _build_programmatic_page_specs(supported_cities: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = [
        {
            "page_id": "pillar-compare-cab-fares",
            "slug": "/compare-cab-fares/",
            "page_type": "pillar",
            "target_keyword": "Cab fare comparison",
            "secondary_keywords": ["Compare taxi prices", "Compare cab prices online", "Cheapest cab service"],
            "location": None,
            "search_intent": "commercial",
            "seo_title": "Compare Cab Fares Online Across Uber, Ola, Rapido & Local Taxis — RideCompare",
            "meta_description": "Compare estimated cab, auto, and bike-taxi fares across Uber, Ola, Rapido, Namma Yatri, Kerala Savari, and GoaMiles in one place.",
            "h1": "Compare Cab & Taxi Fares Online",
            "content": {
                "intro": "RideCompare calculates route-aware fare estimates using verified statutory rate cards and regional geofencing so you can compare available ride services side by side before booking.",
                "supported_services": ["Uber", "Ola", "Rapido", "Namma Yatri", "Kerala Savari", "GoaMiles", "Yatri Sathi"],
                "sections": [
                    {"heading": "How RideCompare Estimates Ride Fares", "body": "Enter your pickup and drop-off points to measure road distance and estimated travel time, then inspect base fares, per-km rates, and regulated surge caps across every active provider in your city."},
                    {"heading": "Zero Scraping & Transparent Estimates", "body": "All prices are clearly presented as estimate ranges derived from statutory rate cards and demand models, with direct deep links to open the official provider app."},
                ],
                "faqs": [
                    {"question": "Which cab service is cheapest in India?", "answer": "For solo commutes, bike taxis like Rapido Bike or Uber Moto are usually cheapest. For autos and cabs, zero-commission apps like Namma Yatri, Kerala Savari, and Yatri Sathi often undercut private aggregators during surge hours."},
                    {"question": "Does RideCompare show live prices?", "answer": "RideCompare shows transparent statutory and historical/ML estimate ranges alongside official app deep links so you can confirm the final live fare directly in the provider app."},
                ],
                "cta_label": "Compare Live Route Estimates",
            },
        },
        {
            "page_id": "pillar-taxi-fare-calculator",
            "slug": "/taxi-fare-calculator/",
            "page_type": "pillar",
            "target_keyword": "Taxi fare calculator",
            "secondary_keywords": ["Online taxi fare estimate", "Cab fare estimator", "Auto fare calculator"],
            "location": None,
            "search_intent": "transactional",
            "seo_title": "Taxi Fare Calculator — Estimate Cab, Auto & Bike Ride Costs | RideCompare",
            "meta_description": "Use RideCompare's route-aware taxi fare calculator to estimate cab, auto-rickshaw, and bike-taxi costs using statutory per-km rate cards.",
            "h1": "Online Taxi Fare Calculator",
            "content": {
                "intro": "Calculate estimated taxi, auto-rickshaw, and bike-taxi fares for any supported city route using road routing and regional transport tariffs.",
                "supported_services": ["Uber", "Ola", "Rapido", "Namma Yatri", "Kerala Savari", "GoaMiles"],
                "sections": [
                    {"heading": "What Goes Into a Fare Estimate", "body": "Each calculation accounts for base fare, per-kilometre rate, ride duration, airport toll rules, and time-of-day peak multipliers capped by local transport rules."},
                    {"heading": "Supported Regions & Metered Fallbacks", "body": "Where app aggregators do not operate, RideCompare checks whether government metered autos or local taxis serve the area and displays regulated minimum meter estimates."},
                ],
                "faqs": [
                    {"question": "How accurate is the taxi fare calculator?", "answer": "Estimates are grounded in published city rate cards and road distance via OSRM routing. Final fares in provider apps can differ due to live driver availability, traffic detours, and tolls."},
                ],
                "cta_label": "Calculate Your Route Fare",
            },
        },
        {
            "page_id": "comparison-uber-vs-ola",
            "slug": "/uber-vs-ola/",
            "page_type": "comparison",
            "target_keyword": "Uber vs Ola",
            "secondary_keywords": ["Uber fare comparison", "Uber Go vs Ola Mini", "Ola or Uber cheaper"],
            "location": None,
            "search_intent": "commercial",
            "seo_title": "Uber vs Ola Fare Comparison — Which Cab App Is Cheaper? | RideCompare",
            "meta_description": "Compare Uber Go vs Ola Mini base fares, per-km rates, airport fees, and surge pricing across Indian cities before you book.",
            "h1": "Uber vs Ola: Price & Rate Card Comparison",
            "content": {
                "intro": "Both Uber and Ola use dynamic pricing, so neither app is cheapest on every trip. Comparing base tariffs, per-km rates, and peak multipliers helps you avoid overpaying.",
                "supported_services": ["Uber Go", "Uber Premier", "Ola Mini", "Ola Prime"],
                "sections": [
                    {"heading": "Base Fare & Per-Kilometre Differences", "body": "In major Indian cities like Bangalore, Kochi, and Mumbai, Uber Go and Ola Mini base fares sit within a few rupees of each other, making surge multipliers and airport pickup fees the deciding factor."},
                    {"heading": "When to Check Alternatives", "body": "During heavy rain or 6 PM office rush, checking Namma Yatri, Kerala Savari, or Yatri Sathi alongside Uber and Ola frequently reveals lower zero-surge fares."},
                ],
                "faqs": [
                    {"question": "Is Uber cheaper than Ola for airport rides?", "answer": "During off-peak hours they are usually close in price, though whichever app has fewer waiting drivers at the airport bay will apply higher surge."},
                ],
                "cta_label": "Compare Uber & Ola for Your Route",
            },
        },
        {
            "page_id": "comparison-uber-vs-rapido",
            "slug": "/uber-vs-rapido/",
            "page_type": "comparison",
            "target_keyword": "Uber vs Rapido",
            "secondary_keywords": ["Ola vs Rapido", "Compare Uber Ola Rapido prices", "Rapido Bike vs Uber Moto"],
            "location": None,
            "search_intent": "commercial",
            "seo_title": "Uber vs Rapido (and Ola) — Bike, Auto & Cab Fare Comparison | RideCompare",
            "meta_description": "Compare Uber Moto, Uber Auto, and Uber Go against Rapido Bike, Rapido Auto, and Ola across supported Indian cities.",
            "h1": "Uber vs Rapido: Bike, Auto & Cab Comparison",
            "content": {
                "intro": "Rapido specializes in fast, low-cost bike taxis and autos, while Uber covers bikes, autos, and AC cabs. Compare both before choosing your commute mode.",
                "supported_services": ["Rapido Bike", "Rapido Auto", "Uber Moto", "Uber Auto", "Uber Go"],
                "sections": [
                    {"heading": "Solo Commutes: Bike Taxis", "body": "For short 3–12 km city rides without luggage, Rapido Bike and Uber Moto typically cost less than half of an AC hatchback cab and cut through peak congestion."},
                    {"heading": "Autos & Cabs for Longer Trips", "body": "When travelling with luggage, in rain, or to airports, compare Uber Go, Ola Mini, and state-backed options like Kerala Savari or Namma Yatri."},
                ],
                "faqs": [
                    {"question": "Is Rapido cheaper than Uber?", "answer": "For solo riders on bike taxis or short auto trips, Rapido is often the lowest-cost option, though Uber Moto frequently matches its per-km tariff."},
                ],
                "cta_label": "Compare Uber, Ola & Rapido",
            },
        },
    ]

    for city_name, info in supported_cities.items():
        city_slug = info["slug"]
        providers_list = info["providers"]
        quote_names = info["quote_names"]
        fare_providers = info["fares"].get("providers", {})
        sample_rates = []
        for qn in quote_names[:4]:
            p_cfg = fare_providers.get(qn)
            if p_cfg:
                sym = info["currency_symbol"]
                sample_rates.append(
                    f"{qn}: base {sym}{p_cfg.get('baseFare')} + {sym}{p_cfg.get('perKmRate')}/km ({p_cfg.get('vehicleType', 'Cab')})"
                )

        specs.append(
            {
                "page_id": f"city-{city_slug}",
                "slug": f"/cab-fare/{city_slug}/",
                "page_type": "city",
                "target_keyword": f"Taxi fare in {city_name}",
                "secondary_keywords": [
                    f"Cab fare in {city_name}",
                    f"Cab booking in {city_name}",
                    f"Compare taxi prices in {city_name}",
                ],
                "location": city_name,
                "search_intent": "commercial",
                "seo_title": f"Taxi & Cab Fare in {city_name} — Compare {', '.join(providers_list[:3])} | RideCompare",
                "meta_description": f"Compare estimated taxi, auto, and cab fares in {city_name} across {', '.join(providers_list)}. Check statutory rate cards and route estimates.",
                "h1": f"Taxi & Cab Fare Comparison in {city_name}",
                "content": {
                    "intro": f"RideCompare supports {city_name} ({info['state'] or info['country']}) with verified regional geofencing and rate cards for {', '.join(providers_list)}.",
                    "supported_services": quote_names,
                    "rate_card_highlights": sample_rates,
                    "sections": [
                        {
                            "heading": f"Active Ride Services in {city_name}",
                            "body": f"Available ride options in {city_name} include {', '.join(quote_names)}. {info['regional_notice'] or 'Enter your pickup and destination above to compare estimated ranges sorted cheapest first.'}",
                        },
                        {
                            "heading": f"Local Pricing & Intercity Rules in {city_name}",
                            "body": (
                                f"Intra-city estimates use {city_name}'s statutory base and per-km rate cards. "
                                + (
                                    f"Outstation coverage also supports popular destinations such as {', '.join(info['outstation_destinations'][:5]).title()}."
                                    if info["intercity"] and info["outstation_destinations"]
                                    else "Standard city-ride tariffs apply within the supported local geofence."
                                )
                            ),
                        },
                    ],
                    "faqs": [
                        {
                            "question": f"Which taxi apps operate in {city_name}?",
                            "answer": f"RideCompare currently tracks {', '.join(providers_list)} in {city_name}, covering {', '.join(quote_names[:5])}.",
                        },
                        {
                            "question": f"How can I estimate a cab fare in {city_name}?",
                            "answer": f"Use the RideCompare search panel to select your {city_name} pickup and drop locations and compare estimated ranges sorted from cheapest to fastest.",
                        },
                    ],
                    "cta_label": f"Compare {city_name} Ride Fares",
                },
            }
        )

        if info["airport_keywords"]:
            toll_note = (
                f"Configured airport access/toll surcharge in rate cards: {info['currency_symbol']}{info['airport_toll']}."
                if info["airport_toll"]
                else "Check provider app details for any applicable airport entry or parking fees."
            )
            specs.append(
                {
                    "page_id": f"airport-{city_slug}",
                    "slug": f"/airport-taxi-fare/{city_slug}/",
                    "page_type": "airport",
                    "target_keyword": f"{city_name} airport taxi fare",
                    "secondary_keywords": [
                        f"Airport to city cab fare {city_name}",
                        f"{city_name} airport cab estimate",
                    ],
                    "location": city_name,
                    "search_intent": "transactional",
                    "seo_title": f"{city_name} Airport Taxi Fare — Compare {', '.join(providers_list[:3])} | RideCompare",
                    "meta_description": f"Estimate {city_name} airport to city taxi and cab fares across {', '.join(providers_list)}. Includes airport toll rules and rate-card comparisons.",
                    "h1": f"{city_name} Airport Taxi & Cab Fare Guide",
                    "content": {
                        "intro": f"Compare airport transfer estimates to and from {city_name} airports ({', '.join(info['airport_keywords'][:4])}) across {', '.join(providers_list)}.",
                        "supported_services": quote_names,
                        "rate_card_highlights": sample_rates,
                        "sections": [
                            {
                                "heading": f"Airport Pickup Options in {city_name}",
                                "body": f"Travellers arriving in {city_name} can compare {', '.join(quote_names[:5])} in RideCompare. {toll_note}",
                            },
                            {
                                "heading": "Tips to Avoid Airport Surge",
                                "body": "Flight bank arrivals often trigger temporary demand spikes on private aggregator apps. Compare government-backed or zero-surge services where available before confirming.",
                            },
                        ],
                        "faqs": [
                            {
                                "question": f"How much is a taxi from {city_name} Airport?",
                                "answer": f"Fares depend on drop-off distance and vehicle class. Enter your exact destination in RideCompare to see estimated ranges across {', '.join(providers_list)}.",
                            }
                        ],
                        "cta_label": f"Estimate {city_name} Airport Fare",
                    },
                }
            )

    return specs


def sync_catalog_to_seo(db: Session) -> Dict[str, Any]:
    """
    Auto-discover supported cities/services/routes, seed keywords, generate & validate pages,
    and map keywords to canonical pages.
    """
    supported_cities = get_supported_cities()
    specs = _build_programmatic_page_specs(supported_cities)

    # Also register existing curated route & blog pages from seoContent.json into SeoPage
    if SEO_CONTENT_PATH.exists():
        raw_content = json.loads(SEO_CONTENT_PATH.read_text(encoding="utf-8"))
        for r in raw_content.get("routes", []):
            specs.append(
                {
                    "page_id": f"route-{r['slug']}",
                    "slug": f"/routes/{r['slug']}",
                    "page_type": "route",
                    "target_keyword": r["h1"],
                    "secondary_keywords": [f"{r['origin']} to {r['destination']} cab"],
                    "location": r.get("region"),
                    "search_intent": "transactional",
                    "seo_title": r["title"][:250],
                    "meta_description": r["metaDescription"],
                    "h1": r["h1"],
                    "content": {
                        "intro": r["summary"],
                        "sections": [{"heading": "Route Notes", "body": r.get("routeNotes", "")}],
                        "faqs": r.get("faqs", []),
                        "distance_km": r.get("distanceKm"),
                        "duration_mins": r.get("durationMins"),
                        "cheapest_service": r.get("cheapestService"),
                    },
                }
            )
        for p in raw_content.get("posts", []):
            specs.append(
                {
                    "page_id": f"blog-{p['slug']}",
                    "slug": f"/blog/{p['slug']}",
                    "page_type": "editorial",
                    "target_keyword": p["title"],
                    "secondary_keywords": [p.get("category", "Travel Guide")],
                    "location": None,
                    "search_intent": "informational",
                    "seo_title": f"{p['title']} — RideCompare"[:250],
                    "meta_description": p["metaDescription"],
                    "h1": p["title"],
                    "content": {
                        "intro": p["excerpt"],
                        "sections": [
                            {"heading": s["heading"], "body": " ".join(s.get("paragraphs", []))}
                            for s in p.get("sections", [])
                        ],
                        "faqs": [],
                    },
                }
            )

    created_pages = 0
    updated_pages = 0
    rejected_pages = 0

    for spec in specs:
        slug = spec["slug"]
        breadcrumbs = [{"name": "Home", "path": "/"}]
        if spec["page_type"] == "city":
            breadcrumbs.append({"name": "Cab Fares", "path": "/compare-cab-fares/"})
        elif spec["page_type"] == "airport":
            breadcrumbs.append({"name": "Airport Taxi Fares", "path": "/taxi-fare-calculator/"})
        elif spec["page_type"] == "route":
            breadcrumbs.append({"name": "Route Fares", "path": "/routes"})
        elif spec["page_type"] == "editorial":
            breadcrumbs.append({"name": "Guides & Blog", "path": "/blog"})
        breadcrumbs.append({"name": spec["h1"], "path": slug})

        # For curated route/blog pages, location may be state name ("Kerala", "Karnataka"); skip strict city-name fail for those
        validation_cities = supported_cities if spec["page_type"] in {"city", "airport"} else {
            **supported_cities,
            **(
                {spec["location"]: {}}
                if spec.get("location")
                else {}
            ),
        }
        quality_score, issues = validate_page_quality(spec, validation_cities)
        is_indexable = len(issues) == 0
        status_val = "published" if is_indexable else "draft"
        if not is_indexable:
            rejected_pages += 1

        meta = build_seo_metadata(
            slug=slug,
            title=spec["seo_title"],
            description=spec["meta_description"],
            h1=spec["h1"],
            page_type=spec["page_type"],
            breadcrumbs=breadcrumbs,
            location=spec.get("location"),
            is_indexable=is_indexable,
        )
        content_payload = {**spec["content"], "metadata": meta}

        existing = db.query(SeoPage).filter(SeoPage.page_id == spec["page_id"]).first()
        if existing:
            existing.slug = slug
            existing.target_keyword = spec["target_keyword"]
            existing.secondary_keywords = json.dumps(spec.get("secondary_keywords", []))
            existing.location = spec.get("location")
            existing.search_intent = spec["search_intent"]
            existing.seo_title = spec["seo_title"]
            existing.meta_description = spec["meta_description"]
            existing.h1 = spec["h1"]
            existing.content_json = json.dumps(content_payload)
            existing.quality_score = quality_score
            existing.quality_issues = json.dumps(issues)
            existing.canonical_url = meta["canonical_url"]
            existing.is_indexable = is_indexable
            existing.last_audited_at = datetime.utcnow()
            updated_pages += 1
        else:
            db.add(
                SeoPage(
                    page_id=spec["page_id"],
                    slug=slug,
                    page_type=spec["page_type"],
                    target_keyword=spec["target_keyword"],
                    secondary_keywords=json.dumps(spec.get("secondary_keywords", [])),
                    location=spec.get("location"),
                    search_intent=spec["search_intent"],
                    seo_title=spec["seo_title"],
                    meta_description=spec["meta_description"],
                    h1=spec["h1"],
                    content_json=json.dumps(content_payload),
                    status=status_val,
                    quality_score=quality_score,
                    quality_issues=json.dumps(issues),
                    canonical_url=meta["canonical_url"],
                    is_indexable=is_indexable,
                    last_audited_at=datetime.utcnow(),
                )
            )
            created_pages += 1

    db.commit()

    # Seed & map keywords
    all_pages = db.query(SeoPage).filter(SeoPage.status == "published").all()
    seed_list = list(SEED_KEYWORDS)
    for city_name in supported_cities:
        seed_list.append({"keyword": f"Taxi fare in {city_name}", "category": "local", "intent": "commercial", "location": city_name})
        seed_list.append({"keyword": f"{city_name} airport taxi fare", "category": "route", "intent": "transactional", "location": city_name})

    seeded_kw = 0
    for item in seed_list:
        kw_text = item["keyword"]
        norm = normalize_keyword(kw_text)
        loc = item.get("location") or detect_location(kw_text, supported_cities)
        mapped_slug = _map_keyword_to_page(kw_text, loc, all_pages)
        has_supported = loc is None or loc in supported_cities
        opp = compute_opportunity_score(
            impressions=0,
            clicks=0,
            avg_position=None,
            search_volume=None,
            keyword_difficulty=None,
            has_supported_location=has_supported,
            is_mapped=mapped_slug is not None,
        )
        existing_kw = db.query(SeoKeyword).filter(SeoKeyword.normalized_keyword == norm).first()
        if not existing_kw:
            db.add(
                SeoKeyword(
                    keyword=kw_text,
                    normalized_keyword=norm,
                    category=item["category"],
                    intent=item["intent"],
                    location=loc,
                    mapped_page_slug=mapped_slug,
                    opportunity_score=opp,
                    data_source="seed",
                )
            )
            seeded_kw += 1
        else:
            existing_kw.mapped_page_slug = mapped_slug or existing_kw.mapped_page_slug
            existing_kw.opportunity_score = compute_opportunity_score(
                impressions=existing_kw.impressions,
                clicks=existing_kw.clicks,
                avg_position=existing_kw.avg_position,
                search_volume=existing_kw.search_volume,
                keyword_difficulty=existing_kw.keyword_difficulty,
                has_supported_location=has_supported,
                is_mapped=existing_kw.mapped_page_slug is not None,
            )

    db.commit()
    return {
        "supported_cities": list(supported_cities.keys()),
        "pages_created": created_pages,
        "pages_updated": updated_pages,
        "pages_flagged": rejected_pages,
        "keywords_seeded": seeded_kw,
    }


def _map_keyword_to_page(keyword: str, location: Optional[str], pages: List[SeoPage]) -> Optional[str]:
    norm_kw = normalize_keyword(keyword)
    if "uber vs ola" in norm_kw:
        return "/uber-vs-ola/"
    if "uber vs rapido" in norm_kw or "ola vs rapido" in norm_kw or "uber ola rapido" in norm_kw:
        return "/uber-vs-rapido/"
    if "calculator" in norm_kw or "estimate" in norm_kw and not location:
        return "/taxi-fare-calculator/"
    if "airport" in norm_kw and location:
        for p in pages:
            if p.page_type == "airport" and p.location == location:
                return p.slug
    if location:
        for p in pages:
            if p.page_type == "city" and p.location == location:
                return p.slug
    for p in pages:
        if normalize_keyword(p.target_keyword) == norm_kw:
            return p.slug
    if any(w in norm_kw for w in ("compare", "cheapest", "cab fare", "taxi price")):
        return "/compare-cab-fares/"
    return None


def import_keywords_csv(db: Session, csv_text: str, source: str = "csv_import") -> Dict[str, Any]:
    """Import keyword research or Search Console CSV without fabricating missing metrics."""
    supported_cities = get_supported_cities()
    all_pages = db.query(SeoPage).filter(SeoPage.status == "published").all()
    reader = csv.DictReader(io.StringIO(csv_text.strip()))

    imported = 0
    duplicates = 0
    for row in reader:
        lowered = {str(k).strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        kw = lowered.get("keyword") or lowered.get("query") or lowered.get("top queries")
        if not kw:
            continue
        norm = normalize_keyword(kw)
        loc = detect_location(kw, supported_cities)
        intent = classify_intent(kw)
        category = "local" if loc else ("competitor" if any(c in norm for c in ("uber", "ola", "rapido")) else ("route" if "airport" in norm or "intercity" in norm else "general"))

        def _opt_int(val: Any) -> Optional[int]:
            try:
                return int(float(str(val).replace(",", ""))) if val not in (None, "") else None
            except ValueError:
                return None

        def _opt_float(val: Any) -> Optional[float]:
            try:
                return float(str(val).replace("%", "").replace(",", "")) if val not in (None, "") else None
            except ValueError:
                return None

        vol = _opt_int(lowered.get("search_volume") or lowered.get("volume"))
        kd = _opt_float(lowered.get("keyword_difficulty") or lowered.get("kd"))
        impr = _opt_int(lowered.get("impressions")) or 0
        clicks = _opt_int(lowered.get("clicks")) or 0
        pos = _opt_float(lowered.get("position") or lowered.get("avg_position"))
        ctr = round(clicks / impr, 4) if impr > 0 else (_opt_float(lowered.get("ctr")) or 0.0)
        mapped = _map_keyword_to_page(kw, loc, all_pages)
        has_supported = loc is None or loc in supported_cities
        opp = compute_opportunity_score(
            impressions=impr,
            clicks=clicks,
            avg_position=pos,
            search_volume=vol,
            keyword_difficulty=kd,
            has_supported_location=has_supported,
            is_mapped=mapped is not None,
        )

        existing = db.query(SeoKeyword).filter(SeoKeyword.normalized_keyword == norm).first()
        if existing:
            duplicates += 1
            if vol is not None:
                existing.search_volume = vol
            if kd is not None:
                existing.keyword_difficulty = kd
            if impr > 0:
                existing.impressions = impr
                existing.clicks = clicks
                existing.ctr = ctr
            if pos is not None:
                existing.avg_position = pos
            existing.mapped_page_slug = mapped or existing.mapped_page_slug
            existing.opportunity_score = opp
            existing.data_source = source
        else:
            db.add(
                SeoKeyword(
                    keyword=kw,
                    normalized_keyword=norm,
                    category=category,
                    intent=intent,
                    location=loc,
                    search_volume=vol,
                    keyword_difficulty=kd,
                    impressions=impr,
                    clicks=clicks,
                    ctr=ctr,
                    avg_position=pos,
                    mapped_page_slug=mapped,
                    opportunity_score=opp,
                    data_source=source,
                )
            )
            imported += 1

    db.commit()
    return {"imported": imported, "updated_duplicates": duplicates}


def generate_sitemap_xml(db: Session) -> str:
    """Generate dynamic XML sitemap from published, canonical, indexable SeoPage entries."""
    pages = (
        db.query(SeoPage)
        .filter(SeoPage.status == "published", SeoPage.is_indexable.is_(True))
        .order_by(SeoPage.slug.asc())
        .all()
    )
    seen: set[str] = set()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    entries = [
        {"loc": f"{settings.SITE_URL}/", "lastmod": today, "changefreq": "daily", "priority": "1.0"},
        {"loc": f"{settings.SITE_URL}/routes", "lastmod": today, "changefreq": "weekly", "priority": "0.9"},
        {"loc": f"{settings.SITE_URL}/blog", "lastmod": today, "changefreq": "weekly", "priority": "0.9"},
    ]
    seen.update(e["loc"] for e in entries)

    for page in pages:
        loc = page.canonical_url.split("?")[0]
        if loc in seen:
            continue
        seen.add(loc)
        lastmod = (page.last_updated or datetime.utcnow()).strftime("%Y-%m-%d")
        priority = "0.9" if page.page_type == "pillar" else ("0.85" if page.page_type in {"city", "airport", "comparison"} else "0.8")
        entries.append(
            {
                "loc": loc,
                "lastmod": lastmod,
                "changefreq": "weekly",
                "priority": priority,
            }
        )

    url_blocks = "\n".join(
        f"  <url>\n    <loc>{e['loc']}</loc>\n    <lastmod>{e['lastmod']}</lastmod>\n"
        f"    <changefreq>{e['changefreq']}</changefreq>\n    <priority>{e['priority']}</priority>\n  </url>"
        for e in entries
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{url_blocks}\n</urlset>\n'


def run_maintenance(db: Session, cadence: str = "daily") -> Dict[str, Any]:
    """Run scheduled daily, weekly, or monthly SEO maintenance and log recommendations."""
    recommendations: List[Dict[str, str]] = []
    sync_result: Dict[str, Any] = {}

    if cadence in {"monthly", "manual"}:
        sync_result = sync_catalog_to_seo(db)
    elif db.query(SeoPage).count() == 0:
        sync_result = sync_catalog_to_seo(db)

    pages = db.query(SeoPage).all()
    published = [p for p in pages if p.status == "published" and p.is_indexable]
    flagged = [p for p in pages if p.quality_score < 100.0]

    for p in flagged:
        recommendations.append({
            "type": "quality_warning",
            "page": p.slug,
            "message": f"Quality score {p.quality_score}: {p.quality_issues}",
        })

    if cadence in {"weekly", "monthly", "manual"}:
        stale_cutoff = datetime.utcnow() - timedelta(days=90)
        for p in published:
            if p.last_updated and p.last_updated < stale_cutoff:
                recommendations.append({
                    "type": "outdated_content",
                    "page": p.slug,
                    "message": "Page has not been refreshed in over 90 days; review rate cards and local notes.",
                })
            if p.impressions >= 50 and p.ctr < 0.02:
                recommendations.append({
                    "type": "low_ctr",
                    "page": p.slug,
                    "message": f"High impressions ({p.impressions}) with low CTR ({p.ctr:.2%}); consider sharpening title/description.",
                })

        unmapped_kws = (
            db.query(SeoKeyword)
            .filter(SeoKeyword.mapped_page_slug.is_(None))
            .order_by(SeoKeyword.opportunity_score.desc())
            .limit(10)
            .all()
        )
        for kw in unmapped_kws:
            recommendations.append({
                "type": "keyword_opportunity",
                "page": kw.location or "general",
                "message": f"Unmapped keyword '{kw.keyword}' (score {kw.opportunity_score}) — verify if RideCompare supports this location/topic before creating a page.",
            })

    summary = (
        f"[{cadence.upper()}] Audited {len(pages)} SEO pages ({len(published)} published/indexable, "
        f"{len(flagged)} quality-flagged), {len(recommendations)} recommendations."
    )
    log = SeoAuditLog(
        run_type=cadence,
        status="warning" if flagged else "ok",
        summary=summary,
        recommendations_json=json.dumps(recommendations),
    )
    db.add(log)
    db.commit()
    return {
        "cadence": cadence,
        "summary": summary,
        "sync": sync_result,
        "recommendations": recommendations,
    }
